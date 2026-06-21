import json
import logging
import csv
import io
import os
import random
import uuid
import zipfile
import urllib.request
import cloudinary.uploader
from django.conf import settings as django_settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.db import DataError, transaction, models
from datetime import timedelta
from django.core.paginator import Paginator

from core.decorators import teacher_required
from apps.administation.utils import csv_filename, csv_query_context, get_bool_setting, log_activity
from apps.classrooms.views import _is_classroom_teacher, _is_classroom_member
from apps.classrooms.models import ClassroomMembers
from apps.assignments.models import Assignments, Testcases, Rubrics, QuizSettings, QuizQuestions, QuizChoices
from apps.assignments.models import AssignmentFiles, AssignmentFileRequirements
from apps.administation.models import ProgrammingLanguages, SandboxConfigs
from apps.notifications.services import notify_user
from services.docker_service import execute_code, run_testcase
from .models import (
    Submissions, SubmissionDetails, SubmissionFiles, SubmissionFileFeedbacks,
    CodeDrafts, CodeComments, RubricScores, FeedbackTemplates, ExamSessions, ExamEvents,
    QuizAttempts, QuizAnswers, GradeChangeLogs,
)
from .forms import GradeSubmissionForm, CodeCommentForm, FeedbackTemplateForm
from .utils import (
    assignment_open_error, can_solve_assignment, validate_submission_language,
    update_assignment_statistics, file_checksum, sanitize_upload_filename,
    upload_to_configured_storage, validate_uploaded_files,
)

logger = logging.getLogger(__name__)


EXAM_WARNING_EVENTS = {
    'tab_hidden', 'focus_lost', 'fullscreen_exit', 'paste',
    'copy', 'context_menu', 'devtools_hint',
}

EXAM_MONITOR_FILTER_STATUSES = {
    ExamSessions.STATUS_RUNNING,
    ExamSessions.STATUS_SUBMITTED,
    ExamSessions.STATUS_AUTO_SUBMITTED,
    ExamSessions.STATUS_EXPIRED,
    ExamSessions.STATUS_CANCELLED,
}

JSON_OUTPUT_LIMIT = 10000
JSON_ERROR_LIMIT = 4000
FEEDBACK_FILE_MAX_MB = 25
FEEDBACK_FILE_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.md',
    '.png', '.jpg', '.jpeg', '.zip',
}


def _submission_attempt_context(assignment, user):
    submission_count = Submissions.objects.filter(
        assignment=assignment,
        student=user,
    ).count()
    remaining_attempts = None
    if assignment.max_attempts:
        remaining_attempts = max(0, assignment.max_attempts - submission_count)
    return submission_count, remaining_attempts


def _sanitize_text_for_db(value):
    """Strip NUL chars that PostgreSQL text columns cannot store."""
    if isinstance(value, str):
        return value.replace('\x00', '')
    return value


def _safe_json_text(value, limit=JSON_OUTPUT_LIMIT):
    value = _sanitize_text_for_db(value or '')
    if not isinstance(value, str):
        value = str(value)
    if len(value) <= limit:
        return value
    return value[:limit] + '\n...[đã rút gọn]'


def _safe_zip_name(value, fallback='file'):
    value = os.path.basename(value or '').strip()
    if not value:
        value = fallback
    return ''.join(ch if ch.isalnum() or ch in '._- ' else '_' for ch in value)[:160]


def _upload_feedback_file(submission, uploaded_file, teacher, note=''):
    errors = validate_uploaded_files(
        [uploaded_file],
        allowed_extensions=FEEDBACK_FILE_EXTENSIONS,
        max_file_size_mb=FEEDBACK_FILE_MAX_MB,
        max_files=1,
        label='file phản hồi',
    )
    if errors:
        return None, errors[0]
    safe_name = sanitize_upload_filename(uploaded_file.name, fallback='feedback')
    result = upload_to_configured_storage(
        uploaded_file,
        folder='submission_feedback/',
        user=teacher,
        safe_name=safe_name,
        prefix='submission-feedback',
    )
    feedback = SubmissionFileFeedbacks.objects.create(
        submission=submission,
        uploaded_by=teacher,
        file_name=safe_name,
        file_url=result.get('url', ''),
        file_size=uploaded_file.size,
        mime_type=uploaded_file.content_type or '',
        note=note or '',
    )
    return feedback, ''


def _create_grade_change_log(submission, teacher, before, reason='', metadata=None):
    return GradeChangeLogs.objects.create(
        submission=submission,
        changed_by=teacher,
        previous_manual_score=before.get('manual_score'),
        new_manual_score=submission.manual_score,
        previous_total_score=before.get('total_score'),
        new_total_score=submission.total_score,
        previous_status=before.get('status'),
        new_status=submission.status,
        previous_comment=before.get('teacher_comment'),
        new_comment=submission.teacher_comment,
        reason=reason,
        metadata=metadata or {},
    )


def _file_checksum(uploaded_file):
    return file_checksum(uploaded_file)


def _validate_submission_files(uploaded_files, requirements):
    errors = []
    if not requirements:
        errors.append('Bài nộp file chưa được giáo viên cấu hình yêu cầu.')
        return errors
    max_files = requirements.max_files or 1
    return validate_uploaded_files(
        uploaded_files,
        allowed_extensions=requirements.allowed_extensions,
        allowed_mime_types=requirements.allowed_mime_types,
        max_file_size_mb=requirements.max_file_size_mb or 20,
        max_files=max_files,
        require_all_files_before_submit=requirements.require_all_files_before_submit,
        label='bài nộp',
    )


def _quiz_settings_for(assignment):
    settings_obj = QuizSettings.objects.filter(assignment=assignment).first()
    if settings_obj:
        return settings_obj
    return QuizSettings.objects.create(assignment=assignment)


def _quiz_active_questions(assignment):
    return QuizQuestions.objects.filter(
        assignment=assignment,
        is_active=True,
    ).prefetch_related('choices').order_by('order_index', 'id')


def _quiz_attempt_count(assignment, user):
    return QuizAttempts.objects.filter(
        assignment=assignment,
        student=user,
    ).exclude(status=QuizAttempts.STATUS_CANCELLED).count()


def _quiz_remaining_attempts(assignment, user):
    if not assignment.max_attempts:
        return None
    return max(0, assignment.max_attempts - _quiz_attempt_count(assignment, user))


def _build_quiz_attempt_metadata(assignment, settings_obj, seed):
    questions = list(_quiz_active_questions(assignment))
    rng = random.Random(seed)
    question_ids = [question.pk for question in questions]
    if settings_obj.question_order_mode == QuizSettings.ORDER_RANDOM:
        rng.shuffle(question_ids)

    choice_order = {}
    for question in questions:
        choices = list(question.choices.all().order_by('order_index', 'id'))
        choice_ids = [choice.pk for choice in choices]
        if settings_obj.choice_order_mode == QuizSettings.ORDER_RANDOM:
            rng.shuffle(choice_ids)
        choice_order[str(question.pk)] = choice_ids

    return {
        'question_order': question_ids,
        'choice_order': choice_order,
        'settings_snapshot': {
            'question_order_mode': settings_obj.question_order_mode,
            'choice_order_mode': settings_obj.choice_order_mode,
            'show_score_after_submit': settings_obj.show_score_after_submit,
            'show_correct_answers': settings_obj.show_correct_answers,
            'show_explanation': settings_obj.show_explanation,
            'time_limit_minutes': settings_obj.time_limit_minutes,
            'passing_score': settings_obj.passing_score,
            'allow_review': settings_obj.allow_review,
        },
    }


def _quiz_questions_for_attempt(attempt):
    metadata = attempt.metadata or {}
    ordered_ids = metadata.get('question_order') or []
    questions_by_id = _quiz_active_questions(attempt.assignment).in_bulk(ordered_ids)
    fallback_questions = [q for q in _quiz_active_questions(attempt.assignment) if q.pk not in questions_by_id]
    questions = [questions_by_id[qid] for qid in ordered_ids if qid in questions_by_id] + fallback_questions

    answers = {
        answer.question_id: answer
        for answer in attempt.answers.select_related('question').prefetch_related('selected_choices')
    }
    choice_order = metadata.get('choice_order') or {}
    for question in questions:
        choices = list(question.choices.all().order_by('order_index', 'id'))
        ordered_choice_ids = choice_order.get(str(question.pk)) or [choice.pk for choice in choices]
        choices_by_id = {choice.pk: choice for choice in choices}
        ordered_choices = [choices_by_id[choice_id] for choice_id in ordered_choice_ids if choice_id in choices_by_id]
        ordered_choices += [choice for choice in choices if choice.pk not in ordered_choice_ids]
        answer = answers.get(question.pk)
        question.ordered_choices = ordered_choices
        question.answer = answer
        question.answer_state = {
            'selected_choice_ids': [int(choice_id) for choice_id in (answer.selected_choice_ids or [])] if answer else [],
            'text_answer': answer.text_answer if answer else '',
            'score_awarded': answer.score_awarded if answer else 0,
            'is_correct': answer.is_correct if answer else None,
            'answered': bool(answer and ((answer.selected_choice_ids or []) or (answer.text_answer or '').strip())),
        }
    return questions


def _selected_choice_ids_from_values(values):
    cleaned = []
    for value in values:
        try:
            value_int = int(value)
        except (TypeError, ValueError):
            continue
        if value_int not in cleaned:
            cleaned.append(value_int)
    return cleaned


def _save_quiz_answer(attempt, question, selected_choice_ids=None, text_answer=''):
    selected_choice_ids = selected_choice_ids or []
    valid_choice_ids = set(
        QuizChoices.objects.filter(question=question, pk__in=selected_choice_ids)
        .values_list('pk', flat=True)
    )
    selected_choice_ids = [choice_id for choice_id in selected_choice_ids if choice_id in valid_choice_ids]
    answer, _ = QuizAnswers.objects.update_or_create(
        attempt=attempt,
        question=question,
        defaults={
            'selected_choice_ids': selected_choice_ids,
            'text_answer': (text_answer or '').strip(),
            'answered_at': timezone.now(),
        },
    )
    answer.selected_choices.set(QuizChoices.objects.filter(pk__in=selected_choice_ids, question=question))
    return answer


def _quiz_attempt_time_remaining(attempt, settings_obj, now=None):
    if attempt.exam_session_id and attempt.exam_session and attempt.exam_session.ends_at:
        now = now or timezone.now()
        return max(0, int((attempt.exam_session.ends_at - now).total_seconds()))
    if not settings_obj.time_limit_minutes or not attempt.started_at:
        return None
    now = now or timezone.now()
    deadline = attempt.started_at + timedelta(minutes=settings_obj.time_limit_minutes)
    return max(0, int((deadline - now).total_seconds()))


def _quiz_attempt_exam_session(attempt):
    if not attempt.exam_session_id:
        return None
    if getattr(attempt, 'exam_session', None):
        return attempt.exam_session
    return ExamSessions.objects.filter(pk=attempt.exam_session_id).first()


def _notify_teacher_quiz_exam_alert(attempt, submission, reason, metadata=None):
    assignment = attempt.assignment
    teacher = assignment.classroom.teacher if assignment and assignment.classroom_id else None
    if not teacher or teacher_id_equals_student(teacher, attempt.student):
        return None
    return notify_user(
        teacher,
        title=f'Quiz exam tự động nộp: {assignment.title}',
        message=f'{attempt.student.get_full_name() or attempt.student.username} có phiên quiz exam kết thúc bởi hệ thống.',
        link=f'/submissions/detail/{submission.pk}/' if submission else f'/assignments/{assignment.pk}/quiz/attempts/',
        notification_type='exam_auto_submitted',
        actor=attempt.student,
        metadata={
            'assignment_id': assignment.pk,
            'attempt_id': attempt.pk,
            'submission_id': submission.pk if submission else None,
            'exam_session_id': attempt.exam_session_id,
            'reason': reason,
            'submission_mode': 'quiz',
            **(metadata or {}),
        },
    )


def teacher_id_equals_student(teacher, student):
    return bool(teacher and student and teacher.pk == student.pk)


def _finalize_quiz_exam_session(attempt, submission, session_status, event_type, metadata=None):
    session = _quiz_attempt_exam_session(attempt)
    if not session:
        return None
    now = timezone.now()
    answered_count = 0
    for answer in attempt.answers.all():
        if (answer.selected_choice_ids or []) or (answer.text_answer or '').strip():
            answered_count += 1
    session.final_submission = submission
    session.status = session_status
    session.submitted_at = now
    session.last_seen_at = now
    session.metadata = {
        **(session.metadata or {}),
        'submission_mode': 'quiz',
        'quiz_attempt_id': attempt.pk,
        'answered_count': answered_count,
    }
    session.save(update_fields=[
        'final_submission', 'status', 'submitted_at',
        'last_seen_at', 'metadata', 'updated_at',
    ])
    _log_exam_event(session, event_type, {
        'submission_id': submission.pk,
        'attempt_id': attempt.pk,
        'submission_mode': 'quiz',
        **(metadata or {}),
    })
    if session_status == ExamSessions.STATUS_AUTO_SUBMITTED or event_type == 'auto_submit':
        _notify_teacher_quiz_exam_alert(
            attempt,
            submission,
            reason=metadata.get('reason') if isinstance(metadata, dict) else event_type,
            metadata={'event_type': event_type, 'session_status': session_status},
        )
    return session


def _ensure_quiz_exam_attempt(assignment, student, session, request=None):
    attempt = QuizAttempts.objects.filter(
        assignment=assignment,
        student=student,
        exam_session=session,
    ).select_related('assignment', 'student', 'exam_session', 'submission').first()
    if attempt:
        return attempt, False

    questions = list(_quiz_active_questions(assignment))
    if not questions:
        return None, False
    settings_obj = _quiz_settings_for(assignment)
    seed = uuid.uuid4().hex
    metadata = _build_quiz_attempt_metadata(assignment, settings_obj, seed)
    attempt = QuizAttempts.objects.create(
        assignment=assignment,
        student=student,
        exam_session=session,
        attempt_no=1,
        status=QuizAttempts.STATUS_IN_PROGRESS,
        started_at=session.started_at or timezone.now(),
        max_score=sum(question.points for question in questions),
        ip_address=_get_client_ip(request) if request else session.ip_address,
        user_agent=(request.META.get('HTTP_USER_AGENT', '')[:500] if request else session.user_agent),
        random_seed=seed,
        metadata={
            **metadata,
            'exam_session_id': session.pk,
            'exam_mode': True,
        },
    )
    return attempt, True


