from django.contrib.auth.models import AnonymousUser
from django.db.models import Count, Max, Q
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profiles


ROLE_ANONYMOUS = 'anonymous'
ROLE_STUDENT = 'student'
ROLE_TEACHER = 'teacher'
ROLE_ADMIN = 'admin'


def get_home_role(user):
    if isinstance(user, AnonymousUser) or not user.is_authenticated:
        return ROLE_ANONYMOUS, None

    if user.is_superuser or user.is_staff:
        return ROLE_ADMIN, None

    try:
        profile = user.profiles
    except Profiles.DoesNotExist:
        profile = Profiles.objects.create(id=user, role=ROLE_STUDENT)

    role = profile.role or ROLE_STUDENT
    if role not in {ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN}:
        role = ROLE_STUDENT
    return role, profile


def build_home_ctas(role):
    ctas = {
        ROLE_ANONYMOUS: {
            'primary_cta_label': 'Bắt đầu miễn phí',
            'primary_cta_url': reverse('accounts:register'),
            'primary_cta_icon': 'rocket_launch',
            'secondary_cta_label': 'Đăng nhập',
            'secondary_cta_url': reverse('accounts:login'),
            'secondary_cta_icon': 'login',
        },
        ROLE_STUDENT: {
            'primary_cta_label': 'Vào lớp học',
            'primary_cta_url': reverse('classrooms:classroom_list'),
            'primary_cta_icon': 'school',
            'secondary_cta_label': 'Lịch deadline',
            'secondary_cta_url': reverse('assignments:calendar'),
            'secondary_cta_icon': 'event',
        },
        ROLE_TEACHER: {
            'primary_cta_label': 'Dashboard giáo viên',
            'primary_cta_url': reverse('accounts:teacher_dashboard'),
            'primary_cta_icon': 'dashboard',
            'secondary_cta_label': 'Tạo lớp học',
            'secondary_cta_url': reverse('classrooms:create'),
            'secondary_cta_icon': 'add_circle',
        },
        ROLE_ADMIN: {
            'primary_cta_label': 'Admin dashboard',
            'primary_cta_url': reverse('administation:dashboard'),
            'primary_cta_icon': 'admin_panel_settings',
            'secondary_cta_label': 'Quản lý người dùng',
            'secondary_cta_url': reverse('administation:user_management'),
            'secondary_cta_icon': 'group',
        },
    }
    return ctas[role]


def percent(part, total):
    if not total:
        return 0
    return round(part / total * 100, 1)


