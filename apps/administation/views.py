import json
import csv
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Avg, Q, F
from django.contrib.auth.models import User

from core.decorators import admin_required
from apps.accounts.models import Profiles, TeacherRegistrations
from apps.classrooms.models import Subjects, SubjectApprovalStatus, Classrooms, ClassroomMembers, ClassroomSubjects, Semesters
from apps.notifications.services import notify_user
from apps.administation.utils import (
    admin_filter_context,
    admin_filter_options,
    build_query_string,
    csv_filename,
    get_choice_param,
    get_date_param,
    get_int_param,
    get_int_setting,
)
from .models import (
    ProgrammingLanguages, SandboxConfigs, ServerMetrics,
    ActivityLogs, SystemSettings,
)
from .forms import (
    AdminPasswordResetForm, AdminUserForm, ProgrammingLanguageForm,
    SandboxConfigForm, SystemSettingForm, SYSTEM_SETTING_SCHEMAS,
)


SUBMISSION_STATUS_FILTER_CHOICES = ['pending', 'running', 'finished', 'error', 'failed', 'timeout']


def _admin_base_context():
    try:
        from apps.classrooms.models import Classrooms
        try:
            pending_classrooms = Classrooms.objects.filter(status='pending').count()
        except:
            pending_classrooms = 0
    except:
        pending_classrooms = 0
    return {
        'pending_teachers_count': TeacherRegistrations.objects.filter(status='pending').count(),
        'pending_subjects_count': Subjects.objects.filter(status=SubjectApprovalStatus.PENDING).count(),
        'pending_classrooms_count': pending_classrooms,
    }


def _log_admin_action(actor, action, resource_type, resource_id=None, metadata=None, request=None):
    ActivityLogs.objects.create(
        user=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=_get_client_ip_from_request(request) if request else None,
        user_agent=(request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''),
        metadata=metadata or {},
    )


