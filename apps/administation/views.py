import json
import csv
from django.shortcuts import render, redirect, get_object_or_404
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
from apps.classrooms.models import Subjects, SubjectApprovalStatus, Classrooms, ClassroomMembers
from apps.notifications.services import notify_user
from apps.administation.utils import get_int_setting
from .models import (
    ProgrammingLanguages, SandboxConfigs, ServerMetrics,
    ActivityLogs, SystemSettings,
)
from .forms import (
    AdminPasswordResetForm, AdminUserForm, ProgrammingLanguageForm,
    SandboxConfigForm, SystemSettingForm, SYSTEM_SETTING_SCHEMAS,
)


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


def _apply_admin_user_form(user, form, actor, request, created=False):
    old_role = None
    if not created:
        old_role = getattr(getattr(user, 'profiles', None), 'role', 'student')

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
    from apps.submissions.models import Submissions
    total_classrooms = Classrooms.objects.filter(is_active=True).count()
    total_submissions = Submissions.objects.count()
    pending_subjects = Subjects.objects.filter(status=SubjectApprovalStatus.PENDING).count()

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
        'total_submissions': total_submissions,
        'pending_subjects': pending_subjects,
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
    status_filter = request.GET.get('status', 'pending')
    search_query = request.GET.get('search', '').strip()

    # Handle teacher registrations (pending/approved/rejected)
    registrations = TeacherRegistrations.objects.select_related(
        'user', 'reviewed_by'
    ).order_by('-created_at')

    if status_filter and status_filter != 'all':
        registrations = registrations.filter(status=status_filter)

    if search_query:
        registrations = registrations.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    paginator = Paginator(registrations, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # Also get approved teachers count
    approved_teachers = User.objects.filter(profiles__role='teacher').count()

    context = {
        **_admin_base_context(),
        'registrations': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'pending_count': TeacherRegistrations.objects.filter(status='pending').count(),
        'approved_count': approved_teachers,
        'rejected_count': TeacherRegistrations.objects.filter(status='rejected').count(),
        'current_page': 'teacher_approvals',
    }
    return render(request, 'administration/teacher_approvals.html', context)


@admin_required
def teacher_management_view(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')

    teachers = User.objects.select_related('profiles').filter(
        profiles__role='teacher'
    ).annotate(
        classroom_count=Count('classrooms', distinct=True),
        assignment_count=Count('assignments', distinct=True),
        submission_count=Count('graded_submissions', distinct=True)
    ).order_by('-date_joined')

    if status_filter == 'active':
        teachers = teachers.filter(is_active=True)
    elif status_filter == 'inactive':
        teachers = teachers.filter(is_active=False)

    if search_query:
        teachers = teachers.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    paginator = Paginator(teachers, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        **_admin_base_context(),
        'teachers': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'current_page': 'teacher_management',
    }
    return render(request, 'administration/teacher_management.html', context)


@admin_required
@require_POST
def user_bulk_action_view(request):
    action = request.POST.get('action')
    user_ids = request.POST.getlist('user_ids')

    if not user_ids:
        messages.error(request, 'Chưa chọn người dùng nào.')
        return redirect('administation:user_management')

    users = User.objects.filter(id__in=user_ids)
    target_ids = list(users.values_list('pk', flat=True))
    if action in ('deactivate', 'delete'):
        if users.filter(pk=request.user.pk).exists():
            messages.error(request, 'Không thể vô hiệu hóa tài khoản đang đăng nhập.')
            return redirect('administation:user_management')
        selected_active_superusers = users.filter(is_superuser=True, is_active=True).count()
        active_superusers = User.objects.filter(is_superuser=True, is_active=True).count()
        if selected_active_superusers and active_superusers - selected_active_superusers <= 0:
            messages.error(request, 'Không thể vô hiệu hóa superuser cuối cùng.')
            return redirect('administation:user_management')

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

    return redirect('administation:user_management')


@admin_required
def subject_management_view(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')

    subjects = Subjects.objects.select_related(
        'created_by', 'approved_by'
    ).prefetch_related('languages').annotate(
        classroom_count=Count('classroom_links', filter=Q(classroom_links__is_active=True), distinct=True)
    ).order_by('-created_at')

    if status_filter != 'all':
        subjects = subjects.filter(status=status_filter)

    if search_query:
        subjects = subjects.filter(
            Q(code__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(created_by__username__icontains=search_query) |
            Q(created_by__first_name__icontains=search_query) |
            Q(created_by__last_name__icontains=search_query)
        )

    paginator = Paginator(subjects, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        **_admin_base_context(),
        'subjects': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'pending_count': Subjects.objects.filter(status='pending').count(),
        'approved_count': Subjects.objects.filter(status='approved').count(),
        'rejected_count': Subjects.objects.filter(status='rejected').count(),
        'current_page': 'subject_management',
    }
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
    return redirect('administation:teacher_approvals')


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
    return redirect('administation:teacher_approvals')


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
    search_query = request.GET.get('search', '').strip()
    languages = ProgrammingLanguages.objects.all().order_by('display_name')

    if search_query:
        languages = languages.filter(
            Q(name__icontains=search_query) |
            Q(display_name__icontains=search_query) |
            Q(file_extension__icontains=search_query)
        )

    context = {
        **_admin_base_context(),
        'languages': languages,
        'search_query': search_query,
        'current_page': 'languages',
    }
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
    search_query = request.GET.get('search', '').strip()
    sandboxes = SandboxConfigs.objects.all().order_by('language')

    if search_query:
        sandboxes = sandboxes.filter(
            Q(language__icontains=search_query) |
            Q(docker_image__icontains=search_query)
        )

    context = {
        **_admin_base_context(),
        'sandboxes': sandboxes,
        'search_query': search_query,
        'current_page': 'sandboxes',
    }
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
def sandbox_delete_view(request, pk):
    sandbox = get_object_or_404(SandboxConfigs, pk=pk)
    name = sandbox.language
    sandbox.delete()
    messages.success(request, f'Đã xóa cấu hình sandbox "{name}".')
    return redirect('administation:sandboxes')


@admin_required
def server_metrics_view(request):
    latest = ServerMetrics.objects.order_by('-recorded_at').first()
    metrics = list(ServerMetrics.objects.order_by('-recorded_at')[:100])
    chart_rows = list(reversed(metrics[:30]))
    metrics_chart_json = json.dumps({
        'labels': [m.recorded_at.strftime('%H:%M') for m in chart_rows],
        'cpu': [m.cpu_usage or 0 for m in chart_rows],
        'memory': [m.memory_usage or 0 for m in chart_rows],
        'queue': [m.queue_length or 0 for m in chart_rows],
    })

    context = {
        **_admin_base_context(),
        'metrics': metrics,
        'latest': latest,
        'metrics_chart_json': metrics_chart_json,
        'current_page': 'metrics',
    }
    return render(request, 'administration/server_metrics.html', context)


@admin_required
def system_settings_view(request):
    search_query = request.GET.get('search', '').strip()
    settings_list = SystemSettings.objects.all().order_by('setting_key')

    if search_query:
        settings_list = settings_list.filter(
            Q(setting_key__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    context = {
        **_admin_base_context(),
        'settings_list': settings_list,
        'search_query': search_query,
        'policy_schemas': SYSTEM_SETTING_SCHEMAS,
        'current_page': 'settings',
    }
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
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
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
    setting.delete()
    messages.success(request, f'Đã xóa cài đặt "{key}".')
    return redirect('administation:system_settings')


@admin_required
@require_POST
def system_setting_toggle_view(request, pk):
    setting = get_object_or_404(SystemSettings, pk=pk)
    if isinstance(setting.setting_value, bool):
        setting.setting_value = not setting.setting_value
        setting.updated_by = request.user
        setting.save(update_fields=['setting_value', 'updated_by'])
        status = 'bật' if setting.setting_value else 'tắt'
        messages.success(request, f'Đã {status} cài đặt "{setting.setting_key}".')
    return redirect('administation:system_settings')


@admin_required
def user_management_view(request):
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')

    users = User.objects.select_related('profiles').annotate(
        assignment_count=Count('submissions__assignment', distinct=True)
    ).order_by('-date_joined')

    if role_filter != 'all':
        users = users.filter(profiles__role=role_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    if search_query:
        # Simple fuzzy search: icontains for name, username, email
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        **_admin_base_context(),
        'users': page_obj,
        'page_obj': page_obj,
        'role_filter': role_filter,
        'search_query': search_query,
        'status_filter': status_filter,
        'current_page': 'user_management',
    }
    return render(request, 'administration/user_management.html', context)


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
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '').strip()

    users = User.objects.select_related('profiles').order_by('-date_joined')

    if role_filter != 'all':
        users = users.filter(profiles__role=role_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
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
    classroom_ids = request.POST.getlist('classroom_ids')

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
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')

    # Build queryset safely without referencing non-existent fields
    classrooms = Classrooms.objects.select_related('teacher').annotate(
        member_count=Count('classroommembers', filter=Q(classroommembers__status='approved')),
        assignment_count=Count('assignments', distinct=True)
    ).order_by('-created_at')

    if status_filter != 'all':
        if status_filter in ['pending', 'approved', 'rejected']:
            try:
                classrooms = classrooms.filter(status=status_filter)
            except:
                pass  # Field doesn't exist yet
        elif status_filter == 'active':
            classrooms = classrooms.filter(is_active=True)
        elif status_filter == 'inactive':
            classrooms = classrooms.filter(is_active=False)

    if search_query:
        classrooms = classrooms.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(teacher__username__icontains=search_query) |
            Q(teacher__first_name__icontains=search_query) |
            Q(teacher__last_name__icontains=search_query)
        )

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
        'classrooms': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'current_page': 'classroom_management',
    }
    return render(request, 'administration/classroom_management.html', context)


@admin_required
def classroom_export_view(request):
    status_filter = request.GET.get('status', 'all')

    classrooms = Classrooms.objects.select_related('teacher').order_by('-created_at')

    if status_filter != 'all':
        if status_filter in ['pending', 'approved', 'rejected']:
            try:
                classrooms = classrooms.filter(status=status_filter)
            except:
                pass
        elif status_filter == 'active':
            classrooms = classrooms.filter(is_active=True)
        elif status_filter == 'inactive':
            classrooms = classrooms.filter(is_active=False)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="classrooms_export.csv"'
    response.write('\ufeff')

    try:
        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Description', 'Invite Code', 'Teacher', 'Status', 'Approved By', 'Max Students', 'Active', 'Created At', 'Members', 'Assignments'])

        for classroom in classrooms:
            # Safely get approval fields (may not exist yet)
            try:
                status = getattr(classroom, 'status', 'N/A')
                approved_by = getattr(classroom, 'approved_by', None)
                approved_by_name = approved_by.username if approved_by else ''
            except:
                status = 'N/A'
                approved_by_name = 'N/A'

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
                classroom.assignment_count,
            ])
    except Exception as e:
        writer.writerow(['Error', str(e)])

    return response


@admin_required
def subject_export_view(request):
    status_filter = request.GET.get('status', 'all')

    subjects = Subjects.objects.select_related('created_by', 'approved_by').order_by('-created_at')

    if status_filter != 'all':
        subjects = subjects.filter(status=status_filter)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="subjects_export.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['ID', 'Code', 'Name', 'Description', 'Status', 'Created By', 'Created At', 'Approved By', 'Classrooms'])

    for subject in subjects:
        writer.writerow([
            subject.id,
            subject.code,
            subject.name,
            subject.description or '',
            subject.status,
            subject.created_by.username if subject.created_by else '',
            subject.created_at.strftime('%Y-%m-%d %H:%M'),
            subject.approved_by.username if subject.approved_by else '',
            subject.classroom_count,
        ])

    return response


@admin_required
@require_POST
def subject_bulk_action_view(request):
    action = request.POST.get('action')
    subject_ids = request.POST.getlist('subject_ids')

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
    from datetime import timedelta
    from django.db.models.functions import TruncDate, TruncHour, TruncMonth
    from apps.submissions.models import Submissions
    from apps.classrooms.models import Classrooms, ClassroomMembers
    from apps.assignments.models import Assignments

    now = timezone.now()

    # 1. Lưu lượng nộp bài theo giờ (24h gần nhất)
    last_24h = now - timedelta(hours=24)
    hourly_subs = (
        Submissions.objects.filter(submitted_at__gte=last_24h)
        .annotate(hour=TruncHour('submitted_at'))
        .values('hour').annotate(count=Count('id')).order_by('hour')
    )
    hourly_labels = [h['hour'].strftime('%H:00') for h in hourly_subs]
    hourly_data = [h['count'] for h in hourly_subs]

    # 2. Lưu lượng nộp bài theo ngày (30 ngày gần nhất)
    last_30d = now - timedelta(days=30)
    daily_subs = (
        Submissions.objects.filter(submitted_at__gte=last_30d)
        .annotate(day=TruncDate('submitted_at'))
        .values('day').annotate(count=Count('id')).order_by('day')
    )
    daily_labels = [d['day'].strftime('%d/%m') for d in daily_subs]
    daily_data = [d['count'] for d in daily_subs]

    # 3. Tăng trưởng người dùng theo tháng (12 tháng)
    last_12m = now - timedelta(days=365)
    monthly_users = (
        User.objects.filter(date_joined__gte=last_12m)
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
        Submissions.objects
        .values('assignment__classroom__id', 'assignment__classroom__name')
        .annotate(sub_count=Count('id'))
        .order_by('-sub_count')[:10]
    )

    # 6. Tổng quan
    total_users_year = User.objects.filter(date_joined__gte=last_12m).count()
    total_subs_month = Submissions.objects.filter(submitted_at__gte=last_30d).count()
    total_subs_today = Submissions.objects.filter(submitted_at__gte=last_24h).count()

    context = {
        **_admin_base_context(),
        'hourly_data_json': _json.dumps({'labels': hourly_labels, 'data': hourly_data}),
        'daily_data_json': _json.dumps({'labels': daily_labels, 'data': daily_data}),
        'growth_data_json': _json.dumps({'labels': growth_labels, 'data': growth_data}),
        'role_distribution_json': _json.dumps(role_distribution),
        'top_classrooms': top_classrooms,
        'total_users_year': total_users_year,
        'total_subs_month': total_subs_month,
        'total_subs_today': total_subs_today,
        'current_page': 'analytics',
    }
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

    # 2. Hàng đợi chấm bài
    pending_subs = Submissions.objects.filter(
        status__in=['pending', 'running']
    ).select_related('student', 'assignment').order_by('submitted_at')

    queue_count = pending_subs.count()

    # 3. Zombie detection
    zombies = pending_subs.filter(submitted_at__lt=zombie_cutoff)
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
        'docker_ok': docker_ok,
        'docker_error': docker_error,
        'docker_containers': docker_containers,
        'queue_count': queue_count,
        'queue_subs': pending_subs[:30],
        'zombies': zombie_list,
        'zombie_count': len(zombie_list),
        'zombie_threshold_min': zombie_threshold_min,
        'stats_24h': stats_24h,
        'current_page': 'sandbox_monitor',
    }
    return render(request, 'administration/sandbox_monitor.html', context)


@admin_required
@require_POST
def kill_zombie_view(request, submission_pk):
    """Đánh dấu zombie task là error (không tự động nộp lại)."""
    from apps.submissions.models import Submissions
    submission = get_object_or_404(Submissions, pk=submission_pk)
    if submission.status not in ('pending', 'running'):
        messages.info(request, 'Bài nộp này không phải zombie (status = %s).' % submission.status)
        return redirect('administation:sandbox_monitor')
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
    return redirect('administation:sandbox_monitor')


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
    return redirect('administation:sandbox_monitor')


@admin_required
def activity_logs_view(request):
    logs = _filtered_activity_logs_from_request(request)
    user_filter = request.GET.get('user', '').strip()
    action_filter = request.GET.get('action', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        **_admin_base_context(),
        'logs': page_obj,
        'page_obj': page_obj,
        'user_filter': user_filter,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_count': paginator.count,
        'current_page': 'logs',
    }
    return render(request, 'administration/activity_logs.html', context)


def _filtered_activity_logs_from_request(request):
    logs = ActivityLogs.objects.select_related('user').order_by('-created_at')

    user_filter = request.GET.get('user', '').strip()
    action_filter = request.GET.get('action', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if user_filter:
        logs = logs.filter(
            Q(user__username__icontains=user_filter) |
            Q(user__first_name__icontains=user_filter) |
            Q(user__last_name__icontains=user_filter)
        )
    if action_filter:
        logs = logs.filter(action__icontains=action_filter)
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)

    return logs


@admin_required
def activity_logs_export_view(request):
    logs = _filtered_activity_logs_from_request(request)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="activity_logs_export.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
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

    search_query = request.GET.get('search', '').strip()
    event_filter = request.GET.get('event_type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    events = ExamEvents.objects.select_related(
        'session',
        'session__student',
        'session__assignment',
        'session__assignment__classroom',
    ).order_by('-created_at')

    sessions = ExamSessions.objects.select_related(
        'student',
        'assignment',
        'assignment__classroom',
    ).order_by('-violation_count', '-updated_at')

    if search_query:
        events = events.filter(
            Q(session__student__username__icontains=search_query) |
            Q(session__student__first_name__icontains=search_query) |
            Q(session__student__last_name__icontains=search_query) |
            Q(session__assignment__title__icontains=search_query) |
            Q(session__assignment__classroom__name__icontains=search_query)
        )
        sessions = sessions.filter(
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(assignment__title__icontains=search_query) |
            Q(assignment__classroom__name__icontains=search_query)
        )
    if event_filter:
        events = events.filter(event_type=event_filter)
    if status_filter:
        sessions = sessions.filter(status=status_filter)
        events = events.filter(session__status=status_filter)
    if date_from:
        events = events.filter(created_at__date__gte=date_from)
        sessions = sessions.filter(updated_at__date__gte=date_from)
    if date_to:
        events = events.filter(created_at__date__lte=date_to)
        sessions = sessions.filter(updated_at__date__lte=date_to)

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
        'events': page_obj,
        'page_obj': page_obj,
        'warning_sessions': warning_sessions,
        'event_types': event_types,
        'status_choices': status_choices,
        'search_query': search_query,
        'event_filter': event_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'active_exam_count': active_exam_count,
        'warning_count': warning_count,
        'exam_assignment_count': exam_assignment_count,
        'current_page': 'exam_events',
    }
    return render(request, 'administration/exam_events.html', context)
