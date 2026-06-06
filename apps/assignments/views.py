import csv
import io
import json
import calendar as pycalendar
import logging
import os
import cloudinary.uploader
from datetime import datetime, time, timedelta
from urllib.parse import urlencode
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.db import transaction, models
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from core.decorators import teacher_required
from apps.classrooms.models import Classrooms, ClassroomMembers, ClassroomSubjects, SubjectApprovalStatus, Semesters
from apps.classrooms.views import _is_classroom_teacher, _is_classroom_member
from apps.administation.models import ProgrammingLanguages
from apps.administation.utils import (
    csv_filename, csv_query_context, get_bool_setting, get_int_param,
    get_int_setting, get_list_setting, log_activity,
)
from apps.notifications.services import notify_users
from apps.submissions.utils import (
    can_solve_assignment, sanitize_upload_filename, upload_to_configured_storage,
    submission_final_score, validate_uploaded_files,
)
from .models import (
    Assignments, Testcases, AssignmentFiles, AssignmentFileRequirements,
    AssignmentStatistics, Rubrics, PlagiarismReports,
    QuizSettings, QuizQuestions, QuizChoices, QuizQuestionImports,
)
from .forms import (
    AssignmentFileRequirementsForm, AssignmentForm, TestcaseForm,
    TestcaseImportForm, RubricForm, QuizQuestionForm,
)


ASSIGNMENT_UPLOAD_MAX_SIZE = 10 * 1024 * 1024
ASSIGNMENT_UPLOAD_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.md',
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.zip', '.csv', '.json',
    '.py', '.java', '.c', '.cpp', '.js', '.html', '.css',
}
SUBMISSION_EXPORT_STATUSES = {
    'pending', 'running', 'finished', 'error', 'failed', 'timeout',
}

logger = logging.getLogger(__name__)


def _is_admin_user(user):
    if user.is_superuser or user.is_staff:
        return True
    return _get_user_role(user) == 'admin'


def _log_assignment_file_access(request, assignment, assignment_file, event_type):
    logger.info(
        'assignment_file_access event=%s file=%s assignment=%s actor=%s',
        event_type,
        assignment_file.pk,
        assignment.pk,
        request.user.pk,
    )
    if not assignment.is_exam or _is_classroom_teacher(request.user, assignment.classroom):
        return
    try:
        from apps.submissions.models import ExamEvents, ExamSessions

        session = ExamSessions.objects.filter(
            assignment=assignment,
            student=request.user,
        ).first()
        if session:
            ExamEvents.objects.create(
                session=session,
                event_type=event_type,
                metadata={
                    'file_id': assignment_file.pk,
                    'file_name': assignment_file.file_name,
                    'actor_id': request.user.pk,
                    'actor_username': request.user.username,
                },
            )
    except Exception:
        logger.exception('Failed to log assignment file access assignment=%s file=%s', assignment.pk, assignment_file.pk)


def _get_user_role(user):
    try:
        return user.profiles.role
    except Exception:
        return 'student'


def _assignment_publish_notification_payload(assignment, classroom):
    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        title_prefix = 'Bài nộp file mới'
        mode_label = 'nộp file'
    elif assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        title_prefix = 'Quiz mới'
        mode_label = 'trắc nghiệm'
    else:
        title_prefix = 'Bài tập mới'
        mode_label = 'lập trình'
    if assignment.is_exam:
        title_prefix = f'Bài thi {mode_label} mới'
    return {
        'title': f'{title_prefix}: {assignment.title}',
        'message': f'Lớp {classroom.name} vừa công bố bài {mode_label}.',
        'notification_type': 'assignment_published',
        'metadata': {
            'assignment_id': assignment.pk,
            'classroom_id': classroom.pk,
            'submission_mode': assignment.submission_mode,
            'is_exam': assignment.is_exam,
        },
    }


def _parse_calendar_date(value, default_date):
    if not value:
        return default_date
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return default_date


def _month_delta(day, months):
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = pycalendar.monthrange(year, month)[1]
    return day.replace(year=year, month=month, day=min(day.day, last_day))


def _local_day_bounds(start_day, end_day):
    current_tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(start_day, time.min), current_tz)
    end = timezone.make_aware(datetime.combine(end_day + timedelta(days=1), time.min), current_tz)
    return start, end


def _build_calendar_query(request, **updates):
    params = request.GET.copy()
    for key, value in updates.items():
        if value in (None, ''):
            params.pop(key, None)
        else:
            params[key] = value
    return urlencode(params, doseq=True)


def _assignment_status_for_calendar(assignment, request, now, completed_ids, submitted_ids):
    role = _get_user_role(request.user)
    due_date = assignment.due_date

    if role == 'student':
        if assignment.pk in completed_ids:
            return {
                'key': 'completed',
                'label': 'Đã nộp',
                'icon': 'task_alt',
                'classes': 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
            }
        if assignment.pk in submitted_ids:
            return {
                'key': 'submitted',
                'label': 'Đã gửi',
                'icon': 'pending_actions',
                'classes': 'border-primary-200 bg-primary-50 text-primary-700 hover:bg-primary-100',
            }
        if due_date and due_date < now:
            if assignment.late_submission_allowed:
                return {
                    'key': 'overdue_open',
                    'label': 'Quá hạn',
                    'icon': 'schedule',
                    'classes': 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100',
                }
            return {
                'key': 'overdue_closed',
                'label': 'Đã đóng',
                'icon': 'lock_clock',
                'classes': 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100',
            }
        if due_date and due_date <= now + timedelta(days=2):
            return {
                'key': 'due_soon',
                'label': 'Sắp hạn',
                'icon': 'alarm',
                'classes': 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100',
            }
        return {
            'key': 'pending',
            'label': 'Chưa nộp',
            'icon': 'radio_button_unchecked',
            'classes': 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
        }

    if not assignment.is_published:
        return {
            'key': 'draft',
            'label': 'Nháp',
            'icon': 'visibility_off',
            'classes': 'border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200',
        }
    if due_date and due_date < now:
        return {
            'key': 'overdue',
            'label': 'Quá hạn',
            'icon': 'warning',
            'classes': 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100',
        }
    if due_date and due_date <= now + timedelta(days=2):
        return {
            'key': 'due_soon',
            'label': 'Sắp hạn',
            'icon': 'alarm',
            'classes': 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100',
        }
    return {
        'key': 'scheduled',
        'label': 'Đã lên lịch',
        'icon': 'event',
        'classes': 'border-primary-200 bg-primary-50 text-primary-700 hover:bg-primary-100',
    }


def _build_calendar_data(request):
    from apps.submissions.models import Submissions

    role = _get_user_role(request.user)
    is_admin = request.user.is_superuser or role == 'admin'
    is_teacher = role == 'teacher'
    is_student = not is_teacher and not is_admin
    now = timezone.now()
    today = timezone.localdate()

    view_mode = request.GET.get('view', 'month')
    if view_mode not in ('month', 'week'):
        view_mode = 'month'
    selected_day = _parse_calendar_date(request.GET.get('date'), today)

    if view_mode == 'week':
        start_day = selected_day - timedelta(days=selected_day.weekday())
        end_day = start_day + timedelta(days=6)
        prev_day = selected_day - timedelta(days=7)
        next_day = selected_day + timedelta(days=7)
        title = f'{start_day:%d/%m/%Y} - {end_day:%d/%m/%Y}'
        week_dates = [start_day + timedelta(days=i) for i in range(7)]
    else:
        start_day = selected_day.replace(day=1)
        last_day = pycalendar.monthrange(selected_day.year, selected_day.month)[1]
        end_day = selected_day.replace(day=last_day)
        prev_day = _month_delta(selected_day, -1)
        next_day = _month_delta(selected_day, 1)
        title = f'Tháng {selected_day.month}/{selected_day.year}'
        week_dates = None

    start_dt, end_dt = _local_day_bounds(start_day, end_day)

    if is_teacher:
        classrooms = Classrooms.objects.filter(teacher=request.user)
    elif is_admin:
        classrooms = Classrooms.objects.filter(is_active=True)
    else:
        classroom_ids = ClassroomMembers.objects.filter(
            student=request.user,
            status='approved',
            classroom__is_active=True,
        ).values_list('classroom_id', flat=True)
        classrooms = Classrooms.objects.filter(id__in=classroom_ids, is_active=True)

    classrooms = classrooms.select_related('teacher').order_by('name')
    classroom_ids = list(classrooms.values_list('id', flat=True))

    assignments_base = Assignments.objects.filter(classroom_id__in=classroom_ids)
    if is_student:
        assignments_base = assignments_base.filter(is_published=True)

    classroom_filter = request.GET.get('classroom', '').strip()
    if classroom_filter.isdigit() and int(classroom_filter) in classroom_ids:
        assignments_base = assignments_base.filter(classroom_id=int(classroom_filter))

    published_filter = request.GET.get('published', 'all').strip()
    if not is_student:
        if published_filter == 'published':
            assignments_base = assignments_base.filter(is_published=True)
        elif published_filter == 'draft':
            assignments_base = assignments_base.filter(is_published=False)
    else:
        published_filter = 'published'

    cs_filter = request.GET.get('cs', '').strip()
    if cs_filter == 'none':
        assignments_base = assignments_base.filter(classroom_subject__isnull=True)
    elif cs_filter.isdigit():
        assignments_base = assignments_base.filter(classroom_subject_id=int(cs_filter))

    sem_filter = request.GET.get('semester', '').strip()
    if sem_filter == 'none':
        assignments_base = assignments_base.filter(classroom_subject__semester__isnull=True)
    elif sem_filter == 'current':
        current_semester = Semesters.objects.filter(is_current=True, is_active=True).first()
        if current_semester:
            assignments_base = assignments_base.filter(classroom_subject__semester=current_semester)
    elif sem_filter.isdigit():
        assignments_base = assignments_base.filter(classroom_subject__semester_id=int(sem_filter))

    period_assignments = assignments_base.filter(
        due_date__gte=start_dt,
        due_date__lt=end_dt,
    ).select_related(
        'classroom',
        'classroom_subject',
        'classroom_subject__subject',
        'classroom_subject__semester',
    ).order_by('due_date', 'title')

    no_due_assignments = assignments_base.filter(
        due_date__isnull=True,
    ).select_related('classroom').order_by('-created_at')[:8]

    assignment_ids = list(period_assignments.values_list('id', flat=True))
    completed_ids = set()
    submitted_ids = set()
    if is_student and assignment_ids:
        submitted_ids = set(Submissions.objects.filter(
            student=request.user,
            assignment_id__in=assignment_ids,
        ).values_list('assignment_id', flat=True))
        completed_ids = set(Submissions.objects.filter(
            student=request.user,
            assignment_id__in=assignment_ids,
            status='finished',
        ).values_list('assignment_id', flat=True))

    events_by_date = {}
    events = []
    status_counts = {}
    for assignment in period_assignments:
        due_local = timezone.localtime(assignment.due_date)
        status = _assignment_status_for_calendar(assignment, request, now, completed_ids, submitted_ids)
        event = {
            'assignment': assignment,
            'due': due_local,
            'day': due_local.date(),
            'url': reverse('assignments:detail', kwargs={'pk': assignment.pk}),
            'status': status,
        }
        events.append(event)
        events_by_date.setdefault(event['day'], []).append(event)
        status_counts[status['key']] = status_counts.get(status['key'], 0) + 1

    if view_mode == 'week':
        calendar_dates = [week_dates]
    else:
        calendar_dates = pycalendar.Calendar(firstweekday=0).monthdatescalendar(
            selected_day.year,
            selected_day.month,
        )

    calendar_weeks = []
    for week in calendar_dates:
        calendar_weeks.append([
            {
                'date': day,
                'events': events_by_date.get(day, []),
                'in_period': start_day <= day <= end_day,
                'in_current_month': day.month == selected_day.month,
                'is_today': day == today,
                'is_selected': day == selected_day,
            }
            for day in week
        ])

    classroom_subjects = ClassroomSubjects.objects.filter(
        classroom_id__in=classroom_ids,
        is_active=True,
        subject__is_active=True,
    ).select_related('classroom', 'subject', 'semester').order_by(
        'classroom__name', '-semester__is_current', '-semester__start_date', 'subject__code'
    )
    if is_student:
        classroom_subjects = classroom_subjects.filter(subject__status=SubjectApprovalStatus.APPROVED)

    semesters = Semesters.objects.filter(is_active=True).order_by('-is_current', '-start_date', 'code')

    context = {
        'role': role,
        'is_teacher_calendar': is_teacher or is_admin,
        'is_student_calendar': is_student,
        'timezone_name': getattr(settings, 'TIME_ZONE', 'Asia/Ho_Chi_Minh'),
        'view_mode': view_mode,
        'selected_day': selected_day,
        'today': today,
        'calendar_title': title,
        'weekday_labels': ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'],
        'calendar_weeks': calendar_weeks,
        'events': events,
        'events_count': len(events),
        'status_counts': status_counts,
        'due_soon_count': status_counts.get('due_soon', 0),
        'overdue_count': (
            status_counts.get('overdue', 0) +
            status_counts.get('overdue_open', 0) +
            status_counts.get('overdue_closed', 0)
        ),
        'done_or_draft_count': status_counts.get('completed', 0) if is_student else status_counts.get('draft', 0),
        'no_due_assignments': no_due_assignments,
        'classrooms': classrooms,
        'classroom_subjects': classroom_subjects,
        'semesters': semesters,
        'classroom_filter': classroom_filter,
        'cs_filter': cs_filter,
        'sem_filter': sem_filter,
        'published_filter': published_filter,
        'prev_query': _build_calendar_query(request, date=prev_day.isoformat(), view=view_mode),
        'next_query': _build_calendar_query(request, date=next_day.isoformat(), view=view_mode),
        'today_query': _build_calendar_query(request, date=today.isoformat(), view=view_mode),
        'month_query': _build_calendar_query(request, date=selected_day.isoformat(), view='month'),
        'week_query': _build_calendar_query(request, date=selected_day.isoformat(), view='week'),
    }
    return context