def _get_client_ip_from_request(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR') if request else None
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') if request else None


def _admin_user_return_redirect(request):
    return_to = request.POST.get('return_to') or request.GET.get('return_to') or 'user_management'
    allowed = {
        'user_management': 'administation:user_management',
        'teacher_management': 'administation:teacher_management',
        'student_management': 'administation:student_management',
    }
    return redirect(allowed.get(return_to, 'administation:user_management'))


def _csv_response(filename):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    return response


def _csv_dropdown_item(url_name, label, icon='table_rows', export_type='', **kwargs):
    return {
        'url': reverse(url_name, kwargs=kwargs),
        'type': export_type,
        'icon': icon,
        'label': label,
        'primary': not export_type,
    }


def _warn_invalid_int_filters(request, fields):
    invalid_labels = []
    for name, label, minimum in fields:
        raw_value = request.GET.get(name)
        if raw_value in (None, ''):
            continue
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            invalid_labels.append(label)
            continue
        if minimum is not None and value < minimum:
            invalid_labels.append(label)

    if invalid_labels:
        messages.warning(
            request,
            'Đã bỏ qua bộ lọc không hợp lệ: %s.' % ', '.join(invalid_labels),
        )


def _selected_int_ids_from_post(request, name, label):
    valid_ids = []
    invalid_count = 0
    for raw_value in request.POST.getlist(name):
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            invalid_count += 1
            continue
        if value <= 0:
            invalid_count += 1
            continue
        valid_ids.append(value)

    if invalid_count:
        messages.warning(request, f'Đã bỏ qua {invalid_count} {label} không hợp lệ.')
    return list(dict.fromkeys(valid_ids))


def _apply_admin_user_form(user, form, actor, request, created=False):
    old_role = None
    old_is_active = None
    if not created:
        old_role = getattr(getattr(user, 'profiles', None), 'role', 'student')
        old_is_active = user.is_active

    user.username = form.cleaned_data['username']
    user.email = form.cleaned_data.get('email') or ''
    user.first_name = form.cleaned_data.get('first_name') or ''
    user.last_name = form.cleaned_data.get('last_name') or ''
    user.is_active = form.cleaned_data.get('is_active', False)
    role = form.cleaned_data['role']
    user.is_staff = role == 'admin' or user.is_superuser
    password = form.cleaned_data.get('password')
    if password:
        user.set_password(password)
    user.save()

    profile, _ = Profiles.objects.get_or_create(id=user)
    profile.role = role
    profile.status = 'approved' if user.is_active else 'inactive'
    profile.save(update_fields=['role', 'status', 'updated_at'])

    if created or old_role != role:
        _log_admin_action(
            actor,
            'ADMIN_ROLE_CHANGE' if not created else 'ADMIN_USER_CREATE',
            'accounts',
            user.pk,
            {
                'old_role': old_role,
                'new_role': role,
                'actor_id': actor.pk,
                'target_user_id': user.pk,
                'target_username': user.username,
                'created': created,
            },
            request=request,
        )
    if not created and old_is_active != user.is_active:
        _log_admin_action(
            actor,
            'ADMIN_USER_STATUS_CHANGE',
            'accounts',
            user.pk,
            {
                'old_is_active': old_is_active,
                'new_is_active': user.is_active,
                'actor_id': actor.pk,
                'target_user_id': user.pk,
                'target_username': user.username,
            },
            request=request,
        )
    return user


def _notify_classroom_review(classroom, actor, approved=True):
    if not classroom.teacher:
        return
    notify_user(
        classroom.teacher,
        title=(
            f'Lớp học đã được duyệt: {classroom.name}'
            if approved else
            f'Lớp học bị từ chối: {classroom.name}'
        ),
        message=(
            'Lớp của bạn đã được admin duyệt và đang hoạt động.'
            if approved else
            'Admin đã từ chối lớp học này. Vui lòng kiểm tra và tạo lại nếu cần.'
        ),
        link=f'/classrooms/{classroom.pk}/' if approved else '/classrooms/',
        notification_type='classroom_approved' if approved else 'classroom_rejected',
        actor=actor,
        metadata={'classroom_id': classroom.pk},
    )


def _notify_subject_review(subject, actor, approved=True):
    if not subject.created_by:
        return
    notify_user(
        subject.created_by,
        title=(
            f'Môn học đã được duyệt: {subject.name}'
            if approved else
            f'Môn học bị từ chối: {subject.name}'
        ),
        message=(
            'Môn học của bạn đã được admin duyệt và có thể sử dụng.'
            if approved else
            'Admin đã từ chối môn học này. Vui lòng kiểm tra lại thông tin môn.'
        ),
        link='/classrooms/',
        notification_type='subject_approved' if approved else 'subject_rejected',
        actor=actor,
        metadata={'subject_id': subject.pk},
    )


@admin_required
def admin_dashboard_view(request):
    total_users = User.objects.count()
    total_teachers = Profiles.objects.filter(role='teacher').count()
    total_students = Profiles.objects.filter(role='student').count()
    pending_teachers = TeacherRegistrations.objects.filter(status='pending').count()

    from apps.classrooms.models import Classrooms
    from apps.submissions.models import ExamSessions, Submissions
    total_classrooms = Classrooms.objects.filter(is_active=True).count()
    pending_classrooms = Classrooms.objects.filter(status='pending').count()
    total_submissions = Submissions.objects.count()
    pending_subjects = Subjects.objects.filter(status=SubjectApprovalStatus.PENDING).count()
    zombie_cutoff = timezone.now() - timezone.timedelta(minutes=30)
    zombie_submissions = Submissions.objects.filter(
        status__in=['pending', 'running'],
        submitted_at__lt=zombie_cutoff,
    ).count()
    warning_sessions = ExamSessions.objects.filter(violation_count__gt=0).count()

    active_languages = ProgrammingLanguages.objects.filter(is_active=True).count()
    active_sandboxes = SandboxConfigs.objects.filter(is_active=True).count()

    latest_metrics = ServerMetrics.objects.order_by('-recorded_at').first()

    recent_registrations = TeacherRegistrations.objects.filter(
        status='pending'
    ).select_related('user').order_by('-created_at')[:5]

    recent_logs = ActivityLogs.objects.select_related(
        'user'
    ).order_by('-created_at')[:10]

    context = {
        **_admin_base_context(),
        'total_users': total_users,
        'total_teachers': total_teachers,
        'total_students': total_students,
        'pending_teachers': pending_teachers,
        'total_classrooms': total_classrooms,
        'pending_classrooms': pending_classrooms,
        'total_submissions': total_submissions,
        'pending_subjects': pending_subjects,
        'zombie_submissions': zombie_submissions,
        'warning_sessions': warning_sessions,
        'active_languages': active_languages,
        'active_sandboxes': active_sandboxes,
        'latest_metrics': latest_metrics,
        'recent_registrations': recent_registrations,
        'recent_logs': recent_logs,
        'current_page': 'dashboard',
    }
    return render(request, 'administration/dashboard.html', context)


@admin_required
def teacher_approvals_view(request):
    return _render_user_management_page(
        request,
        forced_role='teacher',
        current_page='teacher_management',
        page_title='Quản lý giáo viên',
        page_description='Quản lý tài khoản giáo viên và duyệt đơn đăng ký trong cùng một màn hình.',
        empty_icon='school',
        empty_title='Không tìm thấy giáo viên',
        empty_description='Chưa có giáo viên nào được phê duyệt.',
        show_teacher_approvals=True,
        approval_status_source='status',
    )


@admin_required
def teacher_management_view(request):
    return _render_user_management_page(
        request,
        forced_role='teacher',
        current_page='teacher_management',
        page_title='Quản lý giáo viên',
        page_description='Kế thừa đầy đủ search, bulk action, CSV và hồ sơ từ quản lý người dùng.',
        empty_icon='school',
        empty_title='Không tìm thấy giáo viên',
        empty_description='Chưa có giáo viên nào được phê duyệt.',
        show_teacher_approvals=True,
    )


@admin_required
def student_management_view(request):
    return _render_user_management_page(
        request,
        forced_role='student',
        current_page='student_management',
        page_title='Quản lý học sinh',
        page_description='Kế thừa đầy đủ search, bulk action, CSV và hồ sơ từ quản lý người dùng.',
        empty_icon='person',
        empty_title='Không tìm thấy học sinh',
        empty_description='Chưa có học sinh nào.',
    )


def _user_management_queryset():
    return User.objects.select_related('profiles').annotate(
        assignment_count=Count('submissions__assignment', distinct=True),
        submission_count=Count('submissions', distinct=True),
        teaching_class_count=Count('classrooms', distinct=True),
        joined_class_count=Count('classroommembers', filter=Q(classroommembers__status='approved'), distinct=True),
        created_assignment_count=Count('assignments', distinct=True),
        graded_submission_count=Count('graded_submissions', distinct=True),
    ).order_by('-date_joined')


def _user_filter_values(request, forced_role=None):
    role_choices = ['all', 'student', 'teacher', 'admin', 'staff', 'superuser']
    return {
        'role_filter': forced_role or get_choice_param(request.GET, 'role', role_choices, 'all'),
        'search_query': request.GET.get('search', '').strip(),
        'status_filter': get_choice_param(request.GET, 'status', ['all', 'active', 'inactive'], 'all'),
        'profile_status_filter': get_choice_param(
            request.GET,
            'profile_status',
            ['all', 'approved', 'pending', 'rejected', 'inactive'],
            'all',
        ),
        'classroom_filter': get_int_param(request.GET, 'classroom_id', minimum=1),
        'subject_filter': get_int_param(request.GET, 'subject_id', minimum=1),
        'has_teaching_classes_filter': get_choice_param(request.GET, 'has_teaching_classes', ['all', 'yes', 'no'], 'all'),
        'has_joined_class_filter': get_choice_param(request.GET, 'has_joined_class', ['all', 'yes', 'no'], 'all'),
        'last_login_filter': get_choice_param(request.GET, 'last_login', ['all', 'never', '7d', '30d', '90d'], 'all'),
        'date_joined_from': get_date_param(request.GET, 'date_joined_from'),
        'date_joined_to': get_date_param(request.GET, 'date_joined_to'),
        'has_submissions_filter': get_choice_param(request.GET, 'has_submissions', ['all', 'yes', 'no'], 'all'),
        'submission_status_filter': get_choice_param(
            request.GET,
            'submission_status',
            SUBMISSION_STATUS_FILTER_CHOICES,
            '',
        ),
        'approval_status_filter': get_choice_param(
            request.GET,
            'approval_status',
            ['pending', 'approved', 'rejected'],
            '',
        ),
    }


def _apply_user_filters(users, filters):
    role_filter = filters['role_filter']
    search_query = filters['search_query']
    status_filter = filters['status_filter']
    profile_status_filter = filters['profile_status_filter']
    classroom_id = filters['classroom_filter']
    subject_id = filters['subject_filter']

    approval_status_filter = filters.get('approval_status_filter')

    if approval_status_filter and role_filter in ('all', 'teacher'):
        users = users.filter(teacherregistrations__status=approval_status_filter)
    elif role_filter == 'staff':
        users = users.filter(is_staff=True)
    elif role_filter == 'superuser':
        users = users.filter(is_superuser=True)
    elif role_filter != 'all':
        users = users.filter(profiles__role=role_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    if profile_status_filter != 'all':
        users = users.filter(profiles__status=profile_status_filter)

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if filters['has_teaching_classes_filter'] == 'yes':
        users = users.filter(classrooms__isnull=False)
    elif filters['has_teaching_classes_filter'] == 'no':
        users = users.filter(classrooms__isnull=True)

    if filters['has_joined_class_filter'] == 'yes':
        users = users.filter(classroommembers__status='approved')
    elif filters['has_joined_class_filter'] == 'no':
        users = users.exclude(classroommembers__status='approved')

    if classroom_id:
        if role_filter == 'teacher':
            users = users.filter(classrooms__id=classroom_id)
        elif role_filter == 'student':
            users = users.filter(classroommembers__classroom_id=classroom_id, classroommembers__status='approved')
        else:
            users = users.filter(
                Q(classrooms__id=classroom_id) |
                Q(classroommembers__classroom_id=classroom_id, classroommembers__status='approved')
            )

    if subject_id:
        teacher_subject_q = Q(
            classrooms__classroom_subject_links__subject_id=subject_id,
            classrooms__classroom_subject_links__is_active=True,
        )
        student_subject_q = Q(
            classroommembers__classroom__classroom_subject_links__subject_id=subject_id,
            classroommembers__classroom__classroom_subject_links__is_active=True,
            classroommembers__status='approved',
        )
        if role_filter == 'teacher':
            users = users.filter(teacher_subject_q)
        elif role_filter == 'student':
            users = users.filter(student_subject_q)
        else:
            users = users.filter(teacher_subject_q | student_subject_q)

    last_login_filter = filters['last_login_filter']
    if last_login_filter == 'never':
        users = users.filter(last_login__isnull=True)
    elif last_login_filter in ('7d', '30d', '90d'):
        days = int(last_login_filter.removesuffix('d'))
        users = users.filter(last_login__gte=timezone.now() - timedelta(days=days))

    if filters['date_joined_from']:
        users = users.filter(date_joined__date__gte=filters['date_joined_from'])
    if filters['date_joined_to']:
        users = users.filter(date_joined__date__lte=filters['date_joined_to'])

    if filters['has_submissions_filter'] == 'yes':
        users = users.filter(submissions__isnull=False)
    elif filters['has_submissions_filter'] == 'no':
        users = users.filter(submissions__isnull=True)

    if filters['submission_status_filter']:
        users = users.filter(submissions__status=filters['submission_status_filter'])

    return users.distinct()


def _user_filter_badge_value_labels(filters):
    value_labels = {
        'role': {
            'all': 'Tất cả',
            'student': 'Học sinh',
            'teacher': 'Giáo viên',
            'admin': 'Admin',
            'staff': 'Staff',
            'superuser': 'Superuser',
        },
        'status': {'all': 'Tất cả', 'active': 'Hoạt động', 'inactive': 'Vô hiệu'},
        'profile_status': {'all': 'Tất cả', 'approved': 'Đã duyệt', 'pending': 'Chờ duyệt', 'rejected': 'Từ chối', 'inactive': 'Inactive'},
        'has_teaching_classes': {'all': 'Tất cả', 'yes': 'Có lớp dạy', 'no': 'Chưa có lớp dạy'},
        'has_joined_class': {'all': 'Tất cả', 'yes': 'Có lớp học', 'no': 'Chưa tham gia lớp'},
        'last_login': {'all': 'Tất cả', 'never': 'Chưa đăng nhập', '7d': '7 ngày gần đây', '30d': '30 ngày gần đây', '90d': '90 ngày gần đây'},
        'has_submissions': {'all': 'Tất cả', 'yes': 'Có bài nộp', 'no': 'Chưa có bài nộp'},
    }
    if filters.get('classroom_filter'):
        classroom = Classrooms.objects.filter(pk=filters['classroom_filter']).first()
        if classroom:
            value_labels['classroom_id'] = {str(classroom.pk): classroom.name}
    if filters.get('subject_filter'):
        subject = Subjects.objects.filter(pk=filters['subject_filter']).first()
        if subject:
            value_labels['subject_id'] = {str(subject.pk): f'{subject.code} - {subject.name}'}
    return value_labels


APPROVAL_FILTER_KEYS = {
    'approval_status',
    'approval_search',
    'approval_institution',
    'approval_created_from',
    'approval_created_to',
    'approval_reviewed_by',
    'approval_page',
}


def _hidden_fields_from_query(request, excluded_keys):
    fields = []
    for key in request.GET.keys():
        if key in excluded_keys:
            continue
        for value in request.GET.getlist(key):
            if value not in (None, ''):
                fields.append({'name': key, 'value': value})
    return fields


def _teacher_registration_filter_values(request, status_source='approval_status'):
    status_filter = get_choice_param(
        request.GET,
        status_source,
        ['all', 'pending', 'approved', 'rejected'],
        'pending',
    )
    if status_source != 'approval_status':
        status_filter = get_choice_param(
            request.GET,
            'approval_status',
            ['all', 'pending', 'approved', 'rejected'],
            status_filter,
        )

    return {
        'status_filter': status_filter,
        'search_query': request.GET.get('approval_search', '').strip(),
        'institution_filter': request.GET.get('approval_institution', '').strip(),
        'created_from': get_date_param(request.GET, 'approval_created_from'),
        'created_to': get_date_param(request.GET, 'approval_created_to'),
        'reviewed_by_filter': get_int_param(request.GET, 'approval_reviewed_by', minimum=1),
    }


def _apply_teacher_registration_filters(registrations, filters):
    if filters['status_filter'] != 'all':
        registrations = registrations.filter(status=filters['status_filter'])

    if filters['search_query']:
        registrations = registrations.filter(
            Q(user__username__icontains=filters['search_query']) |
            Q(user__first_name__icontains=filters['search_query']) |
            Q(user__last_name__icontains=filters['search_query']) |
            Q(user__email__icontains=filters['search_query'])
        )

    if filters['institution_filter']:
        registrations = registrations.filter(institution__icontains=filters['institution_filter'])

    if filters['created_from']:
        registrations = registrations.filter(created_at__date__gte=filters['created_from'])
    if filters['created_to']:
        registrations = registrations.filter(created_at__date__lte=filters['created_to'])

    if filters['reviewed_by_filter']:
        registrations = registrations.filter(reviewed_by_id=filters['reviewed_by_filter'])

    return registrations


def _teacher_registration_badge_value_labels(filters):
    labels = {
        'approval_status': {
            'all': 'Tất cả',
            'pending': 'Chờ duyệt',
            'approved': 'Đã duyệt',
            'rejected': 'Từ chối',
        },
    }
    if filters.get('reviewed_by_filter'):
        reviewer = User.objects.filter(pk=filters['reviewed_by_filter']).first()
        if reviewer:
            labels['approval_reviewed_by'] = {
                str(reviewer.pk): reviewer.get_full_name() or reviewer.username,
            }
    return labels


def _teacher_registration_query_links(request):
    return {
        status: build_query_string(
            request,
            remove=('approval_page',),
            approval_status=status,
        )
        for status in ('pending', 'approved', 'rejected', 'all')
    }


def _teacher_registration_context(request, status_source='approval_status'):
    filters = _teacher_registration_filter_values(request, status_source)

    registrations = TeacherRegistrations.objects.select_related(
        'user', 'reviewed_by'
    ).order_by('-created_at')

    registrations = _apply_teacher_registration_filters(registrations, filters)

    paginator = Paginator(registrations, 10)
    page_obj = paginator.get_page(request.GET.get('approval_page', 1))
    approval_clear_query_string = build_query_string(
        request,
        remove=APPROVAL_FILTER_KEYS,
    )

    return {
        'registrations': page_obj,
        'registration_page_obj': page_obj,
        'approval_status_filter': filters['status_filter'],
        'approval_search_query': filters['search_query'],
        'approval_institution_filter': filters['institution_filter'],
        'approval_created_from': filters['created_from'].isoformat() if filters['created_from'] else '',
        'approval_created_to': filters['created_to'].isoformat() if filters['created_to'] else '',
        'approval_reviewed_by_filter': filters['reviewed_by_filter'],
        'approval_status_links': _teacher_registration_query_links(request),
        'approval_clear_query_string': approval_clear_query_string,
        'approval_user_filter_hidden_fields': _hidden_fields_from_query(request, APPROVAL_FILTER_KEYS | {'page'}),
        'pending_count': TeacherRegistrations.objects.filter(status='pending').count(),
        'approved_count': TeacherRegistrations.objects.filter(status='approved').count(),
        'rejected_count': TeacherRegistrations.objects.filter(status='rejected').count(),
        'teacher_registration_filter_labels': _teacher_registration_badge_value_labels(filters),
    }


def _subject_filter_values(request):
    return {
        'search_query': request.GET.get('search', '').strip(),
        'classroom_filter': get_int_param(request.GET, 'classroom_id', minimum=1),
        'teacher_filter': get_int_param(request.GET, 'teacher_id', minimum=1),
        'semester_filter': get_int_param(request.GET, 'semester_id', minimum=1),
        'language_filter': get_int_param(request.GET, 'language_id', minimum=1),
        'status_filter': get_choice_param(
            request.GET,
            'status',
            ['all', 'pending', 'approved', 'rejected'],
            'all',
        ),
        'is_active_filter': get_choice_param(request.GET, 'is_active', ['all', 'active', 'inactive'], 'all'),
        'has_assignments_filter': get_choice_param(request.GET, 'has_assignments', ['all', 'yes', 'no'], 'all'),
        'has_exams_filter': get_choice_param(request.GET, 'has_exams', ['all', 'yes', 'no'], 'all'),
        'sandbox_status_filter': get_choice_param(request.GET, 'sandbox_status', ['all', 'ready', 'missing'], 'all'),
        'created_from': get_date_param(request.GET, 'created_from'),
        'created_to': get_date_param(request.GET, 'created_to'),
    }


def _subject_base_queryset():
    return Subjects.objects.select_related(
        'created_by', 'approved_by'
    ).prefetch_related('languages').annotate(
        classroom_count=Count('classroom_links', filter=Q(classroom_links__is_active=True), distinct=True),
        assignment_count=Count('classroom_links__assignments', distinct=True),
        exam_count=Count(
            'classroom_links__assignments',
            filter=Q(classroom_links__assignments__is_exam=True),
            distinct=True,
        ),
        language_count=Count('languages', distinct=True),
    ).order_by('-created_at')


def _apply_subject_filters(subjects, filters):
    if filters['status_filter'] != 'all':
        subjects = subjects.filter(status=filters['status_filter'])

    if filters['is_active_filter'] == 'active':
        subjects = subjects.filter(is_active=True)
    elif filters['is_active_filter'] == 'inactive':
        subjects = subjects.filter(is_active=False)

    if filters['search_query']:
        subjects = subjects.filter(
            Q(code__icontains=filters['search_query']) |
            Q(name__icontains=filters['search_query']) |
            Q(description__icontains=filters['search_query']) |
            Q(created_by__username__icontains=filters['search_query']) |
            Q(created_by__first_name__icontains=filters['search_query']) |
            Q(created_by__last_name__icontains=filters['search_query'])
        )

    if filters['classroom_filter']:
        subjects = subjects.filter(
            classroom_links__classroom_id=filters['classroom_filter'],
            classroom_links__is_active=True,
        )

    if filters['teacher_filter']:
        subjects = subjects.filter(
            Q(created_by_id=filters['teacher_filter']) |
            Q(classroom_links__classroom__teacher_id=filters['teacher_filter'], classroom_links__is_active=True)
        )

    if filters['semester_filter']:
        subjects = subjects.filter(
            classroom_links__semester_id=filters['semester_filter'],
            classroom_links__is_active=True,
        )

    if filters['language_filter']:
        subjects = subjects.filter(languages__id=filters['language_filter'])

    if filters['has_assignments_filter'] == 'yes':
        subjects = subjects.filter(assignment_count__gt=0)
    elif filters['has_assignments_filter'] == 'no':
        subjects = subjects.filter(assignment_count=0)

    if filters['has_exams_filter'] == 'yes':
        subjects = subjects.filter(exam_count__gt=0)
    elif filters['has_exams_filter'] == 'no':
        subjects = subjects.filter(exam_count=0)

    if filters['sandbox_status_filter'] != 'all':
        active_sandbox_languages = list(
            SandboxConfigs.objects.filter(is_active=True).values_list('language', flat=True)
        )
        if filters['sandbox_status_filter'] == 'ready':
            subjects = subjects.filter(languages__name__in=active_sandbox_languages)
        elif filters['sandbox_status_filter'] == 'missing':
            missing_language_ids = ProgrammingLanguages.objects.exclude(
                name__in=active_sandbox_languages
            ).values_list('id', flat=True)
            subjects = subjects.filter(Q(languages__id__in=missing_language_ids) | Q(languages__isnull=True))

    if filters['created_from']:
        subjects = subjects.filter(created_at__date__gte=filters['created_from'])
    if filters['created_to']:
        subjects = subjects.filter(created_at__date__lte=filters['created_to'])

    return subjects.distinct()


def _subject_filter_badge_value_labels(filters):
    labels = {
        'status': {'all': 'Tất cả', 'pending': 'Chờ duyệt', 'approved': 'Đã duyệt', 'rejected': 'Từ chối'},
        'is_active': {'all': 'Tất cả', 'active': 'Đang bật', 'inactive': 'Đã ẩn'},
        'has_assignments': {'all': 'Tất cả', 'yes': 'Có bài tập', 'no': 'Chưa có bài tập'},
        'has_exams': {'all': 'Tất cả', 'yes': 'Có bài thi', 'no': 'Chưa có bài thi'},
        'sandbox_status': {'all': 'Tất cả', 'ready': 'Có sandbox', 'missing': 'Thiếu sandbox'},
    }
    if filters.get('classroom_filter'):
        classroom = Classrooms.objects.filter(pk=filters['classroom_filter']).first()
        if classroom:
            labels['classroom_id'] = {str(classroom.pk): classroom.name}
    if filters.get('teacher_filter'):
        teacher = User.objects.filter(pk=filters['teacher_filter']).first()
        if teacher:
            labels['teacher_id'] = {str(teacher.pk): teacher.get_full_name() or teacher.username}
    if filters.get('semester_filter'):
        semester = Semesters.objects.filter(pk=filters['semester_filter']).first()
        if semester:
            labels['semester_id'] = {str(semester.pk): semester.name}
    if filters.get('language_filter'):
        language = ProgrammingLanguages.objects.filter(pk=filters['language_filter']).first()
        if language:
            labels['language_id'] = {str(language.pk): language.display_name or language.name}
    return labels


def _subject_status_links(request):
    return {
        status: build_query_string(request, remove=('page',), status=status)
        for status in ('all', 'pending', 'approved', 'rejected')
    }


def _subject_classroom_links_for_export(subjects, filters):
    links = ClassroomSubjects.objects.filter(subject__in=subjects).select_related(
        'subject', 'classroom', 'classroom__teacher', 'semester'
    ).annotate(
        assignment_count=Count('assignments', distinct=True),
        exam_count=Count('assignments', filter=Q(assignments__is_exam=True), distinct=True),
    ).order_by('subject__code', 'classroom__name')

    if filters['classroom_filter']:
        links = links.filter(classroom_id=filters['classroom_filter'])
    if filters['teacher_filter']:
        links = links.filter(
            Q(subject__created_by_id=filters['teacher_filter']) |
            Q(classroom__teacher_id=filters['teacher_filter'])
        )
    if filters['semester_filter']:
        links = links.filter(semester_id=filters['semester_filter'])
    return links.distinct()


def _classroom_filter_values(request):
    status_filter = get_choice_param(
        request.GET,
        'status',
        ['all', 'pending', 'approved', 'rejected'],
        'all',
    )
    is_active_filter = get_choice_param(request.GET, 'is_active', ['all', 'active', 'inactive'], 'all')
    legacy_status = request.GET.get('status')
    if legacy_status in ('active', 'inactive') and is_active_filter == 'all':
        status_filter = 'all'
        is_active_filter = legacy_status

    return {
        'search_query': request.GET.get('search', '').strip(),
        'subject_filter': get_int_param(request.GET, 'subject_id', minimum=1),
        'teacher_filter': get_int_param(request.GET, 'teacher_id', minimum=1),
        'semester_filter': get_int_param(request.GET, 'semester_id', minimum=1),
        'status_filter': status_filter,
        'is_active_filter': is_active_filter,
        'member_count_min': get_int_param(request.GET, 'member_count_min', minimum=0),
        'member_count_max': get_int_param(request.GET, 'member_count_max', minimum=0),
        'capacity_status_filter': get_choice_param(
            request.GET,
            'capacity_status',
            ['all', 'available', 'full', 'over_capacity'],
            'all',
        ),
        'has_subjects_filter': get_choice_param(request.GET, 'has_subjects', ['all', 'yes', 'no'], 'all'),
        'has_assignments_filter': get_choice_param(request.GET, 'has_assignments', ['all', 'yes', 'no'], 'all'),
        'has_exams_filter': get_choice_param(request.GET, 'has_exams', ['all', 'yes', 'no'], 'all'),
        'has_pending_members_filter': get_choice_param(request.GET, 'has_pending_members', ['all', 'yes', 'no'], 'all'),
        'created_from': get_date_param(request.GET, 'created_from'),
        'created_to': get_date_param(request.GET, 'created_to'),
    }


def _classroom_base_queryset():
    return Classrooms.objects.select_related('teacher', 'approved_by').annotate(
        member_count=Count('classroommembers', filter=Q(classroommembers__status='approved'), distinct=True),
        pending_member_count=Count('classroommembers', filter=Q(classroommembers__status='pending'), distinct=True),
        subject_count=Count(
            'classroom_subject_links',
            filter=Q(classroom_subject_links__is_active=True),
            distinct=True,
        ),
        assignment_count=Count('assignments', distinct=True),
        exam_assignment_count=Count('assignments', filter=Q(assignments__is_exam=True), distinct=True),
    ).order_by('-created_at')


def _apply_classroom_filters(classrooms, filters):
    if filters['status_filter'] != 'all':
        classrooms = classrooms.filter(status=filters['status_filter'])

    if filters['is_active_filter'] == 'active':
        classrooms = classrooms.filter(is_active=True)
    elif filters['is_active_filter'] == 'inactive':
        classrooms = classrooms.filter(is_active=False)

    if filters['search_query']:
        classrooms = classrooms.filter(
            Q(name__icontains=filters['search_query']) |
            Q(description__icontains=filters['search_query']) |
            Q(teacher__username__icontains=filters['search_query']) |
            Q(teacher__first_name__icontains=filters['search_query']) |
            Q(teacher__last_name__icontains=filters['search_query'])
        )

    if filters['subject_filter']:
        classrooms = classrooms.filter(
            classroom_subject_links__subject_id=filters['subject_filter'],
            classroom_subject_links__is_active=True,
        )

    if filters['teacher_filter']:
        classrooms = classrooms.filter(teacher_id=filters['teacher_filter'])

    if filters['semester_filter']:
        classrooms = classrooms.filter(
            classroom_subject_links__semester_id=filters['semester_filter'],
            classroom_subject_links__is_active=True,
        )

    if filters['member_count_min'] is not None:
        classrooms = classrooms.filter(member_count__gte=filters['member_count_min'])
    if filters['member_count_max'] is not None:
        classrooms = classrooms.filter(member_count__lte=filters['member_count_max'])

    if filters['capacity_status_filter'] == 'available':
        classrooms = classrooms.filter(member_count__lt=F('max_students'))
    elif filters['capacity_status_filter'] == 'full':
        classrooms = classrooms.filter(member_count=F('max_students'))
    elif filters['capacity_status_filter'] == 'over_capacity':
        classrooms = classrooms.filter(member_count__gt=F('max_students'))

    if filters['has_subjects_filter'] == 'yes':
        classrooms = classrooms.filter(subject_count__gt=0)
    elif filters['has_subjects_filter'] == 'no':
        classrooms = classrooms.filter(subject_count=0)

    if filters['has_assignments_filter'] == 'yes':
        classrooms = classrooms.filter(assignment_count__gt=0)
    elif filters['has_assignments_filter'] == 'no':
        classrooms = classrooms.filter(assignment_count=0)

    if filters['has_exams_filter'] == 'yes':
        classrooms = classrooms.filter(exam_assignment_count__gt=0)
    elif filters['has_exams_filter'] == 'no':
        classrooms = classrooms.filter(exam_assignment_count=0)

    if filters['has_pending_members_filter'] == 'yes':
        classrooms = classrooms.filter(pending_member_count__gt=0)
    elif filters['has_pending_members_filter'] == 'no':
        classrooms = classrooms.filter(pending_member_count=0)

    if filters['created_from']:
        classrooms = classrooms.filter(created_at__date__gte=filters['created_from'])
    if filters['created_to']:
        classrooms = classrooms.filter(created_at__date__lte=filters['created_to'])

    return classrooms.distinct()


def _classroom_filter_badge_value_labels(filters):
    labels = {
        'status': {'all': 'Tất cả', 'pending': 'Chờ duyệt', 'approved': 'Đã duyệt', 'rejected': 'Từ chối'},
        'is_active': {'all': 'Tất cả', 'active': 'Hoạt động', 'inactive': 'Vô hiệu'},
        'capacity_status': {'all': 'Tất cả', 'available': 'Còn chỗ', 'full': 'Đầy lớp', 'over_capacity': 'Vượt giới hạn'},
        'has_subjects': {'all': 'Tất cả', 'yes': 'Có môn', 'no': 'Chưa có môn'},
        'has_assignments': {'all': 'Tất cả', 'yes': 'Có bài tập', 'no': 'Chưa có bài tập'},
        'has_exams': {'all': 'Tất cả', 'yes': 'Có bài thi', 'no': 'Chưa có bài thi'},
        'has_pending_members': {'all': 'Tất cả', 'yes': 'Có chờ duyệt', 'no': 'Không có chờ duyệt'},
    }
    if filters.get('subject_filter'):
        subject = Subjects.objects.filter(pk=filters['subject_filter']).first()
        if subject:
            labels['subject_id'] = {str(subject.pk): f'{subject.code} - {subject.name}'}
    if filters.get('teacher_filter'):
        teacher = User.objects.filter(pk=filters['teacher_filter']).first()
        if teacher:
            labels['teacher_id'] = {str(teacher.pk): teacher.get_full_name() or teacher.username}
    if filters.get('semester_filter'):
        semester = Semesters.objects.filter(pk=filters['semester_filter']).first()
        if semester:
            labels['semester_id'] = {str(semester.pk): semester.name}
    return labels


def _classroom_status_links(request):
    return {
        status: build_query_string(request, remove=('page',), status=status, is_active='all')
        for status in ('all', 'pending', 'approved', 'rejected')
    }


def _classroom_active_links(request):
    return {
        state: build_query_string(request, remove=('page',), status='all', is_active=state)
        for state in ('active', 'inactive')
    }


def _assignment_language_names():
    return set(_assignment_language_usage_counts().keys())


def _assignment_language_usage_counts():
    from apps.assignments.models import Assignments

    usage_counts = {}
    for languages in Assignments.objects.exclude(allowed_languages__isnull=True).values_list('allowed_languages', flat=True):
        if languages:
            for language in set(language for language in languages if language):
                usage_counts[language] = usage_counts.get(language, 0) + 1
    return usage_counts


def _language_filter_values(request):
    return {
        'search_query': request.GET.get('search', '').strip(),
        'is_active_filter': get_choice_param(request.GET, 'is_active', ['all', 'active', 'inactive'], 'all'),
        'has_sandbox_filter': get_choice_param(request.GET, 'has_sandbox', ['all', 'yes', 'no'], 'all'),
        'used_by_subject_filter': get_choice_param(request.GET, 'used_by_subject', ['all', 'yes', 'no'], 'all'),
        'used_by_assignment_filter': get_choice_param(request.GET, 'used_by_assignment', ['all', 'yes', 'no'], 'all'),
        'extension_filter': request.GET.get('extension', '').strip(),
        'sort_filter': get_choice_param(
            request.GET,
            'sort',
            ['display_name', 'subject_count', 'created_at'],
            'display_name',
        ),
    }


def _language_base_queryset():
    return ProgrammingLanguages.objects.annotate(
        subject_count=Count('subjects', distinct=True),
    )


def _apply_language_filters(languages, filters):
    if filters['is_active_filter'] == 'active':
        languages = languages.filter(is_active=True)
    elif filters['is_active_filter'] == 'inactive':
        languages = languages.filter(is_active=False)

    if filters['search_query']:
        languages = languages.filter(
            Q(name__icontains=filters['search_query']) |
            Q(display_name__icontains=filters['search_query']) |
            Q(file_extension__icontains=filters['search_query'])
        )

    active_sandbox_languages = SandboxConfigs.objects.filter(is_active=True).values_list('language', flat=True)
    if filters['has_sandbox_filter'] == 'yes':
        languages = languages.filter(name__in=active_sandbox_languages)
    elif filters['has_sandbox_filter'] == 'no':
        languages = languages.exclude(name__in=active_sandbox_languages)

    if filters['used_by_subject_filter'] == 'yes':
        languages = languages.filter(subject_count__gt=0)
    elif filters['used_by_subject_filter'] == 'no':
        languages = languages.filter(subject_count=0)

    assignment_language_names = _assignment_language_names()
    if filters['used_by_assignment_filter'] == 'yes':
        languages = languages.filter(name__in=assignment_language_names)
    elif filters['used_by_assignment_filter'] == 'no':
        languages = languages.exclude(name__in=assignment_language_names)

    if filters['extension_filter']:
        languages = languages.filter(file_extension__iexact=filters['extension_filter'])

    if filters['sort_filter'] == 'subject_count':
        languages = languages.order_by('-subject_count', 'display_name', 'name')
    elif filters['sort_filter'] == 'created_at':
        languages = languages.order_by('-created_at', 'display_name', 'name')
    else:
        languages = languages.order_by('display_name', 'name')

    return languages.distinct()


def _language_filter_badge_value_labels(filters):
    return {
        'is_active': {'all': 'Tất cả', 'active': 'Đang bật', 'inactive': 'Đã tắt'},
        'has_sandbox': {'all': 'Tất cả', 'yes': 'Có sandbox active', 'no': 'Thiếu sandbox'},
        'used_by_subject': {'all': 'Tất cả', 'yes': 'Có môn dùng', 'no': 'Chưa môn nào dùng'},
        'used_by_assignment': {'all': 'Tất cả', 'yes': 'Có bài dùng', 'no': 'Chưa bài nào dùng'},
        'sort': {'display_name': 'Tên hiển thị', 'subject_count': 'Số môn đang dùng', 'created_at': 'Ngày tạo'},
    }


def _get_float_param(params, name, default=None, minimum=None, maximum=None):
    value = params.get(name)
    if value in (None, ''):
        return default
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _sandbox_filter_values(request):
    return {
        'search_query': request.GET.get('search', '').strip(),
        'language_filter': request.GET.get('language', '').strip(),
        'is_active_filter': get_choice_param(request.GET, 'is_active', ['all', 'active', 'inactive'], 'all'),
        'config_status_filter': get_choice_param(request.GET, 'config_status', ['all', 'valid', 'needs_review'], 'all'),
        'language_registered_filter': get_choice_param(request.GET, 'language_registered', ['all', 'yes', 'no'], 'all'),
        'used_by_assignments_filter': get_choice_param(request.GET, 'used_by_assignments', ['all', 'yes', 'no'], 'all'),
        'timeout_min': get_int_param(request.GET, 'timeout_min', minimum=0),
        'timeout_max': get_int_param(request.GET, 'timeout_max', minimum=0),
        'memory_min': get_int_param(request.GET, 'memory_min', minimum=0),
        'memory_max': get_int_param(request.GET, 'memory_max', minimum=0),
        'cpu_min': _get_float_param(request.GET, 'cpu_min', minimum=0),
        'cpu_max': _get_float_param(request.GET, 'cpu_max', minimum=0),
    }


def _sandbox_base_queryset():
    return SandboxConfigs.objects.all().order_by('language')


def _sandbox_config_ok_query():
    return (
        Q(docker_image__isnull=False) &
        ~Q(docker_image='') &
        Q(timeout_seconds__gt=0) &
        Q(memory_limit_mb__gt=0) &
        Q(cpu_limit__gt=0)
    )


def _apply_sandbox_filters(sandboxes, filters):
    registered_language_names = ProgrammingLanguages.objects.values_list('name', flat=True)
    assignment_language_names = _assignment_language_names()
    config_ok_query = _sandbox_config_ok_query()

    if filters['language_filter']:
        sandboxes = sandboxes.filter(language=filters['language_filter'])

    if filters['is_active_filter'] == 'active':
        sandboxes = sandboxes.filter(is_active=True)
    elif filters['is_active_filter'] == 'inactive':
        sandboxes = sandboxes.filter(is_active=False)

    if filters['search_query']:
        sandboxes = sandboxes.filter(
            Q(language__icontains=filters['search_query']) |
            Q(docker_image__icontains=filters['search_query'])
        )

    if filters['language_registered_filter'] == 'yes':
        sandboxes = sandboxes.filter(language__in=registered_language_names)
    elif filters['language_registered_filter'] == 'no':
        sandboxes = sandboxes.exclude(language__in=registered_language_names)

    if filters['used_by_assignments_filter'] == 'yes':
        sandboxes = sandboxes.filter(language__in=assignment_language_names)
    elif filters['used_by_assignments_filter'] == 'no':
        sandboxes = sandboxes.exclude(language__in=assignment_language_names)

    if filters['config_status_filter'] == 'valid':
        sandboxes = sandboxes.filter(config_ok_query, language__in=registered_language_names)
    elif filters['config_status_filter'] == 'needs_review':
        sandboxes = sandboxes.exclude(config_ok_query, language__in=registered_language_names)

    if filters['timeout_min'] is not None:
        sandboxes = sandboxes.filter(timeout_seconds__gte=filters['timeout_min'])
    if filters['timeout_max'] is not None:
        sandboxes = sandboxes.filter(timeout_seconds__lte=filters['timeout_max'])
    if filters['memory_min'] is not None:
        sandboxes = sandboxes.filter(memory_limit_mb__gte=filters['memory_min'])
    if filters['memory_max'] is not None:
        sandboxes = sandboxes.filter(memory_limit_mb__lte=filters['memory_max'])
    if filters['cpu_min'] is not None:
        sandboxes = sandboxes.filter(cpu_limit__gte=filters['cpu_min'])
    if filters['cpu_max'] is not None:
        sandboxes = sandboxes.filter(cpu_limit__lte=filters['cpu_max'])

    return sandboxes


def _sandbox_filter_badge_value_labels(filters):
    labels = {
        'is_active': {'all': 'Tất cả', 'active': 'Active', 'inactive': 'Inactive'},
        'config_status': {'all': 'Tất cả', 'valid': 'Hợp lệ', 'needs_review': 'Cần kiểm tra'},
        'language_registered': {'all': 'Tất cả', 'yes': 'Đã khai báo', 'no': 'Chưa khai báo'},
        'used_by_assignments': {'all': 'Tất cả', 'yes': 'Có bài dùng', 'no': 'Chưa bài nào dùng'},
    }
    if filters.get('language_filter'):
        language = ProgrammingLanguages.objects.filter(name=filters['language_filter']).first()
        labels['language'] = {
            filters['language_filter']: language.display_name if language else filters['language_filter'],
        }
    return labels


def _sandbox_language_options():
    registered = {
        language.name: language.display_name or language.name
        for language in ProgrammingLanguages.objects.order_by('display_name', 'name')
    }
    sandbox_names = SandboxConfigs.objects.values_list('language', flat=True).distinct().order_by('language')
    for language_name in sandbox_names:
        registered.setdefault(language_name, language_name)
    return sorted(registered.items(), key=lambda item: item[1].lower())


CRITICAL_SETTING_PREFIXES = ('exam.', 'sandbox.', 'uploads.')


def _setting_category(key):
    return key.split('.', 1)[0] if '.' in key else 'general'


def _setting_value_type(value):
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, int) and not isinstance(value, bool):
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, str):
        return 'str'
    return 'json'