def _grade_quiz_attempt(attempt, submit_status=QuizAttempts.STATUS_SUBMITTED):
    assignment = attempt.assignment
    now = timezone.now()
    settings_obj = _quiz_settings_for(assignment)
    questions = _quiz_questions_for_attempt(attempt)
    max_score = sum(question.points for question in questions)
    total_score = 0
    passed_count = 0
    total_questions = len(questions)

    for question in questions:
        answer = question.answer or QuizAnswers.objects.create(
            attempt=attempt,
            question=question,
            selected_choice_ids=[],
            answered_at=now,
        )
        correct_ids = set(question.choices.filter(is_correct=True).values_list('pk', flat=True))
        selected_ids = set(int(choice_id) for choice_id in (answer.selected_choice_ids or []))
        score_awarded = 0
        is_correct = False

        if question.question_type in (
            QuizQuestions.TYPE_SINGLE_CHOICE,
            QuizQuestions.TYPE_TRUE_FALSE,
            QuizQuestions.TYPE_MULTIPLE_CHOICE,
        ):
            is_correct = bool(correct_ids) and selected_ids == correct_ids
            score_awarded = question.points if is_correct else 0
            if is_correct:
                passed_count += 1
        else:
            is_correct = None
            score_awarded = 0

        answer.is_correct = is_correct
        answer.score_awarded = score_awarded
        answer.save(update_fields=['is_correct', 'score_awarded', 'updated_at'])
        total_score += score_awarded

    is_late = False
    penalty_percent = 0
    if assignment.due_date and now > assignment.due_date:
        is_late = True
        penalty_percent = assignment.late_penalty_percent if assignment.late_submission_allowed else 0
    if is_late and penalty_percent > 0:
        total_score = max(0, total_score - (total_score * penalty_percent / 100))

    duration_seconds = None
    if attempt.started_at:
        duration_seconds = max(0, int((now - attempt.started_at).total_seconds()))

    submission = attempt.submission
    if not submission:
        submission = Submissions.objects.create(
            assignment=assignment,
            student=attempt.student,
            submission_mode_snapshot=Assignments.SUBMISSION_QUIZ,
            language='quiz',
            code_content='',
            status='finished',
            total_score=round(total_score, 2),
            max_score=max_score or assignment.max_score,
            passed_testcases=passed_count,
            total_testcases=total_questions,
            is_late=is_late,
            penalty_applied=penalty_percent,
        )
    else:
        submission.submission_mode_snapshot = Assignments.SUBMISSION_QUIZ
        submission.language = 'quiz'
        submission.code_content = ''
        submission.status = 'finished'
        submission.total_score = round(total_score, 2)
        submission.max_score = max_score or assignment.max_score
        submission.passed_testcases = passed_count
        submission.total_testcases = total_questions
        submission.is_late = is_late
        submission.penalty_applied = penalty_percent
        submission.save(update_fields=[
            'submission_mode_snapshot', 'language', 'code_content',
            'status', 'total_score', 'max_score', 'passed_testcases',
            'total_testcases', 'is_late', 'penalty_applied',
        ])

    attempt.submission = submission
    attempt.status = submit_status
    attempt.submitted_at = now
    attempt.score = round(total_score, 2)
    attempt.max_score = max_score or assignment.max_score
    attempt.duration_seconds = duration_seconds
    attempt.metadata = {
        **(attempt.metadata or {}),
        'graded_at': now.isoformat(),
        'auto_graded': True,
        'show_score_after_submit': settings_obj.show_score_after_submit,
    }
    attempt.save(update_fields=[
        'submission', 'status', 'submitted_at', 'score',
        'max_score', 'duration_seconds', 'metadata', 'updated_at',
    ])
    update_assignment_statistics(assignment)
    return submission


def _is_admin_user(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    try:
        return user.profiles.role == 'admin'
    except Exception:
        return False


def _can_access_submission_files(user, submission):
    if not user.is_authenticated or not submission or not submission.assignment:
        return False
    if _is_admin_user(user):
        return True
    if submission.student_id == user.id:
        return True
    return _is_classroom_teacher(user, submission.assignment.classroom)


def _submission_exam_session(submission):
    if not submission or not submission.assignment or not submission.assignment.is_exam:
        return None
    return ExamSessions.objects.filter(
        assignment=submission.assignment,
        student=submission.student,
    ).first()


def _log_file_access(request, submission, event_type, file_obj):
    logger.info(
        'file_access event=%s file=%s submission=%s actor=%s',
        event_type,
        getattr(file_obj, 'pk', None),
        getattr(submission, 'pk', None),
        getattr(request.user, 'pk', None),
    )
    session = _submission_exam_session(submission)
    if session:
        _log_exam_event(session, event_type, {
            'file_id': getattr(file_obj, 'pk', None),
            'file_name': getattr(file_obj, 'file_name', ''),
            'actor_id': request.user.pk,
            'actor_username': request.user.username,
        })


@login_required
def open_submission_file_view(request, file_pk):
    submission_file = get_object_or_404(
        SubmissionFiles.objects.select_related(
            'submission',
            'submission__student',
            'submission__assignment',
            'submission__assignment__classroom',
        ),
        pk=file_pk,
    )
    if not _can_access_submission_files(request.user, submission_file.submission):
        messages.error(request, 'Bạn không có quyền mở file bài nộp này.')
        return redirect('classrooms:classroom_list')
    _log_file_access(request, submission_file.submission, 'submission_file_download', submission_file)
    return redirect(submission_file.file_url)


@login_required
def open_feedback_file_view(request, file_pk):
    feedback_file = get_object_or_404(
        SubmissionFileFeedbacks.objects.select_related(
            'submission',
            'submission__student',
            'submission__assignment',
            'submission__assignment__classroom',
        ),
        pk=file_pk,
    )
    if not _can_access_submission_files(request.user, feedback_file.submission):
        messages.error(request, 'Bạn không có quyền mở file phản hồi này.')
        return redirect('classrooms:classroom_list')
    _log_file_access(request, feedback_file.submission, 'feedback_file_download', feedback_file)
    return redirect(feedback_file.file_url)


def _build_file_submission_context(request, assignment, classroom, is_teacher=False, exam_session=None):
    requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).first()
    assignment_files = AssignmentFiles.objects.filter(assignment=assignment).order_by('-uploaded_at')
    submissions = Submissions.objects.filter(
        assignment=assignment,
        student=request.user,
    ).prefetch_related('files', 'feedback_files').order_by('-submitted_at')
    submission_count, remaining_attempts = _submission_attempt_context(assignment, request.user)
    is_exam_running = bool(exam_session and exam_session.status == ExamSessions.STATUS_RUNNING)
    can_submit = (
        not is_teacher
        and bool(requirements)
        and (
            (
                assignment.is_exam
                and is_exam_running
                and not exam_session.final_submission_id
                and submission_count == 0
            )
            or (
                not assignment.is_exam
                and (not assignment.max_attempts or submission_count < assignment.max_attempts)
                and (requirements.allow_resubmit or submission_count == 0)
            )
        )
    )
    return {
        'assignment': assignment,
        'classroom': classroom,
        'requirements': requirements,
        'files': assignment_files,
        'submissions': submissions,
        'submission_count': submission_count,
        'remaining_attempts': remaining_attempts,
        'can_submit': can_submit,
        'is_teacher': is_teacher,
        'exam_session': exam_session,
        'exam_started': bool(exam_session),
        'exam_deadline': exam_session.ends_at if exam_session else None,
        'exam_remaining_seconds': _exam_remaining_seconds(exam_session),
        'max_file_size_bytes': (requirements.max_file_size_mb if requirements else 20) * 1024 * 1024,
        'allowed_extensions': requirements.allowed_extensions if requirements else [],
    }


def _create_submission_detail_with_fallback(submission, testcase, tc_result, score_earned):
    """Persist testcase result with enum-safe status fallback."""
    raw_status = _sanitize_text_for_db(tc_result.get('status'))
    is_passed = bool(tc_result.get('passed'))

    candidate_statuses = [raw_status]
    candidate_statuses.append('passed' if is_passed else 'failed')
    candidate_statuses.append(None)

    # Preserve order while removing duplicates.
    seen = set()
    status_candidates = []
    for status in candidate_statuses:
        key = ('__none__' if status is None else status)
        if key not in seen:
            seen.add(key)
            status_candidates.append(status)

    last_error = None
    for status in status_candidates:
        try:
            return SubmissionDetails.objects.create(
                submission=submission,
                testcase=testcase,
                result_status=status,
                actual_output=_sanitize_text_for_db(tc_result.get('actual_output', ''))[:5000],
                execution_time=tc_result.get('execution_time'),
                memory_usage=tc_result.get('memory_usage'),
                error_message=_sanitize_text_for_db(tc_result.get('error_message', '') or '')[:2000],
                score_earned=round(score_earned, 2),
            )
        except DataError as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error
    return None


def _get_sandbox_config(language_name):
    config = SandboxConfigs.objects.filter(language=language_name, is_active=True).first()
    if config:
        return config.timeout_seconds, config.memory_limit_mb, config.docker_image, config.cpu_limit
    return 5, 256, None, 1.0


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_exam_event(session, event_type, metadata=None):
    event = ExamEvents.objects.create(
        session=session,
        event_type=event_type,
        metadata=metadata or {},
    )
    if event_type in EXAM_WARNING_EVENTS:
        ExamSessions.objects.filter(pk=session.pk).update(
            violation_count=models.F('violation_count') + 1
        )
        session.refresh_from_db(fields=['violation_count'])
    return event


def _filtered_exam_monitor_sessions(assignment, request):
    sessions = ExamSessions.objects.filter(
        assignment=assignment,
    ).select_related('student', 'final_submission').prefetch_related('final_submission__files').order_by('student__username')
    status_filter = request.GET.get('status', 'all')
    if status_filter in EXAM_MONITOR_FILTER_STATUSES:
        if status_filter == ExamSessions.STATUS_SUBMITTED:
            sessions = sessions.filter(status__in=[
                ExamSessions.STATUS_SUBMITTED,
                ExamSessions.STATUS_AUTO_SUBMITTED,
            ])
        else:
            sessions = sessions.filter(status=status_filter)
    return sessions, status_filter


def _expire_session_if_needed(session, now=None):
    now = now or timezone.now()
    grace = session.assignment.exam_grace_seconds or 30
    if (
        session.status == ExamSessions.STATUS_RUNNING
        and session.ends_at
        and now > session.ends_at + timedelta(seconds=grace)
    ):
        metadata = {'reason': 'server_time_exceeded'}
        if session.assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
            attempt = QuizAttempts.objects.filter(
                exam_session=session,
                status=QuizAttempts.STATUS_IN_PROGRESS,
            ).select_related('assignment', 'student', 'exam_session').first()
            if attempt:
                submission = _grade_quiz_attempt(
                    attempt,
                    submit_status=QuizAttempts.STATUS_AUTO_SUBMITTED,
                )
                _finalize_quiz_exam_session(
                    attempt,
                    submission,
                    ExamSessions.STATUS_AUTO_SUBMITTED,
                    'auto_submit',
                    metadata,
                )
                return session
            metadata.update({'submission_mode': 'quiz', 'quiz_attempt_found': False})
            teacher = session.assignment.classroom.teacher if session.assignment.classroom_id else None
            if teacher and teacher.pk != session.student_id:
                notify_user(
                    teacher,
                    title=f'Quiz exam hết giờ bất thường: {session.assignment.title}',
                    message=f'{session.student.get_full_name() or session.student.username} hết giờ nhưng không tìm thấy attempt đang làm.',
                    link=f'/submissions/exam/{session.assignment.pk}/monitor/',
                    notification_type='exam_auto_submitted',
                    actor=session.student,
                    metadata={
                        'assignment_id': session.assignment_id,
                        'exam_session_id': session.pk,
                        'reason': 'expired_without_attempt',
                        'submission_mode': 'quiz',
                    },
                )
        if session.assignment.submission_mode == Assignments.SUBMISSION_FILE:
            metadata.update({
                'submission_mode': 'file',
                'auto_submit_uploaded_draft': get_bool_setting('exam.file.auto_submit_uploaded_draft', False),
                'server_file_draft': False,
            })
        session.status = ExamSessions.STATUS_EXPIRED
        session.save(update_fields=['status', 'updated_at'])
        _log_exam_event(session, 'expired', metadata)
    return session


def _exam_remaining_seconds(session, now=None):
    if not session or not session.ends_at:
        return None
    now = now or timezone.now()
    return max(0, int((session.ends_at - now).total_seconds()))


def _build_ide_context(request, assignment, classroom, is_teacher=False, exam_session=None):
    allowed_langs = assignment.allowed_languages or []
    if allowed_langs:
        languages = ProgrammingLanguages.objects.filter(
            name__in=allowed_langs, is_active=True
        ).order_by('display_name')
    else:
        languages = ProgrammingLanguages.objects.filter(
            is_active=True
        ).order_by('display_name')

    default_lang = languages.first()
    language_names = list(languages.values_list('name', flat=True))
    selected_lang = (
        request.GET.get('lang')
        or (exam_session.current_language if exam_session and exam_session.current_language else None)
        or (default_lang.name if default_lang else 'python')
    )
    if language_names and selected_lang not in language_names:
        selected_lang = default_lang.name
    selected_language = languages.filter(name=selected_lang).first() or default_lang

    draft = CodeDrafts.objects.filter(
        assignment=assignment, student=request.user, language=selected_lang
    ).first()

    initial_code = ''
    if draft:
        initial_code = draft.code_content or ''
    elif (
        exam_session
        and exam_session.latest_draft
        and selected_lang == exam_session.current_language
    ):
        initial_code = exam_session.latest_draft
    elif selected_language and selected_language.default_template:
        initial_code = selected_language.default_template

    sample_testcases = Testcases.objects.filter(
        assignment=assignment, is_sample=True
    ).order_by('order_index')
    if assignment.is_exam and not is_teacher and not assignment.exam_allow_sample_run:
        sample_testcases = sample_testcases.none()

    from apps.assignments.models import AssignmentFiles
    files = AssignmentFiles.objects.filter(assignment=assignment)

    submission_count = Submissions.objects.filter(
        assignment=assignment, student=request.user
    ).count()

    return {
        'assignment': assignment,
        'classroom': classroom,
        'languages': languages,
        'selected_lang': selected_lang,
        'initial_code': initial_code,
        'sample_testcases': sample_testcases,
        'files': files,
        'submission_count': submission_count,
        'is_teacher': is_teacher,
        'exam_session': exam_session,
        'exam_deadline': exam_session.ends_at if exam_session else None,
        'exam_remaining_seconds': _exam_remaining_seconds(exam_session),
        'exam_started': bool(exam_session and exam_session.status == ExamSessions.STATUS_RUNNING),
    }


