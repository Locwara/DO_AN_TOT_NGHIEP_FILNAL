import json
import logging
import csv
from django.conf import settings as django_settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import DataError, transaction, models
from datetime import timedelta
from django.core.paginator import Paginator

from core.decorators import teacher_required
from apps.classrooms.views import _is_classroom_teacher, _is_classroom_member
from apps.classrooms.models import ClassroomMembers
from apps.assignments.models import Assignments, Testcases, Rubrics
from apps.administation.models import ProgrammingLanguages, SandboxConfigs
from apps.notifications.services import notify_user
from services.docker_service import execute_code, run_testcase
from .models import (
    Submissions, SubmissionDetails, CodeDrafts, CodeComments,
    RubricScores, FeedbackTemplates, ExamSessions, ExamEvents,
)
from .forms import GradeSubmissionForm, CodeCommentForm, FeedbackTemplateForm
from .utils import (
    assignment_open_error, can_solve_assignment, validate_submission_language,
    update_assignment_statistics,
)

logger = logging.getLogger(__name__)


EXAM_WARNING_EVENTS = {
    'tab_hidden', 'focus_lost', 'fullscreen_exit', 'paste',
    'copy', 'context_menu', 'devtools_hint',
}

JSON_OUTPUT_LIMIT = 10000
JSON_ERROR_LIMIT = 4000


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


def _expire_session_if_needed(session, now=None):
    now = now or timezone.now()
    grace = session.assignment.exam_grace_seconds or 30
    if (
        session.status == ExamSessions.STATUS_RUNNING
        and session.ends_at
        and now > session.ends_at + timedelta(seconds=grace)
    ):
        session.status = ExamSessions.STATUS_EXPIRED
        session.save(update_fields=['status', 'updated_at'])
        _log_exam_event(session, 'expired', {'reason': 'server_time_exceeded'})
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
    selected_lang = request.GET.get(
        'lang',
        exam_session.current_language if exam_session and exam_session.current_language else (default_lang.name if default_lang else 'python'),
    )

    draft = CodeDrafts.objects.filter(
        assignment=assignment, student=request.user, language=selected_lang
    ).first()

    initial_code = ''
    if exam_session and exam_session.latest_draft:
        initial_code = exam_session.latest_draft
    elif draft:
        initial_code = draft.code_content or ''
    elif default_lang and default_lang.default_template:
        initial_code = default_lang.default_template

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
    return render(request, 'submissions/exam_lobby.html', {
        'assignment': assignment,
        'classroom': classroom,
        'session': session,
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
    sessions = ExamSessions.objects.filter(
        assignment=assignment,
    ).select_related('student', 'final_submission').order_by('student__username')
    status_filter = request.GET.get('status', 'all')
    if status_filter in {
        ExamSessions.STATUS_RUNNING,
        ExamSessions.STATUS_SUBMITTED,
        ExamSessions.STATUS_AUTO_SUBMITTED,
        ExamSessions.STATUS_EXPIRED,
        ExamSessions.STATUS_CANCELLED,
    }:
        if status_filter == ExamSessions.STATUS_SUBMITTED:
            sessions = sessions.filter(status__in=[
                ExamSessions.STATUS_SUBMITTED,
                ExamSessions.STATUS_AUTO_SUBMITTED,
            ])
        else:
            sessions = sessions.filter(status=status_filter)
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
    return render(request, 'submissions/exam_monitor.html', {
        'assignment': assignment,
        'classroom': classroom,
        'sessions': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'counts': counts,
    })


@teacher_required
def exam_monitor_export_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_exam=True)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất báo cáo phòng thi này.')
        return redirect('classrooms:classroom_list')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename=\"exam-report-{assignment.pk}.csv\"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([
        'Username', 'Ho ten', 'Email', 'Trang thai', 'Bat dau',
        'Ket thuc', 'Nop luc', 'Lan run', 'Warning', 'Submission ID', 'Diem',
    ])
    sessions = ExamSessions.objects.filter(
        assignment=assignment,
    ).select_related('student', 'final_submission').order_by('student__username')
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
    ).order_by('-submitted_at')
    submission_count = submissions.count()
    open_error = assignment_open_error(assignment, request.user)
    can_start_new_submission = (
        not is_teacher
        and not assignment.is_exam
        and not open_error
        and (not assignment.max_attempts or submission_count < assignment.max_attempts)
    )

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'submissions': submissions,
        'is_teacher': is_teacher,
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

    details = SubmissionDetails.objects.filter(
        submission=submission
    ).select_related('testcase').order_by('testcase__order_index')

    code_comments = CodeComments.objects.filter(
        submission=submission
    ).select_related('teacher').order_by('line_number')

    code_lines = submission.code_content.split('\n') if submission.code_content else []

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
    can_start_new_submission = (
        not is_teacher
        and not assignment.is_exam
        and not open_error
        and (not assignment.max_attempts or owner_submission_count < assignment.max_attempts)
    )

    context = {
        'submission': submission,
        'assignment': assignment,
        'classroom': classroom,
        'details': visible_details,
        'all_details': details,
        'code_comments': code_comments,
        'comments_by_line': comments_by_line,
        'code_lines': code_lines,
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

    submissions = Submissions.objects.filter(
        assignment=assignment
    ).select_related('student').order_by('-submitted_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        submissions = submissions.filter(status=status_filter)

    paginator = Paginator(submissions, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'submissions': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    return render(request, 'submissions/list_teacher.html', context)


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