def _assignment_publish_errors(assignment):
    errors = []
    if not (assignment.title or '').strip():
        errors.append('Thiếu tên bài tập.')
    if not ((assignment.description or '').strip() or (assignment.instructions or '').strip()):
        errors.append('Nên có mô tả hoặc hướng dẫn đề bài.')
    if (
        assignment.submission_mode == Assignments.SUBMISSION_CODE
        and assignment.grading_mode == Assignments.GRADING_AUTO
        and not Testcases.objects.filter(assignment=assignment).exists()
    ):
        errors.append('Bài chấm tự động cần ít nhất 1 testcase trước khi công bố.')
    if assignment.submission_mode != Assignments.SUBMISSION_CODE:
        if assignment.submission_mode == Assignments.SUBMISSION_FILE:
            if not hasattr(assignment, 'file_requirements'):
                errors.append('Bài nộp file cần cấu hình yêu cầu file trước khi công bố.')
        elif assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
            if not hasattr(assignment, 'quiz_settings'):
                errors.append('Bài trắc nghiệm cần cấu hình quiz trước khi công bố.')
            if not QuizQuestions.objects.filter(assignment=assignment, is_active=True).exists():
                errors.append('Bài trắc nghiệm cần ít nhất 1 câu hỏi trước khi công bố.')
    if assignment.is_exam:
        if not assignment.exam_duration_minutes or assignment.exam_duration_minutes <= 0:
            errors.append('Bài thi cần thời gian làm bài hợp lệ.')
        if assignment.max_attempts and assignment.max_attempts > 1:
            errors.append('Bài thi nên giới hạn 1 lần nộp.')
    return errors


def _assignment_setup_checks(assignment):
    has_file_requirements = False
    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        has_file_requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).exists()
    has_quiz_settings = False
    has_quiz_questions = False
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        has_quiz_settings = QuizSettings.objects.filter(assignment=assignment).exists()
        has_quiz_questions = QuizQuestions.objects.filter(assignment=assignment, is_active=True).exists()
    return [
        {
            'label': 'Có tên bài tập',
            'done': bool((assignment.title or '').strip()),
        },
        {
            'label': 'Có mô tả hoặc hướng dẫn',
            'done': bool((assignment.description or '').strip() or (assignment.instructions or '').strip()),
        },
        {
            'label': 'Auto-grade có ít nhất 1 testcase',
            'done': (
                assignment.submission_mode != Assignments.SUBMISSION_CODE
                or assignment.grading_mode != Assignments.GRADING_AUTO
                or Testcases.objects.filter(assignment=assignment).exists()
            ),
        },
        {
            'label': 'Mode làm bài đã có luồng nộp',
            'done': assignment.submission_mode in (
                Assignments.SUBMISSION_CODE,
                Assignments.SUBMISSION_FILE,
                Assignments.SUBMISSION_QUIZ,
            ),
        },
        {
            'label': 'Bài nộp file có yêu cầu định dạng/dung lượng',
            'done': assignment.submission_mode != Assignments.SUBMISSION_FILE or has_file_requirements,
        },
        {
            'label': 'Bài trắc nghiệm có cấu hình quiz',
            'done': assignment.submission_mode != Assignments.SUBMISSION_QUIZ or has_quiz_settings,
        },
        {
            'label': 'Bài trắc nghiệm có ít nhất 1 câu hỏi',
            'done': assignment.submission_mode != Assignments.SUBMISSION_QUIZ or has_quiz_questions,
        },
        {
            'label': 'Bài thi có thời gian làm bài',
            'done': not assignment.is_exam or bool(assignment.exam_duration_minutes and assignment.exam_duration_minutes > 0),
        },
        {
            'label': 'Rubric không vượt điểm tối đa',
            'done': (Rubrics.objects.filter(assignment=assignment, is_active=True).aggregate(total=Sum('max_points'))['total'] or 0) <= assignment.max_score,
        },
    ]


def _sync_quiz_grading_mode(assignment):
    if assignment.submission_mode != Assignments.SUBMISSION_QUIZ:
        return
    has_short_text = QuizQuestions.objects.filter(
        assignment=assignment,
        is_active=True,
        question_type=QuizQuestions.TYPE_SHORT_TEXT,
    ).exists()
    target_mode = Assignments.GRADING_MIXED if has_short_text else Assignments.GRADING_AUTO
    if assignment.grading_mode != target_mode:
        assignment.grading_mode = target_mode
        assignment.type = 'manual_grade' if target_mode == Assignments.GRADING_MIXED else 'auto_grade'
        assignment.save(update_fields=['grading_mode', 'type', 'updated_at'])


@login_required
def calendar_view(request):
    context = _build_calendar_data(request)
    return render(request, 'assignments/calendar.html', context)


@login_required
def calendar_events_view(request):
    context = _build_calendar_data(request)
    return JsonResponse({
        'events': [
            {
                'id': event['assignment'].pk,
                'title': event['assignment'].title,
                'classroom': event['assignment'].classroom.name if event['assignment'].classroom else '',
                'due': event['due'].isoformat(),
                'url': event['url'],
                'status': event['status']['key'],
                'label': event['status']['label'],
                'is_published': event['assignment'].is_published,
            }
            for event in context['events']
        ],
        'view': context['view_mode'],
        'date': context['selected_day'].isoformat(),
    })


@login_required
def assignment_list_view(request, classroom_pk):
    classroom = get_object_or_404(Classrooms, pk=classroom_pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")
        
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    if is_teacher:
        assignments = Assignments.objects.filter(classroom=classroom)
    else:
        assignments = Assignments.objects.filter(classroom=classroom, is_published=True)

    assignments = assignments.select_related(
        'classroom_subject', 'classroom_subject__subject', 'classroom_subject__semester'
    )

    query = request.GET.get('q', '').strip()
    if query:
        assignments = assignments.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    # Filter theo classroom_subject (lớp+môn+kỳ) nếu được chọn
    cs_filter = request.GET.get('cs', '').strip()
    selected_subject_link = None
    if cs_filter == 'none':
        assignments = assignments.filter(classroom_subject__isnull=True)
    elif cs_filter.isdigit():
        selected_subject_link = ClassroomSubjects.objects.filter(
            pk=int(cs_filter),
            classroom=classroom,
            is_active=True,
            subject__is_active=True,
        ).select_related('subject', 'semester').first()
        assignments = assignments.filter(classroom_subject_id=int(cs_filter))

    # Filter theo semester (nhóm nhiều link cùng kỳ)
    sem_filter = request.GET.get('semester', '').strip()
    if sem_filter.isdigit():
        assignments = assignments.filter(classroom_subject__semester_id=int(sem_filter))
    elif sem_filter == 'current':
        current_sem = Semesters.objects.filter(is_current=True, is_active=True).first()
        if current_sem:
            assignments = assignments.filter(classroom_subject__semester=current_sem)

    assignments = assignments.order_by('-created_at')

    # Danh sách classroom_subjects của lớp (để filter UI)
    from django.db.models import Q
    subj_q = Q(subject__status=SubjectApprovalStatus.APPROVED)
    if is_teacher:
        subj_q |= Q(subject__created_by=request.user)

    classroom_subjects = ClassroomSubjects.objects.filter(
        subj_q,
        classroom=classroom,
        is_active=True,
        subject__is_active=True,
    ).select_related('subject', 'semester').order_by('-semester__is_current', '-semester__start_date', 'subject__code')

    context = {
        'classroom': classroom,
        'assignments': assignments,
        'is_teacher': is_teacher,
        'query': query,
        'classroom_subjects': classroom_subjects,
        'selected_subject_link': selected_subject_link,
        'cs_filter': cs_filter,
        'sem_filter': sem_filter,
        'breadcrumbs': [
            {'label': 'Lớp học', 'url': reverse('classrooms:classroom_list')},
            {'label': classroom.name, 'url': reverse('classrooms:classroom_detail', kwargs={'pk': classroom.pk})},
            {'label': 'Bài tập'},
        ],
    }
    return render(request, 'assignments/list.html', context)


@login_required
def assignment_detail_view(request, pk):
    from apps.submissions.models import ExamSessions, QuizAttempts

    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")
        
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    if not is_teacher and not assignment.is_published:
        messages.error(request, 'Bài tập chưa được công bố.')
        return redirect('assignments:list', classroom_pk=classroom.pk)

    all_testcases = Testcases.objects.filter(assignment=assignment).order_by('order_index')
    files = AssignmentFiles.objects.filter(assignment=assignment).order_by('-uploaded_at')
    file_requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).first()
    quiz_settings = QuizSettings.objects.filter(assignment=assignment).first()
    quiz_questions = QuizQuestions.objects.filter(assignment=assignment, is_active=True).prefetch_related('choices').order_by('order_index', 'id')
    statistics = AssignmentStatistics.objects.filter(assignment=assignment).first()
    rubrics = Rubrics.objects.filter(assignment=assignment, is_active=True).order_by('order_index', 'id')
    rubric_total = sum(r.max_points for r in rubrics)

    if is_teacher:
        testcases = all_testcases
    else:
        testcases = all_testcases.filter(is_sample=True)

    total_weight = sum(tc.weight for tc in all_testcases)
    exam_session = None
    quiz_attempt_count = 0
    quiz_remaining_attempts = None
    if assignment.is_exam and not is_teacher:
        exam_session = ExamSessions.objects.filter(
            assignment=assignment,
            student=request.user,
        ).select_related('final_submission').first()
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ and not is_teacher:
        quiz_attempt_count = QuizAttempts.objects.filter(
            assignment=assignment,
            student=request.user,
        ).exclude(status=QuizAttempts.STATUS_CANCELLED).count()
        if assignment.max_attempts:
            quiz_remaining_attempts = max(0, assignment.max_attempts - quiz_attempt_count)

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'is_teacher': is_teacher,
        'exam_session': exam_session,
        'testcases': testcases,
        'sample_count': all_testcases.filter(is_sample=True).count(),
        'hidden_count': all_testcases.filter(is_hidden=True).count(),
        'total_testcases': all_testcases.count(),
        'total_weight': total_weight,
        'files': files,
        'file_requirements': file_requirements,
        'quiz_settings': quiz_settings,
        'quiz_questions': quiz_questions,
        'statistics': statistics,
        'rubrics': rubrics,
        'rubric_total': rubric_total,
        'rubric_form': RubricForm(),
        'setup_checks': _assignment_setup_checks(assignment) if is_teacher else [],
        'quiz_attempt_count': quiz_attempt_count,
        'quiz_remaining_attempts': quiz_remaining_attempts,
    }
    return render(request, 'assignments/detail.html', context)


def _default_file_requirements(assignment):
    return AssignmentFileRequirements(
        assignment=assignment,
        allowed_extensions=get_list_setting(
            'uploads.submission_allowed_extensions',
            ['.pdf', '.docx', '.zip', '.py', '.cpp'],
            allowed_values=[value for value, _label in AssignmentForm.FILE_EXTENSION_CHOICES],
        ),
        max_file_size_mb=get_int_setting(
            'uploads.submission_default_max_mb',
            20,
            minimum=1,
            maximum=100,
        ),
        max_files=get_int_setting(
            'uploads.submission_default_max_files',
            1,
            minimum=1,
            maximum=20,
        ),
        allow_resubmit=True,
        require_all_files_before_submit=True,
        scan_required=get_bool_setting('uploads.submission_scan_required_default', False),
    )


@teacher_required
def file_requirements_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền chỉnh yêu cầu file của bài này.')
        return redirect('classrooms:classroom_list')
    if assignment.submission_mode != Assignments.SUBMISSION_FILE:
        messages.error(request, 'Chỉ bài dạng nộp file mới có cấu hình yêu cầu file.')
        return redirect('assignments:detail', pk=assignment.pk)

    requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).first()
    if requirements is None:
        requirements = _default_file_requirements(assignment)

    if request.method == 'POST':
        form = AssignmentFileRequirementsForm(request.POST, instance=requirements)
        if form.is_valid():
            saved = form.save(commit=False)
            saved.assignment = assignment
            saved.save()
            log_activity(
                request.user,
                'ASSIGNMENT_FILE_REQUIREMENTS_UPDATE',
                'assignments',
                assignment.pk,
                metadata={
                    'assignment_id': assignment.pk,
                    'classroom_id': classroom.pk,
                    'allowed_extensions': saved.allowed_extensions,
                    'max_file_size_mb': saved.max_file_size_mb,
                    'max_files': saved.max_files,
                    'require_comment': saved.require_comment,
                    'allow_resubmit': saved.allow_resubmit,
                    'scan_required': saved.scan_required,
                },
                request=request,
            )
            messages.success(request, 'Đã cập nhật yêu cầu nộp file.')
            return redirect('assignments:detail', pk=assignment.pk)
    else:
        form = AssignmentFileRequirementsForm(instance=requirements)

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'form': form,
        'selected_extensions': form['allowed_extensions'].value() or [],
    }
    return render(request, 'assignments/file_requirements.html', context)


@teacher_required
@require_POST
def release_grades_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền công bố điểm bài này.')
        return redirect('classrooms:classroom_list')

    show_feedback = request.POST.get('show_feedback_after_release', '1') == '1'
    assignment.grades_released_at = timezone.now()
    assignment.show_feedback_after_release = show_feedback
    assignment.save(update_fields=['grades_released_at', 'show_feedback_after_release', 'updated_at'])

    from apps.submissions.models import Submissions
    student_ids = Submissions.objects.filter(
        assignment=assignment,
        student__isnull=False,
    ).values_list('student_id', flat=True).distinct()
    notify_users(
        student_ids,
        title=f'Đã công bố điểm: {assignment.title}',
        message=f'Giáo viên đã công bố điểm bài {assignment.get_submission_mode_display().lower()} trong lớp {classroom.name}.',
        link=f'/assignments/{assignment.pk}/',
        notification_type='grades_released',
        actor=request.user,
        metadata={
            'assignment_id': assignment.pk,
            'classroom_id': classroom.pk,
            'submission_mode': assignment.submission_mode,
            'is_exam': assignment.is_exam,
        },
    )
    messages.success(request, 'Đã công bố điểm và gửi thông báo cho học sinh có bài nộp.')
    return redirect('assignments:detail', pk=assignment.pk)