@login_required
def solve_problem_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')
    if assignment.is_exam and not is_teacher:
        return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)

    open_error = assignment_open_error(assignment, request.user)
    if open_error and not is_teacher:
        messages.error(request, open_error)
        return redirect('assignments:detail', pk=assignment.pk)

    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        context = _build_file_submission_context(request, assignment, classroom, is_teacher=is_teacher)
        return render(request, 'submissions/submit_file.html', context)
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        return redirect('submissions:quiz_lobby', assignment_pk=assignment.pk)

    # ===== EXAM MODE - tính deadline động =====
    exam_deadline = None
    exam_remaining_seconds = None
    exam_started = False
    if assignment.is_exam and assignment.exam_duration_minutes:
        # Xác định thời điểm bắt đầu exam: assignment.exam_start_time hoặc first submission/draft
        from datetime import timedelta
        now = timezone.now()
        start_time = assignment.exam_start_time

        if not start_time:
            # Sử dụng thời điểm sinh viên bắt đầu làm bài (lưu vào CodeDrafts)
            first_draft = CodeDrafts.objects.filter(
                assignment=assignment, student=request.user
            ).order_by('last_saved_at').first()
            if first_draft:
                # Gần đúng: dùng thời điểm save lạn đầu (không có created_at, tạm dùng last_saved_at)
                # thực tế nên thêm field `created_at` vào CodeDrafts, nhưng để đơn giản ta bắt đầu tính từ đây
                start_time = first_draft.last_saved_at
            else:
                # Lần đầu vào: bắt đầu tính từ now, tạo draft để ghi nhớ
                start_time = now
                CodeDrafts.objects.get_or_create(
                    assignment=assignment, student=request.user, language='python',
                    defaults={'code_content': ''}
                )

        exam_started = True
        exam_deadline = start_time + timedelta(minutes=assignment.exam_duration_minutes)
        remaining = (exam_deadline - now).total_seconds()
        exam_remaining_seconds = max(0, int(remaining))

    allowed_langs = assignment.allowed_languages or []
    if allowed_langs:
        languages = ProgrammingLanguages.objects.filter(
            name__in=allowed_langs, is_active=True
        ).order_by('display_name')
    else:
        languages = ProgrammingLanguages.objects.filter(
            is_active=True
        ).order_by('display_name')

    default_lang = languages.first()
    selected_lang = request.GET.get('lang', default_lang.name if default_lang else 'python')

    draft = CodeDrafts.objects.filter(
        assignment=assignment, student=request.user, language=selected_lang
    ).first()

    initial_code = ''
    if draft:
        initial_code = draft.code_content or ''
    elif default_lang and default_lang.default_template:
        initial_code = default_lang.default_template

    sample_testcases = Testcases.objects.filter(
        assignment=assignment, is_sample=True
    ).order_by('order_index')

    from apps.assignments.models import AssignmentFiles
    files = AssignmentFiles.objects.filter(assignment=assignment)

    submission_count = Submissions.objects.filter(
        assignment=assignment, student=request.user
    ).count()

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'languages': languages,
        'selected_lang': selected_lang,
        'initial_code': initial_code,
        'sample_testcases': sample_testcases,
        'files': files,
        'submission_count': submission_count,
        'is_teacher': is_teacher,
        'exam_deadline': exam_deadline,
        'exam_remaining_seconds': exam_remaining_seconds,
        'exam_started': exam_started,
    }
    return render(request, 'submissions/solve_problem.html', context)


@login_required
def file_submission_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    if assignment.submission_mode != Assignments.SUBMISSION_FILE:
        messages.error(request, 'Bài này không phải dạng nộp file.')
        return redirect('assignments:detail', pk=assignment.pk)
    return solve_problem_view(request, assignment_pk)


@login_required
@require_POST
def clear_file_draft_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    classroom = assignment.classroom
    if assignment.submission_mode != Assignments.SUBMISSION_FILE:
        return JsonResponse({'status': 'error', 'message': 'Bài này không phải dạng nộp file.'}, status=400)
    if not _is_classroom_member(request.user, classroom) or _is_classroom_teacher(request.user, classroom):
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền xóa nháp file.'}, status=403)

    draft_submissions = Submissions.objects.filter(
        assignment=assignment,
        student=request.user,
        submission_mode_snapshot=Assignments.SUBMISSION_FILE,
        status='draft',
    )
    deleted_files = SubmissionFiles.objects.filter(submission__in=draft_submissions).count()
    deleted_submissions = draft_submissions.count()
    if deleted_submissions:
        draft_submissions.delete()

    if assignment.is_exam:
        session = ExamSessions.objects.filter(
            assignment=assignment,
            student=request.user,
            status=ExamSessions.STATUS_RUNNING,
        ).first()
        if session:
            _log_exam_event(session, 'file_draft_cleared', {
                'deleted_files': deleted_files,
                'deleted_submissions': deleted_submissions,
                'has_server_draft': bool(deleted_submissions),
            })

    return JsonResponse({
        'status': 'ok',
        'deleted_files': deleted_files,
        'deleted_submissions': deleted_submissions,
    })


@login_required
@require_POST
def submit_file_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    classroom = assignment.classroom
    is_member = _is_classroom_member(request.user, classroom)
    is_teacher = _is_classroom_teacher(request.user, classroom)

    if assignment.submission_mode != Assignments.SUBMISSION_FILE:
        messages.error(request, 'Bài này không phải dạng nộp file.')
        return redirect('assignments:detail', pk=assignment.pk)
    if not is_member or is_teacher:
        messages.error(request, 'Chỉ học sinh của lớp mới được nộp file.')
        return redirect('assignments:detail', pk=assignment.pk)

    now = timezone.now()
    open_error = assignment_open_error(assignment, request.user, now)
    if open_error:
        messages.error(request, open_error)
        return redirect('assignments:detail', pk=assignment.pk)

    requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).first()
    submission_count, _ = _submission_attempt_context(assignment, request.user)
    exam_session = None
    if assignment.is_exam:
        session_id = request.POST.get('session_id')
        session_qs = ExamSessions.objects.filter(assignment=assignment, student=request.user)
        if session_id:
            session_qs = session_qs.filter(pk=session_id)
        exam_session = session_qs.first()
        if not exam_session:
            messages.error(request, 'Bạn cần bắt đầu phiên thi trước khi nộp file.')
            return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
        exam_session = _expire_session_if_needed(exam_session, now)
        if exam_session.final_submission_id:
            messages.info(request, 'Bạn đã nộp bài thi này.')
            return redirect('submissions:detail', pk=exam_session.final_submission_id)
        if exam_session.status != ExamSessions.STATUS_RUNNING:
            messages.error(request, 'Phiên thi không còn hoạt động.')
            return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
        if exam_session.ends_at and now > exam_session.ends_at + timedelta(seconds=assignment.exam_grace_seconds or 30):
            messages.error(request, 'Đã hết thời gian làm bài. Không thể nộp file.')
            return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
        if submission_count > 0:
            messages.error(request, 'Bài thi nộp file chỉ cho phép nộp chính thức một lần.')
            return redirect('submissions:history', assignment_pk=assignment.pk)
    elif requirements and not requirements.allow_resubmit and submission_count > 0:
        messages.error(request, 'Bài này chỉ cho phép nộp một lần.')
        return redirect('submissions:history', assignment_pk=assignment.pk)
    if not assignment.is_exam and assignment.max_attempts and submission_count >= assignment.max_attempts:
        messages.error(request, f'Bạn đã nộp tối đa {assignment.max_attempts} lần.')
        return redirect('submissions:history', assignment_pk=assignment.pk)

    note = (request.POST.get('submission_text') or '').strip()
    uploaded_files = request.FILES.getlist('files')
    errors = _validate_submission_files(uploaded_files, requirements)
    if requirements and requirements.require_comment and not note:
        errors.append('Bài này yêu cầu ghi chú khi nộp.')
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('submissions:exam_ide' if assignment.is_exam else 'submissions:solve', assignment_pk=assignment.pk)

    is_late = False
    penalty_percent = 0
    if assignment.due_date and now > assignment.due_date:
        if not assignment.late_submission_allowed:
            messages.error(request, 'Đã quá hạn nộp bài và bài tập không cho phép nộp muộn.')
            return redirect('assignments:detail', pk=assignment.pk)
        is_late = True
        penalty_percent = assignment.late_penalty_percent

    uploaded_payloads = []
    try:
        for uploaded_file in uploaded_files:
            checksum = _file_checksum(uploaded_file)
            safe_name = sanitize_upload_filename(uploaded_file.name)
            extension = os.path.splitext(safe_name.lower())[1]
            result = upload_to_configured_storage(
                uploaded_file,
                folder='submission_files/',
                user=request.user,
                safe_name=safe_name,
                prefix='submission-file',
            )
            uploaded_payloads.append({
                'file_name': safe_name,
                'file_url': result.get('url', ''),
                'file_size': uploaded_file.size,
                'mime_type': uploaded_file.content_type or '',
                'extension': extension,
                'checksum': checksum,
                'scan_status': SubmissionFiles.SCAN_PENDING if requirements.scan_required else SubmissionFiles.SCAN_SKIPPED,
                'metadata': {
                    'original_name': uploaded_file.name,
                    'storage_public_id': result.get('public_id', ''),
                    'resource_type': result.get('resource_type', ''),
                    'storage_provider': result.get('storage_provider', ''),
                },
            })
            if exam_session:
                _log_exam_event(exam_session, 'upload_file', {
                    'file_name': safe_name,
                    'file_size': uploaded_file.size,
                    'extension': extension,
                    'checksum': checksum,
                })
    except Exception:
        logger.exception('Failed to upload submission file assignment=%s user=%s', assignment.pk, request.user.pk)
        messages.error(request, 'Có lỗi xảy ra khi tải file. Vui lòng thử lại.')
        return redirect('submissions:exam_ide' if assignment.is_exam else 'submissions:solve', assignment_pk=assignment.pk)

    with transaction.atomic():
        submission = Submissions.objects.create(
            assignment=assignment,
            student=request.user,
            submission_mode_snapshot=Assignments.SUBMISSION_FILE,
            submission_text=note,
            status='pending',
            is_late=is_late,
            penalty_applied=penalty_percent,
            max_score=assignment.max_score,
        )
        for payload in uploaded_payloads:
            metadata = payload.pop('metadata', {})
            SubmissionFiles.objects.create(
                submission=submission,
                uploaded_by=request.user,
                storage_provider=metadata.get('storage_provider') or 'django',
                metadata=metadata,
                **payload,
            )
        if exam_session:
            exam_session.final_submission = submission
            exam_session.status = ExamSessions.STATUS_SUBMITTED
            exam_session.submitted_at = timezone.now()
            exam_session.last_seen_at = timezone.now()
            exam_session.metadata = {
                **(exam_session.metadata or {}),
                'file_count': len(uploaded_payloads),
                'submission_text_size': len(note),
            }
            exam_session.save(update_fields=[
                'final_submission', 'status', 'submitted_at',
                'last_seen_at', 'metadata', 'updated_at',
            ])
            _log_exam_event(exam_session, 'submitted', {
                'submission_id': submission.pk,
                'file_count': len(uploaded_payloads),
                'submission_mode': 'file',
            })

    if classroom.teacher and classroom.teacher_id != request.user.id:
        notify_user(
            classroom.teacher,
            title=f'Bài nộp file mới: {assignment.title}',
            message=f'{request.user.get_full_name() or request.user.username} vừa nộp {len(uploaded_payloads)} file.',
            link=f'/submissions/detail/{submission.pk}/',
            notification_type='submission_submitted',
            actor=request.user,
            metadata={'submission_id': submission.pk, 'assignment_id': assignment.pk, 'submission_mode': 'file'},
        )

    messages.success(request, 'Đã nộp file thành công. Giáo viên sẽ chấm và phản hồi sau.')
    return redirect('submissions:detail', pk=submission.pk)


@login_required
def quiz_lobby_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if assignment.submission_mode != Assignments.SUBMISSION_QUIZ:
        messages.error(request, 'Bài này không phải dạng trắc nghiệm.')
        return redirect('assignments:detail', pk=assignment.pk)
    if is_teacher:
        return redirect('assignments:quiz_manage', pk=assignment.pk)
    if not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')
    if assignment.is_exam:
        return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)

    settings_obj = _quiz_settings_for(assignment)
    questions = list(_quiz_active_questions(assignment))
    attempts = QuizAttempts.objects.filter(
        assignment=assignment,
        student=request.user,
    ).select_related('submission').order_by('-attempt_no')
    open_error = assignment_open_error(assignment, request.user)
    remaining_attempts = _quiz_remaining_attempts(assignment, request.user)
    can_start = (
        not open_error
        and bool(questions)
        and (remaining_attempts is None or remaining_attempts > 0)
    )
    in_progress_attempt = attempts.filter(status=QuizAttempts.STATUS_IN_PROGRESS).first()

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'quiz_settings': settings_obj,
        'question_count': len(questions),
        'attempts': attempts,
        'attempt_count': attempts.count(),
        'remaining_attempts': remaining_attempts,
        'open_error': open_error,
        'can_start': can_start,
        'in_progress_attempt': in_progress_attempt,
    }
    return render(request, 'submissions/quiz_lobby.html', context)


@login_required
@require_POST
def start_quiz_attempt_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    classroom = assignment.classroom

    if assignment.submission_mode != Assignments.SUBMISSION_QUIZ:
        messages.error(request, 'Bài này không phải dạng trắc nghiệm.')
        return redirect('assignments:detail', pk=assignment.pk)
    if assignment.is_exam:
        return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
    if not _is_classroom_member(request.user, classroom) or _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Chỉ học sinh của lớp mới được làm quiz.')
        return redirect('assignments:detail', pk=assignment.pk)

    open_error = assignment_open_error(assignment, request.user)
    if open_error:
        messages.error(request, open_error)
        return redirect('submissions:quiz_lobby', assignment_pk=assignment.pk)

    in_progress = QuizAttempts.objects.filter(
        assignment=assignment,
        student=request.user,
        status=QuizAttempts.STATUS_IN_PROGRESS,
    ).order_by('-attempt_no').first()
    if in_progress:
        messages.info(request, 'Bạn đang có lượt làm chưa nộp. Tiếp tục lượt đó trước nha.')
        return redirect('submissions:quiz_take', attempt_pk=in_progress.pk)

    remaining_attempts = _quiz_remaining_attempts(assignment, request.user)
    if remaining_attempts is not None and remaining_attempts <= 0:
        messages.error(request, f'Bạn đã dùng hết {assignment.max_attempts} lượt làm quiz.')
        return redirect('submissions:quiz_lobby', assignment_pk=assignment.pk)

    questions = list(_quiz_active_questions(assignment))
    if not questions:
        messages.error(request, 'Quiz này chưa có câu hỏi đang bật.')
        return redirect('assignments:detail', pk=assignment.pk)

    settings_obj = _quiz_settings_for(assignment)
    next_attempt_no = (
        QuizAttempts.objects.filter(assignment=assignment, student=request.user)
        .aggregate(max_no=models.Max('attempt_no'))['max_no'] or 0
    ) + 1
    seed = uuid.uuid4().hex
    metadata = _build_quiz_attempt_metadata(assignment, settings_obj, seed)
    attempt = QuizAttempts.objects.create(
        assignment=assignment,
        student=request.user,
        attempt_no=next_attempt_no,
        status=QuizAttempts.STATUS_IN_PROGRESS,
        started_at=timezone.now(),
        max_score=sum(question.points for question in questions),
        ip_address=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        random_seed=seed,
        metadata=metadata,
    )
    messages.success(request, f'Đã bắt đầu lượt làm #{attempt.attempt_no}.')
    return redirect('submissions:quiz_take', attempt_pk=attempt.pk)


