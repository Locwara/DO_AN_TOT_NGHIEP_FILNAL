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
from django.db.models import Q, Count, Sum
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from core.decorators import teacher_required
from apps.classrooms.models import Classrooms, ClassroomMembers, ClassroomSubjects, SubjectApprovalStatus, Semesters
from apps.classrooms.views import _is_classroom_teacher, _is_classroom_member
from apps.administation.models import ProgrammingLanguages
from apps.administation.utils import csv_filename, csv_query_context, get_bool_setting, get_int_param, get_int_setting
from apps.notifications.services import notify_users
from .models import Assignments, Testcases, AssignmentFiles, AssignmentStatistics, Rubrics, PlagiarismReports
from .forms import AssignmentForm, TestcaseForm, TestcaseImportForm, RubricForm


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


def _get_user_role(user):
    try:
        return user.profiles.role
    except Exception:
        return 'student'


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
        classrooms = Classrooms.objects.filter(teacher=request.user, is_active=True)
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
    if assignment.type == 'auto_grade' and not Testcases.objects.filter(assignment=assignment).exists():
        errors.append('Bài chấm tự động cần ít nhất 1 testcase trước khi công bố.')
    if assignment.is_exam:
        if not assignment.exam_duration_minutes or assignment.exam_duration_minutes <= 0:
            errors.append('Bài thi cần thời gian làm bài hợp lệ.')
        if assignment.max_attempts and assignment.max_attempts > 1:
            errors.append('Bài thi nên giới hạn 1 lần nộp.')
    return errors


def _assignment_setup_checks(assignment):
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
            'done': assignment.type != 'auto_grade' or Testcases.objects.filter(assignment=assignment).exists(),
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
    classroom = get_object_or_404(Classrooms, pk=classroom_pk, is_active=True)
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
    classroom_subjects = ClassroomSubjects.objects.filter(
        classroom=classroom,
        is_active=True,
        subject__is_active=True,
        subject__status=SubjectApprovalStatus.APPROVED,
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
    }
    return render(request, 'assignments/list.html', context)


@login_required
def assignment_detail_view(request, pk):
    from apps.submissions.models import ExamSessions

    assignment = get_object_or_404(Assignments, pk=pk)
    classroom = assignment.classroom
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
    statistics = AssignmentStatistics.objects.filter(assignment=assignment).first()
    rubrics = Rubrics.objects.filter(assignment=assignment, is_active=True).order_by('order_index', 'id')
    rubric_total = sum(r.max_points for r in rubrics)

    if is_teacher:
        testcases = all_testcases
    else:
        testcases = all_testcases.filter(is_sample=True)

    total_weight = sum(tc.weight for tc in all_testcases)
    exam_session = None
    if assignment.is_exam and not is_teacher:
        exam_session = ExamSessions.objects.filter(
            assignment=assignment,
            student=request.user,
        ).select_related('final_submission').first()

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
        'statistics': statistics,
        'rubrics': rubrics,
        'rubric_total': rubric_total,
        'rubric_form': RubricForm(),
        'setup_checks': _assignment_setup_checks(assignment) if is_teacher else [],
    }
    return render(request, 'assignments/detail.html', context)


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


