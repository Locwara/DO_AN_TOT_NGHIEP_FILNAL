from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import cloudinary.uploader

from apps.notifications.services import notify_admins
from .forms import RegisterForm, LoginForm, ProfileForm, TeacherRegistrationForm
from .models import Profiles, TeacherRegistrations


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Đăng ký thành công! Chào mừng bạn đến với LH Programming.')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Update last_login in profile
            try:
                profile = user.profiles
                profile.last_login = timezone.now()
                profile.save(update_fields=['last_login'])
            except Profiles.DoesNotExist:
                profile = Profiles.objects.create(id=user, role='student')
            next_url = request.GET.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                messages.success(request, f'Chào mừng trở lại, {user.get_full_name() or user.username}!')
                return redirect(next_url)

            # Redirect theo role
            if user.is_superuser or user.is_staff:
                messages.success(request, f'Chào mừng quản trị viên {user.get_full_name() or user.username}!')
                return redirect('administation:dashboard')

            role = profile.role or 'student'

            if role == 'teacher':
                messages.success(request, f'Chào mừng giáo viên {user.get_full_name() or user.username}!')
                return redirect('accounts:teacher_dashboard')

            messages.success(request, f'Chào mừng trở lại, {user.get_full_name() or user.username}!')
            return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Bạn đã đăng xuất thành công.')
    return redirect('home')