@login_required
def take_quiz_attempt_view(request, attempt_pk):
    attempt = get_object_or_404(
        QuizAttempts.objects.select_related('assignment', 'student', 'exam_session'),
        pk=attempt_pk,
    )
    assignment = attempt.assignment
    if attempt.student_id != request.user.id:
        messages.error(request, 'Bạn không có quyền làm lượt quiz này.')
        return redirect('classrooms:classroom_list')
    exam_session = None
    if assignment.is_exam:
        exam_session = _quiz_attempt_exam_session(attempt)
        if not exam_session:
            messages.error(request, 'Không tìm thấy phiên thi của lượt quiz này.')
            return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
        exam_session = _expire_session_if_needed(exam_session)
        attempt.exam_session = exam_session
        if exam_session.final_submission_id and attempt.status != QuizAttempts.STATUS_IN_PROGRESS:
            return redirect('submissions:quiz_result', attempt_pk=attempt.pk)
        if exam_session.status != ExamSessions.STATUS_RUNNING:
            messages.error(request, 'Phiên thi không còn hoạt động.')
            return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
    if attempt.status != QuizAttempts.STATUS_IN_PROGRESS:
        return redirect('submissions:quiz_result', attempt_pk=attempt.pk)

    settings_obj = _quiz_settings_for(assignment)
    remaining_seconds = _quiz_attempt_time_remaining(attempt, settings_obj)
    if remaining_seconds == 0:
        with transaction.atomic():
            _grade_quiz_attempt(attempt, submit_status=QuizAttempts.STATUS_AUTO_SUBMITTED)
        messages.info(request, 'Đã hết thời gian. Hệ thống đã tự động nộp lượt quiz này.')
        return redirect('submissions:quiz_result', attempt_pk=attempt.pk)

    questions = _quiz_questions_for_attempt(attempt)
    answered_count = sum(1 for question in questions if question.answer_state['answered'])
    context = {
        'assignment': assignment,
        'classroom': assignment.classroom,
        'attempt': attempt,
        'quiz_settings': settings_obj,
        'questions': questions,
        'answered_count': answered_count,
        'total_questions': len(questions),
        'remaining_seconds': remaining_seconds,
        'is_exam_attempt': assignment.is_exam,
        'exam_session': exam_session,
    }
    return render(request, 'submissions/quiz_take.html', context)


@login_required
@require_POST
def autosave_quiz_answer_view(request, attempt_pk):
    attempt = get_object_or_404(
        QuizAttempts.objects.select_related('assignment', 'student', 'exam_session'),
        pk=attempt_pk,
    )
    if attempt.student_id != request.user.id:
        return JsonResponse({'status': 'error', 'message': 'Không có quyền.'}, status=403)
    if attempt.status != QuizAttempts.STATUS_IN_PROGRESS:
        return JsonResponse({'status': 'error', 'message': 'Lượt làm đã kết thúc.'}, status=400)

    exam_session = None
    if attempt.assignment.is_exam:
        exam_session = _quiz_attempt_exam_session(attempt)
        if not exam_session:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy phiên thi.'}, status=400)
        exam_session = _expire_session_if_needed(exam_session)
        attempt.exam_session = exam_session
        if exam_session.status != ExamSessions.STATUS_RUNNING:
            return JsonResponse({'status': 'expired', 'message': 'Phiên thi đã kết thúc.'}, status=400)

    settings_obj = _quiz_settings_for(attempt.assignment)
    if _quiz_attempt_time_remaining(attempt, settings_obj) == 0:
        with transaction.atomic():
            submission = _grade_quiz_attempt(attempt, submit_status=QuizAttempts.STATUS_AUTO_SUBMITTED)
            if exam_session:
                _finalize_quiz_exam_session(
                    attempt,
                    submission,
                    ExamSessions.STATUS_AUTO_SUBMITTED,
                    'auto_submit',
                    {'reason': 'timer_zero_on_autosave'},
                )
        return JsonResponse({'status': 'expired', 'message': 'Đã hết giờ và hệ thống đã tự nộp.'}, status=400)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Payload không hợp lệ.'}, status=400)

    question_id = payload.get('question_id')
    question = QuizQuestions.objects.filter(
        pk=question_id,
        assignment=attempt.assignment,
        is_active=True,
    ).first()
    if not question:
        return JsonResponse({'status': 'error', 'message': 'Câu hỏi không hợp lệ.'}, status=404)

    selected_choice_ids = _selected_choice_ids_from_values(payload.get('selected_choice_ids') or [])
    if question.question_type in (QuizQuestions.TYPE_SINGLE_CHOICE, QuizQuestions.TYPE_TRUE_FALSE):
        selected_choice_ids = selected_choice_ids[:1]
    text_answer = payload.get('text_answer') or ''
    _save_quiz_answer(attempt, question, selected_choice_ids, text_answer)
    if exam_session:
        _log_exam_event(exam_session, 'answer_saved', {
            'attempt_id': attempt.pk,
            'question_id': question.pk,
            'selected_count': len(selected_choice_ids),
            'has_text_answer': bool((text_answer or '').strip()),
        })
        exam_session.last_seen_at = timezone.now()
        exam_session.save(update_fields=['last_seen_at', 'updated_at'])

    questions = _quiz_questions_for_attempt(attempt)
    total_questions = len(questions)
    answered_count = sum(1 for question in questions if question.answer_state['answered'])
    return JsonResponse({
        'status': 'ok',
        'answered_count': min(answered_count, total_questions),
        'total_questions': total_questions,
        'saved_at': timezone.now().strftime('%H:%M:%S'),
    })


@login_required
@require_POST
def submit_quiz_attempt_view(request, attempt_pk):
    attempt = get_object_or_404(
        QuizAttempts.objects.select_related('assignment', 'student', 'exam_session'),
        pk=attempt_pk,
    )
    if attempt.student_id != request.user.id:
        messages.error(request, 'Bạn không có quyền nộp lượt quiz này.')
        return redirect('classrooms:classroom_list')
    if attempt.status != QuizAttempts.STATUS_IN_PROGRESS:
        return redirect('submissions:quiz_result', attempt_pk=attempt.pk)

    exam_session = None
    if attempt.assignment.is_exam:
        exam_session = _quiz_attempt_exam_session(attempt)
        if not exam_session:
            messages.error(request, 'Không tìm thấy phiên thi.')
            return redirect('submissions:exam_lobby', assignment_pk=attempt.assignment.pk)
        exam_session = _expire_session_if_needed(exam_session)
        attempt.exam_session = exam_session
        if exam_session.final_submission_id:
            messages.info(request, 'Bạn đã nộp bài thi này.')
            return redirect('submissions:quiz_result', attempt_pk=attempt.pk)
        if exam_session.status not in (ExamSessions.STATUS_RUNNING, ExamSessions.STATUS_EXPIRED):
            messages.error(request, 'Phiên thi không còn hoạt động.')
            return redirect('submissions:exam_lobby', assignment_pk=attempt.assignment.pk)

    settings_obj = _quiz_settings_for(attempt.assignment)
    submit_status = QuizAttempts.STATUS_SUBMITTED
    if _quiz_attempt_time_remaining(attempt, settings_obj) == 0:
        submit_status = QuizAttempts.STATUS_AUTO_SUBMITTED

    with transaction.atomic():
        for question in _quiz_questions_for_attempt(attempt):
            key = f'question_{question.pk}'
            if question.question_type == QuizQuestions.TYPE_SHORT_TEXT:
                _save_quiz_answer(
                    attempt,
                    question,
                    [],
                    request.POST.get(key, ''),
                )
            else:
                selected_choice_ids = _selected_choice_ids_from_values(request.POST.getlist(key))
                if question.question_type in (QuizQuestions.TYPE_SINGLE_CHOICE, QuizQuestions.TYPE_TRUE_FALSE):
                    selected_choice_ids = selected_choice_ids[:1]
                _save_quiz_answer(attempt, question, selected_choice_ids, '')
        submission = _grade_quiz_attempt(attempt, submit_status=submit_status)
        if exam_session:
            _finalize_quiz_exam_session(
                attempt,
                submission,
                ExamSessions.STATUS_AUTO_SUBMITTED if submit_status == QuizAttempts.STATUS_AUTO_SUBMITTED else ExamSessions.STATUS_SUBMITTED,
                'auto_submit' if submit_status == QuizAttempts.STATUS_AUTO_SUBMITTED else 'submitted',
                {'source': 'student_submit'},
            )

    if attempt.assignment.classroom.teacher and attempt.assignment.classroom.teacher_id != request.user.id:
        notify_user(
            attempt.assignment.classroom.teacher,
            title=f'Học sinh vừa nộp quiz: {attempt.assignment.title}',
            message=f'{request.user.get_full_name() or request.user.username} đã nộp lượt #{attempt.attempt_no}.',
            link=f'/submissions/detail/{submission.pk}/',
            notification_type='submission_submitted',
            actor=request.user,
            metadata={
                'submission_id': submission.pk,
                'assignment_id': attempt.assignment_id,
                'submission_mode': 'quiz',
                'attempt_id': attempt.pk,
            },
        )
    messages.success(request, 'Đã nộp quiz thành công.')
    return redirect('submissions:quiz_result', attempt_pk=attempt.pk)


@login_required
def quiz_result_view(request, attempt_pk):
    attempt = get_object_or_404(
        QuizAttempts.objects.select_related('assignment', 'student', 'submission', 'exam_session'),
        pk=attempt_pk,
    )
    assignment = attempt.assignment
    is_teacher = _is_classroom_teacher(request.user, assignment.classroom)
    is_owner = attempt.student_id == request.user.id
    if not (is_owner or is_teacher or _is_admin_user(request.user)):
        messages.error(request, 'Bạn không có quyền xem kết quả quiz này.')
        return redirect('classrooms:classroom_list')

    settings_obj = _quiz_settings_for(assignment)
    can_review = is_teacher or _is_admin_user(request.user) or settings_obj.allow_review
    show_score = (
        is_teacher
        or _is_admin_user(request.user)
        or settings_obj.show_score_after_submit
        or bool(assignment.grades_released_at)
    )
    show_correct_answers = is_teacher or _is_admin_user(request.user) or (can_review and settings_obj.show_correct_answers)
    show_explanation = show_correct_answers and settings_obj.show_explanation
    questions = _quiz_questions_for_attempt(attempt) if can_review else []
    for question in questions:
        question.correct_choice_ids = list(question.choices.filter(is_correct=True).values_list('pk', flat=True))

    context = {
        'assignment': assignment,
        'classroom': assignment.classroom,
        'attempt': attempt,
        'quiz_settings': settings_obj,
        'questions': questions,
        'show_score': show_score,
        'show_correct_answers': show_correct_answers,
        'show_explanation': show_explanation,
        'can_review': can_review,
    }
    return render(request, 'submissions/quiz_result.html', context)


@login_required
def exam_lobby_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True, is_exam=True)
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)
    if is_teacher:
        return redirect('submissions:exam_monitor', assignment_pk=assignment.pk)
    if not _is_classroom_member(request.user, classroom):
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    open_error = assignment_open_error(assignment, request.user)
    if open_error:
        messages.error(request, open_error)
        return redirect('assignments:detail', pk=assignment.pk)

    now = timezone.now()
    if assignment.exam_start_time and now < assignment.exam_start_time:
        messages.info(request, 'Bài thi chưa đến giờ bắt đầu.')
    if assignment.exam_end_time and now > assignment.exam_end_time:
        messages.error(request, 'Phòng thi đã đóng.')

    session = ExamSessions.objects.filter(assignment=assignment, student=request.user).first()
    if session:
        session = _expire_session_if_needed(session)
    file_requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).first()
    quiz_settings = QuizSettings.objects.filter(assignment=assignment).first()
    quiz_attempt = None
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ and session:
        quiz_attempt = QuizAttempts.objects.filter(exam_session=session).select_related('submission').first()
    return render(request, 'submissions/exam_lobby.html', {
        'assignment': assignment,
        'classroom': classroom,
        'session': session,
        'file_requirements': file_requirements,
        'quiz_settings': quiz_settings,
        'quiz_attempt': quiz_attempt,
        'quiz_question_count': _quiz_active_questions(assignment).count() if assignment.submission_mode == Assignments.SUBMISSION_QUIZ else 0,
        'remaining_seconds': _exam_remaining_seconds(session),
        'now': now,
    })


@login_required
@require_POST
def start_exam_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True, is_exam=True)
    classroom = assignment.classroom
    if not _is_classroom_member(request.user, classroom):
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    open_error = assignment_open_error(assignment, request.user)
    if open_error:
        messages.error(request, open_error)
        return redirect('assignments:detail', pk=assignment.pk)

    now = timezone.now()
    if assignment.exam_start_time and now < assignment.exam_start_time:
        messages.error(request, 'Bài thi chưa đến giờ bắt đầu.')
        return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
    if assignment.exam_end_time and now > assignment.exam_end_time:
        messages.error(request, 'Phòng thi đã đóng.')
        return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)

    session, created = ExamSessions.objects.get_or_create(
        assignment=assignment,
        student=request.user,
        defaults={
            'status': ExamSessions.STATUS_RUNNING,
            'started_at': now,
            'ends_at': (
                (assignment.exam_start_time or now) + timedelta(minutes=assignment.exam_duration_minutes or 0)
            ),
            'ip_address': _get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:1000],
            'last_seen_at': now,
        },
    )
    if not created:
        session = _expire_session_if_needed(session, now)
        if session.status in (ExamSessions.STATUS_SUBMITTED, ExamSessions.STATUS_AUTO_SUBMITTED):
            messages.info(request, 'Bạn đã nộp bài thi này.')
            return redirect('submissions:detail', pk=session.final_submission_id) if session.final_submission_id else redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
        if session.status == ExamSessions.STATUS_EXPIRED:
            messages.error(request, 'Phiên thi đã hết giờ.')
            return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
        if session.status != ExamSessions.STATUS_RUNNING:
            session.status = ExamSessions.STATUS_RUNNING
            session.started_at = session.started_at or now
            session.ends_at = session.ends_at or now + timedelta(minutes=assignment.exam_duration_minutes or 0)
            session.save(update_fields=['status', 'started_at', 'ends_at', 'updated_at'])
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        attempt, attempt_created = _ensure_quiz_exam_attempt(assignment, request.user, session, request)
        if not attempt:
            messages.error(request, 'Bài thi trắc nghiệm này chưa có câu hỏi đang bật.')
            return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
        if attempt.status in (QuizAttempts.STATUS_SUBMITTED, QuizAttempts.STATUS_AUTO_SUBMITTED) and attempt.submission_id:
            messages.info(request, 'Bạn đã nộp bài thi trắc nghiệm này.')
            return redirect('submissions:quiz_result', attempt_pk=attempt.pk)
        _log_exam_event(session, 'quiz_attempt_created' if attempt_created else 'quiz_attempt_continued', {
            'attempt_id': attempt.pk,
            'submission_mode': 'quiz',
        })
    _log_exam_event(session, 'started' if created else 'continued', {'ip': _get_client_ip(request)})
    return redirect('submissions:exam_ide', assignment_pk=assignment.pk)