@teacher_required
@require_POST
def add_rubric_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền sửa rubric của bài này.')
        return redirect('classrooms:classroom_list')
    form = RubricForm(request.POST)
    if form.is_valid():
        current_total = Rubrics.objects.filter(
            assignment=assignment,
            is_active=True,
        ).aggregate(total=Sum('max_points'))['total'] or 0
        max_points = form.cleaned_data['max_points']
        if current_total + max_points > assignment.max_score:
            messages.error(request, f'Tổng điểm rubric không được vượt quá {assignment.max_score}.')
        else:
            rubric = form.save(commit=False)
            rubric.assignment = assignment
            if rubric.order_index is None:
                rubric.order_index = Rubrics.objects.filter(assignment=assignment).count()
            rubric.save()
            messages.success(request, 'Đã thêm tiêu chí rubric.')
    else:
        first_error = next(iter(form.errors.values()))[0]
        messages.error(request, first_error)
    return redirect('assignments:detail', pk=pk)


@teacher_required
@require_POST
def delete_rubric_view(request, pk, rubric_pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền sửa rubric của bài này.')
        return redirect('classrooms:classroom_list')
    rubric = get_object_or_404(Rubrics, pk=rubric_pk, assignment=assignment)
    rubric.is_active = False
    rubric.save(update_fields=['is_active'])
    messages.success(request, 'Đã ẩn tiêu chí rubric.')
    return redirect('assignments:detail', pk=pk)


def _quiz_teacher_assignment(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền quản lý quiz của bài này.')
        return assignment, classroom, False
    if assignment.submission_mode != Assignments.SUBMISSION_QUIZ:
        messages.error(request, 'Bài này không phải dạng trắc nghiệm.')
        return assignment, classroom, False
    return assignment, classroom, True


def _correct_token_to_index(token):
    token = (token or '').strip().upper()
    if not token:
        return None
    if token.isdigit():
        return int(token) - 1
    if len(token) == 1 and 'A' <= token <= 'Z':
        return ord(token) - ord('A')
    return None


def _save_quiz_choices(question, choices, correct_tokens):
    question.choices.all().delete()
    correct_indexes = {
        index
        for index in (_correct_token_to_index(token) for token in correct_tokens)
        if index is not None
    }
    for index, choice_text in enumerate(choices):
        QuizChoices.objects.create(
            question=question,
            choice_text=choice_text,
            is_correct=index in correct_indexes,
            order_index=index,
        )


def _question_form_initial(question):
    choices = list(question.choices.all().order_by('order_index', 'id'))
    correct = []
    for index, choice in enumerate(choices):
        if choice.is_correct:
            correct.append(chr(ord('A') + index))
    return {
        'choices_text': '\n'.join(choice.choice_text for choice in choices),
        'correct_answers': ';'.join(correct),
        'tags': ', '.join(question.tags or []),
    }


@teacher_required
def quiz_manage_view(request, pk):
    assignment, classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)

    from apps.submissions.models import QuizAttempts, QuizAnswers

    settings = QuizSettings.objects.filter(assignment=assignment).first()
    questions = QuizQuestions.objects.filter(assignment=assignment).prefetch_related('choices').order_by('order_index', 'id')
    active_questions = questions.filter(is_active=True)
    next_order = (questions.aggregate(max_order=models.Max('order_index'))['max_order'] or 0) + 1
    form = QuizQuestionForm(initial={'order_index': next_order, 'points': 1})

    attempts = QuizAttempts.objects.filter(assignment=assignment)
    answers = QuizAnswers.objects.filter(question__assignment=assignment).select_related('question').prefetch_related('selected_choices')
    question_stats = {
        question.pk: {
            'answers': 0,
            'correct': 0,
            'correct_rate': 0,
        }
        for question in questions
    }
    for answer in answers:
        stats = question_stats.setdefault(answer.question_id, {'answers': 0, 'correct': 0, 'correct_rate': 0})
        stats['answers'] += 1
        if answer.is_correct:
            stats['correct'] += 1
    for stats in question_stats.values():
        stats['correct_rate'] = round(stats['correct'] / stats['answers'] * 100, 1) if stats['answers'] else 0

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'settings': settings,
        'questions': questions,
        'active_questions': active_questions,
        'form': form,
        'attempt_count': attempts.count(),
        'submitted_attempt_count': attempts.filter(status__in=['submitted', 'auto_submitted']).count(),
        'avg_attempt_score': attempts.exclude(score__isnull=True).aggregate(avg=Avg('score'))['avg'],
        'question_stats': question_stats,
    }
    return render(request, 'assignments/quiz_manage.html', context)


@teacher_required
@require_POST
def add_quiz_question_view(request, pk):
    assignment, _classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    form = QuizQuestionForm(request.POST)
    if form.is_valid():
        question = form.save(commit=False)
        question.assignment = assignment
        question.save()
        _save_quiz_choices(
            question,
            form.cleaned_data.get('_parsed_choices') or [],
            form.cleaned_data.get('_parsed_correct_answers') or [],
        )
        _sync_quiz_grading_mode(assignment)
        messages.success(request, 'Đã thêm câu hỏi trắc nghiệm.')
    else:
        first_error = next(iter(form.errors.values()))[0]
        messages.error(request, first_error)
    return redirect('assignments:quiz_manage', pk=assignment.pk)


@teacher_required
def edit_quiz_question_view(request, pk, question_pk):
    assignment, classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    question = get_object_or_404(QuizQuestions.objects.prefetch_related('choices'), pk=question_pk, assignment=assignment)
    if request.method == 'POST':
        form = QuizQuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save()
            _save_quiz_choices(
                question,
                form.cleaned_data.get('_parsed_choices') or [],
                form.cleaned_data.get('_parsed_correct_answers') or [],
            )
            _sync_quiz_grading_mode(assignment)
            messages.success(request, 'Đã cập nhật câu hỏi.')
            return redirect('assignments:quiz_manage', pk=assignment.pk)
    else:
        form = QuizQuestionForm(instance=question, initial=_question_form_initial(question))
    return render(request, 'assignments/quiz_question_form.html', {
        'assignment': assignment,
        'classroom': classroom,
        'question': question,
        'form': form,
    })


@teacher_required
@require_POST
def toggle_quiz_question_view(request, pk, question_pk):
    assignment, _classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    question = get_object_or_404(QuizQuestions, pk=question_pk, assignment=assignment)
    question.is_active = not question.is_active
    question.save(update_fields=['is_active', 'updated_at'])
    _sync_quiz_grading_mode(assignment)
    messages.success(request, 'Đã cập nhật trạng thái câu hỏi.')
    return redirect('assignments:quiz_manage', pk=assignment.pk)


@teacher_required
@require_POST
def delete_quiz_question_view(request, pk, question_pk):
    assignment, _classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    question = get_object_or_404(QuizQuestions, pk=question_pk, assignment=assignment)
    question.is_active = False
    question.save(update_fields=['is_active', 'updated_at'])
    _sync_quiz_grading_mode(assignment)
    messages.success(request, 'Đã ẩn câu hỏi. Các attempt cũ vẫn giữ dữ liệu.')
    return redirect('assignments:quiz_manage', pk=assignment.pk)


@teacher_required
def quiz_preview_view(request, pk):
    assignment, classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    settings = QuizSettings.objects.filter(assignment=assignment).first()
    questions = QuizQuestions.objects.filter(assignment=assignment, is_active=True).prefetch_related('choices').order_by('order_index', 'id')
    return render(request, 'assignments/quiz_preview.html', {
        'assignment': assignment,
        'classroom': classroom,
        'settings': settings,
        'questions': questions,
    })


def _write_quiz_question_rows(response, questions):
    writer = csv.writer(response)
    writer.writerow([
        'question_text', 'question_type', 'points', 'choice_a', 'choice_b',
        'choice_c', 'choice_d', 'choice_e', 'choice_f', 'choices_json',
        'correct_answers', 'explanation', 'tags', 'difficulty',
    ])
    for question in questions:
        choices = list(question.choices.all().order_by('order_index', 'id'))
        correct = [
            chr(ord('A') + index)
            for index, choice in enumerate(choices)
            if choice.is_correct
        ]
        choice_texts = [choice.choice_text for choice in choices[:6]]
        choice_texts += [''] * (6 - len(choice_texts))
        writer.writerow([
            question.question_text,
            question.question_type,
            question.points,
            *choice_texts,
            '',
            ';'.join(correct),
            question.explanation or '',
            ';'.join(question.tags or []),
            question.difficulty or '',
        ])


@teacher_required
def export_quiz_questions_view(request, pk):
    assignment, _classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    filename = csv_filename(f'quiz_questions_{slugify(assignment.title) or assignment.pk}')
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    questions = QuizQuestions.objects.filter(assignment=assignment).prefetch_related('choices').order_by('order_index', 'id')
    _write_quiz_question_rows(response, questions)
    return response


@teacher_required
def sample_quiz_csv_view(request, pk):
    assignment, _classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="quiz_questions_template.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([
        'question_text', 'question_type', 'points', 'choice_a', 'choice_b',
        'choice_c', 'choice_d', 'choice_e', 'choice_f', 'choices_json',
        'correct_answers', 'explanation', 'tags', 'difficulty',
    ])
    writer.writerow([
        'Độ phức tạp của binary search là gì?', 'single_choice', 1,
        'O(n)', 'O(log n)', 'O(n log n)', 'O(1)', '', '', '', 'B',
        'Binary search chia đôi không gian tìm kiếm.', 'algorithm;search', 'easy',
    ])
    writer.writerow([
        'Chọn các kiểu dữ liệu mutable trong Python', 'multiple_choice', 2,
        'list', 'tuple', 'dict', 'str', '', '', '', 'A;C',
        'list và dict có thể thay đổi tại chỗ.', 'python;datatype', 'medium',
    ])
    writer.writerow([
        'Framework nào dùng virtual DOM?', 'single_choice', 1,
        '', '', '', '', '', '',
        json.dumps(['React', 'Django', 'PostgreSQL', 'Linux'], ensure_ascii=False),
        'A',
        'React dùng virtual DOM để tối ưu render UI.', 'frontend;react', 'easy',
    ])
    return response


def _split_csv_tokens(value):
    return [
        item.strip().upper()
        for item in (value or '').replace(',', ';').split(';')
        if item.strip()
    ]


def _choice_columns_from_row(row):
    choices = []
    for key, value in row.items():
        normalized = (key or '').strip().lower()
        if not normalized.startswith('choice_') or normalized == 'choices_json':
            continue
        suffix = normalized.replace('choice_', '', 1)
        order = None
        if len(suffix) == 1 and 'a' <= suffix <= 'z':
            order = ord(suffix) - ord('a')
        elif suffix.isdigit():
            order = int(suffix) - 1
        if order is not None:
            text = (value or '').strip()
            if text:
                choices.append((order, text))
    return [choice for _order, choice in sorted(choices, key=lambda item: item[0])]


def _choices_from_json(value):
    value = (value or '').strip()
    if not value:
        return [], []
    try:
        raw_choices = json.loads(value)
    except json.JSONDecodeError as exc:
        return [], [f'choices_json không hợp lệ: {exc.msg}.']
    choices = []
    errors = []
    if not isinstance(raw_choices, list):
        return [], ['choices_json phải là JSON array.']
    for index, item in enumerate(raw_choices, start=1):
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(item.get('text') or item.get('choice_text') or '').strip()
        else:
            text = ''
        if text:
            choices.append(text)
        else:
            errors.append(f'choices_json item #{index} thiếu text.')
    return choices, errors


def _correct_indexes_from_tokens(tokens, choices):
    indexes = []
    invalid = []
    for token in tokens:
        index = _correct_token_to_index(token)
        if index is None or index < 0 or index >= len(choices):
            invalid.append(token)
        else:
            indexes.append(index)
    return indexes, invalid


def _parse_quiz_csv_rows(text):
    reader = csv.DictReader(io.StringIO(text))
    required_headers = {'question_text', 'question_type', 'points', 'correct_answers'}
    headers = {header.strip() for header in (reader.fieldnames or []) if header}
    missing_headers = sorted(required_headers - headers)
    if missing_headers:
        return [], [{'line_no': 1, 'errors': [f"CSV thiếu cột: {', '.join(missing_headers)}."]}]

    rows = []
    errors = []
    for line_no, row in enumerate(reader, start=2):
        question_text = (row.get('question_text') or '').strip()
        question_type = (row.get('question_type') or QuizQuestions.TYPE_SINGLE_CHOICE).strip()
        try:
            points = float(row.get('points') or 1)
        except ValueError:
            points = 0
        choices = _choice_columns_from_row(row)
        json_choices, json_errors = _choices_from_json(row.get('choices_json'))
        if json_choices:
            choices = json_choices
        correct = _split_csv_tokens(row.get('correct_answers'))
        correct_indexes, invalid_correct = _correct_indexes_from_tokens(correct, choices)
        row_errors = []
        row_errors.extend(json_errors)
        if not question_text:
            row_errors.append('Thiếu question_text.')
        if question_type not in dict(QuizQuestions.QUESTION_TYPE_CHOICES):
            row_errors.append('question_type không hợp lệ.')
        if points <= 0:
            row_errors.append('points phải lớn hơn 0.')
        if question_type != QuizQuestions.TYPE_SHORT_TEXT:
            if len(choices) < 2:
                row_errors.append('Cần ít nhất 2 đáp án.')
            if not correct:
                row_errors.append('Thiếu correct_answers.')
            if invalid_correct:
                row_errors.append(f"correct_answers không tồn tại trong đáp án: {', '.join(invalid_correct)}.")
            if question_type in (QuizQuestions.TYPE_SINGLE_CHOICE, QuizQuestions.TYPE_TRUE_FALSE) and len(correct) != 1:
                row_errors.append('Single/true_false chỉ có một đáp án đúng.')
            if question_type == QuizQuestions.TYPE_MULTIPLE_CHOICE and len(correct_indexes) < 1:
                row_errors.append('Multiple choice cần ít nhất một đáp án đúng.')
        elif correct:
            row_errors.append('short_text chưa hỗ trợ correct_answers trong phase này.')
        parsed = {
            'line_no': line_no,
            'question_text': question_text,
            'question_type': question_type,
            'points': points,
            'choices': choices,
            'correct_answers': correct,
            'correct_indexes': correct_indexes,
            'explanation': (row.get('explanation') or '').strip(),
            'tags': [item.strip() for item in (row.get('tags') or '').replace(',', ';').split(';') if item.strip()],
            'difficulty': (row.get('difficulty') or '').strip(),
            'errors': row_errors,
        }
        rows.append(parsed)
        if row_errors:
            errors.append({'line_no': line_no, 'errors': row_errors})
    return rows, errors