@login_required
def profile_view(request, user_id=None):
    if user_id:
        target_user = get_object_or_404(User, pk=user_id)
    else:
        target_user = request.user

    try:
        profile = target_user.profiles
    except Profiles.DoesNotExist:
        profile = Profiles.objects.create(id=target_user, role='student')

    is_own_profile = (target_user == request.user)
    can_view_private_info = is_own_profile or request.user.is_superuser
    if not can_view_private_info:
        try:
            can_view_private_info = request.user.profiles.role == 'admin'
        except Profiles.DoesNotExist:
            can_view_private_info = False

    # Get classrooms for this user
    from apps.classrooms.models import Classrooms, ClassroomMembers
    if profile.role == 'teacher':
        classrooms = Classrooms.objects.filter(teacher=target_user, is_active=True)
    else:
        member_ids = ClassroomMembers.objects.filter(
            student=target_user, status='approved'
        ).values_list('classroom_id', flat=True)
        classrooms = Classrooms.objects.filter(id__in=member_ids, is_active=True)

    # Get submission stats
    from apps.submissions.models import Submissions
    total_submissions = Submissions.objects.filter(student=target_user).count()
    from django.db.models import Avg
    from django.db.models.functions import Coalesce
    avg_score = Submissions.objects.filter(
        student=target_user, status='finished'
    ).aggregate(avg=Avg(Coalesce('manual_score', 'total_score')))['avg'] or 0

    context = {
        'target_user': target_user,
        'profile': profile,
        'is_own_profile': is_own_profile,
        'can_view_private_info': can_view_private_info,
        'classrooms': classrooms,
        'total_submissions': total_submissions,
        'avg_score': round(avg_score, 1),
        'classrooms_count': classrooms.count(),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile_view(request):
    try:
        profile = request.user.profiles
    except Profiles.DoesNotExist:
        profile = Profiles.objects.create(id=request.user, role='student')

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=request.user)
        avatar_file = request.FILES.get('avatar_file')

        if form.is_valid():
            # Update User fields
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            email = form.cleaned_data.get('email')
            if email:
                request.user.email = email
            request.user.save()

            # Upload avatar to Cloudinary if provided
            if avatar_file:
                try:
                    result = cloudinary.uploader.upload(
                        avatar_file,
                        folder='lh_avatars',
                        transformation={'width': 300, 'height': 300, 'crop': 'fill'}
                    )
                    profile.avatar_url = result.get('secure_url')
                except Exception:
                    messages.warning(request, 'Không thể upload avatar. Vui lòng thử lại.')

            form.save()
            messages.success(request, 'Cập nhật profile thành công!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=profile, user=request.user)

    return render(request, 'accounts/edit_profile.html', {'form': form, 'profile': profile})


@login_required
def student_dashboard_view(request):
    """Dashboard cá nhân cho sinh viên - tiến độ học tập."""
    from django.utils import timezone
    from django.db.models import Max
    from django.db.models.functions import Coalesce
    from apps.classrooms.models import Classrooms, ClassroomMembers, Leaderboard
    from apps.assignments.models import Assignments
    from apps.submissions.models import Submissions

    user = request.user
    now = timezone.now()

    # Danh sách lớp đang học
    member_records = ClassroomMembers.objects.filter(
        student=user, status='approved'
    ).select_related('classroom')
    classroom_ids = [m.classroom_id for m in member_records if m.classroom and m.classroom.is_active]
    classrooms = list(Classrooms.objects.filter(id__in=classroom_ids, is_active=True))

    # Tổng bài tập trong các lớp đang học (đã publish)
    all_assignments = Assignments.objects.filter(
        classroom_id__in=classroom_ids, is_published=True
    )
    total_assignments = all_assignments.count()

    # Số bài đã hoàn thành (có ít nhất 1 submission status=finished)
    completed_assignment_ids = set(
        Submissions.objects.filter(
            student=user, status='finished',
            assignment__in=all_assignments,
        ).values_list('assignment_id', flat=True)
    )
    completed_count = len(completed_assignment_ids)

    # Điểm trung bình (lấy điểm cao nhất mỗi bài, ưu tiên điểm chấm tay nếu có)
    best_scores = Submissions.objects.filter(
        student=user, status='finished',
        assignment__in=all_assignments,
    ).values('assignment_id').annotate(best=Max(Coalesce('manual_score', 'total_score')))
    if best_scores:
        avg_score = round(sum(b['best'] for b in best_scores) / len(best_scores), 1)
    else:
        avg_score = 0

    # Pass rate cá nhân (pass = điểm >= 50%)
    max_scores_by_assignment = {
        assignment.pk: assignment.max_score
        for assignment in all_assignments.only('id', 'max_score')
    }
    passed = 0
    for b in best_scores:
        max_score = max_scores_by_assignment.get(b['assignment_id'])
        if max_score and b['best'] >= max_score * 0.5:
            passed += 1
    pass_rate = round(passed / completed_count * 100, 1) if completed_count > 0 else 0

    # Rank trong từng lớp
    active_classroom_ids = [classroom.pk for classroom in classrooms]
    leaderboard_by_classroom = {
        lb.classroom_id: lb
        for lb in Leaderboard.objects.filter(
            classroom_id__in=active_classroom_ids,
            student=user,
        )
    }
    member_counts = {
        row['classroom_id']: row['total']
        for row in ClassroomMembers.objects.filter(
            classroom_id__in=active_classroom_ids,
            status='approved',
        ).values('classroom_id').annotate(total=Count('id'))
    }
    ranks_by_classroom = []
    for cr in classrooms:
        lb = leaderboard_by_classroom.get(cr.pk)
        total_members = member_counts.get(cr.pk, 0)
        ranks_by_classroom.append({
            'classroom': cr,
            'rank': lb.rank if lb else None,
            'total_score': lb.total_score if lb else 0,
            'total_members': total_members,
        })

    # Bài tập sắp đến hạn (trong 7 ngày) và chưa nộp
    from datetime import timedelta
    upcoming = all_assignments.filter(
        due_date__gte=now, due_date__lte=now + timedelta(days=7)
    ).exclude(id__in=completed_assignment_ids).order_by('due_date')[:5]

    # Bài tập đã quá hạn chưa nộp
    overdue = all_assignments.filter(
        due_date__lt=now
    ).exclude(id__in=completed_assignment_ids).order_by('-due_date')[:5]

    # Bài nộp gần đây
    recent_submissions = Submissions.objects.filter(
        student=user
    ).select_related('assignment').order_by('-submitted_at')[:5]

    context = {
        'classrooms': classrooms,
        'classrooms_count': len(classrooms),
        'total_assignments': total_assignments,
        'completed_count': completed_count,
        'avg_score': avg_score,
        'pass_rate': pass_rate,
        'ranks_by_classroom': ranks_by_classroom,
        'upcoming': upcoming,
        'overdue': overdue,
        'recent_submissions': recent_submissions,
        'completion_rate': round(completed_count / total_assignments * 100, 1) if total_assignments > 0 else 0,
    }
    return render(request, 'accounts/student_dashboard.html', context)


@login_required
def teacher_dashboard_view(request):
    try:
        profile = request.user.profiles
    except Profiles.DoesNotExist:
        profile = Profiles.objects.create(id=request.user, role='student')

    if request.user.is_superuser or profile.role == 'admin':
        return redirect('administation:dashboard')
    if profile.role != 'teacher':
        return redirect('accounts:student_dashboard')

    from apps.classrooms.models import (
        Classrooms, ClassroomMembers, Subjects, SubjectApprovalStatus,
    )
    from apps.assignments.models import Assignments, AssignmentStatistics
    from apps.submissions.models import Submissions

    user = request.user
    now = timezone.now()
    week_later = now + timedelta(days=7)

    classrooms = Classrooms.objects.filter(teacher=user)
    active_classrooms = classrooms.filter(is_active=True)
    active_classroom_ids = list(active_classrooms.values_list('id', flat=True))

    assignments = Assignments.objects.filter(classroom_id__in=active_classroom_ids)
    submissions = Submissions.objects.filter(
        assignment__classroom_id__in=active_classroom_ids
    ).select_related('assignment', 'assignment__classroom', 'student')

    pending_members = ClassroomMembers.objects.filter(
        classroom_id__in=active_classroom_ids,
        status='pending',
    ).select_related('student', 'classroom').order_by('-joined_at')[:8]

    recent_submissions = submissions.order_by('-submitted_at')[:8]
    needs_review = submissions.filter(
        Q(status__in=['pending', 'running', 'error']) |
        Q(assignment__type__in=['manual_grade', 'project'], manual_score__isnull=True)
    ).order_by('-submitted_at')[:8]

    upcoming_assignments = assignments.filter(
        due_date__gte=now,
        due_date__lte=week_later,
        is_published=True,
    ).select_related('classroom', 'classroom_subject__subject').order_by('due_date')[:8]

    weak_assignments = AssignmentStatistics.objects.filter(
        assignment__classroom_id__in=active_classroom_ids,
        total_submissions__gt=0,
    ).select_related('assignment', 'assignment__classroom').order_by('pass_rate')[:5]

    pending_classrooms = classrooms.filter(status='pending').order_by('-created_at')[:5]
    pending_subjects = Subjects.objects.filter(
        created_by=user,
        status=SubjectApprovalStatus.PENDING,
    ).order_by('-created_at')[:5]

    members_count = ClassroomMembers.objects.filter(
        classroom_id__in=active_classroom_ids,
        status='approved',
    ).count()

    submissions_7d = submissions.filter(submitted_at__gte=now - timedelta(days=7)).count()

    class_summaries = active_classrooms.annotate(
        member_count=Count('classroommembers', filter=Q(classroommembers__status='approved')),
        assignment_count=Count('assignments', distinct=True),
    ).order_by('-created_at')[:6]

    context = {
        'classrooms_count': active_classrooms.count(),
        'members_count': members_count,
        'assignments_count': assignments.count(),
        'published_assignments_count': assignments.filter(is_published=True).count(),
        'submissions_7d': submissions_7d,
        'pending_members_count': ClassroomMembers.objects.filter(
            classroom_id__in=active_classroom_ids,
            status='pending',
        ).count(),
        'running_or_pending_count': submissions.filter(status__in=['pending', 'running']).count(),
        'pending_members': pending_members,
        'recent_submissions': recent_submissions,
        'needs_review': needs_review,
        'upcoming_assignments': upcoming_assignments,
        'weak_assignments': weak_assignments,
        'pending_classrooms': pending_classrooms,
        'pending_subjects': pending_subjects,
        'class_summaries': class_summaries,
    }
    return render(request, 'accounts/teacher_dashboard.html', context)


@login_required
def teacher_register_view(request):
    try:
        profile = request.user.profiles
    except Profiles.DoesNotExist:
        profile = Profiles.objects.create(id=request.user, role='student')

    if profile.role == 'teacher':
        messages.info(request, 'Bạn đã là giáo viên rồi.')
        return redirect('accounts:profile')

    # Check if already has pending registration
    existing = TeacherRegistrations.objects.filter(
        user=request.user, status='pending'
    ).first()
    if existing:
        messages.info(request, 'Bạn đã gửi đơn đăng ký giáo viên. Vui lòng chờ phê duyệt.')
        return render(request, 'accounts/teacher_register.html', {
            'form': None,
            'existing': existing,
        })

    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.user = request.user
            registration.save()
            notify_admins(
                title='Đơn đăng ký giáo viên mới',
                message=f'{request.user.get_full_name() or request.user.username} vừa gửi đơn đăng ký giáo viên.',
                link='/administration/teacher-approvals/',
                notification_type='teacher_registration_pending',
                actor=request.user,
                metadata={'registration_id': registration.pk},
            )
            messages.success(request, 'Đơn đăng ký giáo viên đã được gửi! Vui lòng chờ phê duyệt.')
            return redirect('accounts:profile')
    else:
        form = TeacherRegistrationForm()

    return render(request, 'accounts/teacher_register.html', {'form': form})