@login_required
def exam_ide_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True, is_exam=True)
    classroom = assignment.classroom
    if not _is_classroom_member(request.user, classroom):
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    session = get_object_or_404(ExamSessions, assignment=assignment, student=request.user)
    session = _expire_session_if_needed(session)
    if session.status != ExamSessions.STATUS_RUNNING:
        messages.error(request, 'Phiên thi không còn hoạt động.')
        return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        context = _build_file_submission_context(
            request,
            assignment,
            classroom,
            is_teacher=False,
            exam_session=session,
        )
        return render(request, 'submissions/submit_file.html', context)
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        attempt, _attempt_created = _ensure_quiz_exam_attempt(assignment, request.user, session, request)
        if not attempt:
            messages.error(request, 'Bài thi trắc nghiệm này chưa có câu hỏi đang bật.')
            return redirect('submissions:exam_lobby', assignment_pk=assignment.pk)
        return redirect('submissions:quiz_take', attempt_pk=attempt.pk)
    context = _build_ide_context(request, assignment, classroom, is_teacher=False, exam_session=session)
    return render(request, 'submissions/solve_problem.html', context)


@login_required
@require_POST
def exam_ping_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True, is_exam=True)
    session = get_object_or_404(ExamSessions, assignment=assignment, student=request.user)
    session = _expire_session_if_needed(session)
    if session.status == ExamSessions.STATUS_RUNNING:
        session.last_seen_at = timezone.now()
        session.save(update_fields=['last_seen_at', 'updated_at'])
    return JsonResponse({
        'status': 'ok',
        'session_status': session.status,
        'remaining_seconds': _exam_remaining_seconds(session),
        'violation_count': session.violation_count,
    })


@login_required
@require_POST
def exam_event_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True, is_exam=True)
    session = get_object_or_404(ExamSessions, assignment=assignment, student=request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    event_type = (data.get('event_type') or '').strip()[:64]
    if not event_type:
        return JsonResponse({'status': 'error', 'message': 'Thiếu event_type.'}, status=400)
    metadata = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
    _log_exam_event(session, event_type, metadata)
    session.last_seen_at = timezone.now()
    session.save(update_fields=['last_seen_at', 'updated_at'])
    return JsonResponse({'status': 'ok', 'violation_count': session.violation_count})


@teacher_required
def exam_monitor_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_exam=True)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xem phòng thi này.')
        return redirect('classrooms:classroom_list')
    sessions, status_filter = _filtered_exam_monitor_sessions(assignment, request)
    member_ids = set(ClassroomMembers.objects.filter(
        classroom=classroom,
        status='approved',
    ).values_list('student_id', flat=True))
    all_sessions = ExamSessions.objects.filter(assignment=assignment)
    session_student_ids = set(all_sessions.values_list('student_id', flat=True))
    not_started_count = len(member_ids - session_student_ids)
    counts = {
        'not_started': not_started_count,
        'running': all_sessions.filter(status=ExamSessions.STATUS_RUNNING).count(),
        'submitted': all_sessions.filter(status__in=[
            ExamSessions.STATUS_SUBMITTED,
            ExamSessions.STATUS_AUTO_SUBMITTED,
        ]).count(),
        'expired': all_sessions.filter(status=ExamSessions.STATUS_EXPIRED).count(),
        'warnings': sum(all_sessions.values_list('violation_count', flat=True)),
    }
    page_obj = Paginator(sessions, 25).get_page(request.GET.get('page'))
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        page_sessions = list(page_obj.object_list)
        attempts = QuizAttempts.objects.filter(
            exam_session__in=page_sessions,
        ).prefetch_related('answers').select_related('submission')
        attempts_by_session = {attempt.exam_session_id: attempt for attempt in attempts}
        for session in page_sessions:
            attempt = attempts_by_session.get(session.pk)
            session.quiz_attempt = attempt
            if attempt:
                questions = _quiz_questions_for_attempt(attempt)
                session.quiz_answered_count = sum(1 for question in questions if question.answer_state['answered'])
                session.quiz_total_questions = len(questions)
                session.quiz_score = attempt.score if attempt.status != QuizAttempts.STATUS_IN_PROGRESS else None
            else:
                session.quiz_answered_count = 0
                session.quiz_total_questions = _quiz_active_questions(assignment).count()
                session.quiz_score = None
    context = {
        'assignment': assignment,
        'classroom': classroom,
        'sessions': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'counts': counts,
        'is_file_exam': assignment.submission_mode == Assignments.SUBMISSION_FILE,
        'is_quiz_exam': assignment.submission_mode == Assignments.SUBMISSION_QUIZ,
    }
    context.update(csv_query_context(request))
    context['csv_items'] = [
        {
            'url': reverse('submissions:exam_monitor_export', kwargs={'assignment_pk': assignment.pk}),
            'type': '',
            'icon': 'csv',
            'label': 'Xuất CSV phiên thi theo lọc' if context['has_active_filters'] else 'Xuất CSV toàn bộ phiên thi',
            'primary': True,
        },
        {
            'url': reverse('submissions:exam_monitor_export', kwargs={'assignment_pk': assignment.pk}) + '?format=xlsx',
            'type': '',
            'icon': 'table_chart',
            'label': 'Xuất Excel phiên thi theo lọc' if context['has_active_filters'] else 'Xuất Excel toàn bộ phiên thi',
            'primary': False,
        },
        {
            'url': reverse('submissions:exam_monitor_export', kwargs={'assignment_pk': assignment.pk}),
            'type': 'scores',
            'icon': 'grading',
            'label': 'Xuất điểm bài thi theo lọc hiện tại' if context['has_active_filters'] else 'Xuất điểm bài thi',
            'primary': False,
        },
        {
            'url': reverse('submissions:exam_monitor_export', kwargs={'assignment_pk': assignment.pk}),
            'type': 'warnings',
            'icon': 'warning',
            'label': 'Xuất cảnh báo theo lọc hiện tại' if context['has_active_filters'] else 'Xuất cảnh báo thi',
            'primary': False,
        },
    ]
    return render(request, 'submissions/exam_monitor.html', context)


@teacher_required
def exam_monitor_export_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_exam=True)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất báo cáo phòng thi này.')
        return redirect('classrooms:classroom_list')

    export_type = request.GET.get('type', 'summary')
    suffix = export_type if export_type in {'summary', 'warnings', 'scores'} else 'summary'
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="%s"' % csv_filename(
        f'exam_{assignment.pk}',
        suffix,
        filtered=bool(csv_query_context(request)['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    )
    response.write('\ufeff')
    writer = csv.writer(response)

    sessions, _status_filter = _filtered_exam_monitor_sessions(assignment, request)

    if export_type == 'warnings':
        writer.writerow([
            'Thời gian', 'Username', 'Họ tên', 'Email', 'Sự kiện',
            'Số cảnh báo phiên', 'Trạng thái phiên', 'IP', 'Metadata',
        ])
        events = ExamEvents.objects.filter(
            session__in=sessions,
            event_type__in=EXAM_WARNING_EVENTS,
        ).select_related('session', 'session__student').order_by('session__student__username', 'created_at')
        for event in events:
            session = event.session
            writer.writerow([
                timezone.localtime(event.created_at).strftime('%d/%m/%Y %H:%M:%S') if event.created_at else '',
                session.student.username,
                session.student.get_full_name(),
                session.student.email,
                event.event_type,
                session.violation_count,
                session.get_status_display(),
                session.ip_address or '',
                json.dumps(event.metadata or {}, ensure_ascii=False),
            ])
        return response

    if export_type == 'scores':
        writer.writerow([
            'Username', 'Họ tên', 'Email', 'Trạng thái phiên', 'Submission ID',
            'Ngôn ngữ', 'Nộp lúc', 'Điểm', 'Điểm tối đa', 'Testcase pass',
            'Tổng testcase', 'Cảnh báo', 'Số lần run',
        ])
        for session in sessions:
            submission = session.final_submission
            writer.writerow([
                session.student.username,
                session.student.get_full_name(),
                session.student.email,
                session.get_status_display(),
                submission.pk if submission else '',
                submission.language if submission else session.current_language or '',
                timezone.localtime(submission.submitted_at).strftime('%d/%m/%Y %H:%M:%S') if submission and submission.submitted_at else '',
                submission.manual_score if submission and submission.manual_score is not None else (submission.total_score if submission else ''),
                submission.max_score if submission else assignment.max_score,
                submission.passed_testcases if submission else '',
                submission.total_testcases if submission else '',
                session.violation_count,
                session.run_count,
            ])
        return response

    writer.writerow([
        'Username', 'Ho ten', 'Email', 'Trang thai', 'Bat dau',
        'Ket thuc', 'Nop luc', 'Lan run', 'Warning', 'Submission ID', 'Diem',
    ])
    for session in sessions:
        submission = session.final_submission
        writer.writerow([
            session.student.username,
            session.student.get_full_name(),
            session.student.email,
            session.get_status_display(),
            timezone.localtime(session.started_at).strftime('%d/%m/%Y %H:%M:%S') if session.started_at else '',
            timezone.localtime(session.ends_at).strftime('%d/%m/%Y %H:%M:%S') if session.ends_at else '',
            timezone.localtime(session.submitted_at).strftime('%d/%m/%Y %H:%M:%S') if session.submitted_at else '',
            session.run_count,
            session.violation_count,
            submission.pk if submission else '',
            submission.manual_score if submission and submission.manual_score is not None else (submission.total_score if submission else ''),
        ])
    return response


@teacher_required
def exam_monitor_json_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_exam=True)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
        
    sessions, status_filter = _filtered_exam_monitor_sessions(assignment, request)
    member_ids = set(ClassroomMembers.objects.filter(classroom=classroom, status='approved').values_list('student_id', flat=True))
    all_sessions = ExamSessions.objects.filter(assignment=assignment)
    session_student_ids = set(all_sessions.values_list('student_id', flat=True))
    
    counts = {
        'not_started': len(member_ids - session_student_ids),
        'running': all_sessions.filter(status=ExamSessions.STATUS_RUNNING).count(),
        'submitted': all_sessions.filter(status__in=[ExamSessions.STATUS_SUBMITTED, ExamSessions.STATUS_AUTO_SUBMITTED]).count(),
        'expired': all_sessions.filter(status=ExamSessions.STATUS_EXPIRED).count(),
        'warnings': sum(all_sessions.values_list('violation_count', flat=True)),
    }
    
    page_obj = Paginator(sessions, 25).get_page(request.GET.get('page'))
    is_quiz_exam = (assignment.submission_mode == Assignments.SUBMISSION_QUIZ)
    is_file_exam = (assignment.submission_mode == Assignments.SUBMISSION_FILE)
    
    if is_quiz_exam:
        page_sessions = list(page_obj.object_list)
        attempts = QuizAttempts.objects.filter(exam_session__in=page_sessions).prefetch_related('answers').select_related('submission')
        attempts_by_session = {attempt.exam_session_id: attempt for attempt in attempts}
        for session in page_sessions:
            attempt = attempts_by_session.get(session.pk)
            session.quiz_attempt = attempt
            if attempt:
                from .views import _quiz_questions_for_attempt, _quiz_active_questions
                questions = _quiz_questions_for_attempt(attempt)
                session.quiz_answered_count = sum(1 for q in questions if q.answer_state['answered'])
                session.quiz_total_questions = len(questions)
                session.quiz_score = attempt.score if attempt.status != QuizAttempts.STATUS_IN_PROGRESS else None
            else:
                session.quiz_answered_count = 0
                session.quiz_total_questions = _quiz_active_questions(assignment).count()
                session.quiz_score = None

    sessions_data = []
    for s in page_obj:
        name = s.student.get_full_name() or s.student.username
        
        progress = str(s.run_count)
        if is_file_exam:
            progress = str(s.final_submission.files.count() if s.final_submission else 0)
        elif is_quiz_exam:
            progress = f"{getattr(s, 'quiz_answered_count', 0)}/{getattr(s, 'quiz_total_questions', 0)}"
            
        sessions_data.append({
            'id': s.pk,
            'name': name,
            'status': s.get_status_display(),
            'status_raw': s.status,
            'started_at': timezone.localtime(s.started_at).strftime("%d/%m %H:%M") if s.started_at else "-",
            'ends_at': timezone.localtime(s.ends_at).strftime("%d/%m %H:%M") if s.ends_at else "-",
            'progress': progress,
            'violations': s.violation_count,
            'quiz_score': getattr(s, 'quiz_score', None),
            'has_submission': bool(s.final_submission),
            'submission_id': s.final_submission.pk if s.final_submission else None
        })
        
    return JsonResponse({
        'status': 'ok',
        'counts': counts,
        'sessions': sessions_data
    })

@teacher_required
@require_POST
def extend_exam_session_view(request, session_pk):
    session = get_object_or_404(ExamSessions, pk=session_pk)
    if not _is_classroom_teacher(request.user, session.assignment.classroom):
        messages.error(request, 'Bạn không có quyền gia hạn phiên thi này.')
        return redirect('classrooms:classroom_list')
    try:
        minutes = int(request.POST.get('minutes') or 0)
    except ValueError:
        minutes = 0
    if minutes <= 0:
        messages.error(request, 'Số phút gia hạn không hợp lệ.')
    else:
        session.extra_time_minutes += minutes
        session.ends_at = (session.ends_at or timezone.now()) + timedelta(minutes=minutes)
        if session.status == ExamSessions.STATUS_EXPIRED:
            session.status = ExamSessions.STATUS_RUNNING
        session.save(update_fields=['extra_time_minutes', 'ends_at', 'status', 'updated_at'])
        _log_exam_event(session, 'teacher_extend', {'minutes': minutes, 'teacher_id': request.user.pk})
        messages.success(request, f'Đã gia hạn {minutes} phút.')
    return redirect('submissions:exam_monitor', assignment_pk=session.assignment_id)


@teacher_required
@require_POST
def force_submit_exam_session_view(request, session_pk):
    session = get_object_or_404(ExamSessions, pk=session_pk)
    assignment = session.assignment
    if not _is_classroom_teacher(request.user, assignment.classroom):
        messages.error(request, 'Bạn không có quyền force submit phiên thi này.')
        return redirect('classrooms:classroom_list')
    if session.final_submission_id:
        messages.info(request, 'Phiên thi đã có bài nộp.')
        return redirect('submissions:exam_monitor', assignment_pk=assignment.pk)
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        attempt = QuizAttempts.objects.filter(
            exam_session=session,
        ).select_related('assignment', 'student', 'exam_session').first()
        if not attempt:
            attempt, _created = _ensure_quiz_exam_attempt(assignment, session.student, session, request)
        if not attempt:
            session.status = ExamSessions.STATUS_EXPIRED
            session.save(update_fields=['status', 'updated_at'])
            _log_exam_event(session, 'teacher_force_submit_empty', {
                'teacher_id': request.user.pk,
                'submission_mode': 'quiz',
                'reason': 'no_quiz_questions',
            })
            messages.warning(request, 'Không có câu hỏi quiz để force submit; phiên đã được đánh dấu hết giờ.')
            return redirect('submissions:exam_monitor', assignment_pk=assignment.pk)
        if attempt.status == QuizAttempts.STATUS_IN_PROGRESS:
            submission = _grade_quiz_attempt(
                attempt,
                submit_status=QuizAttempts.STATUS_AUTO_SUBMITTED,
            )
        else:
            submission = attempt.submission
        if submission:
            _finalize_quiz_exam_session(
                attempt,
                submission,
                ExamSessions.STATUS_AUTO_SUBMITTED,
                'teacher_force_submit',
                {'teacher_id': request.user.pk, 'submission_mode': 'quiz'},
            )
            messages.success(request, 'Đã force submit quiz theo các đáp án đã autosave.')
        else:
            messages.error(request, 'Không thể tạo bài nộp quiz cho phiên này.')
        return redirect('submissions:exam_monitor', assignment_pk=assignment.pk)
    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        session.status = ExamSessions.STATUS_EXPIRED
        session.save(update_fields=['status', 'updated_at'])
        _log_exam_event(session, 'teacher_force_submit_empty', {
            'teacher_id': request.user.pk,
            'submission_mode': 'file',
            'reason': 'no_server_file_draft',
        })
        messages.warning(request, 'Bài thi file chưa có file nháp trên server để force submit; phiên đã được đánh dấu hết giờ.')
        return redirect('submissions:exam_monitor', assignment_pk=assignment.pk)
    code = session.latest_draft or ''
    if not code.strip():
        session.status = ExamSessions.STATUS_EXPIRED
        session.save(update_fields=['status', 'updated_at'])
        _log_exam_event(session, 'teacher_force_submit_empty', {'teacher_id': request.user.pk})
        messages.warning(request, 'Không có draft để force submit.')
        return redirect('submissions:exam_monitor', assignment_pk=assignment.pk)
    submission = Submissions.objects.create(
        assignment=assignment,
        student=session.student,
        code_content=code,
        language=session.current_language or (assignment.allowed_languages or ['python'])[0],
        status='pending',
        max_score=assignment.max_score,
    )
    session.final_submission = submission
    session.status = ExamSessions.STATUS_AUTO_SUBMITTED
    session.submitted_at = timezone.now()
    session.save(update_fields=['final_submission', 'status', 'submitted_at', 'updated_at'])
    _log_exam_event(session, 'teacher_force_submit', {'teacher_id': request.user.pk, 'submission_id': submission.pk})
    from .tasks import grade_submission_task
    grade_submission_task.delay(submission.pk)
    messages.success(request, 'Đã force submit draft hiện tại.')
    return redirect('submissions:exam_monitor', assignment_pk=assignment.pk)


@login_required
@require_POST
def save_draft_view(request):
    try:
        data = json.loads(request.body)
        assignment_pk = data.get('assignment_id')
        code_content = _sanitize_text_for_db(data.get('code', ''))
        language = _sanitize_text_for_db(data.get('language', 'python'))

        assignment = get_object_or_404(Assignments, pk=assignment_pk)
        if not can_solve_assignment(request.user, assignment):
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền lưu nháp bài này.'}, status=403)
        open_error = assignment_open_error(assignment, request.user)
        if open_error:
            return JsonResponse({'status': 'error', 'message': open_error}, status=400)
        if not validate_submission_language(assignment, language):
            return JsonResponse({'status': 'error', 'message': 'Ngôn ngữ này không được phép cho bài tập.'}, status=400)
        if assignment.is_exam and not _is_classroom_teacher(request.user, assignment.classroom):
            session = ExamSessions.objects.filter(
                assignment=assignment,
                student=request.user,
                status=ExamSessions.STATUS_RUNNING,
            ).first()
            if not session:
                return JsonResponse({'status': 'error', 'message': 'Bạn cần bắt đầu phiên thi trước khi lưu nháp.'}, status=400)
            session.latest_draft = code_content
            session.current_language = language
            session.last_seen_at = timezone.now()
            session.save(update_fields=['latest_draft', 'current_language', 'last_seen_at', 'updated_at'])
            _log_exam_event(session, 'autosaved', {'language': language, 'size': len(code_content)})

        draft, created = CodeDrafts.objects.update_or_create(
            assignment=assignment,
            student=request.user,
            language=language,
            defaults={'code_content': code_content},
        )
        return JsonResponse({'status': 'ok', 'saved_at': draft.last_saved_at.isoformat()})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu không hợp lệ.'}, status=400)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Có lỗi xảy ra khi lưu nháp.'}, status=400)