@teacher_required
def import_quiz_questions_view(request, pk):
    assignment, classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    preview_rows = None
    errors = []
    preview_summary = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'confirm':
            payload = request.session.get(f'quiz_import_{assignment.pk}', {})
            rows = payload.get('rows', []) if isinstance(payload, dict) else payload
            file_name = payload.get('file_name', '') if isinstance(payload, dict) else ''
            clear_existing = bool(request.POST.get('clear_existing'))
            success = 0
            with transaction.atomic():
                if clear_existing:
                    QuizQuestions.objects.filter(assignment=assignment).update(is_active=False)
                order_base = QuizQuestions.objects.filter(assignment=assignment).aggregate(
                    max_order=models.Max('order_index')
                )['max_order'] or 0
                for row in rows:
                    if row.get('errors'):
                        continue
                    order_base += 1
                    question = QuizQuestions.objects.create(
                        assignment=assignment,
                        question_text=row['question_text'],
                        question_type=row['question_type'],
                        points=row['points'],
                        order_index=order_base,
                        explanation=row.get('explanation') or '',
                        tags=row.get('tags') or [],
                        difficulty=row.get('difficulty') or '',
                        metadata={
                            'import_line_no': row.get('line_no'),
                            'import_source': file_name or 'pasted_csv',
                        },
                    )
                    _save_quiz_choices(question, row.get('choices') or [], row.get('correct_answers') or [])
                    success += 1
                import_record = QuizQuestionImports.objects.create(
                    assignment=assignment,
                    file_name=file_name or 'pasted_csv.csv',
                    imported_by=request.user,
                    total_rows=len(rows),
                    success_rows=success,
                    error_rows=sum(1 for row in rows if row.get('errors')),
                    clear_existing=clear_existing,
                    metadata={
                        'valid_rows': success,
                        'error_lines': [
                            {'line_no': row.get('line_no'), 'errors': row.get('errors')}
                            for row in rows if row.get('errors')
                        ],
                    },
                )
                _sync_quiz_grading_mode(assignment)
                log_activity(
                    request.user,
                    'QUIZ_CSV_IMPORT',
                    'assignments',
                    assignment.pk,
                    metadata={
                        'assignment_id': assignment.pk,
                        'classroom_id': classroom.pk,
                        'import_id': import_record.pk,
                        'file_name': import_record.file_name,
                        'total_rows': import_record.total_rows,
                        'success_rows': import_record.success_rows,
                        'error_rows': import_record.error_rows,
                        'clear_existing': clear_existing,
                    },
                    request=request,
                )
            request.session.pop(f'quiz_import_{assignment.pk}', None)
            messages.success(request, f'Đã import {success} câu hỏi quiz.')
            return redirect('assignments:quiz_manage', pk=assignment.pk)

        uploaded = request.FILES.get('file')
        content = request.POST.get('content') or ''
        file_name = ''
        if uploaded:
            file_name = uploaded.name or ''
            if uploaded.size > 1024 * 1024:
                errors.append('File CSV tối đa 1MB.')
            else:
                content = uploaded.read().decode('utf-8-sig')
        if not content.strip():
            errors.append('Vui lòng upload hoặc dán nội dung CSV.')
        if not errors:
            preview_rows, errors = _parse_quiz_csv_rows(content)
            preview_summary = {
                'total': len(preview_rows),
                'valid': sum(1 for row in preview_rows if not row.get('errors')),
                'error': sum(1 for row in preview_rows if row.get('errors')),
            }
            request.session[f'quiz_import_{assignment.pk}'] = {
                'file_name': file_name,
                'rows': preview_rows,
                'summary': preview_summary,
            }
    import_history = QuizQuestionImports.objects.filter(assignment=assignment).select_related('imported_by')[:8]
    return render(request, 'assignments/quiz_import.html', {
        'assignment': assignment,
        'classroom': classroom,
        'preview_rows': preview_rows,
        'errors': errors,
        'preview_summary': preview_summary,
        'import_history': import_history,
    })


@teacher_required
def quiz_attempts_view(request, pk):
    assignment, classroom, ok = _quiz_teacher_assignment(request, pk)
    if not ok:
        return redirect('assignments:detail', pk=pk)
    from apps.submissions.models import QuizAttempts

    attempts = QuizAttempts.objects.filter(assignment=assignment).select_related(
        'student', 'submission', 'exam_session'
    ).order_by('-created_at')
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        attempts = attempts.filter(status=status_filter)
    paginator = Paginator(attempts, 30)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'assignments/quiz_attempts.html', {
        'assignment': assignment,
        'classroom': classroom,
        'attempts': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': QuizAttempts.STATUS_CHOICES,
    })


@teacher_required
def create_assignment_view(request, classroom_pk):
    classroom = get_object_or_404(Classrooms, pk=classroom_pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")
        
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền tạo bài tập cho lớp này.')
        return redirect('classrooms:classroom_list')

    languages = ProgrammingLanguages.objects.filter(is_active=True).order_by('display_name')

    if request.method == 'POST':
        form = AssignmentForm(request.POST, classroom=classroom, user=request.user)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.classroom = classroom
            assignment.created_by = request.user

            selected_langs = request.POST.getlist('allowed_languages')
            assignment.allowed_languages = (
                selected_langs if assignment.submission_mode == Assignments.SUBMISSION_CODE and selected_langs else None
            )

            # Validate: nếu có chọn classroom_subject thì phải thuộc lớp này
            cs = form.cleaned_data.get('classroom_subject')
            if cs and cs.classroom_id != classroom.pk:
                messages.error(request, 'Môn học được chọn không thuộc lớp này.')
                return render(request, 'assignments/create.html', {
                    'form': form, 'classroom': classroom, 'languages': languages,
                    'selected_languages': request.POST.getlist('allowed_languages'),
                })

            # --- Integrated Testcase Extraction ---
            testcases_to_create = []
            if assignment.submission_mode == Assignments.SUBMISSION_CODE:
                import re
                p = re.compile(r'^tc_name_(\d+)$')
                for key in request.POST:
                    match = p.match(key)
                    if match:
                        idx = match.group(1)
                        name = request.POST.get(f'tc_name_{idx}', '').strip()
                        input_data = request.POST.get(f'tc_input_{idx}', '')
                        output_data = request.POST.get(f'tc_output_{idx}', '')
                        is_sample = request.POST.get(f'tc_sample_{idx}') == 'on'
                        if output_data.strip():
                            testcases_to_create.append({
                                'name': name,
                                'input_data': input_data,
                                'expected_output': output_data,
                                'is_sample': is_sample,
                                'is_hidden': not is_sample
                            })

            # --- Quiz Import Handling ---
            quiz_import_file = request.FILES.get('quiz_import_file')
            
            requested_publish = 'publish' in request.POST
            
            # --- Solution Verification (CODE mode) ---
            if requested_publish and assignment.submission_mode == Assignments.SUBMISSION_CODE:
                solution_code = assignment.solution_code
                if not solution_code:
                    form.add_error('solution_code', 'Bạn phải cung cấp mã nguồn mẫu để hệ thống kiểm tra testcase khi công bố.')
                elif not testcases_to_create:
                    messages.error(request, 'Bạn phải thêm ít nhất một testcase để hệ thống kiểm tra bài tập lập trình.')
                else:
                    from services.docker_service import run_testcase
                    lang = (selected_langs[0] if selected_langs else 'python3')
                    failed_tests = []
                    for tc in testcases_to_create:
                        result = run_testcase(solution_code, lang, tc['input_data'], tc['expected_output'])
                        if not result['passed']:
                            error_detail = result.get('error_message') or f"Kết quả thực tế: '{result['actual_output']}'"
                            failed_tests.append(f"Testcase '{tc['name']}': {error_detail}")
                    if failed_tests:
                        error_msg = "Mã nguồn mẫu không vượt qua các testcase sau:<br>• " + "<br>• ".join(failed_tests)
                        messages.error(request, error_msg)
                        return render(request, 'assignments/create.html', {
                            'form': form, 'classroom': classroom, 'languages': languages,
                            'selected_languages': request.POST.getlist('allowed_languages'),
                        })

            if requested_publish:
                assignment.is_published = True
            
            assignment.save()
            form.save_file_requirements(assignment)
            form.save_quiz_settings(assignment)
            
            # Save Testcases
            from .models import Testcases
            for tc_data in testcases_to_create:
                Testcases.objects.create(assignment=assignment, **tc_data)

            # Process Quiz Import if file exists
            if assignment.submission_mode == Assignments.SUBMISSION_QUIZ and quiz_import_file:
                from .quiz_utils import process_quiz_import
                success, result = process_quiz_import(quiz_import_file, assignment)
                if success:
                    messages.success(request, f'Đã import thành công {result} câu hỏi trắc nghiệm từ file.')
                else:
                    messages.error(request, f'Lỗi khi import câu hỏi: {result}')

            publish_errors = _assignment_publish_errors(assignment) if requested_publish else []
            if publish_errors:
                assignment.is_published = False
                assignment.save(update_fields=['is_published'])
                for error in publish_errors:
                    messages.warning(request, error)
                messages.info(request, 'Bài đã được lưu nháp. Hoàn tất checklist rồi công bố sau.')
            elif assignment.is_published:
                # Notify students
                from apps.classrooms.models import ClassroomMembers
                from apps.notifications.services import notify_users
                student_ids = ClassroomMembers.objects.filter(classroom=classroom, status='approved').values_list('student_id', flat=True)
                payload = _assignment_publish_notification_payload(assignment, classroom)
                notify_users(
                    student_ids, title=payload['title'], message=payload['message'],
                    link=f'/assignments/{assignment.pk}/', notification_type=payload['notification_type'],
                    actor=request.user, metadata=payload['metadata'],
                )

            messages.success(request, f'Bài tập "{assignment.title}" đã được tạo!')
            return redirect('assignments:detail', pk=assignment.pk)
    else:
        # Nếu từ URL có ?cs=<id> thì preselect
        initial = {}
        cs_preselect = request.GET.get('cs')
        if cs_preselect and cs_preselect.isdigit():
            initial['classroom_subject'] = int(cs_preselect)
        mode_preselect = request.GET.get('mode')
        if mode_preselect in dict(Assignments.SUBMISSION_MODE_CHOICES):
            initial['submission_mode'] = mode_preselect
            if mode_preselect == Assignments.SUBMISSION_QUIZ:
                initial['max_attempts'] = get_int_setting('quiz.default_max_attempts', 2, minimum=1, maximum=50)
        initial.setdefault(
            'exam_grace_seconds',
            get_int_setting('exam.default_grace_seconds', 30, minimum=0, maximum=600),
        )
        initial.setdefault(
            'exam_require_fullscreen',
            get_bool_setting('exam.require_fullscreen_default', False),
        )
        initial.setdefault(
            'exam_allow_custom_input',
            get_bool_setting('exam.allow_custom_input_default', True),
        )
        if request.GET.get('exam') == '1':
            initial['is_exam'] = True
            initial['max_attempts'] = 1
        form = AssignmentForm(initial=initial, classroom=classroom, user=request.user)

    # Chuẩn bị map môn học -> ngôn ngữ cho frontend
    subject_lang_map = {}
    for cs in form.fields['classroom_subject'].queryset:
        subject_lang_map[cs.pk] = list(cs.subject.languages.values_list('name', flat=True))

    context = {
        'form': form,
        'classroom': classroom,
        'languages': languages,
        'selected_languages': request.POST.getlist('allowed_languages') if request.method == 'POST' else [],
        'subject_lang_json': json.dumps(subject_lang_map),
    }
    return render(request, 'assignments/create.html', context)


@teacher_required
def edit_assignment_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền chỉnh sửa bài tập này.')
        return redirect('classrooms:classroom_list')

    languages = ProgrammingLanguages.objects.filter(is_active=True).order_by('display_name')

    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=assignment, classroom=classroom, user=request.user)
        if form.is_valid():
            assignment = form.save(commit=False)
            selected_langs = request.POST.getlist('allowed_languages')
            assignment.allowed_languages = (
                selected_langs if assignment.submission_mode == Assignments.SUBMISSION_CODE and selected_langs else None
            )

            cs = form.cleaned_data.get('classroom_subject')
            if cs and cs.classroom_id != classroom.pk:
                messages.error(request, 'Môn học được chọn không thuộc lớp này.')
                return render(request, 'assignments/edit.html', {
                    'form': form, 'assignment': assignment, 'classroom': classroom,
                    'languages': languages,
                    'selected_languages': assignment.allowed_languages or [],
                })

            # --- Integrated Testcase Extraction ---
            testcases_to_save = []
            if assignment.submission_mode == Assignments.SUBMISSION_CODE:
                import re
                p = re.compile(r'^tc_name_(\d+)$')
                for key in request.POST:
                    match = p.match(key)
                    if match:
                        idx = match.group(1)
                        name = request.POST.get(f'tc_name_{idx}', '').strip()
                        input_data = request.POST.get(f'tc_input_{idx}', '')
                        output_data = request.POST.get(f'tc_output_{idx}', '')
                        is_sample = request.POST.get(f'tc_sample_{idx}') == 'on'
                        if output_data.strip():
                            testcases_to_save.append({
                                'name': name,
                                'input_data': input_data,
                                'expected_output': output_data,
                                'is_sample': is_sample,
                                'is_hidden': not is_sample
                            })

            # --- Quiz Import Handling ---
            quiz_import_file = request.FILES.get('quiz_import_file')

            requested_publish = 'publish' in request.POST
            
            # --- Solution Verification ---
            if (requested_publish or assignment.is_published) and assignment.submission_mode == Assignments.SUBMISSION_CODE:
                solution_code = assignment.solution_code
                if not solution_code:
                    form.add_error('solution_code', 'Bạn phải cung cấp mã nguồn mẫu để hệ thống kiểm tra testcase.')
                elif not testcases_to_save:
                    messages.error(request, 'Bạn phải thêm ít nhất một testcase để hệ thống kiểm tra bài tập lập trình.')
                else:
                    from services.docker_service import run_testcase
                    lang = (selected_langs[0] if selected_langs else 'python3')
                    failed_tests = []
                    for tc in testcases_to_save:
                        result = run_testcase(solution_code, lang, tc['input_data'], tc['expected_output'])
                        if not result['passed']:
                            error_detail = result.get('error_message') or f"Kết quả thực tế: '{result['actual_output']}'"
                            failed_tests.append(f"Testcase '{tc['name']}': {error_detail}")
                    
                    if failed_tests:
                        error_msg = "Mã nguồn mẫu không vượt qua các testcase sau:<br>• " + "<br>• ".join(failed_tests)
                        messages.error(request, error_msg)
                        return render(request, 'assignments/edit.html', {
                            'form': form, 'assignment': assignment, 'classroom': classroom, 'languages': languages,
                            'selected_languages': selected_langs,
                        })

            if requested_publish:
                assignment.is_published = True

            assignment.save()
            form.save_file_requirements(assignment)
            form.save_quiz_settings(assignment)

            # Process Quiz Import if file exists
            if assignment.submission_mode == Assignments.SUBMISSION_QUIZ and quiz_import_file:
                from .quiz_utils import process_quiz_import
                success, result = process_quiz_import(quiz_import_file, assignment)
                if success:
                    messages.success(request, f'Đã import thành công {result} câu hỏi trắc nghiệm mới từ file.')
                else:
                    messages.error(request, f'Lỗi khi import câu hỏi: {result}')

            # Update Testcases
            if assignment.submission_mode == Assignments.SUBMISSION_CODE and testcases_to_save:
                from .models import Testcases
                Testcases.objects.filter(assignment=assignment).delete()
                for tc_data in testcases_to_save:
                    Testcases.objects.create(assignment=assignment, **tc_data)

            messages.success(request, 'Cập nhật bài tập thành công!')
            return redirect('assignments:detail', pk=assignment.pk)
    else:
        form = AssignmentForm(instance=assignment, classroom=classroom, user=request.user)

    # Load existing testcases for the integrated manager
    from .models import Testcases
    existing_tcs = Testcases.objects.filter(assignment=assignment).order_by('order_index', 'id')
    existing_tcs_list = []
    for tc in existing_tcs:
        existing_tcs_list.append({
            'name': tc.name,
            'input': tc.input_data,
            'output': tc.expected_output,
            'is_sample': tc.is_sample,
        })

    # Chuẩn bị map môn học -> ngôn ngữ cho frontend
    subject_lang_map = {}
    for cs in form.fields['classroom_subject'].queryset:
        subject_lang_map[cs.pk] = list(cs.subject.languages.values_list('name', flat=True))

    context = {
        'form': form,
        'assignment': assignment,
        'classroom': classroom,
        'languages': languages,
        'selected_languages': assignment.allowed_languages or [],
        'existing_testcases_json': json.dumps(existing_tcs_list),
        'subject_lang_json': json.dumps(subject_lang_map),
    }
    return render(request, 'assignments/edit.html', context)