def build_student_home_context(user):
    from datetime import timedelta

    from apps.assignments.models import Assignments
    from apps.classrooms.models import ClassroomMembers, Classrooms
    from apps.notifications.models import Notifications
    from apps.submissions.models import CodeDrafts, ExamSessions, Submissions

    now = timezone.now()
    week_later = now + timedelta(days=7)

    member_records = ClassroomMembers.objects.filter(
        student=user,
        status='approved',
        classroom__is_active=True,
    ).select_related('classroom')
    classroom_ids = list(member_records.values_list('classroom_id', flat=True))

    classrooms = list(
        Classrooms.objects.filter(id__in=classroom_ids, is_active=True)
        .select_related('teacher')
        .annotate(
            subject_count=Count(
                'classroom_subject_links',
                filter=Q(classroom_subject_links__is_active=True),
                distinct=True,
            ),
            assignment_count=Count(
                'assignments',
                filter=Q(assignments__is_published=True),
                distinct=True,
            ),
        )
        .order_by('name')[:4]
    )

    assignments = Assignments.objects.filter(
        classroom_id__in=classroom_ids,
        is_published=True,
    ).select_related(
        'classroom',
        'classroom_subject',
        'classroom_subject__subject',
        'classroom_subject__semester',
    )
    total_assignments = assignments.count()
    assignment_ids = list(assignments.values_list('id', flat=True))

    finished_submissions = Submissions.objects.filter(
        student=user,
        status='finished',
        assignment_id__in=assignment_ids,
    )
    completed_assignment_ids = set(
        finished_submissions.values_list('assignment_id', flat=True)
    )
    submitted_assignment_ids = set(
        Submissions.objects.filter(
            student=user,
            assignment_id__in=assignment_ids,
        ).values_list('assignment_id', flat=True)
    )
    completed_count = len(completed_assignment_ids)
    missing_count = max(total_assignments - completed_count, 0)

    # Fetch assignments to get their mode
    asg_dict = {a.pk: a for a in assignments}
    
    student_subs = list(finished_submissions)
    subs_by_asg = {}
    for sub in student_subs:
        subs_by_asg.setdefault(sub.assignment_id, []).append(sub)

    best_scores = []
    for asg_id, subs in subs_by_asg.items():
        mode = getattr(asg_dict.get(asg_id), 'score_aggregation_mode', 'best')
        scores = [(s.manual_score if s.manual_score is not None else s.total_score) or 0 for s in subs]
        
        if mode == 'best':
            val = max(scores)
        elif mode == 'latest':
            latest_sub = max(subs, key=lambda s: s.submitted_at)
            val = (latest_sub.manual_score if latest_sub.manual_score is not None else latest_sub.total_score) or 0
        elif mode == 'first':
            first_sub = min(subs, key=lambda s: s.submitted_at)
            val = (first_sub.manual_score if first_sub.manual_score is not None else first_sub.total_score) or 0
        elif mode == 'average':
            val = sum(scores) / len(scores) if scores else 0
        else:
            val = max(scores)
            
        best_scores.append({'assignment_id': asg_id, 'best': val})

    avg_score = (
        round(sum(row['best'] or 0 for row in best_scores) / len(best_scores), 1)
        if best_scores
        else 0
    )
    max_scores_by_assignment = {
        assignment_id: max_score
        for assignment_id, max_score in Assignments.objects.filter(
            id__in=assignment_ids
        ).values_list('id', 'max_score')
    }
    passed_count = 0
    for row in best_scores:
        max_score = max_scores_by_assignment.get(row['assignment_id'])
        if max_score and (row['best'] or 0) >= max_score * 0.5:
            passed_count += 1

    upcoming_assignment_rows = []
    upcoming_assignments = list(
        assignments.filter(due_date__gte=now, due_date__lte=week_later)
        .order_by('due_date', 'title')[:5]
    )
    for assignment in upcoming_assignments:
        is_completed = assignment.pk in completed_assignment_ids
        has_submission = assignment.pk in submitted_assignment_ids
        upcoming_assignment_rows.append({
            'assignment': assignment,
            'subject': (
                assignment.classroom_subject.subject
                if assignment.classroom_subject_id and assignment.classroom_subject.subject_id
                else None
            ),
            'is_completed': is_completed,
            'status_label': 'Đã nộp' if is_completed or has_submission else 'Chưa nộp',
            'status_class': (
                'bg-success-100 text-success-600'
                if is_completed
                else 'bg-warning-100 text-warning-600'
            ),
            'action_url': reverse('assignments:detail', kwargs={'pk': assignment.pk}),
        })

    deadline_counts = {timezone.localdate() + timedelta(days=offset): 0 for offset in range(7)}
    deadline_values = assignments.filter(
        due_date__gte=now,
        due_date__lt=now + timedelta(days=7),
    ).exclude(
        id__in=completed_assignment_ids,
    ).values_list('due_date', flat=True)
    for due_date in deadline_values:
        day = timezone.localtime(due_date).date()
        if day in deadline_counts:
            deadline_counts[day] += 1
    deadline_heat_strip = []
    for day, count in deadline_counts.items():
        if count >= 4:
            tone = 'danger'
        elif count:
            tone = 'warning'
        else:
            tone = 'success'
        deadline_heat_strip.append({
            'date': day,
            'day_label': 'Hôm nay' if day == timezone.localdate() else day.strftime('%d/%m'),
            'count': count,
            'tone': tone,
        })

    exam_sessions = {
        session.assignment_id: session
        for session in ExamSessions.objects.filter(
            student=user,
            assignment__classroom_id__in=classroom_ids,
        ).select_related('assignment', 'final_submission')
    }
    exam_rows = []
    exam_assignments = list(
        assignments.filter(is_exam=True)
        .filter(Q(exam_end_time__isnull=True) | Q(exam_end_time__gte=now))
        .order_by('exam_start_time', 'due_date', 'title')[:4]
    )
    for assignment in exam_assignments:
        session = exam_sessions.get(assignment.pk)
        if session and session.status in (
            ExamSessions.STATUS_SUBMITTED,
            ExamSessions.STATUS_AUTO_SUBMITTED,
        ):
            label = 'Đã nộp'
            badge_class = 'bg-success-100 text-success-600'
        elif session and session.status == ExamSessions.STATUS_RUNNING:
            label = 'Đang làm'
            badge_class = 'bg-primary-100 text-primary-700'
        elif assignment.exam_start_time and assignment.exam_start_time > now:
            label = 'Chưa mở'
            badge_class = 'bg-warning-100 text-warning-600'
        else:
            label = 'Có thể vào'
            badge_class = 'bg-primary-100 text-primary-700'
        exam_rows.append({
            'assignment': assignment,
            'session': session,
            'status_label': label,
            'status_class': badge_class,
            'action_url': reverse('submissions:exam_lobby', kwargs={'assignment_pk': assignment.pk}),
        })

    recent_submission_rows = []
    recent_submissions = Submissions.objects.filter(
        student=user,
        assignment__classroom_id__in=classroom_ids,
    ).select_related(
        'assignment',
        'assignment__classroom',
        'assignment__classroom_subject',
        'assignment__classroom_subject__subject',
    ).order_by('-submitted_at')[:5]
    for submission in recent_submissions:
        earned_score = submission.manual_score if submission.manual_score is not None else submission.total_score
        is_passed = submission.max_score and earned_score >= submission.max_score * 0.5
        recent_submission_rows.append({
            'submission': submission,
            'earned_score': earned_score,
            'is_passed': is_passed,
            'status_label': 'Đạt' if is_passed else 'Cần cải thiện',
            'status_class': (
                'bg-success-100 text-success-600'
                if is_passed
                else 'bg-warning-100 text-warning-600'
            ),
        })

    classroom_rows = []
    classroom_assignment_counts = {
        row['classroom_id']: row['total']
        for row in assignments.values('classroom_id').annotate(total=Count('id'))
    }
    classroom_completed_counts = {
        row['assignment__classroom_id']: row['total']
        for row in finished_submissions.values('assignment__classroom_id').annotate(
            total=Count('assignment_id', distinct=True)
        )
    }
    for classroom in classrooms:
        assignment_count = classroom_assignment_counts.get(classroom.pk, 0)
        completed_in_class = classroom_completed_counts.get(classroom.pk, 0)
        classroom_rows.append({
            'classroom': classroom,
            'subject_count': classroom.subject_count,
            'assignment_count': assignment_count,
            'completed_count': completed_in_class,
            'completion_rate': percent(completed_in_class, assignment_count),
        })

    notification_rows = list(
        Notifications.objects.filter(recipient=user).order_by('-created_at')[:5]
    )

    draft_rows = list(
        CodeDrafts.objects.filter(
            student=user,
            assignment__classroom_id__in=classroom_ids,
        ).select_related(
            'assignment',
            'assignment__classroom',
        ).order_by('-last_saved_at')[:3]
    )

    continue_learning = None
    if draft_rows:
        latest_draft = draft_rows[0]
        continue_learning = {
            'label': 'Tiếp tục bản nháp',
            'title': latest_draft.assignment.title,
            'meta': f'{latest_draft.assignment.classroom.name} · {latest_draft.language or "code"} · lưu {latest_draft.last_saved_at.strftime("%d/%m %H:%M")}',
            'url': reverse('assignments:detail', kwargs={'pk': latest_draft.assignment.pk}),
            'icon': 'edit_note',
            'button_label': 'Khôi phục bản nháp',
        }
    elif upcoming_assignment_rows:
        next_assignment = upcoming_assignment_rows[0]
        continue_learning = {
            'label': 'Tiếp tục học',
            'title': next_assignment['assignment'].title,
            'meta': f'{next_assignment["assignment"].classroom.name} · hạn {timezone.localtime(next_assignment["assignment"].due_date).strftime("%d/%m %H:%M")}',
            'url': next_assignment['action_url'],
            'icon': 'play_arrow',
            'button_label': 'Làm bài',
        }
    elif recent_submission_rows:
        latest_submission = recent_submission_rows[0]['submission']
        continue_learning = {
            'label': 'Xem lại bài vừa nộp',
            'title': latest_submission.assignment.title,
            'meta': f'{latest_submission.assignment.classroom.name} · nộp {latest_submission.submitted_at.strftime("%d/%m %H:%M")}',
            'url': reverse('submissions:detail', kwargs={'pk': latest_submission.pk}),
            'icon': 'fact_check',
            'button_label': 'Xem kết quả',
        }

    subject_shortcut_row = (
        assignments.exclude(id__in=completed_assignment_ids)
        .filter(classroom_subject__isnull=False, classroom_subject__is_active=True)
        .values(
            'classroom_id',
            'classroom__name',
            'classroom_subject_id',
            'classroom_subject__subject__code',
            'classroom_subject__subject__name',
        )
        .annotate(total=Count('id'))
        .order_by('-total', 'classroom__name', 'classroom_subject__subject__code')
        .first()
    )
    subject_shortcut = None
    if subject_shortcut_row:
        subject_shortcut = {
            'classroom_name': subject_shortcut_row['classroom__name'],
            'subject_code': subject_shortcut_row['classroom_subject__subject__code'],
            'subject_name': subject_shortcut_row['classroom_subject__subject__name'],
            'unfinished_count': subject_shortcut_row['total'],
            'url': reverse('classrooms:subject_detail', kwargs={
                'pk': subject_shortcut_row['classroom_id'],
                'link_pk': subject_shortcut_row['classroom_subject_id'],
            }),
        }

    upcoming_count = assignments.filter(
        due_date__gte=now,
        due_date__lte=week_later,
    ).exclude(id__in=completed_assignment_ids).count()

    return {
        'home_summary': {
            'classrooms_count': len(classroom_ids),
            'total_assignments': total_assignments,
            'completed_count': completed_count,
            'missing_count': missing_count,
            'upcoming_count': upcoming_count,
            'avg_score': avg_score,
            'pass_rate': percent(passed_count, completed_count),
            'completion_rate': percent(completed_count, total_assignments),
        },
        'home_sections': {
            'upcoming_assignments': upcoming_assignment_rows,
            'exam_assignments': exam_rows,
            'recent_submissions': recent_submission_rows,
            'classrooms': classroom_rows,
            'notifications': notification_rows,
            'drafts': draft_rows,
            'continue_learning': continue_learning,
            'deadline_heat_strip': deadline_heat_strip,
            'subject_shortcut': subject_shortcut,
        },
    }