@teacher_required
def create_assignment_view(request, classroom_pk):
    classroom = get_object_or_404(Classrooms, pk=classroom_pk, is_active=True)
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền tạo bài tập cho lớp này.')
        return redirect('classrooms:classroom_list')

    languages = ProgrammingLanguages.objects.filter(is_active=True).order_by('display_name')

    if request.method == 'POST':
        form = AssignmentForm(request.POST, classroom=classroom)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.classroom = classroom
            assignment.created_by = request.user

            selected_langs = request.POST.getlist('allowed_languages')
            assignment.allowed_languages = selected_langs if selected_langs else None

            # Validate: nếu có chọn classroom_subject thì phải thuộc lớp này
            cs = form.cleaned_data.get('classroom_subject')
            if cs and cs.classroom_id != classroom.pk:
                messages.error(request, 'Môn học được chọn không thuộc lớp này.')
                return render(request, 'assignments/create.html', {
                    'form': form, 'classroom': classroom, 'languages': languages,
                    'selected_languages': request.POST.getlist('allowed_languages'),
                })

            requested_publish = 'publish' in request.POST
            if requested_publish:
                assignment.is_published = True
            assignment.save()
            publish_errors = _assignment_publish_errors(assignment) if requested_publish else []
            if publish_errors:
                assignment.is_published = False
                assignment.save(update_fields=['is_published'])
                for error in publish_errors:
                    messages.warning(request, error)
                messages.info(request, 'Bài đã được lưu nháp. Hoàn tất checklist rồi công bố sau.')
            elif assignment.is_published:
                student_ids = ClassroomMembers.objects.filter(
                    classroom=classroom,
                    status='approved',
                ).values_list('student_id', flat=True)
                notify_users(
                    student_ids,
                    title=f'Bài tập mới: {assignment.title}',
                    message=f'Lớp {classroom.name} vừa công bố bài tập mới.',
                    link=f'/assignments/{assignment.pk}/',
                    notification_type='assignment_published',
                    actor=request.user,
                    metadata={'assignment_id': assignment.pk, 'classroom_id': classroom.pk},
                )

            messages.success(request, f'Bài tập "{assignment.title}" đã được tạo!')
            return redirect('assignments:detail', pk=assignment.pk)
    else:
        # Nếu từ URL có ?cs=<id> thì preselect
        initial = {}
        cs_preselect = request.GET.get('cs')
        if cs_preselect and cs_preselect.isdigit():
            initial['classroom_subject'] = int(cs_preselect)
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
        form = AssignmentForm(initial=initial, classroom=classroom)

    context = {
        'form': form,
        'classroom': classroom,
        'languages': languages,
        'selected_languages': request.POST.getlist('allowed_languages') if request.method == 'POST' else [],
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
        form = AssignmentForm(request.POST, instance=assignment, classroom=classroom)
        if form.is_valid():
            assignment = form.save(commit=False)
            selected_langs = request.POST.getlist('allowed_languages')
            assignment.allowed_languages = selected_langs if selected_langs else None

            cs = form.cleaned_data.get('classroom_subject')
            if cs and cs.classroom_id != classroom.pk:
                messages.error(request, 'Môn học được chọn không thuộc lớp này.')
                return render(request, 'assignments/edit.html', {
                    'form': form, 'assignment': assignment, 'classroom': classroom,
                    'languages': languages,
                    'selected_languages': assignment.allowed_languages or [],
                })

            assignment.save()
            messages.success(request, 'Cập nhật bài tập thành công!')
            return redirect('assignments:detail', pk=assignment.pk)
    else:
        form = AssignmentForm(instance=assignment, classroom=classroom)

    context = {
        'form': form,
        'assignment': assignment,
        'classroom': classroom,
        'languages': languages,
        'selected_languages': assignment.allowed_languages or [],
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
            type=assignment.type,
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
        notify_users(
            student_ids,
            title=f'Bài tập mới: {assignment.title}',
            message=f'Lớp {classroom.name} vừa công bố bài tập.',
            link=f'/assignments/{assignment.pk}/',
            notification_type='assignment_published',
            actor=request.user,
            metadata={'assignment_id': assignment.pk, 'classroom_id': classroom.pk},
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
        max_size = max_size_mb * 1024 * 1024
        ext = os.path.splitext((uploaded_file.name or '').lower())[1]
        if uploaded_file.size > max_size:
            messages.error(request, f'File tối đa {max_size_mb}MB.')
            return redirect('assignments:detail', pk=pk)
        if ext not in ASSIGNMENT_UPLOAD_EXTENSIONS:
            messages.error(request, 'Định dạng file này chưa được phép tải lên.')
            return redirect('assignments:detail', pk=pk)
        try:
            result = cloudinary.uploader.upload(
                uploaded_file,
                folder='assignment_files/',
                resource_type='auto',
            )
            AssignmentFiles.objects.create(
                assignment=assignment,
                file_name=uploaded_file.name,
                file_url=result.get('secure_url', ''),
                file_size=uploaded_file.size,
                mime_type=uploaded_file.content_type or '',
            )
            messages.success(request, f'Đã tải lên "{uploaded_file.name}".')
        except Exception:
            logger.exception('Failed to upload assignment file assignment=%s user=%s', assignment.pk, request.user.pk)
            messages.error(request, 'Có lỗi xảy ra khi tải file. Vui lòng thử lại.')
    else:
        messages.error(request, 'Vui lòng chọn file để tải lên.')
    return redirect('assignments:detail', pk=pk)


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

    statistics = AssignmentStatistics.objects.filter(assignment=assignment).first()
    testcases = Testcases.objects.filter(assignment=assignment).annotate(
        total_details=Count('submissiondetails'),
        failed_details=Count(
            'submissiondetails',
            filter=~Q(submissiondetails__result_status='passed'),
        ),
    ).order_by('order_index')

    from apps.submissions.models import Submissions, SubmissionDetails
    submissions = Submissions.objects.filter(
        assignment=assignment
    ).select_related('student').order_by('-submitted_at')

    # ===== PHÂN TÍCH NÂNG CAO =====
    # 1. Phổ điểm (distribution) - dựa trên % của max_score
    max_score = assignment.max_score or 100
    buckets = [0, 0, 0, 0, 0]  # [0-20%, 20-40%, 40-60%, 60-80%, 80-100%]
    finished = submissions.filter(status='finished')
    for s in finished:
        pct = (s.total_score / max_score * 100) if max_score > 0 else 0
        idx = min(int(pct // 20), 4)
        buckets[idx] += 1

    score_distribution = {
        'labels': ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
        'data': buckets,
    }

    # 2. Thời gian làm bài trung bình (execution_time)
    exec_times = [s.execution_time for s in finished if s.execution_time]
    avg_exec_time = round(sum(exec_times) / len(exec_times), 2) if exec_times else 0

    # 3. Top sinh viên xuất sắc / yếu (lấy điểm cao nhất mỗi sinh viên)
    best_per_student = {}
    for s in finished:
        uid = s.student_id
        if uid not in best_per_student or s.total_score > best_per_student[uid].total_score:
            best_per_student[uid] = s
    ranked = sorted(best_per_student.values(), key=lambda s: s.total_score, reverse=True)
    top_students = ranked[:5]
    weak_students = list(reversed(ranked[-5:])) if len(ranked) >= 5 else ranked[::-1][:5]

    # 4. Testcase bị fail nhiều nhất
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

    # 6. Số lượng nộp trễ
    late_count = submissions.filter(is_late=True).count()

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'statistics': statistics,
        'testcases': testcases,
        'submissions': submissions[:50],
        'total_submissions_count': submissions.count(),
        'score_distribution_json': json.dumps(score_distribution),
        'error_distribution_json': json.dumps(error_distribution),
        'avg_exec_time': avg_exec_time,
        'top_students': top_students,
        'weak_students': weak_students,
        'tc_fail_stats': tc_fail_stats[:10],
        'late_count': late_count,
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
                score = submission.manual_score if submission.manual_score is not None else submission.total_score
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
            best_score = best.manual_score if best and best.manual_score is not None else (best.total_score if best else 0)
            current_score = submission.manual_score if submission.manual_score is not None else submission.total_score
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
            'delta_minutes': delta_minutes if is_late else 0,
            'delta_label': _format_minutes_vi(delta_minutes) if is_late else 'Đúng hạn',
            'is_late': is_late,
            'is_passed': submission.total_testcases > 0 and submission.passed_testcases >= submission.total_testcases,
        })

    late_rows = [row for row in rows if row['is_late']]
    finished_rows = [row for row in rows if row['sub'].status == 'finished']
    avg_score = round(
        sum(row['sub'].total_score for row in rows) / len(rows),
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
        'Ngôn ngữ', 'Trạng thái'
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
            f'{s.total_score:.2f}',
            f'{s.max_score:.2f}',
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
    writer.writerow([
        'Submission ID', 'Username', 'Họ tên', 'Email', 'Ngôn ngữ',
        'Trạng thái', 'Thời gian nộp', deadline_label, 'Trễ', 'Trễ (phút)',
        '% Phạt', 'Điểm', 'Điểm tối đa', 'Testcase pass', 'Tổng testcase',
        'Thời gian chạy (ms)', 'Bộ nhớ', 'Chấm tay', 'Giáo viên nhận xét',
    ])

    for submission in submissions:
        is_late = _submission_is_late_for_report(submission, deadline)
        late_minutes = _late_minutes_for_submission(submission, deadline) if is_late else 0
        writer.writerow([
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
            f'{submission.total_score:.2f}',
            f'{submission.max_score:.2f}',
            submission.passed_testcases,
            submission.total_testcases,
            submission.execution_time or '',
            submission.memory_usage or '',
            submission.manual_score if submission.manual_score is not None else '',
            submission.teacher_comment or '',
        ])
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
    writer.writerow([
        'Username', 'Họ tên', 'Email', 'Số lần nộp', 'Có nộp',
        'Trạng thái mới nhất', 'Nộp lần cuối', 'Có nộp trễ',
        'Điểm tốt nhất', 'Điểm tối đa', 'Testcase tốt nhất',
        'Submission tốt nhất', 'Submission mới nhất',
    ])

    for row in rows:
        student = row['student']
        best = row['best']
        latest = row['latest']
        best_score = ''
        best_testcases = ''
        if best:
            score = best.manual_score if best.manual_score is not None else best.total_score
            best_score = f'{score:.2f}'
            best_testcases = f'{best.passed_testcases}/{best.total_testcases}'
        writer.writerow([
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
    writer.writerow(['Username', 'Họ tên', 'Email', 'Lớp', 'Bài tập', 'Deadline/Kết thúc thi'])
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
            timezone.localtime(deadline).strftime('%d/%m/%Y %H:%M:%S') if deadline else '',
        ])
    return response