@login_required
@require_POST
def run_test_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk)
    is_teacher = _is_classroom_teacher(request.user, assignment.classroom)
    if not can_solve_assignment(request.user, assignment):
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền chạy bài này.'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    code = _sanitize_text_for_db(data.get('code', ''))
    language = _sanitize_text_for_db(data.get('language', 'python'))
    custom_input = data.get('custom_input')
    open_error = assignment_open_error(assignment, request.user)
    if open_error and not is_teacher:
        return JsonResponse({'status': 'error', 'message': open_error}, status=400)
    if not validate_submission_language(assignment, language):
        return JsonResponse({'status': 'error', 'message': 'Ngôn ngữ này không được phép cho bài tập.'}, status=400)
    exam_session = None
    if assignment.is_exam and not is_teacher:
        exam_session = ExamSessions.objects.filter(
            assignment=assignment,
            student=request.user,
            status=ExamSessions.STATUS_RUNNING,
        ).first()
        if not exam_session:
            return JsonResponse({'status': 'error', 'message': 'Bạn cần bắt đầu phiên thi trước khi chạy thử.'}, status=400)
        exam_session = _expire_session_if_needed(exam_session)
        if exam_session.status != ExamSessions.STATUS_RUNNING:
            return JsonResponse({'status': 'error', 'message': 'Phiên thi không còn hoạt động.'}, status=400)
        if custom_input is not None and not assignment.exam_allow_custom_input:
            return JsonResponse({'status': 'error', 'message': 'Bài thi này không cho phép custom input.'}, status=400)
        if custom_input is None and not assignment.exam_allow_sample_run:
            return JsonResponse({'status': 'error', 'message': 'Bài thi này không cho phép chạy testcase mẫu.'}, status=400)
        if assignment.exam_max_run_count and exam_session.run_count >= assignment.exam_max_run_count:
            return JsonResponse({'status': 'error', 'message': f'Bạn đã chạy thử tối đa {assignment.exam_max_run_count} lần.'}, status=400)
        exam_session.run_count += 1
        exam_session.current_language = language
        exam_session.last_seen_at = timezone.now()
        exam_session.save(update_fields=['run_count', 'current_language', 'last_seen_at', 'updated_at'])
        _log_exam_event(exam_session, 'run_test', {'custom': custom_input is not None, 'language': language})

    timeout, memory, docker_image, cpu_limit = _get_sandbox_config(language)

    if custom_input is not None:
        result = execute_code(code, language, custom_input, timeout, memory, docker_image, cpu_limit)
        return JsonResponse({
            'status': 'ok',
            'mode': 'custom',
            'output': _safe_json_text(result.stdout),
            'error': _safe_json_text(result.stderr, JSON_ERROR_LIMIT),
            'execution_time': result.execution_time,
            'timed_out': result.timed_out,
        })

    sample_testcases = Testcases.objects.filter(
        assignment=assignment, is_sample=True
    ).order_by('order_index')

    results = []
    for tc in sample_testcases:
        tc_result = run_testcase(
            code, language,
            tc.input_data or '',
            tc.expected_output or '',
            timeout, memory,
            docker_image, cpu_limit,
        )
        results.append({
            'name': tc.name or f'Test #{tc.order_index + 1}',
            'status': tc_result['status'],
            'passed': tc_result['passed'],
            'actual_output': _safe_json_text(tc_result['actual_output']),
            'expected_output': _safe_json_text(tc_result['expected_output']),
            'execution_time': tc_result['execution_time'],
            'error_message': _safe_json_text(tc_result['error_message'], JSON_ERROR_LIMIT),
        })

    passed = sum(1 for r in results if r['passed'])
    return JsonResponse({
        'status': 'ok',
        'mode': 'sample',
        'results': results,
        'passed': passed,
        'total': len(results),
    })


@login_required
@require_POST
def submit_code_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    classroom = assignment.classroom
    is_member = _is_classroom_member(request.user, classroom)
    is_teacher = _is_classroom_teacher(request.user, classroom)

    if not is_member and not is_teacher:
        return JsonResponse({'status': 'error', 'message': 'Bạn không phải thành viên của lớp này.'}, status=403)

    if assignment.max_attempts:
        existing_count = Submissions.objects.filter(
            assignment=assignment, student=request.user
        ).count()
        if existing_count >= assignment.max_attempts:
            return JsonResponse({
                'status': 'error',
                'message': f'Bạn đã nộp tối đa {assignment.max_attempts} lần.'
            }, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    code = _sanitize_text_for_db(data.get('code', ''))
    language = _sanitize_text_for_db(data.get('language', 'python'))
    session_id = data.get('session_id')

    if not code.strip():
        return JsonResponse({'status': 'error', 'message': 'Code không được để trống.'}, status=400)
    if not validate_submission_language(assignment, language):
        return JsonResponse({'status': 'error', 'message': 'Ngôn ngữ này không được phép cho bài tập.'}, status=400)

    now = timezone.now()
    is_late = False
    penalty_percent = 0
    exam_session = None
    open_error = assignment_open_error(assignment, request.user, now)
    if open_error and not is_teacher:
        return JsonResponse({'status': 'error', 'message': open_error}, status=400)

    # Kiểm tra exam mode: nếu exam đã hết giờ và không phải auto-submit thì từ chối
    if assignment.is_exam and assignment.exam_duration_minutes and not is_teacher:
        session_qs = ExamSessions.objects.filter(assignment=assignment, student=request.user)
        if session_id:
            session_qs = session_qs.filter(pk=session_id)
        exam_session = session_qs.first()
        if not exam_session:
            return JsonResponse({'status': 'error', 'message': 'Bạn cần bắt đầu phiên thi trước khi nộp bài.'}, status=400)
        exam_session = _expire_session_if_needed(exam_session, now)
        if exam_session.status not in (ExamSessions.STATUS_RUNNING, ExamSessions.STATUS_EXPIRED):
            return JsonResponse({'status': 'error', 'message': 'Phiên thi này đã kết thúc.'}, status=400)
        exam_deadline = exam_session.ends_at
        # Cho phép grace period 30 giây cho auto-submit
        if exam_deadline and now > exam_deadline + timedelta(seconds=assignment.exam_grace_seconds or 30):
            return JsonResponse({
                'status': 'error',
                'message': 'Đã hết thời gian làm bài. Không thể nộp.'
            }, status=400)

    if assignment.due_date and now > assignment.due_date:
        if not assignment.late_submission_allowed:
            return JsonResponse({
                'status': 'error',
                'message': 'Đã quá hạn nộp bài và bài tập không cho phép nộp muộn.'
            }, status=400)
        is_late = True
        penalty_percent = assignment.late_penalty_percent

    try:
        submission = Submissions.objects.create(
            assignment=assignment,
            student=request.user,
            code_content=code,
            language=language,
            status='pending',
            is_late=is_late,
            penalty_applied=penalty_percent,
            max_score=assignment.max_score,
        )
    except DataError:
        return JsonResponse({
            'status': 'error',
            'message': 'Dữ liệu bài nộp chứa ký tự không hợp lệ. Vui lòng kiểm tra code và thử lại.',
        }, status=400)

    if classroom.teacher and classroom.teacher_id != request.user.id:
        notify_user(
            classroom.teacher,
            title=f'Bài nộp mới: {assignment.title}',
            message=f'{request.user.get_full_name() or request.user.username} vừa nộp bài.',
            link=f'/submissions/detail/{submission.pk}/',
            notification_type='submission_submitted',
            actor=request.user,
            metadata={'submission_id': submission.pk, 'assignment_id': assignment.pk},
        )

    use_async = not getattr(django_settings, 'CELERY_TASK_ALWAYS_EAGER', True)

    if use_async:
        from .tasks import grade_submission_task
        if exam_session:
            exam_session.final_submission = submission
            exam_session.status = ExamSessions.STATUS_SUBMITTED
            exam_session.submitted_at = timezone.now()
            exam_session.latest_draft = code
            exam_session.current_language = language
            exam_session.save(update_fields=[
                'final_submission', 'status', 'submitted_at',
                'latest_draft', 'current_language', 'updated_at',
            ])
            _log_exam_event(exam_session, 'submitted', {'submission_id': submission.pk, 'async': True})
        grade_submission_task.delay(submission.pk)
        return JsonResponse({
            'status': 'ok',
            'submission_id': submission.pk,
            'async': True,
            'message': 'Bài nộp đang được chấm điểm...',
        })

    all_testcases = Testcases.objects.filter(assignment=assignment).order_by('order_index')
    total_weight = sum(tc.weight for tc in all_testcases)

    if total_weight == 0:
        submission.status = 'finished'
        submission.total_score = 0
        submission.total_testcases = 0
        submission.passed_testcases = 0
        submission.save()
        if exam_session:
            exam_session.final_submission = submission
            exam_session.status = ExamSessions.STATUS_SUBMITTED
            exam_session.submitted_at = timezone.now()
            exam_session.latest_draft = code
            exam_session.current_language = language
            exam_session.save(update_fields=[
                'final_submission', 'status', 'submitted_at',
                'latest_draft', 'current_language', 'updated_at',
            ])
            _log_exam_event(exam_session, 'submitted', {'submission_id': submission.pk, 'score': 0})
        notify_user(
            request.user,
            title=f'Bài nộp đã được chấm: {assignment.title}',
            message='Bài nộp không có testcase nào để chấm. Điểm hiện tại là 0.',
            link=f'/submissions/detail/{submission.pk}/',
            notification_type='submission_graded',
            actor=classroom.teacher,
            metadata={'submission_id': submission.pk, 'assignment_id': assignment.pk},
        )
        return JsonResponse({
            'status': 'ok',
            'submission_id': submission.pk,
            'message': 'Bài nộp không có testcase nào để chấm.',
        })

    submission.status = 'running'
    submission.save(update_fields=['status'])

    timeout, memory, docker_image, cpu_limit = _get_sandbox_config(language)
    passed_count = 0
    total_score = 0
    total_exec_time = 0
    max_memory = 0

    try:
        for tc in all_testcases:
            tc_result = run_testcase(
                code, language,
                tc.input_data or '',
                tc.expected_output or '',
                tc.timeout_override or timeout,
                tc.memory_override or memory,
                docker_image,
                cpu_limit,
            )

            score_earned = 0
            if tc_result['passed']:
                passed_count += 1
                score_earned = (tc.weight / total_weight) * assignment.max_score

            _create_submission_detail_with_fallback(
                submission=submission,
                testcase=tc,
                tc_result=tc_result,
                score_earned=score_earned,
            )

            total_score += score_earned
            total_exec_time += tc_result['execution_time']
            max_memory = max(max_memory, tc_result['memory_usage'])

        if is_late and penalty_percent > 0:
            penalty_amount = total_score * (penalty_percent / 100)
            total_score = max(0, total_score - penalty_amount)

        submission.status = 'finished'
        submission.total_score = round(total_score, 2)
        submission.passed_testcases = passed_count
        submission.total_testcases = all_testcases.count()
        submission.execution_time = round(total_exec_time, 2)
        submission.memory_usage = round(max_memory, 2)
        submission.save()
        if exam_session:
            exam_session.final_submission = submission
            exam_session.status = ExamSessions.STATUS_SUBMITTED
            exam_session.submitted_at = timezone.now()
            exam_session.latest_draft = code
            exam_session.current_language = language
            exam_session.save(update_fields=[
                'final_submission', 'status', 'submitted_at',
                'latest_draft', 'current_language', 'updated_at',
            ])
            _log_exam_event(exam_session, 'submitted', {'submission_id': submission.pk, 'score': submission.total_score})

        update_assignment_statistics(assignment)
        notify_user(
            request.user,
            title=f'Bài nộp đã được chấm: {assignment.title}',
            message=f'Điểm của bạn: {submission.total_score}/{submission.max_score}.',
            link=f'/submissions/detail/{submission.pk}/',
            notification_type='submission_graded',
            actor=classroom.teacher,
            metadata={'submission_id': submission.pk, 'assignment_id': assignment.pk},
        )

        return JsonResponse({
            'status': 'ok',
            'submission_id': submission.pk,
            'total_score': submission.total_score,
            'max_score': submission.max_score,
            'passed': passed_count,
            'total': all_testcases.count(),
            'is_late': is_late,
            'penalty_applied': penalty_percent,
        })
    except DataError:
        logger.exception('DataError while grading submission=%s', submission.pk)
        submission.status = 'error'
        submission.save(update_fields=['status'])
        return JsonResponse({
            'status': 'error',
            'message': 'Không thể lưu kết quả chấm vì dữ liệu đầu ra không hợp lệ. Vui lòng thử lại.',
        }, status=400)
    except Exception:
        logger.exception('Unexpected error while grading submission=%s', submission.pk)
        submission.status = 'error'
        submission.save(update_fields=['status'])
        return JsonResponse({
            'status': 'error',
            'message': 'Lỗi hệ thống khi chấm bài. Vui lòng thử lại sau.',
        }, status=500)


@login_required
def submission_history_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk)
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    submissions = Submissions.objects.filter(
        assignment=assignment, student=request.user
    ).prefetch_related('files', 'feedback_files').order_by('-submitted_at')
    submission_count = submissions.count()
    open_error = assignment_open_error(assignment, request.user)
    file_requirements = None
    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        file_requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).first()
    can_start_new_submission = (
        not is_teacher
        and not assignment.is_exam
        and not open_error
        and (not assignment.max_attempts or submission_count < assignment.max_attempts)
        and (
            assignment.submission_mode != Assignments.SUBMISSION_FILE
            or not file_requirements
            or file_requirements.allow_resubmit
            or submission_count == 0
        )
    )

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'submissions': submissions,
        'is_teacher': is_teacher,
        'grades_visible': is_teacher or bool(assignment.grades_released_at),
        'can_start_new_submission': can_start_new_submission,
        'submission_count': submission_count,
    }
    return render(request, 'submissions/history.html', context)