def _setting_schema_type(schema):
    expected_type = schema.get('type')
    if expected_type is bool:
        return 'bool'
    if expected_type is int:
        return 'int'
    if expected_type is float:
        return 'float'
    if expected_type is str:
        return 'str'
    return 'json'


def _setting_is_critical(key):
    return key.startswith(CRITICAL_SETTING_PREFIXES)


def _setting_filter_values(request):
    return {
        'search_query': request.GET.get('search', '').strip(),
        'category_filter': request.GET.get('category', '').strip(),
        'type_filter': get_choice_param(request.GET, 'type', ['all', 'bool', 'int', 'float', 'str', 'json'], 'all'),
        'critical_filter': get_choice_param(request.GET, 'critical', ['all', 'yes', 'no'], 'all'),
        'missing_filter': get_choice_param(request.GET, 'missing', ['all', 'yes', 'no'], 'all'),
        'updated_by_filter': get_int_param(request.GET, 'updated_by', minimum=1),
        'updated_from': get_date_param(request.GET, 'updated_from'),
        'updated_to': get_date_param(request.GET, 'updated_to'),
    }


def _setting_updater_options():
    updater_ids = SystemSettings.objects.exclude(
        updated_by__isnull=True
    ).values_list('updated_by_id', flat=True).distinct()
    return User.objects.filter(pk__in=updater_ids).order_by('first_name', 'username')


def _apply_setting_queryset_filters(settings_qs, filters):
    if filters['search_query']:
        settings_qs = settings_qs.filter(
            Q(setting_key__icontains=filters['search_query']) |
            Q(description__icontains=filters['search_query'])
        )
    if filters['category_filter']:
        settings_qs = settings_qs.filter(setting_key__startswith=f"{filters['category_filter']}.")
    if filters['updated_by_filter']:
        settings_qs = settings_qs.filter(updated_by_id=filters['updated_by_filter'])
    if filters['updated_from']:
        settings_qs = settings_qs.filter(updated_at__date__gte=filters['updated_from'])
    if filters['updated_to']:
        settings_qs = settings_qs.filter(updated_at__date__lte=filters['updated_to'])
    return settings_qs


def _apply_setting_object_filters(settings_list, filters):
    filtered = []
    for setting in settings_list:
        setting.value_type = _setting_value_type(setting.setting_value)
        setting.is_critical = _setting_is_critical(setting.setting_key)
        if filters['type_filter'] != 'all' and setting.value_type != filters['type_filter']:
            continue
        if filters['critical_filter'] == 'yes' and not setting.is_critical:
            continue
        if filters['critical_filter'] == 'no' and setting.is_critical:
            continue
        filtered.append(setting)
    if filters['missing_filter'] == 'yes':
        return []
    return filtered


def _setting_warning_items(filters, existing_all_keys):
    if filters['missing_filter'] == 'no':
        return []

    warnings = []
    for key, schema in SYSTEM_SETTING_SCHEMAS.items():
        if key in existing_all_keys:
            continue
        category = _setting_category(key)
        value_type = _setting_schema_type(schema)
        is_critical = _setting_is_critical(key)

        if filters['search_query'] and filters['search_query'].lower() not in key.lower() and filters['search_query'].lower() not in (schema.get('description', '') or '').lower():
            continue
        if filters['category_filter'] and category != filters['category_filter']:
            continue
        if filters['type_filter'] != 'all' and value_type != filters['type_filter']:
            continue
        if filters['critical_filter'] == 'yes' and not is_critical:
            continue
        if filters['critical_filter'] == 'no' and is_critical:
            continue
        if filters['updated_by_filter'] or filters['updated_from'] or filters['updated_to']:
            continue

        warnings.append({
            'key': key,
            'message': 'Chưa tạo setting, hệ thống đang dùng giá trị mặc định trong code.',
            'description': schema.get('description', ''),
            'value_type': value_type,
            'is_critical': is_critical,
        })
    return warnings


def _setting_filter_badge_value_labels(filters):
    labels = {
        'type': {
            'all': 'Tất cả',
            'bool': 'Boolean',
            'int': 'Integer',
            'float': 'Float',
            'str': 'String',
            'json': 'JSON',
        },
        'critical': {'all': 'Tất cả', 'yes': 'Quan trọng', 'no': 'Thường'},
        'missing': {'all': 'Tất cả', 'yes': 'Chưa tạo', 'no': 'Đã tạo'},
    }
    if filters.get('updated_by_filter'):
        updater = User.objects.filter(pk=filters['updated_by_filter']).first()
        if updater:
            labels['updated_by'] = {str(updater.pk): updater.get_full_name() or updater.username}
    return labels


ACTIVITY_LOG_RESOURCE_TYPES = (
    'accounts',
    'classrooms',
    'subjects',
    'assignments',
    'submissions',
    'system_settings',
    'sandbox_configs',
)


ACTIVITY_ACTION_GROUPS = {
    'login': ('login', 'signin', 'sign_in'),
    'bulk': ('bulk',),
    'approve': ('approve', 'approved'),
    'reject': ('reject', 'rejected'),
    'create': ('create', 'created'),
    'update': ('update', 'edit', 'edited'),
    'delete': ('delete', 'deleted'),
    'export': ('export', 'csv'),
    'sandbox': ('sandbox', 'zombie', 'requeue'),
}


def _activity_log_filter_values(request):
    preset_filter = get_choice_param(request.GET, 'preset', ['all', '24h', '7d', '30d'], 'all')
    return {
        'user_filter': request.GET.get('user', '').strip(),
        'user_id_filter': get_int_param(request.GET, 'user_id', minimum=1),
        'role_filter': get_choice_param(request.GET, 'role', ['all', 'admin', 'teacher', 'student', 'system'], 'all'),
        'action_filter': request.GET.get('action', '').strip(),
        'action_group_filter': get_choice_param(
            request.GET,
            'action_group',
            ['all', *ACTIVITY_ACTION_GROUPS.keys()],
            'all',
        ),
        'resource_type_filter': request.GET.get('resource_type', '').strip(),
        'resource_id_filter': get_int_param(request.GET, 'resource_id', minimum=1),
        'ip_address_filter': request.GET.get('ip_address', '').strip(),
        'date_from': get_date_param(request.GET, 'date_from'),
        'date_to': get_date_param(request.GET, 'date_to'),
        'preset_filter': preset_filter,
    }


def _apply_activity_log_filters(logs, filters):
    if filters['user_filter']:
        logs = logs.filter(
            Q(user__username__icontains=filters['user_filter']) |
            Q(user__first_name__icontains=filters['user_filter']) |
            Q(user__last_name__icontains=filters['user_filter']) |
            Q(user__email__icontains=filters['user_filter'])
        )

    if filters['user_id_filter']:
        logs = logs.filter(user_id=filters['user_id_filter'])

    role_filter = filters['role_filter']
    if role_filter == 'system':
        logs = logs.filter(user__isnull=True)
    elif role_filter == 'admin':
        logs = logs.filter(Q(user__profiles__role='admin') | Q(user__is_staff=True) | Q(user__is_superuser=True))
    elif role_filter in ('teacher', 'student'):
        logs = logs.filter(user__profiles__role=role_filter)

    if filters['action_filter']:
        logs = logs.filter(action__icontains=filters['action_filter'])

    action_group = filters['action_group_filter']
    if action_group != 'all':
        group_q = Q()
        for keyword in ACTIVITY_ACTION_GROUPS[action_group]:
            group_q |= Q(action__icontains=keyword)
        if action_group == 'sandbox':
            group_q |= Q(resource_type='sandbox_configs')
        logs = logs.filter(group_q)

    if filters['resource_type_filter']:
        logs = logs.filter(resource_type=filters['resource_type_filter'])

    if filters['resource_id_filter']:
        logs = logs.filter(resource_id=filters['resource_id_filter'])

    if filters['ip_address_filter']:
        logs = logs.filter(ip_address__icontains=filters['ip_address_filter'])

    if filters['preset_filter'] == '24h':
        logs = logs.filter(created_at__gte=timezone.now() - timedelta(hours=24))
    elif filters['preset_filter'] == '7d':
        logs = logs.filter(created_at__gte=timezone.now() - timedelta(days=7))
    elif filters['preset_filter'] == '30d':
        logs = logs.filter(created_at__gte=timezone.now() - timedelta(days=30))

    if filters['date_from']:
        logs = logs.filter(created_at__date__gte=filters['date_from'])
    if filters['date_to']:
        logs = logs.filter(created_at__date__lte=filters['date_to'])

    return logs.distinct()


def _activity_log_resource_type_options():
    options = set(ACTIVITY_LOG_RESOURCE_TYPES)
    options.update(
        ActivityLogs.objects.exclude(resource_type__isnull=True).exclude(
            resource_type=''
        ).values_list('resource_type', flat=True).distinct()
    )
    return sorted(options)


def _activity_log_user_options():
    logged_user_ids = ActivityLogs.objects.exclude(user__isnull=True).values_list(
        'user_id',
        flat=True,
    ).distinct()
    return User.objects.filter(pk__in=logged_user_ids).order_by('first_name', 'username')[:300]