def build_teacher_home_context(user):
    from datetime import timedelta

    from apps.assignments.models import AssignmentStatistics, Assignments
    from apps.classrooms.models import ClassroomMembers, ClassroomSubjects, Classrooms
    from apps.submissions.models import ExamSessions, Submissions

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    active_classrooms = Classrooms.objects.filter(
        teacher=user,
        is_active=True,
    ).order_by('name')
    active_classroom_ids = list(active_classrooms.values_list('id', flat=True))
    first_classroom_id = active_classroom_ids[0] if active_classroom_ids else None

    assignments = Assignments.objects.filter(classroom_id__in=active_classroom_ids)
    submissions = Submissions.objects.filter(
        assignment__classroom_id__in=active_classroom_ids,
    ).select_related(
        'assignment',
        'assignment__classroom',
        'student',
    )

    pending_members = list(
        ClassroomMembers.objects.filter(
            classroom_id__in=active_classroom_ids,
            status='pending',
        ).select_related('student', 'classroom').order_by('-joined_at')[:6]
    )
    pending_members_count = ClassroomMembers.objects.filter(
        classroom_id__in=active_classroom_ids,
        status='pending',
    ).count()

    needs_review = list(
        submissions.filter(
            Q(status__in=['pending', 'running', 'error']) |
            Q(assignment__type__in=['manual_grade', 'project'], manual_score__isnull=True)
        ).order_by('-submitted_at')[:6]
    )

    running_exam_sessions = list(
        ExamSessions.objects.filter(
            assignment__classroom_id__in=active_classroom_ids,
            status=ExamSessions.STATUS_RUNNING,
        ).select_related(
            'assignment',
            'assignment__classroom',
            'student',
        ).order_by('-violation_count', 'ends_at')[:6]
    )
    exam_warning_sessions = list(
        ExamSessions.objects.filter(
            assignment__classroom_id__in=active_classroom_ids,
            violation_count__gt=0,
        ).select_related(
            'assignment',
            'assignment__classroom',
            'student',
        ).order_by('-violation_count', '-updated_at')[:5]
    )

    classroom_rows = list(
        active_classrooms.annotate(
            member_count=Count('classroommembers', filter=Q(classroommembers__status='approved'), distinct=True),
            subject_count=Count('classroom_subject_links', filter=Q(classroom_subject_links__is_active=True), distinct=True),
            assignment_count=Count('assignments', distinct=True),
        )[:6]
    )

    recent_finished = list(
        submissions.filter(
            submitted_at__gte=seven_days_ago,
            status='finished',
        ).order_by('-submitted_at')[:100]
    )
    submissions_7d_count = submissions.filter(submitted_at__gte=seven_days_ago).count()
    score_values = [
        submission.manual_score if submission.manual_score is not None else submission.total_score
        for submission in recent_finished
    ]
    avg_score_7d = round(sum(score_values) / len(score_values), 1) if score_values else 0
    passed_count = sum(
        1
        for submission, score in zip(recent_finished, score_values)
        if submission.max_score and score >= submission.max_score * 0.5
    )
    pass_rate_7d = percent(passed_count, len(recent_finished))

    weak_assignments = list(
        AssignmentStatistics.objects.filter(
            assignment__classroom_id__in=active_classroom_ids,
            total_submissions__gt=0,
        ).select_related('assignment', 'assignment__classroom').order_by('pass_rate')[:4]
    )

    if first_classroom_id:
        create_assignment_url = reverse('assignments:create', kwargs={'classroom_pk': first_classroom_id})
        create_exam_url = f'{create_assignment_url}?exam=1'
    else:
        create_assignment_url = reverse('classrooms:classroom_list')
        create_exam_url = reverse('classrooms:classroom_list')

    grade_queue_url = (
        reverse('submissions:grade', kwargs={'pk': needs_review[0].pk})
        if needs_review
        else reverse('classrooms:classroom_list')
    )
    subject_setup_url = (
        reverse('classrooms:subjects', kwargs={'pk': first_classroom_id})
        if first_classroom_id
        else reverse('classrooms:classroom_list')
    )
    has_classroom = bool(active_classroom_ids)
    has_subject_link = ClassroomSubjects.objects.filter(
        classroom_id__in=active_classroom_ids,
        is_active=True,
    ).exists()
    has_assignment = assignments.exists()
    has_published_assignment = assignments.filter(is_published=True).exists()
    has_submission = submissions.exists()
    teacher_checklist = [
        {
            'label': 'Tạo lớp học',
            'done': has_classroom,
            'url': reverse('classrooms:create'),
            'icon': 'add_circle',
        },
        {
            'label': 'Gán môn cho lớp',
            'done': has_subject_link,
            'url': subject_setup_url,
            'icon': 'menu_book',
        },
        {
            'label': 'Tạo bài tập',
            'done': has_assignment,
            'url': create_assignment_url,
            'icon': 'assignment_add',
        },
        {
            'label': 'Công bố bài',
            'done': has_published_assignment,
            'url': reverse('classrooms:classroom_list'),
            'icon': 'publish',
        },
        {
            'label': 'Xem bài nộp',
            'done': has_submission,
            'url': reverse('accounts:teacher_dashboard'),
            'icon': 'fact_check',
        },
    ]

    return {
        'home_summary': {
            'classrooms_count': active_classrooms.count(),
            'published_assignments_count': assignments.filter(is_published=True).count(),
            'assignments_count': assignments.count(),
            'submissions_7d': submissions_7d_count,
            'pending_members_count': pending_members_count,
            'needs_review_count': len(needs_review),
            'running_exams_count': len(running_exam_sessions),
            'exam_warning_count': len(exam_warning_sessions),
            'members_count': ClassroomMembers.objects.filter(
                classroom_id__in=active_classroom_ids,
                status='approved',
            ).count(),
            'pass_rate_7d': pass_rate_7d,
            'avg_score_7d': avg_score_7d,
        },
        'home_sections': {
            'classrooms': classroom_rows,
            'needs_review': needs_review,
            'running_exam_sessions': running_exam_sessions,
            'exam_warning_sessions': exam_warning_sessions,
            'pending_members': pending_members,
            'weak_assignments': weak_assignments,
            'teacher_checklist': teacher_checklist,
        },
        'teacher_actions': {
            'create_assignment_url': create_assignment_url,
            'create_exam_url': create_exam_url,
            'grade_queue_url': grade_queue_url,
        },
    }