@teacher_required
@require_POST
def clone_assignment_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền nhân bản bài tập này.')
        return redirect('classrooms:classroom_list')
    with transaction.atomic():
        clone = Assignments.objects.create(
            classroom=assignment.classroom,
            classroom_subject=assignment.classroom_subject,
            title=f'Bản sao - {assignment.title}',
            description=assignment.description,
            instructions=assignment.instructions,
            starter_code=assignment.starter_code,
            solution_code=assignment.solution_code,
            solution_language=assignment.solution_language,
            type=assignment.type,
            submission_mode=assignment.submission_mode,
            grading_mode=assignment.grading_mode,
            difficulty=assignment.difficulty,
            allowed_languages=assignment.allowed_languages,
            start_date=None,
            due_date=None,
            late_submission_allowed=assignment.late_submission_allowed,
            late_penalty_percent=assignment.late_penalty_percent,
            max_score=assignment.max_score,
            max_attempts=assignment.max_attempts,
            show_testcase_result=assignment.show_testcase_result,
            enable_leaderboard=assignment.enable_leaderboard,
            is_exam=assignment.is_exam,
            exam_duration_minutes=assignment.exam_duration_minutes,
            exam_require_fullscreen=assignment.exam_require_fullscreen,
            exam_allow_custom_input=assignment.exam_allow_custom_input,
            exam_allow_sample_run=assignment.exam_allow_sample_run,
            exam_max_run_count=assignment.exam_max_run_count,
            exam_grace_seconds=assignment.exam_grace_seconds,
            is_published=False,
            created_by=request.user,
        )
        for testcase in Testcases.objects.filter(assignment=assignment).order_by('order_index'):
            Testcases.objects.create(
                assignment=clone,
                name=testcase.name,
                input_data=testcase.input_data,
                expected_output=testcase.expected_output,
                is_hidden=testcase.is_hidden,
                is_sample=testcase.is_sample,
                weight=testcase.weight,
                timeout_override=testcase.timeout_override,
                memory_override=testcase.memory_override,
                order_index=testcase.order_index,
            )
        for rubric in Rubrics.objects.filter(assignment=assignment, is_active=True).order_by('order_index', 'id'):
            Rubrics.objects.create(
                assignment=clone,
                name=rubric.name,
                description=rubric.description,
                max_points=rubric.max_points,
                order_index=rubric.order_index,
                is_active=True,
            )
        for file in AssignmentFiles.objects.filter(assignment=assignment):
            AssignmentFiles.objects.create(
                assignment=clone,
                file_name=file.file_name,
                file_url=file.file_url,
                file_size=file.file_size,
                mime_type=file.mime_type,
            )
        requirements = AssignmentFileRequirements.objects.filter(assignment=assignment).first()
        if requirements:
            AssignmentFileRequirements.objects.create(
                assignment=clone,
                allowed_extensions=requirements.allowed_extensions,
                allowed_mime_types=requirements.allowed_mime_types,
                max_file_size_mb=requirements.max_file_size_mb,
                max_files=requirements.max_files,
                require_comment=requirements.require_comment,
                allow_resubmit=requirements.allow_resubmit,
                require_all_files_before_submit=requirements.require_all_files_before_submit,
                scan_required=requirements.scan_required,
            )
        quiz_settings = QuizSettings.objects.filter(assignment=assignment).first()
        if quiz_settings:
            QuizSettings.objects.create(
                assignment=clone,
                question_order_mode=quiz_settings.question_order_mode,
                choice_order_mode=quiz_settings.choice_order_mode,
                show_score_after_submit=quiz_settings.show_score_after_submit,
                show_correct_answers=quiz_settings.show_correct_answers,
                show_explanation=quiz_settings.show_explanation,
                time_limit_minutes=quiz_settings.time_limit_minutes,
                passing_score=quiz_settings.passing_score,
                allow_review=quiz_settings.allow_review,
            )
        for question in QuizQuestions.objects.filter(assignment=assignment).prefetch_related('choices').order_by('order_index', 'id'):
            cloned_question = QuizQuestions.objects.create(
                assignment=clone,
                question_text=question.question_text,
                question_type=question.question_type,
                points=question.points,
                order_index=question.order_index,
                explanation=question.explanation,
                is_active=question.is_active,
                media_url=question.media_url,
                tags=question.tags,
                difficulty=question.difficulty,
                metadata=question.metadata,
            )
            for choice in question.choices.all():
                QuizChoices.objects.create(
                    question=cloned_question,
                    choice_text=choice.choice_text,
                    is_correct=choice.is_correct,
                    order_index=choice.order_index,
                    explanation=choice.explanation,
                    metadata=choice.metadata,
                )
    messages.success(request, 'Đã nhân bản bài tập thành bản nháp mới.')
    return redirect('assignments:detail', pk=clone.pk)


@teacher_required
def delete_assignment_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xóa bài tập này.')
        return redirect('classrooms:classroom_list')

    if request.method == 'POST':
        title = assignment.title
        classroom_pk = classroom.pk
        assignment.delete()
        messages.success(request, f'Đã xóa bài tập "{title}".')
        return redirect('assignments:list', classroom_pk=classroom_pk)

    return render(request, 'assignments/delete_confirm.html', {
        'assignment': assignment,
        'classroom': classroom,
    })


@teacher_required
@require_POST
def toggle_publish_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
        return redirect('classrooms:classroom_list')

    if not assignment.is_published:
        publish_errors = _assignment_publish_errors(assignment)
        if publish_errors:
            for error in publish_errors:
                messages.warning(request, error)
            messages.error(request, 'Chưa thể công bố bài tập. Vui lòng hoàn tất các mục trên.')
            return redirect('assignments:detail', pk=pk)
    assignment.is_published = not assignment.is_published
    assignment.save(update_fields=['is_published'])
    action = 'công bố' if assignment.is_published else 'ẩn'
    if assignment.is_published:
        student_ids = ClassroomMembers.objects.filter(
            classroom=classroom,
            status='approved',
        ).values_list('student_id', flat=True)
        payload = _assignment_publish_notification_payload(assignment, classroom)
        notify_users(
            student_ids,
            title=payload['title'],
            message=payload['message'],
            link=f'/assignments/{assignment.pk}/',
            notification_type=payload['notification_type'],
            actor=request.user,
            metadata=payload['metadata'],
        )
    messages.success(request, f'Đã {action} bài tập "{assignment.title}".')
    return redirect('assignments:detail', pk=pk)


@teacher_required
def add_testcase_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền thêm testcase.')
        return redirect('assignments:detail', pk=pk)

    if request.method == 'POST':
        form = TestcaseForm(request.POST)
        if form.is_valid():
            testcase = form.save(commit=False)
            testcase.assignment = assignment
            testcase.save()
            messages.success(request, f'Đã thêm testcase "{testcase.name or "#" + str(testcase.pk)}".')
            return redirect('assignments:detail', pk=pk)
    else:
        next_order = Testcases.objects.filter(assignment=assignment).count()
        form = TestcaseForm(initial={'order_index': next_order, 'weight': 1.0})

    return render(request, 'assignments/testcase_form.html', {
        'form': form,
        'assignment': assignment,
        'classroom': classroom,
        'is_edit': False,
    })