def _activity_log_preset_links(request):
    return {
        preset: build_query_string(request, remove=('page',), preset=preset)
        for preset in ('24h', '7d', '30d')
    }


def _activity_log_filter_badge_value_labels(filters):
    labels = {
        'role': {'all': 'Tất cả', 'admin': 'Admin', 'teacher': 'Giáo viên', 'student': 'Học sinh', 'system': 'System'},
        'action_group': {
            'all': 'Tất cả',
            'login': 'Login',
            'bulk': 'Bulk',
            'approve': 'Approve',
            'reject': 'Reject',
            'create': 'Create',
            'update': 'Update',
            'delete': 'Delete',
            'export': 'Export',
            'sandbox': 'Sandbox',
        },
        'preset': {'all': 'Tất cả', '24h': '24 giờ', '7d': '7 ngày', '30d': '30 ngày'},
    }
    if filters.get('user_id_filter'):
        user = User.objects.filter(pk=filters['user_id_filter']).first()
        if user:
            labels['user_id'] = {str(user.pk): user.get_full_name() or user.username}
    return labels


def _exam_event_filter_values(request):
    from apps.submissions.models import ExamSessions

    status_choices = [value for value, _ in ExamSessions.STATUS_CHOICES]
    return {
        'search_query': request.GET.get('search', '').strip(),
        'assignment_filter': get_int_param(request.GET, 'assignment_id', minimum=1),
        'classroom_filter': get_int_param(request.GET, 'classroom_id', minimum=1),
        'subject_filter': get_int_param(request.GET, 'subject_id', minimum=1),
        'teacher_filter': get_int_param(request.GET, 'teacher_id', minimum=1),
        'student_filter': get_int_param(request.GET, 'student_id', minimum=1),
        'event_filter': request.GET.get('event_type', '').strip(),
        'status_filter': get_choice_param(request.GET, 'status', status_choices, ''),
        'min_warnings_value': get_int_param(request.GET, 'min_warnings', minimum=0),
        'has_final_submission_filter': get_choice_param(request.GET, 'has_final_submission', ['all', 'yes', 'no'], 'all'),
        'session_duration_filter': get_choice_param(
            request.GET,
            'session_duration',
            ['all', 'over_time', 'running', 'force_submitted'],
            'all',
        ),
        'date_from': get_date_param(request.GET, 'date_from'),
        'date_to': get_date_param(request.GET, 'date_to'),
    }


def _exam_events_base_queryset():
    from apps.submissions.models import ExamEvents

    return ExamEvents.objects.select_related(
        'session',
        'session__student',
        'session__assignment',
        'session__assignment__classroom',
        'session__assignment__classroom_subject',
        'session__assignment__classroom_subject__subject',
    ).order_by('-created_at')


def _exam_sessions_base_queryset():
    from apps.submissions.models import ExamSessions

    return ExamSessions.objects.select_related(
        'student',
        'assignment',
        'assignment__classroom',
        'assignment__classroom_subject',
        'assignment__classroom_subject__subject',
    ).order_by('-violation_count', '-updated_at')


def _exam_session_filter_q(filters, prefix=''):
    from apps.submissions.models import ExamSessions

    now = timezone.now()
    q = Q()
    if filters['search_query']:
        q &= (
            Q(**{f'{prefix}student__username__icontains': filters['search_query']}) |
            Q(**{f'{prefix}student__first_name__icontains': filters['search_query']}) |
            Q(**{f'{prefix}student__last_name__icontains': filters['search_query']}) |
            Q(**{f'{prefix}assignment__title__icontains': filters['search_query']}) |
            Q(**{f'{prefix}assignment__classroom__name__icontains': filters['search_query']})
        )
    if filters['assignment_filter']:
        q &= Q(**{f'{prefix}assignment_id': filters['assignment_filter']})
    if filters['classroom_filter']:
        q &= Q(**{f'{prefix}assignment__classroom_id': filters['classroom_filter']})
    if filters['subject_filter']:
        q &= Q(**{f'{prefix}assignment__classroom_subject__subject_id': filters['subject_filter']})
    if filters['teacher_filter']:
        q &= (
            Q(**{f'{prefix}assignment__created_by_id': filters['teacher_filter']}) |
            Q(**{f'{prefix}assignment__classroom__teacher_id': filters['teacher_filter']})
        )
    if filters['student_filter']:
        q &= Q(**{f'{prefix}student_id': filters['student_filter']})
    if filters['status_filter']:
        q &= Q(**{f'{prefix}status': filters['status_filter']})
    if filters['min_warnings_value'] is not None:
        q &= Q(**{f'{prefix}violation_count__gte': filters['min_warnings_value']})
    if filters['has_final_submission_filter'] == 'yes':
        q &= Q(**{f'{prefix}final_submission__isnull': False})
    elif filters['has_final_submission_filter'] == 'no':
        q &= Q(**{f'{prefix}final_submission__isnull': True})
    if filters['session_duration_filter'] == 'over_time':
        q &= Q(**{f'{prefix}status': ExamSessions.STATUS_RUNNING}) & Q(**{f'{prefix}ends_at__lt': now})
    elif filters['session_duration_filter'] == 'running':
        q &= Q(**{f'{prefix}status': ExamSessions.STATUS_RUNNING}) & (
            Q(**{f'{prefix}ends_at__isnull': True}) | Q(**{f'{prefix}ends_at__gte': now})
        )
    elif filters['session_duration_filter'] == 'force_submitted':
        q &= Q(**{f'{prefix}status__in': [ExamSessions.STATUS_AUTO_SUBMITTED, ExamSessions.STATUS_EXPIRED]})
    return q


def _apply_exam_event_filters(events, filters):
    session_q = _exam_session_filter_q(filters, prefix='session__')
    if session_q:
        events = events.filter(session_q)
    if filters['event_filter']:
        events = events.filter(event_type=filters['event_filter'])
    if filters['date_from']:
        events = events.filter(created_at__date__gte=filters['date_from'])
    if filters['date_to']:
        events = events.filter(created_at__date__lte=filters['date_to'])
    return events.distinct()


def _apply_exam_session_filters(sessions, filters):
    session_q = _exam_session_filter_q(filters)
    if session_q:
        sessions = sessions.filter(session_q)
    if filters['event_filter']:
        sessions = sessions.filter(events__event_type=filters['event_filter'])
    if filters['date_from']:
        sessions = sessions.filter(updated_at__date__gte=filters['date_from'])
    if filters['date_to']:
        sessions = sessions.filter(updated_at__date__lte=filters['date_to'])
    return sessions.distinct()


def _exam_event_filter_badge_value_labels(filters):
    from apps.assignments.models import Assignments
    from apps.submissions.models import ExamSessions

    labels = {
        'status': dict(ExamSessions.STATUS_CHOICES),
        'has_final_submission': {'all': 'Tất cả', 'yes': 'Đã nộp', 'no': 'Chưa nộp'},
        'session_duration': {
            'all': 'Tất cả',
            'over_time': 'Quá thời gian',
            'running': 'Còn đang làm',
            'force_submitted': 'Force submit',
        },
    }
    if filters.get('assignment_filter'):
        assignment = Assignments.objects.filter(pk=filters['assignment_filter']).first()
        if assignment:
            labels['assignment_id'] = {str(assignment.pk): assignment.title}
    if filters.get('classroom_filter'):
        classroom = Classrooms.objects.filter(pk=filters['classroom_filter']).first()
        if classroom:
            labels['classroom_id'] = {str(classroom.pk): classroom.name}
    if filters.get('subject_filter'):
        subject = Subjects.objects.filter(pk=filters['subject_filter']).first()
        if subject:
            labels['subject_id'] = {str(subject.pk): f'{subject.code} - {subject.name}'}
    if filters.get('teacher_filter'):
        teacher = User.objects.filter(pk=filters['teacher_filter']).first()
        if teacher:
            labels['teacher_id'] = {str(teacher.pk): teacher.get_full_name() or teacher.username}
    if filters.get('student_filter'):
        student = User.objects.filter(pk=filters['student_filter']).first()
        if student:
            labels['student_id'] = {str(student.pk): student.get_full_name() or student.username}
    return labels


def _exam_assignment_options():
    from apps.assignments.models import Assignments

    return Assignments.objects.filter(is_exam=True).select_related(
        'classroom',
        'classroom_subject',
        'classroom_subject__subject',
    ).order_by('-created_at')[:300]


def _sandbox_monitor_filter_values(request):
    return {
        'submission_status_filter': get_choice_param(
            request.GET,
            'submission_status',
            ['all', 'pending', 'running', 'error', 'finished'],
            'all',
        ),
        'language_filter': request.GET.get('language', '').strip(),
        'assignment_filter': get_int_param(request.GET, 'assignment_id', minimum=1),
        'classroom_filter': get_int_param(request.GET, 'classroom_id', minimum=1),
        'subject_filter': get_int_param(request.GET, 'subject_id', minimum=1),
        'age_min_minutes': get_int_param(request.GET, 'age_min_minutes', minimum=0),
        'student_filter': get_int_param(request.GET, 'student_id', minimum=1),
    }


def _sandbox_monitor_base_queryset():
    from apps.submissions.models import Submissions

    return Submissions.objects.select_related(
        'student',
        'assignment',
        'assignment__classroom',
        'assignment__classroom_subject',
        'assignment__classroom_subject__subject',
    ).order_by('submitted_at')


def _apply_sandbox_monitor_filters(submissions, filters):
    if filters['submission_status_filter'] != 'all':
        submissions = submissions.filter(status=filters['submission_status_filter'])
    if filters['language_filter']:
        submissions = submissions.filter(language=filters['language_filter'])
    if filters['assignment_filter']:
        submissions = submissions.filter(assignment_id=filters['assignment_filter'])
    if filters['classroom_filter']:
        submissions = submissions.filter(assignment__classroom_id=filters['classroom_filter'])
    if filters['subject_filter']:
        submissions = submissions.filter(assignment__classroom_subject__subject_id=filters['subject_filter'])
    if filters['student_filter']:
        submissions = submissions.filter(student_id=filters['student_filter'])
    if filters['age_min_minutes'] is not None:
        submissions = submissions.filter(submitted_at__lt=timezone.now() - timedelta(minutes=filters['age_min_minutes']))
    return submissions.distinct()


def _sandbox_monitor_assignment_options():
    from apps.assignments.models import Assignments

    return Assignments.objects.select_related(
        'classroom',
        'classroom_subject',
        'classroom_subject__subject',
    ).order_by('-created_at')[:300]


def _sandbox_monitor_language_options():
    from apps.submissions.models import Submissions

    return Submissions.objects.exclude(language__isnull=True).exclude(
        language=''
    ).values_list('language', flat=True).distinct().order_by('language')


def _sandbox_monitor_filter_badge_value_labels(filters):
    from apps.assignments.models import Assignments

    labels = {
        'submission_status': {
            'all': 'Tất cả',
            'pending': 'Pending',
            'running': 'Running',
            'error': 'Error',
            'finished': 'Finished',
        },
    }
    if filters.get('assignment_filter'):
        assignment = Assignments.objects.filter(pk=filters['assignment_filter']).first()
        if assignment:
            labels['assignment_id'] = {str(assignment.pk): assignment.title}
    if filters.get('classroom_filter'):
        classroom = Classrooms.objects.filter(pk=filters['classroom_filter']).first()
        if classroom:
            labels['classroom_id'] = {str(classroom.pk): classroom.name}
    if filters.get('subject_filter'):
        subject = Subjects.objects.filter(pk=filters['subject_filter']).first()
        if subject:
            labels['subject_id'] = {str(subject.pk): f'{subject.code} - {subject.name}'}
    if filters.get('student_filter'):
        student = User.objects.filter(pk=filters['student_filter']).first()
        if student:
            labels['student_id'] = {str(student.pk): student.get_full_name() or student.username}
    return labels


def _sandbox_monitor_redirect(request):
    query_string = request.POST.get('query_string', '').strip()
    url = reverse('administation:sandbox_monitor')
    if query_string:
        return redirect(f'{url}?{query_string}')
    return redirect(url)


def _server_metrics_filter_values(request):
    return {
        'range_filter': get_choice_param(request.GET, 'range', ['1h', '6h', '24h', '7d'], '24h'),
        'cpu_min': _get_float_param(request.GET, 'cpu_min', minimum=0, maximum=100),
        'memory_min': _get_float_param(request.GET, 'memory_min', minimum=0, maximum=100),
        'queue_min': get_int_param(request.GET, 'queue_min', minimum=0),
    }


def _server_metrics_range_start(range_filter):
    hours = {'1h': 1, '6h': 6, '24h': 24}
    if range_filter == '7d':
        return timezone.now() - timedelta(days=7)
    return timezone.now() - timedelta(hours=hours.get(range_filter, 24))


def _apply_server_metrics_filters(metrics, filters):
    metrics = metrics.filter(recorded_at__gte=_server_metrics_range_start(filters['range_filter']))
    if filters['cpu_min'] is not None:
        metrics = metrics.filter(cpu_usage__gte=filters['cpu_min'])
    if filters['memory_min'] is not None:
        metrics = metrics.filter(memory_usage__gte=filters['memory_min'])
    if filters['queue_min'] is not None:
        metrics = metrics.filter(queue_length__gte=filters['queue_min'])
    return metrics


def _server_metrics_filter_badge_value_labels(filters):
    return {
        'range': {'1h': '1 giờ', '6h': '6 giờ', '24h': '24 giờ', '7d': '7 ngày'},
    }


def _analytics_filter_values(request):
    default_from = (timezone.localdate() - timedelta(days=30))
    default_to = timezone.localdate()
    return {
        'date_from': get_date_param(request.GET, 'date_from', default_from),
        'date_to': get_date_param(request.GET, 'date_to', default_to),
        'classroom_filter': get_int_param(request.GET, 'classroom_id', minimum=1),
        'subject_filter': get_int_param(request.GET, 'subject_id', minimum=1),
        'teacher_filter': get_int_param(request.GET, 'teacher_id', minimum=1),
        'language_filter': request.GET.get('language', '').strip(),
    }


def _analytics_submission_queryset(filters):
    from apps.submissions.models import Submissions

    submissions = Submissions.objects.select_related(
        'assignment',
        'assignment__classroom',
        'assignment__classroom_subject',
        'assignment__classroom_subject__subject',
        'student',
    )
    if filters['date_from']:
        submissions = submissions.filter(submitted_at__date__gte=filters['date_from'])
    if filters['date_to']:
        submissions = submissions.filter(submitted_at__date__lte=filters['date_to'])
    if filters['classroom_filter']:
        submissions = submissions.filter(assignment__classroom_id=filters['classroom_filter'])
    if filters['subject_filter']:
        submissions = submissions.filter(assignment__classroom_subject__subject_id=filters['subject_filter'])
    if filters['teacher_filter']:
        submissions = submissions.filter(
            Q(assignment__created_by_id=filters['teacher_filter']) |
            Q(assignment__classroom__teacher_id=filters['teacher_filter'])
        )
    if filters['language_filter']:
        submissions = submissions.filter(language=filters['language_filter'])
    return submissions


def _analytics_filter_badge_value_labels(filters):
    labels = {}
    if filters.get('classroom_filter'):
        classroom = Classrooms.objects.filter(pk=filters['classroom_filter']).first()
        if classroom:
            labels['classroom_id'] = {str(classroom.pk): classroom.name}
    if filters.get('subject_filter'):
        subject = Subjects.objects.filter(pk=filters['subject_filter']).first()
        if subject:
            labels['subject_id'] = {str(subject.pk): f'{subject.code} - {subject.name}'}
    if filters.get('teacher_filter'):
        teacher = User.objects.filter(pk=filters['teacher_filter']).first()
        if teacher:
            labels['teacher_id'] = {str(teacher.pk): teacher.get_full_name() or teacher.username}
    return labels


def _analytics_language_options():
    from apps.submissions.models import Submissions

    return Submissions.objects.exclude(language__isnull=True).exclude(
        language=''
    ).values_list('language', flat=True).distinct().order_by('language')