@login_required
def submission_detail_view(request, pk):
    submission = get_object_or_404(Submissions, pk=pk)
    assignment = submission.assignment
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)

    if not is_teacher and submission.student != request.user:
        messages.error(request, 'Bạn không có quyền xem bài nộp này.')
        return redirect('classrooms:classroom_list')

    # If it's a quiz, redirect to quiz_result_view if possible
    if submission.submission_mode_snapshot == Assignments.SUBMISSION_QUIZ:
        from .models import QuizAttempts
        attempt = QuizAttempts.objects.filter(submission=submission).first()
        if attempt:
            return redirect('submissions:quiz_result', attempt_pk=attempt.pk)

    details = SubmissionDetails.objects.filter(
        submission=submission
    ).select_related('testcase').order_by('testcase__order_index', 'id')

    sample_details = [d for d in details if getattr(d.testcase, 'is_sample', False)]
    hidden_details = [d for d in details if not getattr(d.testcase, 'is_sample', False)]
    
    # Calculate stats for display
    sample_passed = sum(1 for d in sample_details if d.result_status in ('accepted', 'passed'))
    hidden_passed = sum(1 for d in hidden_details if d.result_status in ('accepted', 'passed'))

    code_comments = CodeComments.objects.filter(
        submission=submission
    ).select_related('teacher').order_by('line_number')

    code_lines = submission.code_content.split('\n') if submission.code_content else []
    submission_files = submission.files.all().order_by('uploaded_at')
    feedback_files = submission.feedback_files.select_related('uploaded_by').order_by('-uploaded_at')
    grades_visible = is_teacher or bool(assignment.grades_released_at)
    feedback_visible = is_teacher or (grades_visible and assignment.show_feedback_after_release)

    comments_by_line = {}
    for comment in code_comments:
        if comment.line_number not in comments_by_line:
            comments_by_line[comment.line_number] = []
        comments_by_line[comment.line_number].append(comment)

    visible_details = []
    for d in details:
        if is_teacher:
            visible_details.append(d)
        elif d.testcase and d.testcase.is_sample:
            visible_details.append(d)
        elif assignment.show_testcase_result:
            visible_details.append(d)

    rubric_scores = RubricScores.objects.filter(
        submission=submission,
        rubric__assignment=assignment,
        rubric__is_active=True,
    ).select_related('rubric').order_by('rubric__order_index', 'rubric_id')
    rubric_score_total = sum(score.score for score in rubric_scores)
    rubric_max_total = sum(score.rubric.max_points for score in rubric_scores)
    owner_submission_count = Submissions.objects.filter(
        assignment=assignment,
        student=submission.student,
    ).count()
    open_error = assignment_open_error(assignment, submission.student)
    file_requirements = None
    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        file_requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).first()
    can_start_new_submission = (
        not is_teacher
        and not assignment.is_exam
        and not open_error
        and (not assignment.max_attempts or owner_submission_count < assignment.max_attempts)
        and (
            assignment.submission_mode != Assignments.SUBMISSION_FILE
            or not file_requirements
            or file_requirements.allow_resubmit
            or owner_submission_count == 0
        )
    )

    sample_stats = {
        'passed': sample_passed,
        'total': len(sample_details)
    }
    hidden_stats = {
        'passed': hidden_passed,
        'total': len(hidden_details)
    }

    context = {
        'submission': submission,
        'assignment': assignment,
        'classroom': classroom,
        'details': visible_details,
        'sample_details': sample_details,
        'hidden_details': hidden_details,
        'sample_stats': sample_stats,
        'hidden_stats': hidden_stats,
        'all_details': details,
        'code_comments': code_comments,
        'comments_by_line': comments_by_line,
        'code_lines': code_lines,
        'submission_files': submission_files,
        'feedback_files': feedback_files if feedback_visible else [],
        'is_file_submission': submission.submission_mode_snapshot == Assignments.SUBMISSION_FILE or assignment.submission_mode == Assignments.SUBMISSION_FILE,
        'grades_visible': grades_visible,
        'feedback_visible': feedback_visible,
        'final_score': submission.manual_score if submission.manual_score is not None else submission.total_score,
        'rubric_scores': rubric_scores,
        'rubric_score_total': rubric_score_total,
        'rubric_max_total': rubric_max_total,
        'is_teacher': is_teacher,
        'can_start_new_submission': can_start_new_submission,
        'owner_submission_count': owner_submission_count,
    }
    return render(request, 'submissions/detail.html', context)