@teacher_required
def edit_testcase_view(request, pk, tc_pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền chỉnh sửa testcase.')
        return redirect('assignments:detail', pk=pk)

    testcase = get_object_or_404(Testcases, pk=tc_pk, assignment=assignment)

    if request.method == 'POST':
        form = TestcaseForm(request.POST, instance=testcase)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật testcase thành công!')
            return redirect('assignments:detail', pk=pk)
    else:
        form = TestcaseForm(instance=testcase)

    return render(request, 'assignments/testcase_form.html', {
        'form': form,
        'assignment': assignment,
        'classroom': classroom,
        'testcase': testcase,
        'is_edit': True,
    })


@teacher_required
@require_POST
def delete_testcase_view(request, pk, tc_pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xóa testcase.')
        return redirect('assignments:detail', pk=pk)

    testcase = get_object_or_404(Testcases, pk=tc_pk, assignment=assignment)
    testcase.delete()
    messages.success(request, 'Đã xóa testcase.')
    return redirect('assignments:detail', pk=pk)


@teacher_required
@require_POST
def upload_file_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền tải lên file.')
        return redirect('assignments:detail', pk=pk)

    if request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        max_size_mb = get_int_setting(
            'uploads.assignment_max_mb',
            default=getattr(settings, 'ASSIGNMENT_UPLOAD_MAX_SIZE', ASSIGNMENT_UPLOAD_MAX_SIZE) // (1024 * 1024),
            minimum=1,
            maximum=50,
        )
        errors = validate_uploaded_files(
            [uploaded_file],
            allowed_extensions=ASSIGNMENT_UPLOAD_EXTENSIONS,
            max_file_size_mb=max_size_mb,
            max_files=1,
            label='file đề bài',
        )
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('assignments:detail', pk=pk)
        safe_name = sanitize_upload_filename(uploaded_file.name, fallback='assignment-file')
        try:
            result = upload_to_configured_storage(
                uploaded_file,
                folder='assignment_files/',
                user=request.user,
                safe_name=safe_name,
                prefix='assignment-file',
            )
            AssignmentFiles.objects.create(
                assignment=assignment,
                file_name=safe_name,
                file_url=result.get('url', ''),
                file_size=uploaded_file.size,
                mime_type=uploaded_file.content_type or '',
            )
            logger.info(
                'assignment_file_upload file=%s assignment=%s actor=%s public_id=%s',
                safe_name,
                assignment.pk,
                request.user.pk,
                result.get('public_id', ''),
            )
            messages.success(request, f'Đã tải lên "{safe_name}".')
        except Exception:
            logger.exception('Failed to upload assignment file assignment=%s user=%s', assignment.pk, request.user.pk)
            messages.error(request, 'Có lỗi xảy ra khi tải file. Vui lòng thử lại.')
    else:
        messages.error(request, 'Vui lòng chọn file để tải lên.')
    return redirect('assignments:detail', pk=pk)


@login_required
def open_file_view(request, pk, file_pk):
    assignment = get_object_or_404(Assignments.objects.select_related('classroom'), pk=pk)
    assignment_file = get_object_or_404(AssignmentFiles, pk=file_pk, assignment=assignment)
    if not (_is_admin_user(request.user) or can_solve_assignment(request.user, assignment)):
        messages.error(request, 'Bạn không có quyền mở file này.')
        return redirect('classrooms:classroom_list')
    _log_assignment_file_access(request, assignment, assignment_file, 'assignment_file_download')
    return redirect(assignment_file.file_url)


@teacher_required
@require_POST
def delete_file_view(request, pk, file_pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xóa file.')
        return redirect('assignments:detail', pk=pk)

    afile = get_object_or_404(AssignmentFiles, pk=file_pk, assignment=assignment)
    afile.delete()
    messages.success(request, 'Đã xóa file.')
    return redirect('assignments:detail', pk=pk)


@teacher_required
def statistics_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xem thống kê.')
        return redirect('classrooms:classroom_list')

    testcases = Testcases.objects.filter(assignment=assignment).annotate(
        total_details=Count('submissiondetails'),
        failed_details=Count(
            'submissiondetails',
            filter=~Q(submissiondetails__result_status='passed'),
        ),
    ).order_by('order_index')

    from apps.submissions.models import QuizAnswers, QuizAttempts, SubmissionDetails, SubmissionFiles, Submissions
    submissions = Submissions.objects.filter(
        assignment=assignment
    ).select_related('student').order_by('-submitted_at')

    finished = list(submissions.filter(status='finished'))
    for submission in finished:
        submission.final_score = submission_final_score(submission)
        submission.final_percent = round(
            submission.final_score / (assignment.max_score or submission.max_score or 100) * 100,
            1,
        ) if (assignment.max_score or submission.max_score) else 0

    max_score = assignment.max_score or 100
    buckets = [0, 0, 0, 0, 0]  # [0-20%, 20-40%, 40-60%, 60-80%, 80-100%]
    for s in finished:
        pct = (s.final_score / max_score * 100) if max_score > 0 else 0
        idx = min(int(pct // 20), 4)
        buckets[idx] += 1

    score_distribution = {
        'labels': ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
        'data': buckets,
    }

    exec_times = [s.execution_time for s in finished if s.execution_time]
    avg_exec_time = round(sum(exec_times) / len(exec_times), 2) if exec_times else 0

    best_per_student = {}
    for s in finished:
        uid = s.student_id
        if uid not in best_per_student or s.final_score > best_per_student[uid].final_score:
            best_per_student[uid] = s
    ranked = sorted(best_per_student.values(), key=lambda s: s.final_score, reverse=True)
    top_students = ranked[:5]
    weak_students = list(reversed(ranked[-5:])) if len(ranked) >= 5 else ranked[::-1][:5]

    tc_fail_stats = []
    for tc in testcases:
        total = tc.total_details
        failed = tc.failed_details
        fail_rate = round(failed / total * 100, 1) if total > 0 else 0
        tc_fail_stats.append({
            'testcase': tc,
            'total': total,
            'failed': failed,
            'fail_rate': fail_rate,
        })
    tc_fail_stats.sort(key=lambda x: x['fail_rate'], reverse=True)

    # 5. Phân bố lỗi phổ biến (result_status)
    error_counts = SubmissionDetails.objects.filter(
        submission__assignment=assignment
    ).exclude(result_status='passed').values('result_status').annotate(
        count=Count('id')
    ).order_by('-count')
    error_distribution = {
        'labels': [e['result_status'] or 'unknown' for e in error_counts],
        'data': [e['count'] for e in error_counts],
    }

    late_count = submissions.filter(is_late=True).count()
    scores = [s.final_score for s in finished]
    unique_students = submissions.exclude(student__isnull=True).values('student_id').distinct().count()
    attempt_count = submissions.count()
    threshold = max_score * 0.5
    try:
        if assignment.submission_mode == Assignments.SUBMISSION_QUIZ and assignment.quiz_settings.passing_score is not None:
            threshold = assignment.quiz_settings.passing_score
    except QuizSettings.DoesNotExist:
        pass
    computed_statistics = {
        'total_submissions': attempt_count,
        'unique_students': unique_students,
        'avg_score': round(sum(scores) / len(scores), 2) if scores else 0,
        'max_score': max(scores) if scores else 0,
        'min_score': min(scores) if scores else 0,
        'pass_rate': round(sum(1 for score in scores if score >= threshold) / len(scores) * 100, 2) if scores else 0,
        'avg_attempts': round(attempt_count / unique_students, 2) if unique_students else 0,
    }
    statistics = computed_statistics

    members = _assignment_approved_members(classroom, request)
    submitted_student_ids = {
        submission.student_id for submission in submissions
        if submission.student_id
    }
    graded_count = sum(
        1 for submission in submissions
        if submission.manual_score is not None or submission.graded_at or submission.status == 'finished'
    )
    ungraded_count = max(attempt_count - graded_count, 0)

    file_stats = None
    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        file_count = SubmissionFiles.objects.filter(submission__assignment=assignment).count()
        file_stats = {
            'submitted_students': len(submitted_student_ids),
            'missing_students': max(len(members) - len(submitted_student_ids), 0),
            'graded_count': graded_count,
            'ungraded_count': ungraded_count,
            'late_count': late_count,
            'file_count': file_count,
            'avg_files_per_submission': round(file_count / attempt_count, 2) if attempt_count else 0,
        }

    quiz_stats = None
    question_analysis = []
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        submitted_statuses = (
            QuizAttempts.STATUS_SUBMITTED,
            QuizAttempts.STATUS_AUTO_SUBMITTED,
        )
        quiz_attempts = QuizAttempts.objects.filter(assignment=assignment).select_related(
            'student', 'submission'
        ).order_by('-created_at')
        completed_attempts = list(quiz_attempts.filter(status__in=submitted_statuses))
        quiz_scores = [
            submission_final_score(attempt.submission) if attempt.submission else attempt.score
            for attempt in completed_attempts
        ]
        quiz_durations = [attempt.duration_seconds for attempt in completed_attempts if attempt.duration_seconds]
        if quiz_durations:
            avg_exec_time = round(sum(quiz_durations) / len(quiz_durations), 2)

        answers = QuizAnswers.objects.filter(
            attempt__assignment=assignment,
            attempt__status__in=submitted_statuses,
        ).select_related('question')
        answer_rows = {}
        for answer in answers:
            row = answer_rows.setdefault(answer.question_id, {
                'answers': 0,
                'correct': 0,
                'wrong': 0,
                'score_sum': 0,
            })
            row['answers'] += 1
            row['score_sum'] += answer.score_awarded or 0
            if answer.is_correct is True:
                row['correct'] += 1
            elif answer.is_correct is False:
                row['wrong'] += 1

        questions = QuizQuestions.objects.filter(assignment=assignment, is_active=True).order_by('order_index', 'id')
        for question in questions:
            row = answer_rows.get(question.pk, {'answers': 0, 'correct': 0, 'wrong': 0, 'score_sum': 0})
            correct_rate = round(row['correct'] / row['answers'] * 100, 1) if row['answers'] else 0
            wrong_rate = round(row['wrong'] / row['answers'] * 100, 1) if row['answers'] else 0
            question_analysis.append({
                'question': question,
                'answers': row['answers'],
                'correct': row['correct'],
                'wrong': row['wrong'],
                'correct_rate': correct_rate,
                'wrong_rate': wrong_rate,
                'avg_score': round(row['score_sum'] / row['answers'], 2) if row['answers'] else 0,
            })
        question_analysis.sort(key=lambda row: (row['wrong_rate'], -row['correct_rate'], row['answers']), reverse=True)
        hardest = question_analysis[0] if question_analysis else None
        completed_students = len({attempt.student_id for attempt in completed_attempts if attempt.student_id})
        quiz_stats = {
            'total_attempts': quiz_attempts.count(),
            'completed_attempts': len(completed_attempts),
            'avg_score': round(sum(quiz_scores) / len(quiz_scores), 2) if quiz_scores else 0,
            'avg_attempts': round(quiz_attempts.count() / len(submitted_student_ids), 2) if submitted_student_ids else 0,
            'completion_rate': round(completed_students / len(members) * 100, 1) if members else 0,
            'hardest_question': hardest,
        }

    recent_submissions = list(submissions[:50])
    for submission in recent_submissions:
        submission.final_score = submission_final_score(submission)

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'statistics': statistics,
        'testcases': testcases,
        'submissions': recent_submissions,
        'total_submissions_count': submissions.count(),
        'pass_rate_val': statistics.get('pass_rate', 0),
        'score_distribution_json': json.dumps(score_distribution),
        'error_distribution_json': json.dumps(error_distribution),
        'avg_exec_time': avg_exec_time,
        'top_students': top_students,
        'weak_students': weak_students,
        'tc_fail_stats': tc_fail_stats[:10],
        'late_count': late_count,
        'file_stats': file_stats,
        'quiz_stats': quiz_stats,
        'question_analysis': question_analysis[:12],
        'graded_count': graded_count,
        'ungraded_count': ungraded_count,
        'latest_plagiarism_report': PlagiarismReports.objects.filter(assignment=assignment).first(),
    }
    context.update(csv_query_context(request))
    context['csv_items'] = [
        {
            'url': reverse('assignments:export_submissions', kwargs={'pk': assignment.pk}),
            'type': '',
            'icon': 'filter_alt',
            'label': 'Xuất bài nộp theo lọc hiện tại' if context['has_active_filters'] else 'Xuất tất cả bài nộp',
            'primary': True,
        },
        {
            'url': reverse('assignments:export_scores', kwargs={'pk': assignment.pk}),
            'type': '',
            'icon': 'grading',
            'label': 'Xuất bảng điểm theo lọc hiện tại' if context['has_active_filters'] else 'Xuất bảng điểm sinh viên',
            'primary': False,
        },
        {
            'url': reverse('assignments:export_late', kwargs={'pk': assignment.pk}),
            'type': '',
            'icon': 'schedule',
            'label': 'Xuất bài nộp trễ theo lọc hiện tại' if context['has_active_filters'] else 'Xuất bài nộp trễ',
            'primary': False,
        },
        {
            'url': reverse('assignments:export_missing', kwargs={'pk': assignment.pk}),
            'type': '',
            'icon': 'person_off',
            'label': 'Xuất sinh viên chưa nộp theo lọc hiện tại' if context['has_active_filters'] else 'Xuất sinh viên chưa nộp',
            'primary': False,
        },
    ]
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        context['csv_items'].extend([
            {
                'url': reverse('assignments:export_quiz_attempts', kwargs={'pk': assignment.pk}),
                'type': '',
                'icon': 'fact_check',
                'label': 'Xuất attempt quiz theo lọc hiện tại' if context['has_active_filters'] else 'Xuất điểm từng attempt quiz',
                'primary': False,
            },
            {
                'url': reverse('assignments:export_quiz_question_analysis', kwargs={'pk': assignment.pk}),
                'type': '',
                'icon': 'quiz',
                'label': 'Xuất phân tích câu hỏi theo lọc hiện tại' if context['has_active_filters'] else 'Xuất phân tích từng câu',
                'primary': False,
            },
        ])
    return render(request, 'assignments/statistics.html', context)


def _latest_finished_submissions_for_plagiarism(assignment):
    from apps.submissions.models import Submissions

    submissions = Submissions.objects.filter(
        assignment=assignment,
        status='finished',
    ).select_related('student').order_by('-submitted_at')

    seen_students = set()
    latest = []
    for submission in submissions:
        if not submission.student_id or submission.student_id in seen_students:
            continue
        if not (submission.code_content or '').strip():
            continue
        seen_students.add(submission.student_id)
        latest.append(submission)
    return latest


def _run_plagiarism_report(report):
    from services.plagiarism_service import check_plagiarism_batch

    latest_submissions = _latest_finished_submissions_for_plagiarism(report.assignment)
    if len(latest_submissions) < 2:
        report.status = 'finished'
        report.result = []
        report.submissions_count = len(latest_submissions)
        report.pairs_count = 0
        report.suspicious_count = 0
        report.finished_at = timezone.now()
        report.save(update_fields=[
            'status', 'result', 'submissions_count', 'pairs_count',
            'suspicious_count', 'finished_at',
        ])
        return report

    language = latest_submissions[0].language or 'python'
    payload = [
        {
            'id': submission.pk,
            'student_id': submission.student_id,
            'code': submission.code_content or '',
        }
        for submission in latest_submissions
    ]
    results = check_plagiarism_batch(payload, language)
    for result in results:
        result['is_suspicious'] = result['similarity_score'] >= report.threshold

    report.status = 'finished'
    report.language = language
    report.result = results
    report.submissions_count = len(latest_submissions)
    report.pairs_count = len(results)
    report.suspicious_count = sum(1 for result in results if result['is_suspicious'])
    report.finished_at = timezone.now()
    report.save(update_fields=[
        'status', 'language', 'result', 'submissions_count', 'pairs_count',
        'suspicious_count', 'finished_at',
    ])
    return report


def _build_plagiarism_pairs(report, suspicious_only=False):
    from apps.submissions.models import Submissions

    raw_results = report.result or []
    submission_ids = set()
    for result in raw_results:
        submission_ids.add(result.get('submission_a'))
        submission_ids.add(result.get('submission_b'))
    submission_ids.discard(None)

    submissions_by_id = {
        submission.pk: submission
        for submission in Submissions.objects.filter(
            pk__in=submission_ids,
        ).select_related('student')
    }

    pairs = []
    for result in raw_results:
        if suspicious_only and not result.get('is_suspicious'):
            continue
        sub_a = submissions_by_id.get(result.get('submission_a'))
        sub_b = submissions_by_id.get(result.get('submission_b'))
        if not sub_a or not sub_b:
            continue
        pairs.append({
            'submission_a': sub_a,
            'submission_b': sub_b,
            'similarity_score': result.get('similarity_score', 0),
            'text_score': result.get('text_score', 0),
            'token_score': result.get('token_score', 0),
            'structural_score': result.get('structural_score', 0),
            'is_suspicious': result.get('is_suspicious', False),
        })
    return pairs


@teacher_required
def plagiarism_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xem kiểm tra đạo văn.')
        return redirect('classrooms:classroom_list')

    reports = PlagiarismReports.objects.filter(
        assignment=assignment,
    ).select_related('created_by').order_by('-created_at')
    latest_report = reports.first()
    suspicious_only = request.GET.get('suspicious') == '1'
    pairs = _build_plagiarism_pairs(latest_report, suspicious_only) if latest_report else []
    pairs_page_obj = Paginator(pairs, 20).get_page(request.GET.get('page'))
    latest_submissions_count = len(_latest_finished_submissions_for_plagiarism(assignment))

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'reports': reports[:10],
        'latest_report': latest_report,
        'pairs': pairs_page_obj,
        'pairs_page_obj': pairs_page_obj,
        'pairs_count': len(pairs),
        'suspicious_only': suspicious_only,
        'latest_submissions_count': latest_submissions_count,
        'default_threshold': 0.85,
    }
    return render(request, 'assignments/plagiarism.html', context)


@teacher_required
@require_POST
def run_plagiarism_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền chạy kiểm tra đạo văn.')
        return redirect('classrooms:classroom_list')
    try:
        threshold = float(request.POST.get('threshold') or 0.85)
    except ValueError:
        threshold = 0.85
    threshold = min(max(threshold, 0.0), 1.0)

    report = PlagiarismReports.objects.create(
        assignment=assignment,
        created_by=request.user,
        status='running',
        threshold=threshold,
    )
    if not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', True):
        from apps.submissions.tasks import check_plagiarism_task
        check_plagiarism_task.delay(assignment.pk, report.pk, threshold)
        messages.success(request, 'Đã đưa kiểm tra đạo văn vào hàng đợi xử lý.')
        return redirect('assignments:plagiarism', pk=pk)

    try:
        _run_plagiarism_report(report)
    except Exception as exc:
        logger.exception('Failed to run plagiarism report=%s assignment=%s', report.pk, assignment.pk)
        report.status = 'error'
        report.error_message = str(exc)[:1000]
        report.finished_at = timezone.now()
        report.save(update_fields=['status', 'error_message', 'finished_at'])
        messages.error(request, 'Có lỗi khi chạy kiểm tra đạo văn. Vui lòng thử lại.')
        return redirect('assignments:plagiarism', pk=pk)

    if report.submissions_count < 2:
        messages.info(request, 'Cần ít nhất 2 học sinh có bài nộp finished để so sánh.')
    else:
        messages.success(request, f'Đã kiểm tra {report.pairs_count} cặp bài, phát hiện {report.suspicious_count} cặp đáng chú ý.')
    return redirect('assignments:plagiarism', pk=pk)


# ===================================================================
# BULK TESTCASE IMPORT (Phần B)
# ===================================================================

def _parse_testcases_json(raw):
    """Parse JSON array of testcase dicts."""
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError('JSON phải là một array.')
    result = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f'Item #{i + 1} không phải object.')
        if 'expected_output' not in item and 'output' not in item:
            raise ValueError(f'Item #{i + 1} thiếu expected_output/output.')
        weight = float(item.get('weight', 1.0))
        if weight <= 0:
            raise ValueError(f'Trọng số item #{i + 1} phải lớn hơn 0.')
        result.append({
            'name': str(item.get('name') or f'Test {i + 1}'),
            'input_data': str(item.get('input', item.get('input_data', ''))),
            'expected_output': str(item.get('expected_output', item.get('output', ''))),
            'is_sample': bool(item.get('is_sample', False)),
            'is_hidden': bool(item.get('is_hidden', not item.get('is_sample', False))),
            'weight': weight,
        })
    return result


def _parse_testcases_csv(raw):
    """Parse CSV. Header: name,input,expected_output,is_sample,is_hidden,weight"""
    reader = csv.DictReader(io.StringIO(raw))
    fieldnames = set(reader.fieldnames or [])
    if not fieldnames:
        raise ValueError('CSV phải có header.')
    if not ({'expected_output', 'output'} & fieldnames):
        raise ValueError('CSV thiếu cột expected_output hoặc output.')
    result = []
    for i, row in enumerate(reader):
        def _bool(val):
            return str(val).strip().lower() in ('1', 'true', 'yes', 'y', 'on')
        weight = float(row.get('weight') or 1.0)
        if weight <= 0:
            raise ValueError(f'Trọng số dòng #{i + 1} phải lớn hơn 0.')
        result.append({
            'name': (row.get('name') or f'Test {i + 1}').strip(),
            'input_data': row.get('input') or row.get('input_data') or '',
            'expected_output': row.get('expected_output') or row.get('output') or '',
            'is_sample': _bool(row.get('is_sample', False)),
            'is_hidden': _bool(row.get('is_hidden', True)),
            'weight': weight,
        })
    return result


@teacher_required
def import_testcases_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền import testcase.')
        return redirect('assignments:detail', pk=pk)

    if request.method == 'POST':
        form = TestcaseImportForm(request.POST, request.FILES)
        if form.is_valid():
            fmt = form.cleaned_data['import_format']
            content = form.cleaned_data.get('content') or ''
            upload = form.cleaned_data.get('file')
            if upload:
                try:
                    content = upload.read().decode('utf-8')
                except UnicodeDecodeError:
                    messages.error(request, 'File phải có encoding UTF-8.')
                    return redirect('assignments:import_testcases', pk=pk)

            try:
                if fmt == 'json':
                    parsed = _parse_testcases_json(content)
                else:
                    parsed = _parse_testcases_csv(content)
            except (ValueError, json.JSONDecodeError) as exc:
                messages.error(request, f'Lỗi parse dữ liệu: {exc}')
                return redirect('assignments:import_testcases', pk=pk)

            if not parsed:
                messages.error(request, 'Không có testcase hợp lệ.')
                return redirect('assignments:import_testcases', pk=pk)

            with transaction.atomic():
                if form.cleaned_data.get('clear_existing'):
                    Testcases.objects.filter(assignment=assignment).delete()

                start_order = Testcases.objects.filter(assignment=assignment).count()
                created = 0
                for i, tc in enumerate(parsed):
                    Testcases.objects.create(
                        assignment=assignment,
                        name=tc['name'],
                        input_data=tc['input_data'],
                        expected_output=tc['expected_output'],
                        is_sample=tc['is_sample'],
                        is_hidden=tc['is_hidden'],
                        weight=tc['weight'],
                        order_index=start_order + i,
                    )
                    created += 1

            messages.success(request, f'Đã import {created} testcase!')
            return redirect('assignments:detail', pk=pk)
    else:
        form = TestcaseImportForm()

    return render(request, 'assignments/import_testcases.html', {
        'form': form,
        'assignment': assignment,
        'classroom': classroom,
    })


# ===================================================================
# BULK REGRADE (Phần C)
# ===================================================================

@teacher_required
def bulk_regrade_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền chấm lại bài.')
        return redirect('assignments:detail', pk=pk)

    if request.method == 'POST':
        from apps.submissions.models import Submissions, SubmissionDetails
        from apps.submissions.tasks import grade_submission_task

        subs = Submissions.objects.filter(assignment=assignment)
        total = subs.count()
        if total == 0:
            messages.info(request, 'Không có bài nộp nào để chấm lại.')
            return redirect('assignments:statistics', pk=pk)

        # Xóa details cũ, reset status
        SubmissionDetails.objects.filter(submission__in=subs).delete()
        subs.update(
            status='pending',
            total_score=0,
            passed_testcases=0,
            total_testcases=0,
            execution_time=None,
            memory_usage=None,
        )

        # Chấm lại từng bài (eager khi CELERY_ALWAYS_EAGER=True)
        for sub in subs:
            grade_submission_task.delay(sub.pk)

        messages.success(request, f'Đã kích hoạt chấm lại {total} bài nộp.')
        return redirect('assignments:statistics', pk=pk)

    # GET: hiển thị trang xác nhận
    from apps.submissions.models import Submissions
    sub_count = Submissions.objects.filter(assignment=assignment).count()
    return render(request, 'assignments/bulk_regrade_confirm.html', {
        'assignment': assignment,
        'classroom': classroom,
        'sub_count': sub_count,
    })


# ===================================================================
# LATE SUBMISSION REPORT EXPORT (Phần D)
# ===================================================================

def _report_deadline_for_assignment(assignment):
    if assignment.due_date:
        return assignment.due_date, 'Hạn nộp'
    if assignment.is_exam and assignment.exam_end_time:
        return assignment.exam_end_time, 'Kết thúc thi'
    return None, 'Mốc hạn'


def _assignment_mode_label(assignment):
    return {
        Assignments.SUBMISSION_CODE: 'Lập trình',
        Assignments.SUBMISSION_FILE: 'Nộp file',
        Assignments.SUBMISSION_QUIZ: 'Trắc nghiệm',
    }.get(assignment.submission_mode, assignment.submission_mode or '')


def _csv_response(filename):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    return response


def _late_minutes_for_submission(submission, deadline):
    if not deadline or not submission.submitted_at:
        return None
    minutes = round((submission.submitted_at - deadline).total_seconds() / 60)
    return max(minutes, 0)


def _submission_is_late_for_report(submission, deadline):
    if submission.is_late:
        return True
    if not deadline or not submission.submitted_at:
        return False
    return submission.submitted_at > deadline


def _get_float_export_param(params, *names):
    for name in names:
        value = params.get(name)
        if value in (None, ''):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _format_minutes_vi(minutes):
    if minutes is None:
        return '—'
    if minutes < 60:
        return f'{minutes} phút'
    if minutes < 1440:
        hours = minutes // 60
        mins = minutes % 60
        return f'{hours} giờ {mins} phút' if mins else f'{hours} giờ'
    days = minutes // 1440
    hours = (minutes % 1440) // 60
    return f'{days} ngày {hours} giờ' if hours else f'{days} ngày'


def _assignment_report_filename_prefix(assignment):
    title_slug = slugify(assignment.title or '')[:48].strip('-')
    parts = ['bao_cao_nop_bai', str(assignment.pk)]
    if title_slug:
        parts.append(title_slug)
    return '_'.join(parts)


def _assignment_approved_members(classroom, request=None):
    members = ClassroomMembers.objects.filter(
        classroom=classroom,
        status='approved',
    ).select_related('student')
    if request:
        student_id = get_int_param(request.GET, 'student_id', minimum=1)
        if student_id:
            members = members.filter(student_id=student_id)
    return list(members.order_by(
        'student__last_name', 'student__first_name', 'student__username'
    ))


def _assignment_submissions(assignment, request=None):
    from apps.submissions.models import Submissions

    submissions = Submissions.objects.filter(
        assignment=assignment
    ).select_related('student').order_by('-submitted_at')

    if request:
        status = request.GET.get('status', '').strip()
        language = request.GET.get('language', '').strip()
        student_id = get_int_param(request.GET, 'student_id', minimum=1)
        if status in SUBMISSION_EXPORT_STATUSES:
            submissions = submissions.filter(status=status)
        if language:
            submissions = submissions.filter(language__iexact=language)
        if student_id:
            submissions = submissions.filter(student_id=student_id)

    submissions = list(submissions)

    if request:
        late_filter = request.GET.get('late', 'all')
        if late_filter in ('yes', 'no'):
            deadline, _deadline_label = _report_deadline_for_assignment(assignment)
            expected_late = late_filter == 'yes'
            submissions = [
                submission for submission in submissions
                if _submission_is_late_for_report(submission, deadline) == expected_late
            ]
        score_min = _get_float_export_param(request.GET, 'score_min', 'min_score')
        score_max = _get_float_export_param(request.GET, 'score_max', 'max_score')
        if score_min is not None or score_max is not None:
            filtered_submissions = []
            for submission in submissions:
                score = submission_final_score(submission)
                if score_min is not None and score < score_min:
                    continue
                if score_max is not None and score > score_max:
                    continue
                filtered_submissions.append(submission)
            submissions = filtered_submissions

    return submissions


def _best_and_latest_submission_rows(assignment, members, submissions):
    grouped = {}
    for submission in submissions:
        if not submission.student_id:
            continue
        bucket = grouped.setdefault(submission.student_id, {
            'best': None,
            'latest': None,
            'attempts': 0,
            'has_late': False,
        })
        bucket['attempts'] += 1
        bucket['has_late'] = bucket['has_late'] or _submission_is_late_for_report(
            submission,
            _report_deadline_for_assignment(assignment)[0],
        )
        if bucket['latest'] is None or submission.submitted_at > bucket['latest'].submitted_at:
            bucket['latest'] = submission
        if submission.status == 'finished':
            best = bucket['best']
            best_score = submission_final_score(best) if best else 0
            current_score = submission_final_score(submission)
            if best is None or current_score > best_score:
                bucket['best'] = submission

    rows = []
    for member in members:
        bucket = grouped.get(member.student_id, {})
        best = bucket.get('best')
        latest = bucket.get('latest')
        rows.append({
            'member': member,
            'student': member.student,
            'best': best,
            'latest': latest,
            'attempts': bucket.get('attempts', 0),
            'has_late': bucket.get('has_late', False),
        })
    return rows


def _quiz_answer_text(answer):
    if answer.text_answer:
        return answer.text_answer
    choices = list(answer.selected_choices.order_by('order_index', 'id').values_list('choice_text', flat=True))
    if choices:
        return ' | '.join(choices)
    selected_ids = answer.selected_choice_ids or []
    return ', '.join(str(choice_id) for choice_id in selected_ids)


@teacher_required
def late_report_print_view(request, pk):
    """Trang in/xuất PDF báo cáo nộp trễ (dùng window.print() để xuất PDF)."""
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xem báo cáo.')
        return redirect('assignments:detail', pk=pk)

    from apps.submissions.models import Submissions
    deadline, deadline_label = _report_deadline_for_assignment(assignment)

    submissions = _assignment_submissions(assignment, request)
    members = _assignment_approved_members(classroom, request)

    latest_by_student = {}
    for submission in submissions:
        if not submission.student_id:
            continue
        if submission.student_id not in latest_by_student:
            latest_by_student[submission.student_id] = submission

    submitted_student_ids = set(latest_by_student)
    member_student_ids = {member.student_id for member in members if member.student_id}
    missing_members = [
        member for member in members
        if member.student_id and member.student_id not in submitted_student_ids
    ]

    rows = []
    for submission in latest_by_student.values():
        delta_minutes = _late_minutes_for_submission(submission, deadline)
        is_late = _submission_is_late_for_report(submission, deadline)
        rows.append({
            'sub': submission,
            'final_score': submission_final_score(submission),
            'delta_minutes': delta_minutes if is_late else 0,
            'delta_label': _format_minutes_vi(delta_minutes) if is_late else 'Đúng hạn',
            'is_late': is_late,
            'is_passed': submission.total_testcases > 0 and submission.passed_testcases >= submission.total_testcases,
        })

    late_rows = [row for row in rows if row['is_late']]
    finished_rows = [row for row in rows if row['sub'].status == 'finished']
    avg_score = round(
        sum(submission_final_score(row['sub']) for row in rows) / len(rows),
        2,
    ) if rows else 0
    pass_count = sum(1 for row in rows if row['is_passed'])

    submitted_member_count = len(submitted_student_ids & member_student_ids) if member_student_ids else len(submitted_student_ids)
    report_summary = {
        'total_students': len(members),
        'submitted_students': submitted_member_count,
        'missing_students': len(missing_members),
        'total_submissions': len(submissions),
        'latest_submissions': len(rows),
        'on_time_students': max(len(rows) - len(late_rows), 0),
        'late_students': len(late_rows),
        'finished_students': len(finished_rows),
        'pass_count': pass_count,
        'avg_score': avg_score,
    }

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'rows': rows,
        'late_rows': late_rows,
        'missing_members': missing_members,
        'report_summary': report_summary,
        'total_late': len(late_rows),
        'deadline': deadline,
        'deadline_label': deadline_label,
        'due_date': deadline,
        'generated_at': timezone.now(),
        'report_filename_prefix': _assignment_report_filename_prefix(assignment),
    }
    context.update(csv_query_context(request))
    return render(request, 'assignments/late_report_print.html', context)


@teacher_required
def export_late_report_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất báo cáo.')
        return redirect('assignments:detail', pk=pk)

    deadline, _deadline_label = _report_deadline_for_assignment(assignment)
    late_subs = _assignment_submissions(assignment, request)
    late_subs = [
        submission for submission in late_subs
        if _submission_is_late_for_report(submission, deadline)
    ]

    filename = csv_filename(
        _assignment_report_filename_prefix(assignment),
        filtered=bool(csv_query_context(request)['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    )
    response = _csv_response(filename)

    writer = csv.writer(response)
    writer.writerow([
        'Username', 'Họ tên', 'Email',
        'Thời gian nộp', 'Deadline', 'Trễ (phút)',
        '% Phạt', 'Điểm cuối', 'Điểm tối đa',
        'Loại bài', 'Ngôn ngữ', 'Trạng thái'
    ])

    for s in late_subs:
        delta_minutes = ''
        if deadline and s.submitted_at:
            delta = (s.submitted_at - deadline).total_seconds() / 60
            delta_minutes = f'{delta:.0f}'
        writer.writerow([
            s.student.username if s.student else '',
            s.student.get_full_name() if s.student else '',
            s.student.email if s.student else '',
            s.submitted_at.strftime('%d/%m/%Y %H:%M') if s.submitted_at else '',
            deadline.strftime('%d/%m/%Y %H:%M') if deadline else '',
            delta_minutes,
            f'{s.penalty_applied:.1f}',
            f'{submission_final_score(s):.2f}',
            f'{s.max_score:.2f}',
            _assignment_mode_label(assignment),
            s.language,
            s.status,
        ])

    return response


@teacher_required
def export_assignment_submissions_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất bài nộp.')
        return redirect('assignments:detail', pk=pk)

    deadline, deadline_label = _report_deadline_for_assignment(assignment)
    submissions = _assignment_submissions(assignment, request)
    response = _csv_response(csv_filename(
        f'assignment_{assignment.pk}',
        'submissions',
        filtered=bool(csv_query_context(request)['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))
    writer = csv.writer(response)
    header = [
        'Submission ID', 'Username', 'Họ tên', 'Email', 'Ngôn ngữ',
        'Trạng thái', 'Thời gian nộp', deadline_label, 'Trễ', 'Trễ (phút)',
        '% Phạt', 'Điểm', 'Điểm tối đa', 'Testcase pass', 'Tổng testcase',
        'Thời gian chạy (ms)', 'Bộ nhớ', 'Chấm tay', 'Giáo viên nhận xét', 'Loại bài',
    ]
    if assignment.submission_mode == Assignments.SUBMISSION_FILE:
        header.extend([
            'Số file', 'Tên file', 'Link file', 'Trạng thái quét',
            'File phản hồi', 'Trạng thái chấm',
        ])
    writer.writerow(header)

    for submission in submissions:
        is_late = _submission_is_late_for_report(submission, deadline)
        late_minutes = _late_minutes_for_submission(submission, deadline) if is_late else 0
        row = [
            submission.pk,
            submission.student.username if submission.student else '',
            submission.student.get_full_name() if submission.student else '',
            submission.student.email if submission.student else '',
            submission.language,
            submission.status,
            timezone.localtime(submission.submitted_at).strftime('%d/%m/%Y %H:%M:%S') if submission.submitted_at else '',
            timezone.localtime(deadline).strftime('%d/%m/%Y %H:%M:%S') if deadline else '',
            'Có' if is_late else 'Không',
            late_minutes,
            f'{submission.penalty_applied:.1f}',
            f'{submission_final_score(submission):.2f}',
            f'{submission.max_score:.2f}',
            submission.passed_testcases,
            submission.total_testcases,
            submission.execution_time or '',
            submission.memory_usage or '',
            submission.manual_score if submission.manual_score is not None else '',
            submission.teacher_comment or '',
            _assignment_mode_label(assignment),
        ]
        if assignment.submission_mode == Assignments.SUBMISSION_FILE:
            files = list(submission.files.all())
            feedback_files = list(submission.feedback_files.all())
            is_graded = submission.manual_score is not None or submission.graded_at or submission.status == 'finished'
            row.extend([
                len(files),
                ' | '.join(file.file_name for file in files),
                ' | '.join(file.file_url for file in files),
                ' | '.join(file.scan_status for file in files),
                ' | '.join(file.file_name for file in feedback_files),
                'Đã chấm' if is_graded else 'Chưa chấm',
            ])
        writer.writerow(row)
    return response


@teacher_required
def export_assignment_scores_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất bảng điểm.')
        return redirect('assignments:detail', pk=pk)

    members = _assignment_approved_members(classroom, request)
    submissions = _assignment_submissions(assignment, request)
    rows = _best_and_latest_submission_rows(assignment, members, submissions)
    response = _csv_response(csv_filename(
        f'assignment_{assignment.pk}',
        'scores',
        filtered=bool(csv_query_context(request)['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))
    writer = csv.writer(response)
    header = [
        'Username', 'Họ tên', 'Email', 'Số lần nộp', 'Có nộp',
        'Trạng thái mới nhất', 'Nộp lần cuối', 'Có nộp trễ',
        'Điểm tốt nhất', 'Điểm tối đa', 'Testcase tốt nhất',
        'Submission tốt nhất', 'Submission mới nhất', 'Loại bài',
    ]
    if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
        header.extend(['Attempt quiz', 'Attempt tốt nhất'])
    writer.writerow(header)

    for row in rows:
        student = row['student']
        best = row['best']
        latest = row['latest']
        best_score = ''
        best_testcases = ''
        if best:
            score = submission_final_score(best)
            best_score = f'{score:.2f}'
            best_testcases = f'{best.passed_testcases}/{best.total_testcases}'
        line = [
            student.username,
            student.get_full_name() or student.username,
            student.email,
            row['attempts'],
            'Có' if latest else 'Không',
            latest.status if latest else 'Chưa nộp',
            timezone.localtime(latest.submitted_at).strftime('%d/%m/%Y %H:%M:%S') if latest and latest.submitted_at else '',
            'Có' if row['has_late'] else 'Không',
            best_score,
            assignment.max_score,
            best_testcases,
            best.pk if best else '',
            latest.pk if latest else '',
            _assignment_mode_label(assignment),
        ]
        if assignment.submission_mode == Assignments.SUBMISSION_QUIZ:
            from apps.submissions.models import QuizAttempts

            attempts = QuizAttempts.objects.filter(assignment=assignment, student=student)
            best_attempt = attempts.order_by('-score', '-submitted_at').first()
            line.extend([
                attempts.exclude(status=QuizAttempts.STATUS_CANCELLED).count(),
                best_attempt.pk if best_attempt else '',
            ])
        writer.writerow(line)
    return response


@teacher_required
def export_quiz_attempts_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk, submission_mode=Assignments.SUBMISSION_QUIZ)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất attempt quiz.')
        return redirect('assignments:detail', pk=pk)

    from apps.submissions.models import QuizAnswers, QuizAttempts

    attempts = QuizAttempts.objects.filter(assignment=assignment).select_related(
        'student', 'submission', 'exam_session'
    ).order_by('student__username', 'attempt_no')
    status = request.GET.get('status', '').strip()
    student_id = get_int_param(request.GET, 'student_id', minimum=1)
    if status in dict(QuizAttempts.STATUS_CHOICES):
        attempts = attempts.filter(status=status)
    if student_id:
        attempts = attempts.filter(student_id=student_id)

    score_min = _get_float_export_param(request.GET, 'score_min', 'min_score')
    score_max = _get_float_export_param(request.GET, 'score_max', 'max_score')
    attempts = list(attempts)
    if score_min is not None or score_max is not None:
        filtered = []
        for attempt in attempts:
            score = submission_final_score(attempt.submission) if attempt.submission else attempt.score
            if score_min is not None and score < score_min:
                continue
            if score_max is not None and score > score_max:
                continue
            filtered.append(attempt)
        attempts = filtered

    response = _csv_response(csv_filename(
        f'assignment_{assignment.pk}',
        'quiz_attempts',
        filtered=bool(csv_query_context(request)['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))
    writer = csv.writer(response)
    writer.writerow([
        'Attempt ID', 'Submission ID', 'Username', 'Họ tên', 'Email',
        'Lần làm', 'Trạng thái', 'Bắt đầu', 'Nộp lúc',
        'Điểm', 'Điểm tối đa', 'Thời lượng (giây)',
        'Số câu đã trả lời', 'Tổng số câu', 'Phiên thi',
    ])
    total_questions = QuizQuestions.objects.filter(assignment=assignment, is_active=True).count()
    for attempt in attempts:
        answered_count = QuizAnswers.objects.filter(attempt=attempt).filter(
            Q(answered_at__isnull=False) | Q(text_answer__gt='') | ~Q(selected_choice_ids=[])
        ).count()
        score = submission_final_score(attempt.submission) if attempt.submission else attempt.score
        writer.writerow([
            attempt.pk,
            attempt.submission_id or '',
            attempt.student.username if attempt.student else '',
            attempt.student.get_full_name() if attempt.student else '',
            attempt.student.email if attempt.student else '',
            attempt.attempt_no,
            attempt.get_status_display(),
            timezone.localtime(attempt.started_at).strftime('%d/%m/%Y %H:%M:%S') if attempt.started_at else '',
            timezone.localtime(attempt.submitted_at).strftime('%d/%m/%Y %H:%M:%S') if attempt.submitted_at else '',
            f'{score:.2f}',
            f'{attempt.max_score:.2f}',
            attempt.duration_seconds or '',
            answered_count,
            total_questions,
            attempt.exam_session_id or '',
        ])
    return response


@teacher_required
def export_quiz_question_analysis_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk, submission_mode=Assignments.SUBMISSION_QUIZ)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất phân tích câu hỏi.')
        return redirect('assignments:detail', pk=pk)

    from apps.submissions.models import QuizAnswers, QuizAttempts

    submitted_statuses = (
        QuizAttempts.STATUS_SUBMITTED,
        QuizAttempts.STATUS_AUTO_SUBMITTED,
    )
    attempts = QuizAttempts.objects.filter(assignment=assignment, status__in=submitted_statuses)
    student_id = get_int_param(request.GET, 'student_id', minimum=1)
    if student_id:
        attempts = attempts.filter(student_id=student_id)
    attempt_ids = list(attempts.values_list('id', flat=True))

    answers = QuizAnswers.objects.filter(attempt_id__in=attempt_ids).select_related('question').prefetch_related('selected_choices')
    answer_rows = {}
    answer_samples = {}
    for answer in answers:
        row = answer_rows.setdefault(answer.question_id, {
            'answers': 0,
            'correct': 0,
            'wrong': 0,
            'score_sum': 0,
        })
        row['answers'] += 1
        row['score_sum'] += answer.score_awarded or 0
        if answer.is_correct is True:
            row['correct'] += 1
        elif answer.is_correct is False:
            row['wrong'] += 1
        answer_samples.setdefault(answer.question_id, [])
        if len(answer_samples[answer.question_id]) < 3:
            answer_samples[answer.question_id].append(_quiz_answer_text(answer))

    response = _csv_response(csv_filename(
        f'assignment_{assignment.pk}',
        'quiz_question_analysis',
        filtered=bool(csv_query_context(request)['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))
    writer = csv.writer(response)
    writer.writerow([
        'Question ID', 'Thứ tự', 'Loại câu', 'Câu hỏi', 'Điểm',
        'Lượt trả lời', 'Số đúng', 'Số sai', 'Tỷ lệ đúng', 'Tỷ lệ sai',
        'Điểm TB', 'Đáp án đúng', 'Mẫu câu trả lời',
    ])
    questions = QuizQuestions.objects.filter(assignment=assignment, is_active=True).prefetch_related('choices').order_by('order_index', 'id')
    for question in questions:
        row = answer_rows.get(question.pk, {'answers': 0, 'correct': 0, 'wrong': 0, 'score_sum': 0})
        correct_rate = round(row['correct'] / row['answers'] * 100, 1) if row['answers'] else 0
        wrong_rate = round(row['wrong'] / row['answers'] * 100, 1) if row['answers'] else 0
        correct_choices = question.choices.filter(is_correct=True).order_by('order_index', 'id')
        writer.writerow([
            question.pk,
            question.order_index,
            question.get_question_type_display(),
            question.question_text,
            f'{question.points:.2f}',
            row['answers'],
            row['correct'],
            row['wrong'],
            f'{correct_rate:.1f}%',
            f'{wrong_rate:.1f}%',
            f"{(row['score_sum'] / row['answers'] if row['answers'] else 0):.2f}",
            ' | '.join(choice.choice_text for choice in correct_choices),
            ' | '.join(answer_samples.get(question.pk, [])),
        ])
    return response


@teacher_required
def export_assignment_missing_view(request, pk):
    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất danh sách thiếu bài.')
        return redirect('assignments:detail', pk=pk)

    members = _assignment_approved_members(classroom, request)
    submitted_student_ids = {
        submission.student_id for submission in _assignment_submissions(assignment, request)
        if submission.student_id
    }
    response = _csv_response(csv_filename(
        f'assignment_{assignment.pk}',
        'missing',
        filtered=bool(csv_query_context(request)['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))
    writer = csv.writer(response)
    writer.writerow(['Username', 'Họ tên', 'Email', 'Lớp', 'Bài tập', 'Loại bài', 'Deadline/Kết thúc thi'])
    deadline, _deadline_label = _report_deadline_for_assignment(assignment)

    for member in members:
        if not member.student_id or member.student_id in submitted_student_ids:
            continue
        student = member.student
        writer.writerow([
            student.username,
            student.get_full_name() or student.username,
            student.email,
            classroom.name,
            assignment.title,
            _assignment_mode_label(assignment),
            timezone.localtime(deadline).strftime('%d/%m/%Y %H:%M:%S') if deadline else '',
        ])
    return response


@teacher_required
def download_submission_files_view(request, pk):
    from apps.submissions.views import download_submission_files_zip_view

    return download_submission_files_zip_view(request, assignment_pk=pk)