def _render_user_management_page(
    request,
    forced_role=None,
    current_page='user_management',
    page_title='Quản lý người dùng',
    page_description='Quản lý tài khoản học sinh, giáo viên và admin.',
    empty_icon='group',
    empty_title='Không tìm thấy người dùng',
    empty_description='Chưa có người dùng nào.',
    show_teacher_approvals=False,
    approval_status_source='approval_status',
):
    _warn_invalid_int_filters(request, [
        ('classroom_id', 'Lớp học', 1),
        ('subject_id', 'Môn học', 1),
        ('approval_reviewed_by', 'Người duyệt đơn giáo viên', 1),
    ])
    filters = _user_filter_values(request, forced_role=forced_role)
    role_filter = filters['role_filter']
    search_query = filters['search_query']
    status_filter = filters['status_filter']

    users = _apply_user_filters(_user_management_queryset(), filters)

    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    clear_url_name = {
        'teacher': 'administation:teacher_management',
        'student': 'administation:student_management',
    }.get(forced_role, 'administation:user_management')

    csv_scope = {
        'student': ('Xuất học sinh theo lọc hiện tại', 'Xuất toàn bộ học sinh'),
        'teacher': ('Xuất giáo viên theo lọc hiện tại', 'Xuất toàn bộ giáo viên'),
        'admin': ('Xuất admin theo lọc hiện tại', 'Xuất toàn bộ admin'),
        'staff': ('Xuất staff theo lọc hiện tại', 'Xuất toàn bộ staff'),
        'superuser': ('Xuất superuser theo lọc hiện tại', 'Xuất toàn bộ superuser'),
    }.get(role_filter, ('Xuất người dùng theo lọc hiện tại', 'Xuất toàn bộ người dùng'))
    if status_filter == 'inactive':
        csv_scope = ('Xuất tài khoản bị khóa theo lọc hiện tại', 'Xuất toàn bộ tài khoản bị khóa')

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'users': page_obj,
        'page_obj': page_obj,
        'role_filter': role_filter,
        'forced_role': forced_role,
        'search_query': search_query,
        'status_filter': status_filter,
        'profile_status_filter': filters['profile_status_filter'],
        'classroom_filter': filters['classroom_filter'],
        'subject_filter': filters['subject_filter'],
        'has_teaching_classes_filter': filters['has_teaching_classes_filter'],
        'has_joined_class_filter': filters['has_joined_class_filter'],
        'last_login_filter': filters['last_login_filter'],
        'date_joined_from': filters['date_joined_from'].isoformat() if filters['date_joined_from'] else '',
        'date_joined_to': filters['date_joined_to'].isoformat() if filters['date_joined_to'] else '',
        'has_submissions_filter': filters['has_submissions_filter'],
        'submission_status_filter': filters['submission_status_filter'],
        'current_page': current_page,
        'page_title': page_title,
        'page_description': page_description,
        'csv_primary_filtered_label': csv_scope[0],
        'csv_primary_all_label': csv_scope[1],
        'empty_icon': empty_icon,
        'empty_title': empty_title,
        'empty_description': empty_description,
        'clear_url_name': clear_url_name,
        'return_to': current_page,
        'show_teacher_approvals': show_teacher_approvals,
        'pending_count': TeacherRegistrations.objects.filter(status='pending').count(),
        'approval_hidden_fields': _hidden_fields_from_query(
            request,
            {
                'search',
                'role',
                'status',
                'profile_status',
                'classroom_id',
                'subject_id',
                'has_teaching_classes',
                'has_joined_class',
                'last_login',
                'date_joined_from',
                'date_joined_to',
                'has_submissions',
                'submission_status',
                'page',
            },
        ) if show_teacher_approvals else [],
    }
    teacher_registration_labels = {}
    if show_teacher_approvals:
        teacher_registration_labels = _teacher_registration_badge_value_labels(
            _teacher_registration_filter_values(request, approval_status_source)
        )
    context.update(admin_filter_context(
        request,
        clear_url_name,
        labels={
            'search': 'Từ khóa',
            'role': 'Vai trò',
            'status': 'Trạng thái',
            'profile_status': 'Profile',
            'classroom_id': 'Lớp',
            'subject_id': 'Môn',
            'has_teaching_classes': 'Lớp đang dạy',
            'has_joined_class': 'Lớp đang học',
            'last_login': 'Đăng nhập',
            'date_joined_from': 'Tham gia từ',
            'date_joined_to': 'Tham gia đến',
            'has_submissions': 'Bài nộp',
            'submission_status': 'Trạng thái bài nộp',
            'approval_status': 'Trạng thái đơn GV',
            'approval_search': 'Từ khóa đơn GV',
            'approval_institution': 'Tổ chức',
            'approval_created_from': 'Đơn từ ngày',
            'approval_created_to': 'Đơn đến ngày',
            'approval_reviewed_by': 'Người duyệt',
        },
        value_labels={
            **_user_filter_badge_value_labels(filters),
            'approval_status': {'all': 'Tất cả', 'pending': 'Chờ duyệt', 'approved': 'Đã duyệt', 'rejected': 'Từ chối'},
            **teacher_registration_labels,
        },
        defaults={
            'role': forced_role or 'all',
            'status': 'all',
            'profile_status': 'all',
            'has_teaching_classes': 'all',
            'has_joined_class': 'all',
            'last_login': 'all',
            'has_submissions': 'all',
            'approval_status': 'pending',
        },
    ))
    if show_teacher_approvals:
        context.update(_teacher_registration_context(request, approval_status_source))
    if forced_role:
        context['csv_query_string'] = build_query_string(
            request,
            remove=('page', 'type'),
            role=forced_role,
        )
    context['csv_has_active_filters'] = (
        bool(context.get('has_active_filters'))
        or bool(forced_role)
        or role_filter != 'all'
        or status_filter != 'all'
    )
    context['csv_items'] = [
        _csv_dropdown_item(
            'administation:user_export',
            context['csv_primary_filtered_label'] if context['csv_has_active_filters'] else context['csv_primary_all_label'],
            'filter_alt',
        ),
        _csv_dropdown_item(
            'administation:user_export',
            'Danh bạ theo lọc hiện tại' if context['csv_has_active_filters'] else 'Danh bạ người dùng',
            'contacts',
            'contacts',
        ),
        _csv_dropdown_item(
            'administation:user_export',
            'Audit tài khoản theo lọc hiện tại' if context['csv_has_active_filters'] else 'Audit tài khoản',
            'manage_search',
            'audit',
        ),
    ]
    return render(request, 'administration/user_management.html', context)


@admin_required
@require_POST
def user_bulk_action_view(request):
    action = request.POST.get('action')
    user_ids = _selected_int_ids_from_post(request, 'user_ids', 'user ID')

    if not user_ids:
        messages.error(request, 'Chưa chọn người dùng nào.')
        return _admin_user_return_redirect(request)

    users = User.objects.filter(id__in=user_ids)
    target_ids = list(users.values_list('pk', flat=True))
    if action in ('deactivate', 'delete'):
        if users.filter(pk=request.user.pk).exists():
            messages.error(request, 'Không thể vô hiệu hóa tài khoản đang đăng nhập.')
            return _admin_user_return_redirect(request)
        selected_active_superusers = users.filter(is_superuser=True, is_active=True).count()
        active_superusers = User.objects.filter(is_superuser=True, is_active=True).count()
        if selected_active_superusers and active_superusers - selected_active_superusers <= 0:
            messages.error(request, 'Không thể vô hiệu hóa superuser cuối cùng.')
            return _admin_user_return_redirect(request)

    if action == 'activate':
        updated = users.update(is_active=True)
        Profiles.objects.filter(id__in=target_ids).update(status='approved', updated_at=timezone.now())
        _log_admin_action(
            request.user,
            'ADMIN_BULK_USER_ACTIVATE',
            'accounts',
            metadata={'target_user_ids': target_ids, 'count': updated},
            request=request,
        )
        messages.success(request, f'Đã kích hoạt {updated} tài khoản.')
    elif action == 'deactivate':
        updated = users.update(is_active=False)
        Profiles.objects.filter(id__in=target_ids).update(status='inactive', updated_at=timezone.now())
        _log_admin_action(
            request.user,
            'ADMIN_BULK_USER_DEACTIVATE',
            'accounts',
            metadata={'target_user_ids': target_ids, 'count': updated},
            request=request,
        )
        messages.success(request, f'Đã vô hiệu hóa {updated} tài khoản.')
    elif action == 'delete':
        # Soft delete or hard? For now, deactivate
        updated = users.update(is_active=False)
        Profiles.objects.filter(id__in=target_ids).update(status='inactive', updated_at=timezone.now())
        _log_admin_action(
            request.user,
            'ADMIN_BULK_USER_SOFT_DELETE',
            'accounts',
            metadata={'target_user_ids': target_ids, 'count': updated},
            request=request,
        )
        messages.success(request, f'Đã xóa (vô hiệu hóa) {updated} tài khoản.')
    else:
        messages.error(request, 'Hành động không hợp lệ.')

    return _admin_user_return_redirect(request)


@admin_required
def subject_management_view(request):
    _warn_invalid_int_filters(request, [
        ('classroom_id', 'Lớp học', 1),
        ('teacher_id', 'Giáo viên', 1),
        ('semester_id', 'Kỳ học', 1),
        ('language_id', 'Ngôn ngữ', 1),
    ])
    filters = _subject_filter_values(request)
    subjects = _apply_subject_filters(_subject_base_queryset(), filters)

    paginator = Paginator(subjects, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'subjects': page_obj,
        'page_obj': page_obj,
        'search_query': filters['search_query'],
        'classroom_filter': filters['classroom_filter'],
        'teacher_filter': filters['teacher_filter'],
        'semester_filter': filters['semester_filter'],
        'language_filter': filters['language_filter'],
        'status_filter': filters['status_filter'],
        'is_active_filter': filters['is_active_filter'],
        'has_assignments_filter': filters['has_assignments_filter'],
        'has_exams_filter': filters['has_exams_filter'],
        'sandbox_status_filter': filters['sandbox_status_filter'],
        'created_from': filters['created_from'].isoformat() if filters['created_from'] else '',
        'created_to': filters['created_to'].isoformat() if filters['created_to'] else '',
        'subject_status_links': _subject_status_links(request),
        'pending_count': Subjects.objects.filter(status='pending').count(),
        'approved_count': Subjects.objects.filter(status='approved').count(),
        'rejected_count': Subjects.objects.filter(status='rejected').count(),
        'current_page': 'subject_management',
    }
    context.update(admin_filter_context(
        request,
        'administation:subject_approvals',
        labels={
            'search': 'Từ khóa',
            'classroom_id': 'Lớp',
            'teacher_id': 'Giáo viên',
            'semester_id': 'Kỳ học',
            'language_id': 'Ngôn ngữ',
            'status': 'Trạng thái',
            'is_active': 'Hiển thị',
            'has_assignments': 'Bài tập',
            'has_exams': 'Bài thi',
            'sandbox_status': 'Sandbox',
            'created_from': 'Tạo từ',
            'created_to': 'Tạo đến',
        },
        value_labels=_subject_filter_badge_value_labels(filters),
        defaults={
            'status': 'all',
            'is_active': 'all',
            'has_assignments': 'all',
            'has_exams': 'all',
            'sandbox_status': 'all',
        },
    ))
    context['csv_items'] = [
        _csv_dropdown_item(
            'administation:subject_export',
            'Xuất môn học theo lọc hiện tại' if context['has_active_filters'] else 'Xuất toàn bộ môn học',
            'filter_alt',
        ),
        _csv_dropdown_item(
            'administation:subject_export',
            'Xuất gán lớp/môn/kỳ theo lọc hiện tại' if context['has_active_filters'] else 'Xuất gán lớp/môn/kỳ',
            'hub',
            'classrooms',
        ),
    ]
    return render(request, 'administration/subject_management.html', context)


@admin_required
@require_POST
def approve_teacher_view(request, pk):
    registration = get_object_or_404(
        TeacherRegistrations.objects.select_related('user'), pk=pk, status='pending'
    )
    registration.status = 'approved'
    registration.reviewed_by = request.user
    registration.reviewed_at = timezone.now()
    registration.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    profile = get_object_or_404(Profiles, id=registration.user)
    profile.role = 'teacher'
    profile.status = 'approved'
    profile.save(update_fields=['role', 'status', 'updated_at'])

    notify_user(
        registration.user,
        title='Đơn đăng ký giáo viên đã được duyệt',
        message='Tài khoản của bạn đã được cấp quyền giáo viên.',
        link='/accounts/profile/',
        notification_type='teacher_registration_approved',
        actor=request.user,
        metadata={'registration_id': registration.pk},
    )
    messages.success(request, f'Đã phê duyệt {registration.user.get_full_name() or registration.user.username} làm giáo viên.')
    return _admin_user_return_redirect(request)


@admin_required
@require_POST
def reject_teacher_view(request, pk):
    registration = get_object_or_404(
        TeacherRegistrations.objects.select_related('user'), pk=pk, status='pending'
    )
    registration.status = 'rejected'
    registration.reviewed_by = request.user
    registration.reviewed_at = timezone.now()
    registration.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    Profiles.objects.filter(id=registration.user).update(status='rejected', updated_at=timezone.now())

    notify_user(
        registration.user,
        title='Đơn đăng ký giáo viên bị từ chối',
        message='Admin đã từ chối đơn đăng ký giáo viên của bạn.',
        link='/accounts/profile/',
        notification_type='teacher_registration_rejected',
        actor=request.user,
        metadata={'registration_id': registration.pk},
    )
    messages.success(request, f'Đã từ chối đơn đăng ký của {registration.user.get_full_name() or registration.user.username}.')
    return _admin_user_return_redirect(request)


@admin_required
@require_POST
def approve_subject_view(request, pk):
    subject = get_object_or_404(
        Subjects.objects.select_related('created_by'), pk=pk, status='pending'
    )
    subject.status = SubjectApprovalStatus.APPROVED
    subject.approved_by = request.user
    subject.reviewed_at = timezone.now()
    subject.is_active = True
    subject.save(update_fields=['status', 'approved_by', 'reviewed_at', 'is_active'])
    _notify_subject_review(subject, request.user, approved=True)
    messages.success(request, f'Đã duyệt môn học "{subject.name}".')
    return redirect('administation:subject_approvals')


@admin_required
@require_POST
def reject_subject_view(request, pk):
    subject = get_object_or_404(
        Subjects.objects.select_related('created_by'), pk=pk, status='pending'
    )
    subject.status = SubjectApprovalStatus.REJECTED
    subject.approved_by = request.user
    subject.reviewed_at = timezone.now()
    subject.is_active = False
    subject.save(update_fields=['status', 'approved_by', 'reviewed_at', 'is_active'])
    _notify_subject_review(subject, request.user, approved=False)
    messages.success(request, f'Đã từ chối môn học "{subject.name}".')
    return redirect('administation:subject_approvals')


@admin_required
def language_list_view(request):
    filters = _language_filter_values(request)
    languages = _apply_language_filters(_language_base_queryset(), filters)
    sandbox_languages = set(SandboxConfigs.objects.filter(is_active=True).values_list('language', flat=True))
    assignment_usage_counts = _assignment_language_usage_counts()
    languages = list(languages)
    for language in languages:
        language.has_active_sandbox = language.name in sandbox_languages
        language.assignment_usage_count = assignment_usage_counts.get(language.name, 0)

    missing_sandbox_count = sum(1 for language in languages if language.is_active and not language.has_active_sandbox)
    extension_options = ProgrammingLanguages.objects.exclude(
        file_extension__isnull=True
    ).exclude(
        file_extension=''
    ).values_list('file_extension', flat=True).distinct().order_by('file_extension')

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'languages': languages,
        'missing_sandbox_count': missing_sandbox_count,
        'search_query': filters['search_query'],
        'is_active_filter': filters['is_active_filter'],
        'has_sandbox_filter': filters['has_sandbox_filter'],
        'used_by_subject_filter': filters['used_by_subject_filter'],
        'used_by_assignment_filter': filters['used_by_assignment_filter'],
        'extension_filter': filters['extension_filter'],
        'sort_filter': filters['sort_filter'],
        'extension_options': extension_options,
        'current_page': 'languages',
        'filter_result_label': f'Đang hiển thị {len(languages)} ngôn ngữ',
    }
    context.update(admin_filter_context(
        request,
        'administation:languages',
        labels={
            'search': 'Từ khóa',
            'is_active': 'Trạng thái',
            'has_sandbox': 'Sandbox',
            'used_by_subject': 'Môn học',
            'used_by_assignment': 'Bài tập/bài thi',
            'extension': 'Extension',
            'sort': 'Sắp xếp',
        },
        value_labels=_language_filter_badge_value_labels(filters),
        defaults={
            'is_active': 'all',
            'has_sandbox': 'all',
            'used_by_subject': 'all',
            'used_by_assignment': 'all',
            'sort': 'display_name',
        },
    ))
    return render(request, 'administration/languages.html', context)


@admin_required
def language_create_view(request):
    if request.method == 'POST':
        form = ProgrammingLanguageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm ngôn ngữ lập trình mới.')
            return redirect('administation:languages')
    else:
        form = ProgrammingLanguageForm()
    context = {
        **_admin_base_context(),
        'form': form,
        'is_edit': False,
        'current_page': 'languages',
    }
    return render(request, 'administration/language_form.html', context)


@admin_required
def language_edit_view(request, pk):
    language = get_object_or_404(ProgrammingLanguages, pk=pk)
    if request.method == 'POST':
        form = ProgrammingLanguageForm(request.POST, instance=language)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật ngôn ngữ.')
            return redirect('administation:languages')
    else:
        form = ProgrammingLanguageForm(instance=language)
    context = {
        **_admin_base_context(),
        'form': form,
        'language': language,
        'is_edit': True,
        'current_page': 'languages',
    }
    return render(request, 'administration/language_form.html', context)


@admin_required
@require_POST
def language_delete_view(request, pk):
    language = get_object_or_404(ProgrammingLanguages, pk=pk)
    name = language.display_name
    language.delete()
    messages.success(request, f'Đã xóa ngôn ngữ "{name}".')
    return redirect('administation:languages')


@admin_required
@require_POST
def language_toggle_view(request, pk):
    language = get_object_or_404(ProgrammingLanguages, pk=pk)
    language.is_active = not language.is_active
    language.save(update_fields=['is_active'])
    action = 'bật' if language.is_active else 'tắt'
    messages.success(request, f'Đã {action} ngôn ngữ "{language.display_name}".')
    return redirect('administation:languages')


@admin_required
def sandbox_list_view(request):
    filters = _sandbox_filter_values(request)
    sandboxes = _apply_sandbox_filters(_sandbox_base_queryset(), filters)

    language_names = set(ProgrammingLanguages.objects.values_list('name', flat=True))
    assignment_usage_counts = _assignment_language_usage_counts()
    sandboxes = list(sandboxes)
    for sandbox in sandboxes:
        sandbox.language_is_registered = sandbox.language in language_names
        sandbox.assignment_usage_count = assignment_usage_counts.get(sandbox.language, 0)
        sandbox.config_ok = bool(
            sandbox.docker_image and sandbox.timeout_seconds > 0 and
            sandbox.memory_limit_mb > 0 and sandbox.cpu_limit > 0
        )

    missing_sandbox_languages = ProgrammingLanguages.objects.filter(
        is_active=True,
    ).exclude(
        name__in=SandboxConfigs.objects.filter(is_active=True).values_list('language', flat=True)
    ).order_by('display_name')

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'sandboxes': sandboxes,
        'missing_sandbox_languages': missing_sandbox_languages,
        'search_query': filters['search_query'],
        'language_filter': filters['language_filter'],
        'is_active_filter': filters['is_active_filter'],
        'config_status_filter': filters['config_status_filter'],
        'language_registered_filter': filters['language_registered_filter'],
        'used_by_assignments_filter': filters['used_by_assignments_filter'],
        'timeout_min': filters['timeout_min'] if filters['timeout_min'] is not None else '',
        'timeout_max': filters['timeout_max'] if filters['timeout_max'] is not None else '',
        'memory_min': filters['memory_min'] if filters['memory_min'] is not None else '',
        'memory_max': filters['memory_max'] if filters['memory_max'] is not None else '',
        'cpu_min': filters['cpu_min'] if filters['cpu_min'] is not None else '',
        'cpu_max': filters['cpu_max'] if filters['cpu_max'] is not None else '',
        'sandbox_language_options': _sandbox_language_options(),
        'current_page': 'sandboxes',
        'filter_result_label': f'Đang hiển thị {len(sandboxes)} cấu hình',
    }
    context.update(admin_filter_context(
        request,
        'administation:sandboxes',
        labels={
            'search': 'Từ khóa',
            'language': 'Ngôn ngữ',
            'is_active': 'Trạng thái',
            'config_status': 'Cấu hình',
            'language_registered': 'Language',
            'used_by_assignments': 'Bài tập/bài thi',
            'timeout_min': 'Timeout từ',
            'timeout_max': 'Timeout đến',
            'memory_min': 'Memory từ',
            'memory_max': 'Memory đến',
            'cpu_min': 'CPU từ',
            'cpu_max': 'CPU đến',
        },
        value_labels=_sandbox_filter_badge_value_labels(filters),
        defaults={
            'is_active': 'all',
            'config_status': 'all',
            'language_registered': 'all',
            'used_by_assignments': 'all',
        },
    ))
    return render(request, 'administration/sandboxes.html', context)