@teacher_required
def submission_list_teacher_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xem danh sách bài nộp.')
        return redirect('classrooms:classroom_list')

    if request.method == 'POST' and request.POST.get('action') == 'quick_grade':
        selected_ids = request.POST.getlist('selected_submission')
        graded_count = 0
        with transaction.atomic():
            for submission_id in selected_ids:
                score_raw = (request.POST.get(f'quick_score_{submission_id}') or '').strip()
                comment = (request.POST.get(f'quick_comment_{submission_id}') or '').strip()
                if score_raw == '' and comment == '':
                    continue
                try:
                    score = float(score_raw) if score_raw != '' else None
                except ValueError:
                    messages.error(request, f'Điểm của bài #{submission_id} không hợp lệ.')
                    continue
                submission = Submissions.objects.filter(
                    pk=submission_id,
                    assignment=assignment,
                ).select_related('student').first()
                if not submission:
                    continue
                if score is not None and (score < 0 or score > submission.max_score):
                    messages.error(request, f'Điểm của bài #{submission_id} phải nằm trong 0 - {submission.max_score}.')
                    continue
                before_grade = {
                    'manual_score': submission.manual_score,
                    'total_score': submission.total_score,
                    'status': submission.status,
                    'teacher_comment': submission.teacher_comment,
                }
                if score is not None:
                    submission.manual_score = score
                    submission.status = 'finished'
                if comment:
                    submission.teacher_comment = comment
                submission.graded_by = request.user
                submission.graded_at = timezone.now()
                submission.save(update_fields=[
                    'manual_score', 'teacher_comment', 'graded_by', 'graded_at', 'status'
                ])
                _create_grade_change_log(
                    submission,
                    request.user,
                    before_grade,
                    reason='quick_grade',
                    metadata={'assignment_id': assignment.pk},
                )
                notify_user(
                    submission.student,
                    title=f'Giáo viên đã chấm bài: {assignment.title}',
                    message=f'Điểm hiện tại: {submission.manual_score if submission.manual_score is not None else submission.total_score}/{submission.max_score}.',
                    link=f'/submissions/detail/{submission.pk}/',
                    notification_type='submission_graded',
                    actor=request.user,
                    metadata={'submission_id': submission.pk, 'assignment_id': assignment.pk, 'quick_grade': True},
                )
                graded_count += 1
        if graded_count:
            update_assignment_statistics(assignment)
            messages.success(request, f'Đã chấm nhanh {graded_count} bài nộp.')
        else:
            messages.info(request, 'Chưa có bài nào được chấm nhanh.')
        return redirect(f"{reverse('submissions:teacher_list', kwargs={'assignment_pk': assignment.pk})}?{request.GET.urlencode()}")

    submissions = Submissions.objects.filter(
        assignment=assignment
    ).select_related('student').prefetch_related('files', 'feedback_files').order_by('-submitted_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        submissions = submissions.filter(status=status_filter)

    submitted_filter = request.GET.get('submitted', 'submitted')
    if submitted_filter not in {'all', 'submitted', 'missing'}:
        submitted_filter = 'submitted'

    grade_filter = request.GET.get('grade', '')
    if grade_filter == 'graded':
        submissions = submissions.filter(status='finished')
    elif grade_filter == 'ungraded':
        submissions = submissions.exclude(status='finished')

    late_filter = request.GET.get('late', '')
    if late_filter == 'late':
        submissions = submissions.filter(is_late=True)
    elif late_filter == 'ontime':
        submissions = submissions.filter(is_late=False)

    file_ext_filter = (request.GET.get('file_ext') or '').strip().lower()
    if file_ext_filter:
        if not file_ext_filter.startswith('.'):
            file_ext_filter = f'.{file_ext_filter}'
        submissions = submissions.filter(files__extension__iexact=file_ext_filter).distinct()

    score_min = request.GET.get('score_min')
    score_max = request.GET.get('score_max')
    try:
        if score_min not in (None, ''):
            submissions = submissions.filter(manual_score__gte=float(score_min))
    except ValueError:
        score_min = ''
    try:
        if score_max not in (None, ''):
            submissions = submissions.filter(manual_score__lte=float(score_max))
    except ValueError:
        score_max = ''

    missing_members = []
    if submitted_filter == 'missing':
        submitted_student_ids = Submissions.objects.filter(
            assignment=assignment,
        ).values_list('student_id', flat=True)
        missing_members = ClassroomMembers.objects.filter(
            classroom=classroom,
            status='approved',
        ).exclude(student_id__in=submitted_student_ids).select_related('student').order_by('student__username')
        submissions = submissions.none()

    file_extensions = SubmissionFiles.objects.filter(
        submission__assignment=assignment,
        extension__isnull=False,
    ).exclude(extension='').values_list('extension', flat=True).distinct().order_by('extension')

    paginator = Paginator(submissions, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'submissions': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'submitted_filter': submitted_filter,
        'grade_filter': grade_filter,
        'late_filter': late_filter,
        'file_ext_filter': file_ext_filter,
        'score_min': score_min or '',
        'score_max': score_max or '',
        'file_extensions': file_extensions,
        'missing_members': missing_members,
        'csv_export_url': reverse('submissions:export_grades_csv', kwargs={'assignment_pk': assignment.pk}) + '?' + request.GET.urlencode(),
    }
    return render(request, 'submissions/list_teacher.html', context)


@teacher_required
def export_assignment_grades_csv_view(request, assignment_pk):
    """Xuất điểm của sinh viên cho một bài tập cụ thể ra file CSV."""
    assignment = get_object_or_404(Assignments, pk=assignment_pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        return HttpResponse("Unauthorized", status=403)

    # Lấy danh sách bài nộp (áp dụng tương tự các filter như view danh sách)
    submissions = Submissions.objects.filter(
        assignment=assignment
    ).select_related('student').order_by('student__username', '-submitted_at')

    # Chỉ lấy bài nộp mới nhất của mỗi sinh viên cho báo cáo điểm
    student_latest_submissions = {}
    for sub in submissions:
        if sub.student_id not in student_latest_submissions:
            student_latest_submissions[sub.student_id] = sub

    # Chuẩn bị CSV
    response = HttpResponse(content_type='text/csv')
    filename = slugify(f"grades_{assignment.title}_{timezone.now().strftime('%Y%m%d')}")
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    # Thêm BOM cho Excel hiển thị đúng tiếng Việt (UTF-8)
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([
        'MSSV/Username', 'Họ tên', 'Trạng thái', 'Điểm hệ thống', 
        'Điểm chấm tay', 'Tổng điểm', 'Thang điểm', 'Nộp muộn', 'Ngày nộp'
    ])

    # Lấy tất cả thành viên lớp để bao gồm cả những người chưa nộp
    members = ClassroomMembers.objects.filter(
        classroom=classroom, status='approved'
    ).select_related('student').order_by('student__username')

    for member in members:
        student = member.student
        sub = student_latest_submissions.get(student.id)
        
        if sub:
            final_score = sub.manual_score if sub.manual_score is not None else sub.total_score
            writer.writerow([
                student.username,
                student.get_full_name() or student.username,
                sub.status,
                sub.total_score,
                sub.manual_score if sub.manual_score is not None else '',
                final_score,
                sub.max_score,
                'Có' if sub.is_late else 'Không',
                sub.submitted_at.strftime('%d/%m/%Y %H:%M')
            ])
        else:
            writer.writerow([
                student.username,
                student.get_full_name() or student.username,
                'Chưa nộp',
                0, '', 0, assignment.max_score, '', ''
            ])

    return response


@teacher_required
def download_submission_files_zip_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền tải file bài nộp.')
        return redirect('classrooms:classroom_list')

    files = SubmissionFiles.objects.filter(
        submission__assignment=assignment,
    ).select_related('submission', 'submission__student').order_by('submission__student__username', 'uploaded_at')
    buffer = io.BytesIO()
    errors = []
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            'README.txt',
            (
                'DevLearn submission files\n'
                f'Assignment: {assignment.title}\n'
                f'Classroom: {classroom.name}\n'
                f'Downloaded by: {request.user.username} ({request.user.pk})\n'
                f'Downloaded at: {timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M:%S")}\n'
            ),
        )
        for index, item in enumerate(files, start=1):
            student = item.submission.student
            student_folder = slugify(student.get_full_name() or student.username) or f'student-{student.pk}'
            file_name = _safe_zip_name(item.file_name, f'file-{item.pk}')
            arcname = f'{student_folder}/submission-{item.submission_id}/{index:03d}-{file_name}'
            _log_file_access(request, item.submission, 'submission_files_zip_download', item)
            try:
                with urllib.request.urlopen(item.file_url, timeout=8) as response:
                    archive.writestr(arcname, response.read())
            except Exception as exc:
                errors.append(f'{arcname}: {item.file_url} ({exc})')
                archive.writestr(f'{arcname}.url.txt', item.file_url or 'missing url')
        if errors:
            archive.writestr('_download_errors.txt', '\n'.join(errors))
    buffer.seek(0)
    filename = f"{slugify(classroom.name) or 'class'}_{slugify(assignment.title) or 'assignment'}_submission_files.zip"
    logger.info(
        'file_access event=submission_files_zip_download assignment=%s actor=%s files=%s errors=%s',
        assignment.pk,
        request.user.pk,
        files.count(),
        len(errors),
    )
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@teacher_required
def grade_submission_view(request, pk):
    submission = get_object_or_404(Submissions, pk=pk)
    assignment = submission.assignment
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền chấm bài.')
        return redirect('classrooms:classroom_list')

    details = SubmissionDetails.objects.filter(
        submission=submission
    ).select_related('testcase').order_by('testcase__order_index')

    sample_details = [d for d in details if getattr(d.testcase, 'is_sample', False)]
    hidden_details = [d for d in details if not getattr(d.testcase, 'is_sample', False)]
    
    # Calculate stats for display
    sample_passed = sum(1 for d in sample_details if d.result_status in ('accepted', 'passed'))
    hidden_passed = sum(1 for d in hidden_details if d.result_status in ('accepted', 'passed'))

    code_comments = CodeComments.objects.filter(
        submission=submission
    ).select_related('teacher').order_by('line_number')

    code_lines = submission.code_content.split('\n') if submission.code_content else []
    rubrics = list(Rubrics.objects.filter(
        assignment=assignment,
        is_active=True,
    ).order_by('order_index', 'id'))
    rubric_scores = {
        score.rubric_id: score
        for score in RubricScores.objects.filter(
            submission=submission,
            rubric__assignment=assignment,
        ).select_related('rubric')
    }
    rubric_items = [
        {
            'rubric': rubric,
            'score': rubric_scores.get(rubric.pk),
        }
        for rubric in rubrics
    ]
    rubric_total = sum(rubric.max_points for rubric in rubrics)
    feedback_templates = FeedbackTemplates.objects.filter(
        teacher=request.user,
        is_active=True,
    ).order_by('category', 'title')
    feedback_template_form = FeedbackTemplateForm()
    submission_files = submission.files.all().order_by('uploaded_at')
    feedback_files = submission.feedback_files.select_related('uploaded_by').order_by('-uploaded_at')
    quiz_attempt = QuizAttempts.objects.filter(submission=submission).prefetch_related(
        'answers', 'answers__selected_choices'
    ).first()
    quiz_questions = _quiz_questions_for_attempt(quiz_attempt) if quiz_attempt else []
    grade_change_logs = submission.grade_change_logs.select_related('changed_by')[:8]
    ai_suggestions = submission.ai_suggestions.select_related(
        'accepted_by_teacher', 'quiz_answer',
    )[:5]

    comments_by_line = {}
    for comment in code_comments:
        if comment.line_number not in comments_by_line:
            comments_by_line[comment.line_number] = []
        comments_by_line[comment.line_number].append(comment)

    if request.method == 'POST' and request.POST.get('action') == 'create_feedback_template':
        feedback_template_form = FeedbackTemplateForm(request.POST)
        if feedback_template_form.is_valid():
            template = feedback_template_form.save(commit=False)
            template.teacher = request.user
            template.save()
            messages.success(request, 'Đã lưu feedback mẫu.')
            return redirect('submissions:grade', pk=pk)
    elif request.method == 'POST' and request.POST.get('action') == 'upload_feedback_file':
        uploaded_file = request.FILES.get('feedback_file')
        if not uploaded_file:
            messages.error(request, 'Vui lòng chọn file phản hồi.')
        else:
            try:
                _, error = _upload_feedback_file(
                    submission,
                    uploaded_file,
                    request.user,
                    note=(request.POST.get('feedback_file_note') or '').strip(),
                )
                if error:
                    messages.error(request, error)
                else:
                    messages.success(request, 'Đã tải file phản hồi cho bài nộp.')
            except Exception:
                logger.exception('Failed to upload feedback file submission=%s user=%s', submission.pk, request.user.pk)
                messages.error(request, 'Có lỗi xảy ra khi tải file phản hồi.')
        return redirect('submissions:grade', pk=pk)
    elif request.method == 'POST':
        use_rubric_score = bool(request.POST.get('use_rubric_score')) and bool(rubrics)
        form = GradeSubmissionForm(
            request.POST,
            max_score=submission.max_score,
            require_manual=not use_rubric_score,
        )
        rubric_errors = []
        parsed_rubric_scores = []

        if form.is_valid():
            rubric_total_score = 0
            for rubric in rubrics:
                raw_score = (request.POST.get(f'rubric_score_{rubric.pk}') or '').strip()
                raw_comment = (request.POST.get(f'rubric_comment_{rubric.pk}') or '').strip()
                if raw_score == '':
                    score = 0
                else:
                    try:
                        score = float(raw_score)
                    except ValueError:
                        rubric_errors.append(f'Điểm "{rubric.name}" không hợp lệ.')
                        score = 0
                if score < 0:
                    rubric_errors.append(f'Điểm "{rubric.name}" không được âm.')
                if score > rubric.max_points:
                    rubric_errors.append(f'Điểm "{rubric.name}" không được vượt quá {rubric.max_points}.')
                parsed_rubric_scores.append((rubric, max(0, min(score, rubric.max_points)), raw_comment))
                rubric_total_score += max(0, min(score, rubric.max_points))

            manual_score = round(rubric_total_score, 2) if use_rubric_score else form.cleaned_data['manual_score']
            if manual_score is None:
                rubric_errors.append('Vui lòng nhập điểm thủ công hoặc bật dùng tổng rubric.')
            elif manual_score > submission.max_score:
                rubric_errors.append(f'Điểm cuối cùng không được vượt quá {submission.max_score}.')

            if rubric_errors:
                for error in rubric_errors:
                    messages.error(request, error)
            else:
                with transaction.atomic():
                    before_grade = {
                        'manual_score': submission.manual_score,
                        'total_score': submission.total_score,
                        'status': submission.status,
                        'teacher_comment': submission.teacher_comment,
                    }
                    for rubric, score, comment in parsed_rubric_scores:
                        RubricScores.objects.update_or_create(
                            submission=submission,
                            rubric=rubric,
                            defaults={'score': score, 'comment': comment},
                        )
                    submission.manual_score = manual_score
                    submission.teacher_comment = form.cleaned_data['teacher_comment']
                    submission.graded_by = request.user
                    submission.graded_at = timezone.now()
                    submission.status = 'finished'
                    submission.save(update_fields=[
                        'manual_score', 'teacher_comment', 'graded_by', 'graded_at', 'status'
                    ])
                    _create_grade_change_log(
                        submission,
                        request.user,
                        before_grade,
                        reason='manual_grade',
                        metadata={
                            'used_rubric_score': use_rubric_score,
                            'rubric_total_score': round(rubric_total_score, 2),
                            'rubric_count': len(parsed_rubric_scores),
                            'submission_mode': submission.submission_mode_snapshot,
                        },
                    )
                    log_activity(
                        request.user,
                        'SUBMISSION_MANUAL_GRADE',
                        'submissions',
                        submission.pk,
                        metadata={
                            'submission_id': submission.pk,
                            'assignment_id': assignment.pk,
                            'student_id': submission.student_id,
                            'submission_mode': submission.submission_mode_snapshot,
                            'previous_manual_score': before_grade['manual_score'],
                            'new_manual_score': submission.manual_score,
                            'previous_status': before_grade['status'],
                            'new_status': submission.status,
                            'used_rubric_score': use_rubric_score,
                        },
                        request=request,
                    )
                    uploaded_file = request.FILES.get('feedback_file')
                    if uploaded_file:
                        try:
                            _, error = _upload_feedback_file(
                                submission,
                                uploaded_file,
                                request.user,
                                note=(request.POST.get('feedback_file_note') or '').strip(),
                            )
                            if error:
                                messages.error(request, error)
                        except Exception:
                            logger.exception('Failed to upload feedback file submission=%s user=%s', submission.pk, request.user.pk)
                            messages.error(request, 'Đã lưu điểm nhưng chưa tải được file phản hồi.')
                update_assignment_statistics(assignment)
                notify_user(
                    submission.student,
                    title=f'Giáo viên đã chấm bài: {assignment.title}',
                    message=f'Điểm thủ công: {submission.manual_score}/{submission.max_score}.',
                    link=f'/submissions/detail/{submission.pk}/',
                    notification_type='submission_graded',
                    actor=request.user,
                    metadata={'submission_id': submission.pk, 'assignment_id': assignment.pk},
                )
                messages.success(request, 'Đã chấm điểm thành công!')
                return redirect('submissions:grade', pk=pk)
    else:
        form = GradeSubmissionForm(initial={
            'manual_score': submission.manual_score or submission.total_score,
            'teacher_comment': submission.teacher_comment or '',
        }, max_score=submission.max_score)

    comment_form = CodeCommentForm()

    all_submissions = Submissions.objects.filter(
        assignment=assignment
    ).select_related('student').order_by('-submitted_at')
    current_index = None
    prev_submission = None
    next_submission = None
    for i, s in enumerate(all_submissions):
        if s.pk == submission.pk:
            current_index = i
            if i > 0:
                prev_submission = all_submissions[i - 1]
            if i < len(all_submissions) - 1:
                next_submission = all_submissions[i + 1]
            break

    context = {
        'submission': submission,
        'assignment': assignment,
        'classroom': classroom,
        'details': details,
        'sample_details': sample_details,
        'hidden_details': hidden_details,
        'sample_stats': {'passed': sample_passed, 'total': len(sample_details)},
        'hidden_stats': {'passed': hidden_passed, 'total': len(hidden_details)},
        'code_comments': code_comments,
        'comments_by_line': comments_by_line,
        'code_lines': code_lines,
        'form': form,
        'comment_form': comment_form,
        'rubrics': rubrics,
        'rubric_items': rubric_items,
        'rubric_scores': rubric_scores,
        'rubric_total': rubric_total,
        'feedback_templates': feedback_templates,
        'feedback_template_form': feedback_template_form,
        'submission_files': submission_files,
        'feedback_files': feedback_files,
        'is_file_submission': submission.submission_mode_snapshot == Assignments.SUBMISSION_FILE or assignment.submission_mode == Assignments.SUBMISSION_FILE,
        'is_quiz_submission': submission.submission_mode_snapshot == Assignments.SUBMISSION_QUIZ or assignment.submission_mode == Assignments.SUBMISSION_QUIZ,
        'quiz_attempt': quiz_attempt,
        'quiz_questions': quiz_questions,
        'grade_change_logs': grade_change_logs,
        'ai_suggestions': ai_suggestions,
        'all_submissions': all_submissions,
        'current_index': current_index,
        'prev_submission': prev_submission,
        'next_submission': next_submission,
        'total_submissions': all_submissions.count(),
    }
    return render(request, 'submissions/grade.html', context)


@teacher_required
@require_POST
def delete_feedback_template_view(request, pk, template_pk):
    submission = get_object_or_404(Submissions, pk=pk)
    classroom = submission.assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền thao tác trong lớp này.')
        return redirect('classrooms:classroom_list')
    template = get_object_or_404(
        FeedbackTemplates,
        pk=template_pk,
        teacher=request.user,
        is_active=True,
    )
    template.is_active = False
    template.save(update_fields=['is_active'])
    messages.success(request, 'Đã xóa feedback mẫu.')
    return redirect('submissions:grade', pk=pk)


@teacher_required
@require_POST
def add_code_comment_view(request, pk):
    submission = get_object_or_404(Submissions, pk=pk)
    classroom = submission.assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        return JsonResponse({'status': 'error', 'message': 'Không có quyền.'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    line_number = data.get('line_number')
    comment_text = data.get('comment_text', '').strip()

    if not line_number or not comment_text:
        return JsonResponse({'status': 'error', 'message': 'Thiếu thông tin.'}, status=400)

    comment = CodeComments.objects.create(
        submission=submission,
        teacher=request.user,
        line_number=line_number,
        comment_text=comment_text,
    )
    notify_user(
        submission.student,
        title=f'Nhận xét mới: {submission.assignment.title}',
        message=f'Giáo viên đã nhận xét dòng {line_number}.',
        link=f'/submissions/detail/{submission.pk}/',
        notification_type='code_comment_added',
        actor=request.user,
        metadata={'submission_id': submission.pk, 'line_number': line_number},
    )
    return JsonResponse({
        'status': 'ok',
        'comment_id': comment.pk,
        'line_number': comment.line_number,
        'comment_text': comment.comment_text,
        'teacher_name': request.user.get_full_name() or request.user.username,
        'created_at': comment.created_at.isoformat(),
    })


@login_required
@require_POST
def resolve_comment_view(request, pk):
    comment = get_object_or_404(CodeComments, pk=pk)
    classroom = comment.submission.assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)

    if not is_teacher and comment.submission.student != request.user:
        return JsonResponse({'status': 'error', 'message': 'Không có quyền.'}, status=403)

    comment.is_resolved = not comment.is_resolved
    comment.save(update_fields=['is_resolved'])
    return JsonResponse({'status': 'ok', 'is_resolved': comment.is_resolved})