def build_admin_home_context():
    from datetime import timedelta

    from django.contrib.auth.models import User

    from apps.accounts.models import Profiles, TeacherRegistrations
    from apps.administation.models import ActivityLogs, SandboxConfigs, ServerMetrics, SystemSettings
    from apps.administation.utils import get_int_setting
    from apps.assignments.models import Assignments
    from apps.classrooms.models import (
        ClassroomApprovalStatus,
        Classrooms,
        SubjectApprovalStatus,
        Subjects,
    )
    from apps.submissions.models import ExamSessions, Submissions

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    pending_teachers = TeacherRegistrations.objects.filter(status='pending')
    pending_classrooms = Classrooms.objects.filter(status=ClassroomApprovalStatus.PENDING)
    pending_subjects = Subjects.objects.filter(status=SubjectApprovalStatus.PENDING)
    warning_exam_sessions = ExamSessions.objects.filter(violation_count__gt=0)

    zombie_threshold_min = get_int_setting(
        'sandbox.zombie_threshold_minutes',
        default=5,
        minimum=1,
        maximum=1440,
    )
    queue_submissions = Submissions.objects.filter(status__in=['pending', 'running'])
    zombie_count = queue_submissions.filter(
        submitted_at__lt=now - timedelta(minutes=zombie_threshold_min)
    ).count()

    total_users = User.objects.count()
    total_classrooms = Classrooms.objects.count()
    total_subjects = Subjects.objects.count()
    teacher_registrations_count = TeacherRegistrations.objects.count()
    total_teachers = Profiles.objects.filter(role='teacher').count()
    total_students = Profiles.objects.filter(role='student').count()

    approval_items = [
        {
            'title': 'Giáo viên chờ duyệt',
            'total': pending_teachers.count(),
            'description': 'Đơn đăng ký giáo viên mới',
            'icon': 'person_check',
            'url': reverse('administation:teacher_approvals'),
            'tone': 'warning',
        },
        {
            'title': 'Lớp học chờ duyệt',
            'total': pending_classrooms.count(),
            'description': 'Lớp mới cần kiểm tra',
            'icon': 'school',
            'url': reverse('administation:classroom_management'),
            'tone': 'primary',
        },
        {
            'title': 'Môn học chờ duyệt',
            'total': pending_subjects.count(),
            'description': 'Môn do giáo viên đề xuất',
            'icon': 'menu_book',
            'url': reverse('administation:subject_approvals'),
            'tone': 'primary',
        },
        {
            'title': 'Phiên thi có cảnh báo',
            'total': warning_exam_sessions.count(),
            'description': 'Session có violation_count > 0',
            'icon': 'gpp_maybe',
            'url': reverse('administation:exam_events'),
            'tone': 'danger',
        },
    ]

    latest_metrics = ServerMetrics.objects.order_by('-recorded_at').first()
    recent_logs = list(
        ActivityLogs.objects.select_related('user').order_by('-created_at')[:6]
    )
    pending_approval_total = (
        approval_items[0]['total'] + approval_items[1]['total'] + approval_items[2]['total']
    )
    admin_health_checklist = [
        {
            'label': 'Xử lý hàng chờ duyệt',
            'done': pending_approval_total == 0,
            'total': pending_approval_total,
            'url': reverse('administation:dashboard'),
            'icon': 'approval',
        },
        {
            'label': 'Kiểm tra zombie task',
            'done': zombie_count == 0,
            'total': zombie_count,
            'url': reverse('administation:sandbox_monitor'),
            'icon': 'memory',
        },
        {
            'label': 'Rà soát cảnh báo thi',
            'done': approval_items[3]['total'] == 0,
            'total': approval_items[3]['total'],
            'url': reverse('administation:exam_events'),
            'icon': 'gpp_maybe',
        },
        {
            'label': 'Cấu hình hệ thống',
            'done': SystemSettings.objects.exists(),
            'total': SystemSettings.objects.count(),
            'url': reverse('administation:system_settings'),
            'icon': 'settings',
        },
    ]

    return {
        'home_summary': {
            'total_users': total_users,
            'total_teachers': total_teachers,
            'total_students': total_students,
            'total_classrooms': total_classrooms,
            'total_subjects': total_subjects,
            'teacher_registrations_count': teacher_registrations_count,
            'pending_teachers_count': approval_items[0]['total'],
            'pending_classrooms_count': approval_items[1]['total'],
            'pending_subjects_count': approval_items[2]['total'],
            'exam_warning_count': approval_items[3]['total'],
            'new_users_7d': User.objects.filter(date_joined__gte=seven_days_ago).count(),
            'submissions_7d': Submissions.objects.filter(submitted_at__gte=seven_days_ago).count(),
            'new_classrooms_30d': Classrooms.objects.filter(created_at__gte=thirty_days_ago).count(),
            'queue_count': queue_submissions.count(),
            'zombie_count': zombie_count,
            'active_sandboxes': SandboxConfigs.objects.filter(is_active=True).count(),
            'exam_assignments_count': Assignments.objects.filter(is_exam=True).count(),
        },
        'home_sections': {
            'approval_items': approval_items,
            'pending_teachers': list(pending_teachers.select_related('user').order_by('-created_at')[:4]),
            'pending_classrooms': list(pending_classrooms.select_related('teacher').order_by('-created_at')[:4]),
            'pending_subjects': list(pending_subjects.select_related('created_by').order_by('-created_at')[:4]),
            'warning_exam_sessions': list(
                warning_exam_sessions.select_related(
                    'student',
                    'assignment',
                    'assignment__classroom',
                ).order_by('-violation_count', '-updated_at')[:5]
            ),
            'latest_metrics': latest_metrics,
            'recent_logs': recent_logs,
            'admin_health_checklist': admin_health_checklist,
        },
    }


def build_base_home_context(request):
    role, profile = get_home_role(request.user)
    context = {
        'home_role': role,
        'home_profile': profile,
        'is_role_home': role != ROLE_ANONYMOUS,
        'role_labels': {
            ROLE_ANONYMOUS: 'Khách',
            ROLE_STUDENT: 'Học sinh',
            ROLE_TEACHER: 'Giáo viên',
            ROLE_ADMIN: 'Admin',
        },
        'home_summary': {},
        'home_sections': {},
    }
    context.update(build_home_ctas(role))
    if role == ROLE_STUDENT:
        context.update(build_student_home_context(request.user))
    elif role == ROLE_TEACHER:
        context.update(build_teacher_home_context(request.user))
    elif role == ROLE_ADMIN:
        context.update(build_admin_home_context())
    return context


def home_view(request):
    return render(request, 'home.html', build_base_home_context(request))