@admin_required
def sandbox_create_view(request):
    if request.method == 'POST':
        form = SandboxConfigForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm cấu hình sandbox mới.')
            return redirect('administation:sandboxes')
    else:
        form = SandboxConfigForm()
    context = {
        **_admin_base_context(),
        'form': form,
        'is_edit': False,
        'current_page': 'sandboxes',
    }
    return render(request, 'administration/sandbox_form.html', context)


@admin_required
def sandbox_edit_view(request, pk):
    sandbox = get_object_or_404(SandboxConfigs, pk=pk)
    if request.method == 'POST':
        form = SandboxConfigForm(request.POST, instance=sandbox)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật cấu hình sandbox.')
            return redirect('administation:sandboxes')
    else:
        form = SandboxConfigForm(instance=sandbox)
    context = {
        **_admin_base_context(),
        'form': form,
        'sandbox': sandbox,
        'is_edit': True,
        'current_page': 'sandboxes',
    }
    return render(request, 'administration/sandbox_form.html', context)


@admin_required
@require_POST
def sandbox_test_view(request, pk):
    sandbox = get_object_or_404(SandboxConfigs, pk=pk)
    errors = []
    if not sandbox.docker_image:
        errors.append('thiếu Docker image')
    if sandbox.timeout_seconds <= 0:
        errors.append('timeout phải lớn hơn 0')
    if sandbox.memory_limit_mb <= 0:
        errors.append('memory phải lớn hơn 0')
    if sandbox.cpu_limit <= 0:
        errors.append('CPU phải lớn hơn 0')
    if not ProgrammingLanguages.objects.filter(name=sandbox.language, is_active=True).exists():
        errors.append('ngôn ngữ chưa active hoặc chưa được khai báo')

    if errors:
        messages.error(request, f'Cấu hình {sandbox.language} chưa ổn: {", ".join(errors)}.')
        status = 'failed'
    else:
        messages.success(request, f'Cấu hình sandbox {sandbox.language} hợp lệ để sử dụng.')
        status = 'ok'

    _log_admin_action(
        request.user,
        'ADMIN_SANDBOX_CONFIG_TEST',
        'sandbox_configs',
        sandbox.pk,
        {'language': sandbox.language, 'status': status, 'errors': errors},
        request=request,
    )
    return redirect('administation:sandboxes')


@admin_required
@require_POST
def sandbox_delete_view(request, pk):
    sandbox = get_object_or_404(SandboxConfigs, pk=pk)
    name = sandbox.language
    sandbox.delete()
    messages.success(request, f'Đã xóa cấu hình sandbox "{name}".')
    return redirect('administation:sandboxes')


@admin_required
def server_metrics_view(request):
    from apps.submissions.models import ExamSessions, Submissions

    filters = _server_metrics_filter_values(request)
    metrics_qs = _apply_server_metrics_filters(ServerMetrics.objects.order_by('-recorded_at'), filters)
    latest = metrics_qs.first()
    metrics = list(metrics_qs[:100])
    chart_rows = list(reversed(metrics[:30]))
    metrics_chart_json = json.dumps({
        'labels': [m.recorded_at.strftime('%H:%M') for m in chart_rows],
        'cpu': [m.cpu_usage or 0 for m in chart_rows],
        'memory': [m.memory_usage or 0 for m in chart_rows],
        'queue': [m.queue_length or 0 for m in chart_rows],
    })

    zombie_cutoff = timezone.now() - timezone.timedelta(minutes=30)
    zombie_count = Submissions.objects.filter(
        status__in=['pending', 'running'],
        submitted_at__lt=zombie_cutoff,
    ).count()
    warning_sessions_count = ExamSessions.objects.filter(violation_count__gt=0).count()
    recent_log_count = ActivityLogs.objects.filter(
        created_at__gte=timezone.now() - timezone.timedelta(hours=24)
    ).count()

    context = {
        **_admin_base_context(),
        'metrics': metrics,
        'latest': latest,
        'range_filter': filters['range_filter'],
        'cpu_min': filters['cpu_min'] if filters['cpu_min'] is not None else '',
        'memory_min': filters['memory_min'] if filters['memory_min'] is not None else '',
        'queue_min': filters['queue_min'] if filters['queue_min'] is not None else '',
        'zombie_count': zombie_count,
        'warning_sessions_count': warning_sessions_count,
        'recent_log_count': recent_log_count,
        'metrics_chart_json': metrics_chart_json,
        'current_page': 'metrics',
        'filter_result_label': f'Đang hiển thị {len(metrics)} bản ghi metrics',
    }
    context.update(admin_filter_context(
        request,
        'administation:metrics',
        labels={
            'range': 'Khoảng thời gian',
            'cpu_min': 'CPU từ',
            'memory_min': 'Memory từ',
            'queue_min': 'Queue từ',
        },
        value_labels=_server_metrics_filter_badge_value_labels(filters),
        defaults={'range': '24h'},
    ))
    return render(request, 'administration/server_metrics.html', context)


@admin_required
def system_settings_view(request):
    _warn_invalid_int_filters(request, [
        ('updated_by', 'Người cập nhật', 1),
    ])
    filters = _setting_filter_values(request)
    settings_qs = _apply_setting_queryset_filters(
        SystemSettings.objects.select_related('updated_by').order_by('setting_key'),
        filters,
    )
    settings_list = _apply_setting_object_filters(list(settings_qs), filters)
    categories = sorted({
        _setting_category(setting.setting_key)
        for setting in SystemSettings.objects.all()
    } | {
        _setting_category(key)
        for key in SYSTEM_SETTING_SCHEMAS
    })
    grouped_settings = []
    for category in categories:
        items = [
            setting for setting in settings_list
            if _setting_category(setting.setting_key) == category
        ]
        if items or not filters['category_filter']:
            grouped_settings.append({'category': category, 'settings': items})

    existing_all_keys = set(SystemSettings.objects.values_list('setting_key', flat=True))
    setting_warnings = _setting_warning_items(filters, existing_all_keys)
    policy_schemas = {
        key: schema
        for key, schema in SYSTEM_SETTING_SCHEMAS.items()
        if (
            (not filters['category_filter'] or _setting_category(key) == filters['category_filter']) and
            (filters['type_filter'] == 'all' or _setting_schema_type(schema) == filters['type_filter']) and
            (filters['critical_filter'] == 'all' or (filters['critical_filter'] == 'yes') == _setting_is_critical(key))
        )
    }

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'settings_list': settings_list,
        'grouped_settings': grouped_settings,
        'categories': categories,
        'category_filter': filters['category_filter'],
        'type_filter': filters['type_filter'],
        'critical_filter': filters['critical_filter'],
        'missing_filter': filters['missing_filter'],
        'updated_by_filter': filters['updated_by_filter'],
        'updated_from': filters['updated_from'].isoformat() if filters['updated_from'] else '',
        'updated_to': filters['updated_to'].isoformat() if filters['updated_to'] else '',
        'setting_updaters': _setting_updater_options(),
        'setting_warnings': setting_warnings,
        'search_query': filters['search_query'],
        'policy_schemas': policy_schemas,
        'current_page': 'settings',
        'filter_result_label': f'Đang hiển thị {len(settings_list)} cài đặt',
    }
    context.update(admin_filter_context(
        request,
        'administation:system_settings',
        labels={
            'search': 'Từ khóa',
            'category': 'Nhóm',
            'type': 'Kiểu',
            'critical': 'Mức độ',
            'missing': 'Tình trạng',
            'updated_by': 'Người sửa',
            'updated_from': 'Sửa từ',
            'updated_to': 'Sửa đến',
        },
        value_labels=_setting_filter_badge_value_labels(filters),
        defaults={
            'type': 'all',
            'critical': 'all',
            'missing': 'all',
        },
    ))
    return render(request, 'administration/system_settings.html', context)


def _policy_schema_cards():
    cards = []
    for key, schema in SYSTEM_SETTING_SCHEMAS.items():
        schema_type = schema.get('type')
        if schema_type is bool:
            kind = 'bool'
            sample_value = False
        elif schema_type is int:
            kind = 'int'
            sample_value = schema.get('min', 1)
        else:
            kind = 'json'
            sample_value = {}
        cards.append({
            'key': key,
            'kind': kind,
            'sample_value': json.dumps(sample_value, ensure_ascii=False),
            'min': schema.get('min'),
            'max': schema.get('max'),
            'description': schema.get('description', ''),
        })
    return cards


@admin_required
def system_setting_create_view(request):
    if request.method == 'POST':
        form = SystemSettingForm(request.POST)
        if form.is_valid():
            setting = form.save(commit=False)
            setting.updated_by = request.user
            setting.save()
            _log_admin_action(
                request.user,
                'ADMIN_SETTING_CREATE',
                'system_settings',
                setting.pk,
                {'setting_key': setting.setting_key, 'setting_value': setting.setting_value},
                request=request,
            )
            messages.success(request, 'Đã thêm cài đặt mới.')
            return redirect('administation:system_settings')
    else:
        setting_key = request.GET.get('key', '').strip()
        schema = SYSTEM_SETTING_SCHEMAS.get(setting_key)
        if schema:
            default_value = False if schema['type'] is bool else schema.get('min', 0)
            form = SystemSettingForm(initial={
                'setting_key': setting_key,
                'setting_value': json.dumps(default_value),
                'description': schema.get('description', ''),
            })
        else:
            form = SystemSettingForm()
    context = {
        **_admin_base_context(),
        'form': form,
        'is_edit': False,
        'policy_schemas': SYSTEM_SETTING_SCHEMAS,
        'policy_schema_cards': _policy_schema_cards(),
        'current_page': 'settings',
    }
    return render(request, 'administration/setting_form.html', context)


@admin_required
def system_setting_edit_view(request, pk):
    setting = get_object_or_404(SystemSettings, pk=pk)
    if request.method == 'POST':
        form = SystemSettingForm(request.POST, instance=setting)
        if form.is_valid():
            old_value = setting.setting_value
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            _log_admin_action(
                request.user,
                'ADMIN_SETTING_UPDATE',
                'system_settings',
                obj.pk,
                {'setting_key': obj.setting_key, 'old_value': old_value, 'new_value': obj.setting_value},
                request=request,
            )
            messages.success(request, 'Đã cập nhật cài đặt.')
            return redirect('administation:system_settings')
    else:
        initial_data = {
            'setting_key': setting.setting_key,
            'setting_value': json.dumps(setting.setting_value, indent=2, ensure_ascii=False),
            'description': setting.description,
        }
        form = SystemSettingForm(initial=initial_data)
    context = {
        **_admin_base_context(),
        'form': form,
        'setting': setting,
        'is_edit': True,
        'policy_schemas': SYSTEM_SETTING_SCHEMAS,
        'policy_schema_cards': _policy_schema_cards(),
        'current_page': 'settings',
    }
    return render(request, 'administration/setting_form.html', context)


@admin_required
@require_POST
def system_setting_delete_view(request, pk):
    setting = get_object_or_404(SystemSettings, pk=pk)
    key = setting.setting_key
    old_value = setting.setting_value
    setting_id = setting.pk
    setting.delete()
    _log_admin_action(
        request.user,
        'ADMIN_SETTING_DELETE',
        'system_settings',
        setting_id,
        {'setting_key': key, 'old_value': old_value},
        request=request,
    )
    messages.success(request, f'Đã xóa cài đặt "{key}".')
    return redirect('administation:system_settings')


@admin_required
@require_POST
def system_setting_toggle_view(request, pk):
    setting = get_object_or_404(SystemSettings, pk=pk)
    if isinstance(setting.setting_value, bool):
        old_value = setting.setting_value
        setting.setting_value = not setting.setting_value
        setting.updated_by = request.user
        setting.save(update_fields=['setting_value', 'updated_by'])
        _log_admin_action(
            request.user,
            'ADMIN_SETTING_TOGGLE',
            'system_settings',
            setting.pk,
            {'setting_key': setting.setting_key, 'old_value': old_value, 'new_value': setting.setting_value},
            request=request,
        )
        status = 'bật' if setting.setting_value else 'tắt'
        messages.success(request, f'Đã {status} cài đặt "{setting.setting_key}".')
    return redirect('administation:system_settings')


@admin_required
def user_management_view(request):
    return _render_user_management_page(request)


@admin_required
def user_detail_view(request, pk):
    target_user = get_object_or_404(User.objects.select_related('profiles'), pk=pk)
    logs = ActivityLogs.objects.filter(
        Q(user=target_user) | Q(resource_type='accounts', resource_id=target_user.pk)
    ).select_related('user').order_by('-created_at')[:50]
    from apps.submissions.models import Submissions
    submissions = Submissions.objects.filter(student=target_user).select_related(
        'assignment', 'assignment__classroom'
    ).order_by('-submitted_at')[:20]
    context = {
        **_admin_base_context(),
        'target_user': target_user,
        'profile': getattr(target_user, 'profiles', None),
        'logs': logs,
        'submissions': submissions,
        'current_page': 'user_management',
    }
    return render(request, 'administration/user_detail.html', context)


@admin_required
def user_create_view(request):
    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            user = User()
            _apply_admin_user_form(user, form, request.user, request, created=True)
            messages.success(request, f'Đã tạo user "{user.username}".')
            return redirect('administation:user_detail', pk=user.pk)
    else:
        form = AdminUserForm(initial={'role': 'student', 'is_active': True})
    context = {
        **_admin_base_context(),
        'form': form,
        'is_edit': False,
        'current_page': 'user_management',
    }
    return render(request, 'administration/user_form.html', context)


@admin_required
def user_edit_view(request, pk):
    target_user = get_object_or_404(User.objects.select_related('profiles'), pk=pk)
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=target_user)
        if form.is_valid():
            if target_user.pk == request.user.pk and not form.cleaned_data.get('is_active'):
                form.add_error('is_active', 'Không thể khóa tài khoản đang đăng nhập.')
            elif target_user.is_superuser and form.cleaned_data['role'] != 'admin':
                form.add_error('role', 'Không nên hạ role của superuser qua màn hình này.')
            else:
                _apply_admin_user_form(target_user, form, request.user, request, created=False)
                messages.success(request, 'Đã cập nhật user.')
                return redirect('administation:user_detail', pk=target_user.pk)
    else:
        profile = getattr(target_user, 'profiles', None)
        form = AdminUserForm(instance=target_user, initial={
            'username': target_user.username,
            'email': target_user.email,
            'first_name': target_user.first_name,
            'last_name': target_user.last_name,
            'role': profile.role if profile else ('admin' if target_user.is_staff else 'student'),
            'is_active': target_user.is_active,
        })
    context = {
        **_admin_base_context(),
        'form': form,
        'target_user': target_user,
        'is_edit': True,
        'current_page': 'user_management',
    }
    return render(request, 'administration/user_form.html', context)


@admin_required
def user_reset_password_view(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            target_user.set_password(form.cleaned_data['new_password'])
            target_user.save(update_fields=['password'])
            _log_admin_action(
                request.user,
                'ADMIN_PASSWORD_RESET',
                'accounts',
                target_user.pk,
                {'target_user_id': target_user.pk, 'target_username': target_user.username},
                request=request,
            )
            messages.success(request, 'Đã đặt lại mật khẩu.')
            return redirect('administation:user_detail', pk=target_user.pk)
    else:
        form = AdminPasswordResetForm()
    context = {
        **_admin_base_context(),
        'form': form,
        'target_user': target_user,
        'current_page': 'user_management',
    }
    return render(request, 'administration/user_reset_password.html', context)


@admin_required
def user_export_view(request):
    export_type = get_choice_param(request.GET, 'type', ['full', 'contacts', 'audit'], 'full')
    filters = _user_filter_values(request)

    users = _apply_user_filters(_user_management_queryset(), filters)

    response = _csv_response(csv_filename(
        'users',
        export_type,
        filtered=bool(build_query_string(request, remove=('page', 'type'))),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))

    writer = csv.writer(response)
    if export_type == 'contacts':
        writer.writerow(['Username', 'Họ tên', 'Email', 'Vai trò', 'Hoạt động'])
        for user in users:
            profile = getattr(user, 'profiles', None)
            writer.writerow([
                user.username,
                user.get_full_name() or '',
                user.email,
                profile.role if profile else '',
                'Có' if user.is_active else 'Không',
            ])
        return response

    if export_type == 'audit':
        writer.writerow([
            'ID', 'Username', 'Role', 'Active', 'Staff', 'Superuser',
            'Joined', 'Last Login', 'Submissions', 'Assignments touched',
            'Teacher classrooms', 'Joined classrooms', 'Profile status',
        ])
        for user in users:
            profile = getattr(user, 'profiles', None)
            writer.writerow([
                user.id,
                user.username,
                profile.role if profile else '',
                'Yes' if user.is_active else 'No',
                'Yes' if user.is_staff else 'No',
                'Yes' if user.is_superuser else 'No',
                user.date_joined.strftime('%Y-%m-%d %H:%M'),
                user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '',
                user.submission_count,
                user.assignment_count,
                user.teaching_class_count,
                user.joined_class_count,
                profile.status if profile else '',
            ])
        return response

    writer.writerow(['ID', 'Username', 'Full Name', 'Email', 'Role', 'Active', 'Joined', 'Last Login'])

    for user in users:
        profile = getattr(user, 'profiles', None)
        writer.writerow([
            user.id,
            user.username,
            user.get_full_name() or '',
            user.email,
            profile.role if profile else '',
            'Yes' if user.is_active else 'No',
            user.date_joined.strftime('%Y-%m-%d %H:%M'),
            user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '',
        ])

    return response


@admin_required
@require_POST
def classroom_bulk_action_view(request):
    action = request.POST.get('action')
    classroom_ids = _selected_int_ids_from_post(request, 'classroom_ids', 'lớp học ID')

    if not classroom_ids:
        messages.error(request, 'Chưa chọn lớp học nào.')
        return redirect('administation:classroom_management')

    classrooms = Classrooms.objects.select_related('teacher').filter(id__in=classroom_ids)

    if action in ('approve', 'approve_all'):
        try:
            pending_classrooms = list(classrooms.filter(status='pending'))
            with transaction.atomic():
                for classroom in pending_classrooms:
                    classroom.status = 'approved'
                    classroom.approved_by = request.user
                    classroom.reviewed_at = timezone.now()
                    classroom.is_active = True
                    classroom.save(update_fields=['status', 'approved_by', 'reviewed_at', 'is_active'])
                    _notify_classroom_review(classroom, request.user, approved=True)
            messages.success(request, f'Đã duyệt {len(pending_classrooms)} lớp học.')
        except Exception:
            messages.error(request, 'Chức năng duyệt chưa khả dụng. Vui lòng thử lại sau.')
            return redirect('administation:classroom_management')
    elif action in ('reject', 'reject_all'):
        try:
            pending_classrooms = list(classrooms.filter(status='pending'))
            with transaction.atomic():
                for classroom in pending_classrooms:
                    classroom.status = 'rejected'
                    classroom.approved_by = request.user
                    classroom.reviewed_at = timezone.now()
                    classroom.is_active = False
                    classroom.save(update_fields=['status', 'approved_by', 'reviewed_at', 'is_active'])
                    _notify_classroom_review(classroom, request.user, approved=False)
            messages.success(request, f'Đã từ chối {len(pending_classrooms)} lớp học.')
        except Exception:
            messages.error(request, 'Chức năng duyệt chưa khả dụng. Vui lòng thử lại sau.')
            return redirect('administation:classroom_management')
    elif action == 'activate':
        updated = classrooms.update(is_active=True)
        messages.success(request, f'Đã kích hoạt {updated} lớp học.')
    elif action == 'deactivate':
        updated = classrooms.update(is_active=False)
        messages.success(request, f'Đã vô hiệu hóa {updated} lớp học.')
    else:
        messages.error(request, f'Hành động không hợp lệ: {action}')

    return redirect('administation:classroom_management')


@admin_required
@require_POST
def approve_classroom_view(request, pk):
    try:
        classroom = get_object_or_404(
            Classrooms.objects.select_related('teacher'), pk=pk, status='pending'
        )
        classroom.status = 'approved'
        classroom.approved_by = request.user
        classroom.reviewed_at = timezone.now()
        classroom.is_active = True
        classroom.save(update_fields=['status', 'approved_by', 'reviewed_at', 'is_active'])
        _notify_classroom_review(classroom, request.user, approved=True)
        messages.success(request, f'Đã duyệt lớp học "{classroom.name}".')
    except:
        messages.error(request, 'Chức năng duyệt chưa khả dụng. Vui lòng thử lại sau.')
    return redirect('administation:classroom_management')


@admin_required
@require_POST
def reject_classroom_view(request, pk):
    try:
        classroom = get_object_or_404(
            Classrooms.objects.select_related('teacher'), pk=pk, status='pending'
        )
        classroom.status = 'rejected'
        classroom.approved_by = request.user
        classroom.reviewed_at = timezone.now()
        classroom.is_active = False
        classroom.save(update_fields=['status', 'approved_by', 'reviewed_at', 'is_active'])
        _notify_classroom_review(classroom, request.user, approved=False)
        messages.success(request, f'Đã từ chối lớp học "{classroom.name}".')
    except:
        messages.error(request, 'Chức năng duyệt chưa khả dụng. Vui lòng thử lại sau.')
    return redirect('administation:classroom_management')


@admin_required
def classroom_management_view(request):
    _warn_invalid_int_filters(request, [
        ('subject_id', 'Môn học', 1),
        ('teacher_id', 'Giáo viên', 1),
        ('semester_id', 'Kỳ học', 1),
        ('member_count_min', 'Sĩ số từ', 0),
        ('member_count_max', 'Sĩ số đến', 0),
    ])
    filters = _classroom_filter_values(request)
    classrooms = _apply_classroom_filters(_classroom_base_queryset(), filters)

    paginator = Paginator(classrooms, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    try:
        pending_count = Classrooms.objects.filter(status='pending').count()
        approved_count = Classrooms.objects.filter(status='approved').count()
        rejected_count = Classrooms.objects.filter(status='rejected').count()
    except:
        pending_count = approved_count = rejected_count = 0

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'classrooms': page_obj,
        'page_obj': page_obj,
        'search_query': filters['search_query'],
        'subject_filter': filters['subject_filter'],
        'teacher_filter': filters['teacher_filter'],
        'semester_filter': filters['semester_filter'],
        'status_filter': filters['status_filter'],
        'is_active_filter': filters['is_active_filter'],
        'member_count_min': filters['member_count_min'] if filters['member_count_min'] is not None else '',
        'member_count_max': filters['member_count_max'] if filters['member_count_max'] is not None else '',
        'capacity_status_filter': filters['capacity_status_filter'],
        'has_subjects_filter': filters['has_subjects_filter'],
        'has_assignments_filter': filters['has_assignments_filter'],
        'has_exams_filter': filters['has_exams_filter'],
        'has_pending_members_filter': filters['has_pending_members_filter'],
        'created_from': filters['created_from'].isoformat() if filters['created_from'] else '',
        'created_to': filters['created_to'].isoformat() if filters['created_to'] else '',
        'classroom_status_links': _classroom_status_links(request),
        'classroom_active_links': _classroom_active_links(request),
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'current_page': 'classroom_management',
    }
    context.update(admin_filter_context(
        request,
        'administation:classroom_management',
        labels={
            'search': 'Từ khóa',
            'subject_id': 'Môn',
            'teacher_id': 'Giáo viên',
            'semester_id': 'Kỳ học',
            'status': 'Trạng thái duyệt',
            'is_active': 'Hoạt động',
            'member_count_min': 'Sĩ số từ',
            'member_count_max': 'Sĩ số đến',
            'capacity_status': 'Sức chứa',
            'has_subjects': 'Môn học',
            'has_assignments': 'Bài tập',
            'has_exams': 'Bài thi',
            'has_pending_members': 'HS chờ duyệt',
            'created_from': 'Tạo từ',
            'created_to': 'Tạo đến',
        },
        value_labels=_classroom_filter_badge_value_labels(filters),
        defaults={
            'status': 'all',
            'is_active': 'all',
            'capacity_status': 'all',
            'has_subjects': 'all',
            'has_assignments': 'all',
            'has_exams': 'all',
            'has_pending_members': 'all',
        },
    ))
    context['csv_items'] = [
        _csv_dropdown_item(
            'administation:classroom_export',
            'Xuất lớp học theo lọc hiện tại' if context['has_active_filters'] else 'Xuất toàn bộ lớp học',
            'filter_alt',
        ),
        _csv_dropdown_item(
            'administation:classroom_export',
            'Xuất thành viên của các lớp đang lọc' if context['has_active_filters'] else 'Xuất thành viên theo lớp',
            'groups',
            'members',
        ),
    ]
    return render(request, 'administration/classroom_management.html', context)


@admin_required
def classroom_export_view(request):
    export_type = get_choice_param(request.GET, 'type', ['summary', 'members'], 'summary')
    filters = _classroom_filter_values(request)
    classrooms = _apply_classroom_filters(_classroom_base_queryset(), filters)

    response = _csv_response(csv_filename(
        'classrooms',
        export_type,
        filtered=bool(build_query_string(request, remove=('page', 'type'))),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))

    try:
        writer = csv.writer(response)
        if export_type == 'members':
            writer.writerow([
                'Classroom ID', 'Classroom', 'Teacher', 'Student Username',
                'Student Name', 'Student Email', 'Member Status', 'Joined At',
            ])
            memberships = ClassroomMembers.objects.filter(
                classroom__in=classrooms,
            ).select_related('classroom', 'classroom__teacher', 'student').order_by(
                'classroom__name', 'student__username'
            )
            for member in memberships:
                writer.writerow([
                    member.classroom_id,
                    member.classroom.name if member.classroom else '',
                    member.classroom.teacher.username if member.classroom and member.classroom.teacher else '',
                    member.student.username if member.student else '',
                    member.student.get_full_name() if member.student else '',
                    member.student.email if member.student else '',
                    member.status,
                    member.joined_at.strftime('%Y-%m-%d %H:%M') if member.joined_at else '',
                ])
            return response

        writer.writerow([
            'ID', 'Name', 'Description', 'Invite Code', 'Teacher', 'Status',
            'Approved By', 'Max Students', 'Active', 'Created At',
            'Members', 'Pending Members', 'Subjects', 'Assignments', 'Exams',
        ])

        for classroom in classrooms:
            status = getattr(classroom, 'status', 'N/A')
            approved_by = getattr(classroom, 'approved_by', None)
            approved_by_name = approved_by.username if approved_by else ''

            writer.writerow([
                classroom.id,
                classroom.name,
                classroom.description or '',
                classroom.invite_code,
                classroom.teacher.username if classroom.teacher else '',
                status,
                approved_by_name,
                classroom.max_students,
                'Yes' if classroom.is_active else 'No',
                classroom.created_at.strftime('%Y-%m-%d %H:%M'),
                classroom.member_count,
                classroom.pending_member_count,
                classroom.subject_count,
                classroom.assignment_count,
                classroom.exam_assignment_count,
            ])
    except Exception as e:
        writer.writerow(['Error', str(e)])

    return response


@admin_required
def subject_export_view(request):
    export_type = get_choice_param(request.GET, 'type', ['summary', 'classrooms'], 'summary')
    filters = _subject_filter_values(request)
    subjects = _apply_subject_filters(_subject_base_queryset(), filters)

    response = _csv_response(csv_filename(
        'subjects',
        export_type,
        filtered=bool(build_query_string(request, remove=('page', 'type'))),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))

    writer = csv.writer(response)
    if export_type == 'classrooms':
        writer.writerow([
            'Subject ID', 'Code', 'Subject', 'Status', 'Classroom',
            'Semester', 'Teacher', 'Active Link', 'Assignments', 'Exams',
        ])
        links = _subject_classroom_links_for_export(subjects, filters)
        for link in links:
            writer.writerow([
                link.subject_id,
                link.subject.code if link.subject else '',
                link.subject.name if link.subject else '',
                link.subject.status if link.subject else '',
                link.classroom.name if link.classroom else '',
                link.semester.name if link.semester else '',
                link.classroom.teacher.username if link.classroom and link.classroom.teacher else '',
                'Yes' if link.is_active else 'No',
                link.assignment_count,
                link.exam_count,
            ])
        return response

    writer.writerow([
        'ID', 'Code', 'Name', 'Description', 'Status', 'Created By',
        'Created At', 'Approved By', 'Active', 'Classrooms', 'Assignments', 'Exams', 'Languages',
    ])

    for subject in subjects:
        languages = ', '.join(language.display_name or language.name for language in subject.languages.all())
        writer.writerow([
            subject.id,
            subject.code,
            subject.name,
            subject.description or '',
            subject.status,
            subject.created_by.username if subject.created_by else '',
            subject.created_at.strftime('%Y-%m-%d %H:%M'),
            subject.approved_by.username if subject.approved_by else '',
            'Yes' if subject.is_active else 'No',
            subject.classroom_count,
            subject.assignment_count,
            subject.exam_count,
            languages,
        ])

    return response


@admin_required
@require_POST
def subject_bulk_action_view(request):
    action = request.POST.get('action')
    subject_ids = _selected_int_ids_from_post(request, 'subject_ids', 'môn học ID')

    if not subject_ids:
        messages.error(request, 'Chưa chọn môn học nào.')
        return redirect('administation:subject_approvals')

    subjects = Subjects.objects.select_related('created_by').filter(id__in=subject_ids)

    if action in ('approve', 'approve_all'):
        pending_subjects = list(subjects.filter(status='pending'))
        with transaction.atomic():
            for subject in pending_subjects:
                subject.status = SubjectApprovalStatus.APPROVED
                subject.approved_by = request.user
                subject.reviewed_at = timezone.now()
                subject.is_active = True
                subject.save(update_fields=['status', 'approved_by', 'reviewed_at', 'is_active'])
                _notify_subject_review(subject, request.user, approved=True)
        messages.success(request, f'Đã duyệt {len(pending_subjects)} môn học.')
    elif action in ('reject', 'reject_all'):
        pending_subjects = list(subjects.filter(status='pending'))
        with transaction.atomic():
            for subject in pending_subjects:
                subject.status = SubjectApprovalStatus.REJECTED
                subject.approved_by = request.user
                subject.reviewed_at = timezone.now()
                subject.is_active = False
                subject.save(update_fields=['status', 'approved_by', 'reviewed_at', 'is_active'])
                _notify_subject_review(subject, request.user, approved=False)
        messages.success(request, f'Đã từ chối {len(pending_subjects)} môn học.')
    elif action == 'activate':
        updated = subjects.update(is_active=True)
        messages.success(request, f'Đã kích hoạt {updated} môn học.')
    elif action == 'deactivate':
        updated = subjects.update(is_active=False)
        messages.success(request, f'Đã vô hiệu hóa {updated} môn học.')
    else:
        messages.error(request, f'Hành động không hợp lệ: {action}')

    return redirect('administation:subject_approvals')


@admin_required
def analytics_view(request):
    """Admin analytics: lưu lượng nộp bài, tăng trưởng người dùng."""
    import json as _json
    from django.db.models.functions import TruncDate, TruncHour, TruncMonth

    _warn_invalid_int_filters(request, [
        ('classroom_id', 'Lớp học', 1),
        ('subject_id', 'Môn học', 1),
        ('teacher_id', 'Giáo viên', 1),
    ])
    now = timezone.now()
    filters = _analytics_filter_values(request)
    submissions = _analytics_submission_queryset(filters)

    # 1. Lưu lượng nộp bài theo giờ (24h gần nhất, có xét filter lớp/môn/gv/ngôn ngữ)
    last_24h = now - timedelta(hours=24)
    hourly_subs = (
        submissions.filter(submitted_at__gte=last_24h)
        .annotate(hour=TruncHour('submitted_at'))
        .values('hour').annotate(count=Count('id')).order_by('hour')
    )
    hourly_labels = [h['hour'].strftime('%H:00') for h in hourly_subs]
    hourly_data = [h['count'] for h in hourly_subs]

    # 2. Lưu lượng nộp bài theo ngày trong khoảng lọc
    daily_subs = (
        submissions
        .annotate(day=TruncDate('submitted_at'))
        .values('day').annotate(count=Count('id')).order_by('day')
    )
    daily_labels = [d['day'].strftime('%d/%m') for d in daily_subs]
    daily_data = [d['count'] for d in daily_subs]

    # 3. Tăng trưởng người dùng theo tháng (12 tháng)
    last_12m = now - timedelta(days=365)
    users_qs = User.objects.filter(date_joined__gte=last_12m)
    if filters['date_from']:
        users_qs = users_qs.filter(date_joined__date__gte=filters['date_from'])
    if filters['date_to']:
        users_qs = users_qs.filter(date_joined__date__lte=filters['date_to'])
    monthly_users = (
        users_qs
        .annotate(month=TruncMonth('date_joined'))
        .values('month').annotate(count=Count('id')).order_by('month')
    )
    growth_labels = [m['month'].strftime('%m/%Y') for m in monthly_users]
    growth_data = [m['count'] for m in monthly_users]

    # 4. Phân bố role
    role_counts = Profiles.objects.values('role').annotate(c=Count('id'))
    role_distribution = {
        'labels': [r['role'] or 'unknown' for r in role_counts],
        'data': [r['c'] for r in role_counts],
    }

    # 5. Top lớp học có nhiều hoạt động nhất (nhiều submission)
    top_classrooms = (
        submissions
        .values('assignment__classroom__id', 'assignment__classroom__name')
        .annotate(sub_count=Count('id'))
        .order_by('-sub_count')[:10]
    )

    # 6. Tổng quan
    total_users_year = users_qs.count()
    total_subs_month = submissions.count()
    total_subs_today = submissions.filter(submitted_at__gte=last_24h).count()
    has_analytics_data = total_subs_month > 0 or total_users_year > 0

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'hourly_data_json': _json.dumps({'labels': hourly_labels, 'data': hourly_data}),
        'daily_data_json': _json.dumps({'labels': daily_labels, 'data': daily_data}),
        'growth_data_json': _json.dumps({'labels': growth_labels, 'data': growth_data}),
        'role_distribution_json': _json.dumps(role_distribution),
        'top_classrooms': top_classrooms,
        'total_users_year': total_users_year,
        'total_subs_month': total_subs_month,
        'total_subs_today': total_subs_today,
        'has_analytics_data': has_analytics_data,
        'date_from': filters['date_from'].isoformat() if filters['date_from'] else '',
        'date_to': filters['date_to'].isoformat() if filters['date_to'] else '',
        'classroom_filter': filters['classroom_filter'],
        'subject_filter': filters['subject_filter'],
        'teacher_filter': filters['teacher_filter'],
        'language_filter': filters['language_filter'],
        'analytics_language_options': _analytics_language_options(),
        'current_page': 'analytics',
        'filter_result_label': f'Bài nộp khớp bộ lọc: {total_subs_month}',
    }
    context.update(admin_filter_context(
        request,
        'administation:analytics',
        labels={
            'date_from': 'Từ ngày',
            'date_to': 'Đến ngày',
            'classroom_id': 'Lớp',
            'subject_id': 'Môn',
            'teacher_id': 'Giáo viên',
            'language': 'Ngôn ngữ',
        },
        value_labels=_analytics_filter_badge_value_labels(filters),
    ))
    return render(request, 'administration/analytics.html', context)


@admin_required
def sandbox_monitor_view(request):
    """Giám sát Sandbox (Docker containers + hàng đợi chấm bài + Zombie tasks).

    - Kiểm tra trạng thái Docker daemon (available/unavailable)
    - List Docker containers đang chạy (từ `docker ps`)
    - Hàng đợi chấm bài: Submissions với status=pending/running
    - Phát hiện Zombie: submissions stuck ở pending/running > ZOMBIE_THRESHOLD_MIN
    """
    import subprocess
    from datetime import timedelta
    from apps.submissions.models import Submissions
    from services import docker_service

    _warn_invalid_int_filters(request, [
        ('assignment_id', 'Bài tập', 1),
        ('classroom_id', 'Lớp học', 1),
        ('subject_id', 'Môn học', 1),
        ('student_id', 'Học sinh', 1),
        ('age_min_minutes', 'Treo quá N phút', 0),
    ])

    zombie_threshold_min = get_int_setting(
        'sandbox.zombie_threshold_minutes',
        default=5,
        minimum=1,
        maximum=1440,
    )
    now = timezone.now()
    zombie_cutoff = now - timedelta(minutes=zombie_threshold_min)

    # 1. Docker status (reset cache để monitor luôn detect lại trạng thái mới)
    docker_service._DOCKER_AVAILABLE = None
    docker_ok = docker_service.is_docker_available()
    docker_containers = []
    docker_error = None
    if docker_ok:
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format',
                 '{{.ID}}||{{.Image}}||{{.Status}}||{{.Names}}||{{.RunningFor}}'],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split('||')
                    if len(parts) >= 5:
                        docker_containers.append({
                            'id': parts[0][:12],
                            'image': parts[1],
                            'status': parts[2],
                            'name': parts[3],
                            'running_for': parts[4],
                        })
            else:
                docker_error = result.stderr.strip() or 'docker ps failed'
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            docker_error = str(e)

    filters = _sandbox_monitor_filter_values(request)

    # 2. Bài nộp trong monitor
    filtered_subs = _apply_sandbox_monitor_filters(_sandbox_monitor_base_queryset(), filters)
    queue_subs = filtered_subs.filter(status__in=['pending', 'running'])
    queue_count = queue_subs.count()
    filtered_submission_count = filtered_subs.count()

    # 3. Zombie detection
    zombies = filtered_subs.filter(status__in=['pending', 'running'], submitted_at__lt=zombie_cutoff)
    zombie_list = list(zombies[:50])

    # 4. Thống kê 24h gần nhất
    last_24h = now - timedelta(hours=24)
    subs_24h = Submissions.objects.filter(submitted_at__gte=last_24h)
    stats_24h = {
        'total': subs_24h.count(),
        'finished': subs_24h.filter(status='finished').count(),
        'failed': subs_24h.filter(status='error').count(),
        'pending': subs_24h.filter(status__in=['pending', 'running']).count(),
    }

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'docker_ok': docker_ok,
        'docker_error': docker_error,
        'docker_containers': docker_containers,
        'queue_count': queue_count,
        'queue_subs': filtered_subs[:30],
        'filtered_submission_count': filtered_submission_count,
        'zombies': zombie_list,
        'zombie_count': len(zombie_list),
        'zombie_threshold_min': zombie_threshold_min,
        'submission_status_filter': filters['submission_status_filter'],
        'language_filter': filters['language_filter'],
        'assignment_filter': filters['assignment_filter'],
        'classroom_filter': filters['classroom_filter'],
        'subject_filter': filters['subject_filter'],
        'age_min_minutes': filters['age_min_minutes'] if filters['age_min_minutes'] is not None else '',
        'student_filter': filters['student_filter'],
        'sandbox_monitor_assignments': _sandbox_monitor_assignment_options(),
        'sandbox_monitor_languages': _sandbox_monitor_language_options(),
        'monitor_query_string': build_query_string(request, remove=()),
        'stats_24h': stats_24h,
        'current_page': 'sandbox_monitor',
        'filter_result_label': f'Đang hiển thị {filtered_submission_count} bài nộp',
    }
    context.update(admin_filter_context(
        request,
        'administation:sandbox_monitor',
        labels={
            'submission_status': 'Trạng thái',
            'language': 'Ngôn ngữ',
            'assignment_id': 'Bài tập',
            'classroom_id': 'Lớp',
            'subject_id': 'Môn',
            'age_min_minutes': 'Treo quá',
            'student_id': 'Học sinh',
        },
        value_labels=_sandbox_monitor_filter_badge_value_labels(filters),
        defaults={'submission_status': 'all'},
    ))
    return render(request, 'administration/sandbox_monitor.html', context)


@admin_required
@require_POST
def kill_zombie_view(request, submission_pk):
    """Đánh dấu zombie task là error (không tự động nộp lại)."""
    from apps.submissions.models import Submissions
    submission = get_object_or_404(Submissions, pk=submission_pk)
    if submission.status not in ('pending', 'running'):
        messages.info(request, 'Bài nộp này không phải zombie (status = %s).' % submission.status)
        return _sandbox_monitor_redirect(request)
    submission.status = 'error'
    submission.teacher_comment = ((submission.teacher_comment or '') +
        f'\n[Admin killed zombie task at {timezone.now():%d/%m/%Y %H:%M}]')
    submission.graded_by = request.user
    submission.graded_at = timezone.now()
    submission.save(update_fields=['status', 'teacher_comment', 'graded_by', 'graded_at'])
    _log_admin_action(
        request.user,
        'ADMIN_KILL_ZOMBIE_SUBMISSION',
        'submissions',
        submission.pk,
        {
            'student_id': submission.student_id,
            'assignment_id': submission.assignment_id,
            'previous_status': 'pending/running',
        },
        request=request,
    )
    if submission.student:
        notify_user(
            submission.student,
            title='Bài nộp bị lỗi hệ thống',
            message='Admin đã đánh dấu bài nộp bị treo là lỗi. Vui lòng liên hệ giáo viên nếu cần nộp lại.',
            link=f'/assignments/{submission.assignment_id}/' if submission.assignment_id else '/submissions/',
            notification_type='submission_zombie_killed',
            actor=request.user,
            metadata={'submission_id': submission.pk},
        )
    messages.success(request, f'Đã kill zombie task #{submission.pk}.')
    return _sandbox_monitor_redirect(request)


@admin_required
@require_POST
def requeue_zombie_view(request, submission_pk):
    """Đưa zombie task vào lại hàng đợi chấm (qua Celery task)."""
    from apps.submissions.models import Submissions, SubmissionDetails
    from apps.submissions.tasks import grade_submission_task

    submission = get_object_or_404(Submissions, pk=submission_pk)
    # Xóa details cũ và reset
    SubmissionDetails.objects.filter(submission=submission).delete()
    submission.status = 'pending'
    submission.total_score = 0
    submission.passed_testcases = 0
    submission.total_testcases = 0
    submission.execution_time = None
    submission.memory_usage = None
    submission.save(update_fields=[
        'status', 'total_score', 'passed_testcases',
        'total_testcases', 'execution_time', 'memory_usage',
    ])
    grade_submission_task.delay(submission.pk)
    _log_admin_action(
        request.user,
        'ADMIN_REQUEUE_ZOMBIE_SUBMISSION',
        'submissions',
        submission.pk,
        {
            'student_id': submission.student_id,
            'assignment_id': submission.assignment_id,
        },
        request=request,
    )
    if submission.student:
        notify_user(
            submission.student,
            title='Bài nộp đang được chấm lại',
            message='Admin đã đưa bài nộp bị treo vào lại hàng đợi chấm.',
            link=f'/assignments/{submission.assignment_id}/' if submission.assignment_id else '/submissions/',
            notification_type='submission_zombie_requeued',
            actor=request.user,
            metadata={'submission_id': submission.pk},
        )
    messages.success(request, f'Đã đưa bài nộp #{submission.pk} vào lại hàng đợi chấm.')
    return _sandbox_monitor_redirect(request)


@admin_required
def activity_logs_view(request):
    _warn_invalid_int_filters(request, [
        ('user_id', 'User', 1),
        ('resource_id', 'Resource ID', 1),
    ])
    logs = _filtered_activity_logs_from_request(request)
    filters = _activity_log_filter_values(request)

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'logs': page_obj,
        'page_obj': page_obj,
        'user_filter': filters['user_filter'],
        'user_id_filter': filters['user_id_filter'],
        'role_filter': filters['role_filter'],
        'action_filter': filters['action_filter'],
        'action_group_filter': filters['action_group_filter'],
        'resource_type_filter': filters['resource_type_filter'],
        'resource_id_filter': filters['resource_id_filter'] or '',
        'ip_address_filter': filters['ip_address_filter'],
        'date_from': filters['date_from'].isoformat() if filters['date_from'] else '',
        'date_to': filters['date_to'].isoformat() if filters['date_to'] else '',
        'preset_filter': filters['preset_filter'],
        'resource_type_options': _activity_log_resource_type_options(),
        'activity_user_options': _activity_log_user_options(),
        'preset_links': _activity_log_preset_links(request),
        'total_count': paginator.count,
        'current_page': 'logs',
    }
    context.update(admin_filter_context(
        request,
        'administation:activity_logs',
        labels={
            'user': 'Người dùng',
            'user_id': 'User',
            'role': 'Vai trò',
            'action': 'Hành động',
            'action_group': 'Nhóm hành động',
            'resource_type': 'Loại resource',
            'resource_id': 'Resource ID',
            'ip_address': 'IP',
            'date_from': 'Từ ngày',
            'date_to': 'Đến ngày',
            'preset': 'Nhanh',
        },
        value_labels=_activity_log_filter_badge_value_labels(filters),
        defaults={
            'role': 'all',
            'action_group': 'all',
            'preset': 'all',
        },
    ))
    context['csv_items'] = [
        _csv_dropdown_item(
            'administation:activity_logs_export',
            'Xuất log theo lọc hiện tại' if context['has_active_filters'] else 'Xuất toàn bộ log',
            'filter_alt',
        ),
        _csv_dropdown_item(
            'administation:activity_logs_export',
            'Xuất bản gọn theo lọc hiện tại' if context['has_active_filters'] else 'Xuất bản gọn',
            'short_text',
            'compact',
        ),
    ]
    return render(request, 'administration/activity_logs.html', context)


def _filtered_activity_logs_from_request(request):
    logs = ActivityLogs.objects.select_related('user').order_by('-created_at')
    return _apply_activity_log_filters(logs, _activity_log_filter_values(request))


@admin_required
def activity_logs_export_view(request):
    logs = _filtered_activity_logs_from_request(request)
    export_type = get_choice_param(request.GET, 'type', ['full', 'compact'], 'full')

    response = _csv_response(csv_filename(
        'activity_logs',
        export_type,
        filtered=bool(build_query_string(request, remove=('page', 'type'))),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))

    writer = csv.writer(response)
    if export_type == 'compact':
        writer.writerow(['Time', 'Username', 'Action', 'Resource', 'IP'])
        for log in logs:
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username if log.user else 'System',
                log.action,
                f'{log.resource_type or ""}#{log.resource_id or ""}'.strip('#'),
                log.ip_address or '',
            ])
        return response

    writer.writerow([
        'ID', 'Time', 'Username', 'Action', 'Resource Type', 'Resource ID',
        'IP Address', 'User Agent', 'Metadata',
    ])
    for log in logs:
        writer.writerow([
            log.pk,
            log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.username if log.user else 'System',
            log.action,
            log.resource_type or '',
            log.resource_id or '',
            log.ip_address or '',
            log.user_agent or '',
            json.dumps(log.metadata or {}, ensure_ascii=False),
        ])

    return response


@admin_required
def exam_events_view(request):
    from apps.assignments.models import Assignments
    from apps.submissions.models import ExamEvents, ExamSessions

    _warn_invalid_int_filters(request, [
        ('assignment_id', 'Bài thi', 1),
        ('classroom_id', 'Lớp học', 1),
        ('subject_id', 'Môn học', 1),
        ('teacher_id', 'Giáo viên', 1),
        ('student_id', 'Học sinh', 1),
        ('min_warnings', 'Cảnh báo từ', 0),
    ])
    filters = _exam_event_filter_values(request)
    events = _apply_exam_event_filters(_exam_events_base_queryset(), filters)
    sessions = _apply_exam_session_filters(_exam_sessions_base_queryset(), filters)

    warning_sessions = sessions.filter(violation_count__gt=0)[:20]
    event_types = ExamEvents.objects.values_list('event_type', flat=True).distinct().order_by('event_type')
    status_choices = ExamSessions.STATUS_CHOICES
    active_exam_count = ExamSessions.objects.filter(status=ExamSessions.STATUS_RUNNING).count()
    warning_count = ExamSessions.objects.filter(violation_count__gt=0).count()
    exam_assignment_count = Assignments.objects.filter(is_exam=True).count()

    paginator = Paginator(events, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        **_admin_base_context(),
        **admin_filter_options(),
        'events': page_obj,
        'page_obj': page_obj,
        'warning_sessions': warning_sessions,
        'event_types': event_types,
        'status_choices': status_choices,
        'exam_assignment_options': _exam_assignment_options(),
        'search_query': filters['search_query'],
        'assignment_filter': filters['assignment_filter'],
        'classroom_filter': filters['classroom_filter'],
        'subject_filter': filters['subject_filter'],
        'teacher_filter': filters['teacher_filter'],
        'student_filter': filters['student_filter'],
        'event_filter': filters['event_filter'],
        'status_filter': filters['status_filter'],
        'min_warnings': filters['min_warnings_value'] if filters['min_warnings_value'] is not None else '',
        'has_final_submission_filter': filters['has_final_submission_filter'],
        'session_duration_filter': filters['session_duration_filter'],
        'date_from': filters['date_from'].isoformat() if filters['date_from'] else '',
        'date_to': filters['date_to'].isoformat() if filters['date_to'] else '',
        'active_exam_count': active_exam_count,
        'warning_count': warning_count,
        'exam_assignment_count': exam_assignment_count,
        'current_page': 'exam_events',
    }
    context.update(admin_filter_context(
        request,
        'administation:exam_events',
        labels={
            'search': 'Từ khóa',
            'assignment_id': 'Bài thi',
            'classroom_id': 'Lớp',
            'subject_id': 'Môn',
            'teacher_id': 'Giáo viên',
            'student_id': 'Học sinh',
            'event_type': 'Loại sự kiện',
            'status': 'Trạng thái',
            'min_warnings': 'Cảnh báo tối thiểu',
            'has_final_submission': 'Bài nộp cuối',
            'session_duration': 'Thời lượng',
            'date_from': 'Từ ngày',
            'date_to': 'Đến ngày',
        },
        value_labels=_exam_event_filter_badge_value_labels(filters),
        defaults={
            'has_final_submission': 'all',
            'session_duration': 'all',
        },
    ))
    context['csv_items'] = [
        _csv_dropdown_item(
            'administation:exam_events_export',
            'Xuất sự kiện thi theo lọc hiện tại' if context['has_active_filters'] else 'Xuất toàn bộ sự kiện thi',
            'filter_alt',
        ),
        _csv_dropdown_item(
            'administation:exam_events_export',
            'Xuất phiên thi theo lọc hiện tại' if context['has_active_filters'] else 'Xuất toàn bộ phiên thi',
            'assignment_ind',
            'sessions',
        ),
    ]
    return render(request, 'administration/exam_events.html', context)


@admin_required
def exam_events_export_view(request):
    filters = _exam_event_filter_values(request)
    events = _apply_exam_event_filters(_exam_events_base_queryset(), filters)
    export_type = get_choice_param(request.GET, 'type', ['full', 'sessions'], 'full')
    response = _csv_response(csv_filename(
        'exam_events',
        export_type,
        filtered=bool(build_query_string(request, remove=('page', 'type'))),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))
    writer = csv.writer(response)

    if export_type == 'sessions':
        sessions = _apply_exam_session_filters(_exam_sessions_base_queryset(), filters)
        writer.writerow([
            'Session ID', 'Assignment', 'Classroom', 'Subject', 'Student',
            'Status', 'Warnings', 'Started At', 'Ends At', 'Submitted At',
            'Has Final Submission',
        ])
        for session in sessions:
            assignment = session.assignment
            classroom = assignment.classroom if assignment else None
            subject = assignment.classroom_subject.subject if assignment and assignment.classroom_subject else None
            writer.writerow([
                session.pk,
                assignment.title if assignment else '',
                classroom.name if classroom else '',
                subject.name if subject else '',
                session.student.username if session.student else '',
                session.status,
                session.violation_count,
                session.started_at.strftime('%Y-%m-%d %H:%M:%S') if session.started_at else '',
                session.ends_at.strftime('%Y-%m-%d %H:%M:%S') if session.ends_at else '',
                session.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if session.submitted_at else '',
                'Yes' if session.final_submission_id else 'No',
            ])
        return response

    writer.writerow([
        'Event ID', 'Time', 'Event Type', 'Session ID', 'Assignment',
        'Classroom', 'Subject', 'Student', 'Session Status', 'Warnings',
        'Metadata',
    ])
    for event in events:
        session = event.session
        assignment = session.assignment if session else None
        classroom = assignment.classroom if assignment else None
        subject = assignment.classroom_subject.subject if assignment and assignment.classroom_subject else None
        writer.writerow([
            event.pk,
            event.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            event.event_type,
            session.pk if session else '',
            assignment.title if assignment else '',
            classroom.name if classroom else '',
            subject.name if subject else '',
            session.student.username if session and session.student else '',
            session.status if session else '',
            session.violation_count if session else '',
            json.dumps(event.metadata or {}, ensure_ascii=False),
        ])
    return response
