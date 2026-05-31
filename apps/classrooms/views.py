import string
import random
import re
import unicodedata
import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from django.db import IntegrityError, transaction
from django.http import JsonResponse, HttpResponse, Http404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import teacher_required, admin_required
from apps.administation.utils import csv_filename, csv_query_context
from apps.notifications.services import notify_admins, notify_user, notify_users
from .models import Classrooms, ClassroomMembers, Announcements, Leaderboard, Subjects, SubjectApprovalStatus, ClassroomSubjects, Semesters
from .forms import ClassroomForm, JoinClassroomForm, MemberImportForm, AnnouncementForm, SubjectForm, ClassroomSubjectForm, SemesterForm


def _generate_invite_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=8))
        if not Classrooms.objects.filter(invite_code=code).exists():
            return code


_SUBJECT_CODE_PATTERN_CACHE = {}


def _generate_subject_code(prefix='MH', width=3):
    """Sinh mã môn học tự tăng dạng MH001, MH002, ... dựa trên DB.

    - Chỉ xét các code có dạng ``{prefix}\\d+`` để tìm số lớn nhất.
    - Nếu chưa có record nào phù hợp -> bắt đầu từ 1.
    - Đảm bảo không trùng tại thời điểm gọi (race condition được xử lý
      bằng retry trên IntegrityError ở callsite save()).
    """
    pattern = _SUBJECT_CODE_PATTERN_CACHE.get(prefix)
    if pattern is None:
        pattern = re.compile(rf'^{re.escape(prefix)}(\d+)$')
        _SUBJECT_CODE_PATTERN_CACHE[prefix] = pattern
    max_num = 0
    for code in Subjects.objects.filter(code__startswith=prefix).values_list('code', flat=True):
        m = pattern.match(code)
        if m:
            try:
                n = int(m.group(1))
                if n > max_num:
                    max_num = n
            except ValueError:
                continue
    next_num = max_num + 1
    code = f'{prefix}{next_num:0{width}d}'
    # Phòng ngừa trùng (hiếm) — tăng cho đến khi không trùng
    while Subjects.objects.filter(code=code).exists():
        next_num += 1
        code = f'{prefix}{next_num:0{width}d}'
    return code


def _normalize_subject_name(name):
    """Chuẩn hóa tên môn để so sánh trùng lặp (bỏ dấu, lowercase, trim whitespace)."""
    if not name:
        return ''
    # NFKD + bỏ combining marks
    s = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    # Thay đ -> d
    s = s.replace('đ', 'd').replace('Đ', 'd')
    s = s.lower().strip()
    # Gộp khoảng trắng liên tiếp
    s = re.sub(r'\s+', ' ', s)
    return s


def _is_admin_user(user):
    if user.is_superuser:
        return True
    return _get_user_role(user) == 'admin'


def _is_classroom_teacher(user, classroom):
    if _is_admin_user(user):
        return True
    return classroom.teacher == user


def _is_classroom_member(user, classroom):
    if _is_admin_user(user):
        return True
    return ClassroomMembers.objects.filter(
        classroom=classroom, student=user, status='approved'
    ).exists()


def _classroom_join_requires_approval(classroom):
    # Mặc định là True nếu chưa được thiết lập trong settings
    return bool((classroom.settings or {}).get('join_requires_approval', True))


def _apply_classroom_form_settings(classroom, form):
    settings = classroom.settings or {}
    settings['join_requires_approval'] = bool(form.cleaned_data.get('join_requires_approval'))
    classroom.settings = settings
    classroom.save(update_fields=['settings'])


def _get_user_role(user):
    from apps.accounts.models import Profiles
    try:
        return user.profiles.role
    except (AttributeError, Profiles.DoesNotExist):
        return 'student'


def _submission_grade_value(submission):
    if submission is None:
        return None
    if submission.manual_score is not None:
        return submission.manual_score
    return submission.total_score


def _assignment_mode_meta(assignment):
    mode = getattr(assignment, 'submission_mode', 'code') or 'code'
    return {
        'mode': mode,
        'label': {
            'code': 'Lập trình',
            'file': 'Nộp file',
            'quiz': 'Trắc nghiệm',
        }.get(mode, mode),
        'icon': {
            'code': 'code',
            'file': 'upload_file',
            'quiz': 'quiz',
        }.get(mode, 'assignment'),
    }


def _csv_response(filename):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    return response


def _build_gradebook_data(classroom, request):
    from apps.assignments.models import Assignments
    from apps.submissions.models import Submissions

    cs_filter = request.GET.get('cs', '').strip()
    sem_filter = request.GET.get('semester', '').strip()
    published_filter = request.GET.get('published', 'all').strip()
    status_filter = request.GET.get('status', 'all').strip()

    classroom_subjects = ClassroomSubjects.objects.filter(
        classroom=classroom,
        is_active=True,
        subject__is_active=True,
    ).select_related('subject', 'semester').order_by(
        '-semester__is_current', '-semester__start_date', 'subject__code'
    )

    assignments = Assignments.objects.filter(classroom=classroom).select_related(
        'classroom_subject', 'classroom_subject__subject', 'classroom_subject__semester'
    )
    if published_filter == 'published':
        assignments = assignments.filter(is_published=True)
    elif published_filter == 'draft':
        assignments = assignments.filter(is_published=False)

    if cs_filter == 'none':
        assignments = assignments.filter(classroom_subject__isnull=True)
    elif cs_filter.isdigit():
        assignments = assignments.filter(classroom_subject_id=int(cs_filter))

    if sem_filter == 'none':
        assignments = assignments.filter(classroom_subject__semester__isnull=True)
    elif sem_filter == 'current':
        current_semester = Semesters.objects.filter(is_current=True, is_active=True).first()
        if current_semester:
            assignments = assignments.filter(classroom_subject__semester=current_semester)
    elif sem_filter.isdigit():
        assignments = assignments.filter(classroom_subject__semester_id=int(sem_filter))

    assignments = list(assignments.order_by('due_date', 'created_at', 'id'))
    assignment_ids = [assignment.pk for assignment in assignments]

    members = list(ClassroomMembers.objects.filter(
        classroom=classroom,
        status='approved',
    ).select_related('student').order_by(
        'student__last_name', 'student__first_name', 'student__username'
    ))
    student_ids = [member.student_id for member in members if member.student_id]

    submissions = Submissions.objects.filter(
        assignment_id__in=assignment_ids,
        student_id__in=student_ids,
    ).select_related('assignment', 'student').order_by('-submitted_at')

    grouped = {}
    for submission in submissions:
        key = (submission.student_id, submission.assignment_id)
        bucket = grouped.setdefault(key, {
            'best': None,
            'latest': None,
            'attempts': 0,
            'has_late': False,
        })
        bucket['attempts'] += 1
        bucket['has_late'] = bucket['has_late'] or submission.is_late
        if bucket['latest'] is None or submission.submitted_at > bucket['latest'].submitted_at:
            bucket['latest'] = submission
        if submission.status == 'finished':
            best = bucket['best']
            current_score = _submission_grade_value(submission) or 0
            best_score = _submission_grade_value(best) or 0
            if best is None or current_score > best_score:
                bucket['best'] = submission

    rows = []
    submitted_cells = 0
    total_score_sum = 0
    total_score_count = 0

    for member in members:
        cells = []
        completed_count = 0
        student_score_sum = 0
        student_score_count = 0
        late_count = 0

        for assignment in assignments:
            bucket = grouped.get((member.student_id, assignment.pk), {})
            best = bucket.get('best')
            latest = bucket.get('latest')
            display_submission = best or latest
            score = _submission_grade_value(best)
            percent = None
            if score is not None and assignment.max_score:
                percent = round(score / assignment.max_score * 100, 1)

            if best:
                completed_count += 1
                submitted_cells += 1
                student_score_sum += score or 0
                student_score_count += 1
                total_score_sum += score or 0
                total_score_count += 1
            elif latest:
                submitted_cells += 1

            if bucket.get('has_late'):
                late_count += 1

            cell_status = 'missing'
            if best:
                cell_status = 'finished'
            elif latest:
                cell_status = latest.status

            cells.append({
                'assignment': assignment,
                'mode_meta': _assignment_mode_meta(assignment),
                'submission': display_submission,
                'score': score,
                'has_score': score is not None,
                'percent': percent,
                'has_percent': percent is not None,
                'status': cell_status,
                'attempts': bucket.get('attempts', 0),
                'is_late': bucket.get('has_late', False),
            })

        if status_filter == 'missing' and completed_count == len(assignments):
            continue
        if status_filter == 'completed' and completed_count == 0:
            continue
        if status_filter == 'late' and late_count == 0:
            continue

        completion_rate = round(completed_count / len(assignments) * 100, 1) if assignments else 0
        avg_score = round(student_score_sum / student_score_count, 1) if student_score_count else None

        rows.append({
            'member': member,
            'student': member.student,
            'cells': cells,
            'completed_count': completed_count,
            'late_count': late_count,
            'completion_rate': completion_rate,
            'avg_score': avg_score,
        })

    class_avg_score = round(total_score_sum / total_score_count, 1) if total_score_count else 0
    total_cells = len(assignments) * len(rows)
    overall_completion_rate = round(submitted_cells / total_cells * 100, 1) if total_cells else 0
    semesters = Semesters.objects.filter(is_active=True).order_by('-is_current', '-start_date', 'code')

    csv_context = csv_query_context(request)
    has_filters = csv_context['has_active_filters']

    return {
        'classroom': classroom,
        'assignments': assignments,
        'rows': rows,
        'classroom_subjects': classroom_subjects,
        'semesters': semesters,
        'cs_filter': cs_filter,
        'sem_filter': sem_filter,
        'published_filter': published_filter,
        'status_filter': status_filter,
        'members_count': len(rows),
        'assignments_count': len(assignments),
        'submitted_cells': submitted_cells,
        'overall_completion_rate': overall_completion_rate,
        'class_avg_score': class_avg_score,
        'querystring': csv_context['csv_query_string'],
        'csv_items': [
            {
                'url': reverse('classrooms:gradebook_export', kwargs={'pk': classroom.pk}),
                'type': '',
                'icon': 'filter_alt',
                'label': 'Xuất sổ điểm theo lọc hiện tại' if has_filters else 'Xuất toàn bộ sổ điểm',
                'primary': True,
            },
            {
                'url': reverse('classrooms:members_export', kwargs={'pk': classroom.pk}),
                'type': '',
                'icon': 'groups',
                'label': 'Xuất học sinh theo lọc hiện tại' if has_filters else 'Xuất danh sách học sinh',
                'primary': False,
            },
            {
                'url': reverse('classrooms:gradebook_missing_export', kwargs={'pk': classroom.pk}),
                'type': '',
                'icon': 'assignment_late',
                'label': 'Xuất bài còn thiếu theo lọc hiện tại' if has_filters else 'Xuất bài còn thiếu',
                'primary': False,
            },
        ],
        **csv_context,
    }


@login_required
def classroom_list_view(request):
    role = _get_user_role(request.user)
    query = request.GET.get('q', '').strip()

    # Lớp user đang có quan hệ (teacher sở hữu hoặc student đã approved)
    if role == 'teacher':
        # Giáo viên được xem cả lớp đã duyệt và lớp đang chờ duyệt của mình
        my_classrooms = Classrooms.objects.filter(teacher=request.user)
        joined_ids = set(my_classrooms.values_list('id', flat=True))
        pending_ids = set()
    else:
        approved_ids = set(ClassroomMembers.objects.filter(
            student=request.user, status='approved'
        ).values_list('classroom_id', flat=True))
        pending_ids = set(ClassroomMembers.objects.filter(
            student=request.user, status='pending'
        ).values_list('classroom_id', flat=True))
        # Học sinh chỉ được thấy lớp đã duyệt và active
        my_classrooms = Classrooms.objects.filter(id__in=approved_ids, is_active=True)
        joined_ids = approved_ids

    if query:
        my_classrooms = my_classrooms.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    my_classrooms = my_classrooms.annotate(
        member_count=Count('classroommembers', filter=Q(classroommembers__status='approved'))
    ).order_by('-created_at')
    my_classrooms = my_classrooms.annotate(
        subject_count=Count(
            'classroom_subject_links',
            filter=Q(
                classroom_subject_links__is_active=True,
                classroom_subject_links__subject__is_active=True,
                classroom_subject_links__subject__status=SubjectApprovalStatus.APPROVED,
            ),
            distinct=True,
        )
    )

    # Lớp khám phá (không phải lớp của mình / chưa tham gia)
    # Teacher chỉ thấy lớp của mình, sinh viên thấy tất cả lớp có thể tham gia
    discover_classrooms = []
    if role != 'teacher':
        discover_qs = Classrooms.objects.filter(is_active=True).exclude(
            id__in=joined_ids
        ).exclude(teacher=request.user)
        if query:
            discover_qs = discover_qs.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        discover_classrooms = discover_qs.select_related('teacher').annotate(
            member_count=Count('classroommembers', filter=Q(classroommembers__status='approved'))
        ).annotate(
            subject_count=Count(
                'classroom_subject_links',
                filter=Q(
                    classroom_subject_links__is_active=True,
                    classroom_subject_links__subject__is_active=True,
                    classroom_subject_links__subject__status=SubjectApprovalStatus.APPROVED,
                ),
                distinct=True,
            )
        ).order_by('-created_at')[:24]

    context = {
        'classrooms': my_classrooms,
        'discover_classrooms': discover_classrooms,
        'pending_ids': pending_ids,
        'role': role,
        'query': query,
        'breadcrumbs': [{'label': 'Lớp học'}],
    }
    return render(request, 'classrooms/list.html', context)


@login_required
def classroom_detail_view(request, pk):
    # Lấy lớp học (không bắt buộc is_active=True để teacher vào chỉnh sửa trước)
    classroom = get_object_or_404(Classrooms, pk=pk)
    is_teacher = _is_classroom_teacher(request.user, classroom)
    
    # Nếu không phải giáo viên của lớp, yêu cầu lớp phải active
    if not is_teacher and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    members = ClassroomMembers.objects.filter(
        classroom=classroom, status='approved'
    ).select_related('student')

    pending_members = []
    if is_teacher:
        pending_members = ClassroomMembers.objects.filter(
            classroom=classroom, status='pending'
        ).select_related('student')

    announcements = Announcements.objects.filter(
        classroom=classroom
    ).order_by('-is_pinned', '-created_at')[:10]

    subject_links_qs = ClassroomSubjects.objects.filter(
        classroom=classroom,
        is_active=True,
        subject__is_active=True,
    ).select_related(
        'subject', 'subject__created_by', 'subject__approved_by', 'assigned_by', 'semester'
    ).prefetch_related('subject__languages').order_by('-semester__is_current', '-semester__start_date', 'subject__status', 'subject__code')
    if not is_teacher:
        subject_links_qs = subject_links_qs.filter(subject__status=SubjectApprovalStatus.APPROVED)
        subject_links_qs = subject_links_qs.annotate(assignment_count=Count('assignments', filter=Q(assignments__is_published=True), distinct=True))
    else:
        subject_links_qs = subject_links_qs.annotate(assignment_count=Count('assignments', distinct=True))

    from apps.assignments.models import Assignments
    assignments = Assignments.objects.filter(
        classroom=classroom, is_published=True
    ).order_by('-created_at')[:10]

    context = {
        'classroom': classroom,
        'is_teacher': is_teacher,
        'is_member': is_member,
        'can_manage_subjects': _can_manage_subjects(request.user, classroom),
        'members': members,
        'pending_members': pending_members,
        'announcements': announcements,
        'subject_links': subject_links_qs,
        'assignments': assignments,
        'member_count': members.count(),
        'assign_form': ClassroomSubjectForm() if is_teacher else None,
        'breadcrumbs': [
            {'label': 'Lớp học', 'url': reverse('classrooms:classroom_list')},
            {'label': classroom.name},
        ],
    }
    return render(request, 'classrooms/detail.html', context)


@login_required
def gradebook_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xem sổ điểm lớp này.')
        return redirect('classrooms:classroom_list')

    context = _build_gradebook_data(classroom, request)
    context.update({
        'is_teacher': True,
    })
    return render(request, 'classrooms/gradebook.html', context)


@login_required
def gradebook_export_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất sổ điểm lớp này.')
        return redirect('classrooms:classroom_list')

    data = _build_gradebook_data(classroom, request)
    safe_name = re.sub(r'[^A-Za-z0-9_-]+', '-', classroom.name).strip('-') or f'classroom-{classroom.pk}'
    response = _csv_response(csv_filename(
        f'gradebook_{safe_name}',
        filtered=bool(data['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))

    writer = csv.writer(response)
    header = [
        'Username',
        'Ho ten',
        'Email',
        'Da hoan thanh',
        'Ti le hoan thanh',
        'Diem trung binh',
        'Bai nop tre',
    ]
    header.extend([
        f"{assignment.title} [{_assignment_mode_meta(assignment)['label']}] ({assignment.max_score:g} diem)"
        for assignment in data['assignments']
    ])
    writer.writerow(header)

    for row in data['rows']:
        student = row['student']
        values = [
            student.username,
            student.get_full_name() or student.username,
            student.email,
            f"{row['completed_count']}/{data['assignments_count']}",
            f"{row['completion_rate']}%",
            row['avg_score'] if row['avg_score'] is not None else '',
            row['late_count'],
        ]
        for cell in row['cells']:
            assignment = cell['assignment']
            if cell['has_score']:
                value = f"{cell['score']:g}/{assignment.max_score:g}"
                if cell['is_late']:
                    value += ' (nop tre)'
            elif cell['submission']:
                value = cell['status']
                if cell['is_late']:
                    value += ' (nop tre)'
            else:
                value = ''
            values.append(value)
        writer.writerow(values)

    return response


@login_required
def gradebook_missing_export_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất danh sách thiếu bài lớp này.')
        return redirect('classrooms:classroom_list')

    data = _build_gradebook_data(classroom, request)
    safe_name = re.sub(r'[^A-Za-z0-9_-]+', '-', classroom.name).strip('-') or f'classroom-{classroom.pk}'
    response = _csv_response(csv_filename(
        f'gradebook_{safe_name}',
        'missing',
        filtered=bool(data['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))
    writer = csv.writer(response)
    writer.writerow([
        'Username', 'Họ tên', 'Email', 'Bài tập', 'Loại bài', 'Môn học', 'Học kỳ',
        'Deadline', 'Công bố', 'Trạng thái ô điểm',
    ])

    for row in data['rows']:
        student = row['student']
        for cell in row['cells']:
            if cell['submission']:
                continue
            assignment = cell['assignment']
            subject_link = assignment.classroom_subject
            writer.writerow([
                student.username,
                student.get_full_name() or student.username,
                student.email,
                assignment.title,
                _assignment_mode_meta(assignment)['label'],
                subject_link.subject.name if subject_link and subject_link.subject else 'Chưa gắn môn',
                subject_link.semester.name if subject_link and subject_link.semester else '',
                timezone.localtime(assignment.due_date).strftime('%d/%m/%Y %H:%M') if assignment.due_date else '',
                'Có' if assignment.is_published else 'Không',
                cell['status'],
            ])
    return response


@login_required
def classroom_members_export_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xuất danh sách học sinh lớp này.')
        return redirect('classrooms:classroom_list')

    data = _build_gradebook_data(classroom, request)
    safe_name = re.sub(r'[^A-Za-z0-9_-]+', '-', classroom.name).strip('-') or f'classroom-{classroom.pk}'
    response = _csv_response(csv_filename(
        f'gradebook_{safe_name}',
        'members',
        filtered=bool(data['csv_query_string']),
        timestamp=timezone.now().strftime('%Y%m%d_%H%M'),
    ))
    writer = csv.writer(response)
    writer.writerow([
        'Username', 'Họ tên', 'Email', 'Ngày tham gia', 'Hoàn thành',
        'Tỉ lệ hoàn thành', 'Điểm trung bình', 'Bài nộp trễ',
    ])

    for row in data['rows']:
        member = row['member']
        student = row['student']
        writer.writerow([
            student.username,
            student.get_full_name() or student.username,
            student.email,
            timezone.localtime(member.joined_at).strftime('%d/%m/%Y %H:%M') if member.joined_at else '',
            f"{row['completed_count']}/{data['assignments_count']}",
            f"{row['completion_rate']}%",
            row['avg_score'] if row['avg_score'] is not None else '',
            row['late_count'],
        ])
    return response


def _decode_member_import_file(uploaded_file):
    try:
        raw = uploaded_file.read()
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('File CSV cần dùng encoding UTF-8.') from exc


def _read_member_import_rows(uploaded_file):
    content = _decode_member_import_file(uploaded_file)
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError('File CSV không có header.')

    normalized_fields = {
        (field or '').strip().lower(): field
        for field in reader.fieldnames
    }
    if 'username' not in normalized_fields and 'email' not in normalized_fields:
        raise ValueError('File CSV cần có ít nhất một cột username hoặc email.')

    rows = []
    for index, raw_row in enumerate(reader, start=2):
        username_key = normalized_fields.get('username')
        email_key = normalized_fields.get('email')
        full_name_key = normalized_fields.get('full_name') or normalized_fields.get('name') or normalized_fields.get('ho_ten')
        username = (raw_row.get(username_key) or '').strip() if username_key else ''
        email = (raw_row.get(email_key) or '').strip().lower() if email_key else ''
        full_name = (raw_row.get(full_name_key) or '').strip() if full_name_key else ''
        if not username and not email and not full_name:
            continue
        rows.append({
            'line': index,
            'username': username,
            'email': email,
            'full_name': full_name,
        })

    if not rows:
        raise ValueError('File CSV không có dòng dữ liệu nào.')
    if len(rows) > 500:
        raise ValueError('Mỗi lần chỉ nên import tối đa 500 dòng.')
    return rows


def _build_member_import_results(classroom, rows):
    usernames = {row['username'].lower() for row in rows if row['username']}
    emails = {row['email'] for row in rows if row['email']}

    user_query = Q()
    for username in usernames:
        user_query |= Q(username__iexact=username)
    for email in emails:
        user_query |= Q(email__iexact=email)
    users = User.objects.filter(user_query).select_related('profiles') if user_query else User.objects.none()

    users_by_username = {user.username.lower(): user for user in users if user.username}
    users_by_email = {}
    duplicate_emails = set()
    for user in users:
        email = (user.email or '').strip().lower()
        if not email:
            continue
        if email in users_by_email:
            duplicate_emails.add(email)
        else:
            users_by_email[email] = user

    existing_members = {
        member.student_id: member
        for member in ClassroomMembers.objects.filter(
            classroom=classroom,
            student_id__in=[user.pk for user in users],
        ).select_related('student')
    }

    seen_users = set()
    results = []
    for row in rows:
        username_user = users_by_username.get(row['username'].lower()) if row['username'] else None
        email_user = users_by_email.get(row['email']) if row['email'] else None

        if row['email'] in duplicate_emails:
            results.append({**row, 'status': 'invalid', 'message': 'Email khớp nhiều tài khoản.'})
            continue
        if username_user and email_user and username_user.pk != email_user.pk:
            results.append({**row, 'status': 'invalid', 'message': 'Username và email thuộc hai tài khoản khác nhau.'})
            continue

        user = username_user or email_user
        if not user:
            results.append({**row, 'status': 'missing', 'message': 'Không tìm thấy user có sẵn.'})
            continue
        if user.pk == classroom.teacher_id:
            results.append({**row, 'status': 'invalid', 'message': 'User này là giáo viên của lớp.'})
            continue
        if _get_user_role(user) != 'student':
            results.append({**row, 'status': 'invalid', 'message': 'User không phải role student.'})
            continue
        if user.pk in seen_users:
            results.append({**row, 'user': user, 'status': 'duplicate', 'message': 'Trùng user trong file CSV.'})
            continue

        member = existing_members.get(user.pk)
        if member:
            if member.status == 'approved':
                status = 'already'
                message = 'Đã là thành viên.'
            else:
                status = 'reactivate'
                message = f'Sẽ chuyển trạng thái từ {member.status or "trống"} sang approved.'
            results.append({**row, 'user': user, 'member': member, 'status': status, 'message': message})
        else:
            results.append({**row, 'user': user, 'status': 'add', 'message': 'Sẽ thêm vào lớp.'})
        seen_users.add(user.pk)

    return results


def _summarize_member_import(results):
    summary = {
        'added': 0,
        'already': 0,
        'duplicate': 0,
        'missing': 0,
        'invalid': 0,
        'processed': len(results),
    }
    for result in results:
        status = result.get('status')
        if status in ('add', 'reactivate', 'added'):
            summary['added'] += 1
        elif status in summary:
            summary[status] += 1
    summary['imported'] = summary['added']
    summary['skipped'] = summary['already'] + summary['duplicate'] + summary['missing'] + summary['invalid']
    return summary


def _apply_member_import(classroom, results):
    added_user_ids = []
    with transaction.atomic():
        for result in results:
            if result['status'] == 'add':
                member = ClassroomMembers.objects.create(
                    classroom=classroom,
                    student=result['user'],
                    status='approved',
                )
                result['member'] = member
                result['status'] = 'added'
                result['message'] = 'Đã thêm vào lớp.'
                added_user_ids.append(result['user'].pk)
            elif result['status'] == 'reactivate':
                member = result['member']
                member.status = 'approved'
                member.save(update_fields=['status'])
                result['status'] = 'added'
                result['message'] = 'Đã chuyển sang approved.'
                added_user_ids.append(result['user'].pk)

    if added_user_ids:
        notify_users(
            added_user_ids,
            title=f'Bạn đã được thêm vào lớp {classroom.name}',
            message='Giáo viên đã thêm bạn vào lớp bằng danh sách CSV.',
            link=f'/classrooms/{classroom.pk}/',
            notification_type='class_import_added',
            actor=classroom.teacher,
            metadata={'classroom_id': classroom.pk},
        )
    return added_user_ids


@teacher_required
def import_members_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền import học sinh vào lớp này.')
        return redirect('classrooms:classroom_list')

    if request.GET.get('sample') == '1':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="class_members_template.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['username', 'email', 'full_name'])
        writer.writerow(['student01', 'student01@example.com', 'Nguyen Van A'])
        writer.writerow(['student02', 'student02@example.com', 'Tran Thi B'])
        return response

    results = []
    summary = None
    form = MemberImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            rows = _read_member_import_rows(form.cleaned_data['csv_file'])
            results = _build_member_import_results(classroom, rows)
            _apply_member_import(classroom, results)
            summary = _summarize_member_import(results)
            if summary['imported']:
                messages.success(request, f'Đã thêm/cập nhật {summary["imported"]} học sinh vào lớp.')
            else:
                messages.info(request, 'Không có học sinh mới được thêm. Xem chi tiết kết quả bên dưới.')
        except ValueError as exc:
            form.add_error('csv_file', str(exc))

    context = {
        'classroom': classroom,
        'form': form,
        'results': results,
        'summary': summary,
    }
    return render(request, 'classrooms/import_members.html', context)


@login_required
def search_classroom_view(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = Classrooms.objects.filter(
            Q(name__icontains=query) | Q(invite_code__iexact=query),
            is_active=True
        ).annotate(
            member_count=Count('classroommembers', filter=Q(classroommembers__status='approved'))
        )[:20]

    context = {
        'results': results,
        'query': query,
    }
    return render(request, 'classrooms/search.html', context)


@teacher_required
def create_classroom_view(request):
    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.teacher = request.user
            classroom.invite_code = _generate_invite_code()
            classroom.save()
            _apply_classroom_form_settings(classroom, form)
            notify_admins(
                title=f'Lớp mới chờ duyệt: {classroom.name}',
                message=f'{request.user.get_full_name() or request.user.username} vừa tạo lớp mới.',
                link='/administration/classrooms/?status=pending',
                notification_type='classroom_pending',
                actor=request.user,
                metadata={'classroom_id': classroom.pk},
            )
            messages.success(request, f'Lớp "{classroom.name}" đã được tạo! Mã mời: {classroom.invite_code}')
            if classroom.is_active:
                return redirect('classrooms:classroom_detail', pk=classroom.pk)
            messages.info(request, 'Lớp đang chờ admin duyệt trước khi mở cho học sinh.')
            return redirect('accounts:teacher_dashboard')
    else:
        form = ClassroomForm()
    return render(request, 'classrooms/create.html', {'form': form})


@teacher_required
def edit_classroom_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền chỉnh sửa lớp này.')
        return redirect('classrooms:classroom_list')

    if request.method == 'POST':
        if request.POST.get('action') == 'reset_invite_code':
            old_code = classroom.invite_code
            classroom.invite_code = _generate_invite_code()
            classroom.save(update_fields=['invite_code', 'updated_at'])
            messages.success(request, f'Đã đổi mã mời từ {old_code} sang {classroom.invite_code}.')
            return redirect('classrooms:edit', pk=classroom.pk)

        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            classroom = form.save()
            _apply_classroom_form_settings(classroom, form)
            messages.success(request, 'Cập nhật lớp học thành công!')
            return redirect('classrooms:classroom_detail', pk=classroom.pk)
    else:
        form = ClassroomForm(instance=classroom)

    return render(request, 'classrooms/edit.html', {'form': form, 'classroom': classroom})


@teacher_required
def delete_classroom_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền xóa lớp này.')
        return redirect('classrooms:classroom_list')

    if request.method == 'POST':
        classroom.is_active = False
        classroom.save(update_fields=['is_active'])
        messages.success(request, f'Đã xóa lớp "{classroom.name}".')
        return redirect('classrooms:classroom_list')

    return render(request, 'classrooms/delete_confirm.html', {'classroom': classroom})


@login_required
def join_classroom_view(request):
    if request.method == 'POST':
        form = JoinClassroomForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['invite_code'].strip().upper()
            classroom = Classrooms.objects.filter(invite_code=code, is_active=True).first()
            if not classroom:
                messages.error(request, 'Mã mời không hợp lệ hoặc lớp không tồn tại.')
            elif classroom.teacher == request.user:
                messages.info(request, 'Bạn là giáo viên của lớp này.')
                return redirect('classrooms:classroom_detail', pk=classroom.pk)
            else:
                target_status = 'pending' if _classroom_join_requires_approval(classroom) else 'approved'
                member, created = ClassroomMembers.objects.get_or_create(
                    classroom=classroom,
                    student=request.user,
                    defaults={'status': target_status}
                )
                if not created:
                    if member.status == 'approved':
                        messages.info(request, 'Bạn đã là thành viên của lớp này.')
                    elif member.status == 'pending':
                        messages.info(request, 'Đơn tham gia của bạn đang chờ phê duyệt.')
                    else:
                        member.status = target_status
                        member.save(update_fields=['status'])
                        messages.success(request, f'Đã tham gia lớp "{classroom.name}"!' if target_status == 'approved' else 'Đã gửi yêu cầu tham gia lớp.')
                else:
                    messages.success(request, f'Đã tham gia lớp "{classroom.name}"!' if target_status == 'approved' else 'Đã gửi yêu cầu tham gia lớp.')
                    if classroom.teacher:
                        notify_user(
                            classroom.teacher,
                            title=(f'Học sinh mới tham gia: {classroom.name}' if target_status == 'approved' else f'Yêu cầu tham gia lớp: {classroom.name}'),
                            message=f'{request.user.get_full_name() or request.user.username} vừa {"tham gia" if target_status == "approved" else "gửi yêu cầu vào"} lớp.',
                            link=f'/classrooms/{classroom.pk}/',
                            notification_type='class_join_approved' if target_status == 'approved' else 'class_join_requested',
                            actor=request.user,
                            metadata={'classroom_id': classroom.pk},
                        )
                return redirect('classrooms:classroom_detail', pk=classroom.pk) if target_status == 'approved' else redirect('classrooms:classroom_list')
    else:
        form = JoinClassroomForm()
    return render(request, 'classrooms/join.html', {'form': form})


@login_required
@require_POST
def quick_join_classroom_view(request, pk):
    """Tham gia lớp trực tiếp từ danh sách khám phá (không cần mã mời)."""
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    if classroom.teacher == request.user:
        messages.info(request, 'Bạn là giáo viên của lớp này.')
        return redirect('classrooms:classroom_detail', pk=pk)

    target_status = 'pending' if _classroom_join_requires_approval(classroom) else 'approved'
    member, created = ClassroomMembers.objects.get_or_create(
        classroom=classroom, student=request.user,
        defaults={'status': target_status},
    )
    if created:
        messages.success(request, f'Đã tham gia lớp “{classroom.name}”!' if target_status == 'approved' else 'Đã gửi yêu cầu tham gia lớp.')
        if classroom.teacher:
            notify_user(
                classroom.teacher,
                title=(f'Học sinh mới tham gia: {classroom.name}' if target_status == 'approved' else f'Yêu cầu tham gia lớp: {classroom.name}'),
                message=f'{request.user.get_full_name() or request.user.username} vừa {"tham gia" if target_status == "approved" else "gửi yêu cầu vào"} lớp.',
                link=f'/classrooms/{classroom.pk}/',
                notification_type='class_join_approved' if target_status == 'approved' else 'class_join_requested',
                actor=request.user,
                metadata={'classroom_id': classroom.pk},
            )
    else:
        if member.status == 'approved':
            messages.info(request, 'Bạn đã là thành viên của lớp này.')
        elif member.status == 'pending':
            messages.info(request, 'Đơn tham gia đang chờ phê duyệt.')
        else:
            member.status = target_status
            member.save(update_fields=['status'])
            messages.success(request, f'Đã tham gia lớp “{classroom.name}”!' if target_status == 'approved' else 'Đã gửi yêu cầu tham gia lớp.')
    return redirect('classrooms:classroom_detail', pk=pk) if target_status == 'approved' else redirect('classrooms:classroom_list')


@login_required
@require_POST
def leave_classroom_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    deleted, _ = ClassroomMembers.objects.filter(
        classroom=classroom, student=request.user
    ).delete()
    if deleted:
        messages.success(request, f'Bạn đã rời khỏi lớp "{classroom.name}".')
    else:
        messages.info(request, 'Bạn không phải thành viên của lớp này.')
    return redirect('classrooms:classroom_list')


@teacher_required
@require_POST
def approve_member_view(request, pk, member_id):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
        return redirect('classrooms:classroom_list')

    member = get_object_or_404(ClassroomMembers, pk=member_id, classroom=classroom)
    member.status = 'approved'
    member.save(update_fields=['status'])
    notify_user(
        member.student,
        title=f'Bạn đã được duyệt vào lớp {classroom.name}',
        message='Bạn có thể bắt đầu xem bài tập và thông báo trong lớp.',
        link=f'/classrooms/{classroom.pk}/',
        notification_type='class_join_approved',
        actor=request.user,
        metadata={'classroom_id': classroom.pk},
    )
    messages.success(request, f'Đã phê duyệt {member.student.get_full_name() or member.student.username}.')
    return redirect('classrooms:classroom_detail', pk=pk)


@teacher_required
@require_POST
def remove_member_view(request, pk, member_id):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
        return redirect('classrooms:classroom_list')

    member = get_object_or_404(ClassroomMembers, pk=member_id, classroom=classroom)
    name = member.student.get_full_name() or member.student.username
    member.delete()
    messages.success(request, f'Đã xóa {name} khỏi lớp.')
    return redirect('classrooms:classroom_detail', pk=pk)


@teacher_required
def create_announcement_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền đăng thông báo.')
        return redirect('classrooms:classroom_detail', pk=pk)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.classroom = classroom
            announcement.teacher = request.user
            announcement.save()
            student_ids = ClassroomMembers.objects.filter(
                classroom=classroom,
                status='approved',
            ).values_list('student_id', flat=True)
            notify_users(
                student_ids,
                title=f'Thông báo lớp {classroom.name}: {announcement.title}',
                message=announcement.content[:180],
                link=f'/classrooms/{classroom.pk}/',
                notification_type='class_announcement',
                actor=request.user,
                metadata={'classroom_id': classroom.pk, 'announcement_id': announcement.pk},
            )
            messages.success(request, 'Đã đăng thông báo!')
            return redirect('classrooms:classroom_detail', pk=pk)
    else:
        form = AnnouncementForm()

    return render(request, 'classrooms/create_announcement.html', {
        'form': form, 'classroom': classroom
    })


def _can_manage_subjects(user, classroom):
    return _is_admin_user(user) or _is_classroom_teacher(user, classroom)


@login_required
def classroom_subjects_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)
    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    subject_links = ClassroomSubjects.objects.filter(
        classroom=classroom,
        is_active=True,
        subject__is_active=True,
    ).select_related(
        'subject', 'subject__created_by', 'subject__approved_by', 'assigned_by', 'semester'
    ).prefetch_related('subject__languages').order_by('-semester__is_current', '-semester__start_date', 'subject__status', 'subject__code')
    if not is_teacher:
        subject_links = subject_links.filter(subject__status=SubjectApprovalStatus.APPROVED)
        subject_links = subject_links.annotate(assignment_count=Count('assignments', filter=Q(assignments__is_published=True), distinct=True))
    else:
        subject_links = subject_links.annotate(assignment_count=Count('assignments', distinct=True))

    # Lọc theo kỳ học (nếu được chọn)
    semester_filter = request.GET.get('semester', '').strip()
    current_semester = None
    if semester_filter == 'current':
        current_semester = Semesters.objects.filter(is_current=True, is_active=True).first()
        if current_semester:
            subject_links = subject_links.filter(semester=current_semester)
    elif semester_filter == 'none':
        subject_links = subject_links.filter(semester__isnull=True)
    elif semester_filter.isdigit():
        subject_links = subject_links.filter(semester_id=int(semester_filter))

    # Group theo kỳ học để hiển thị
    from collections import OrderedDict
    grouped = OrderedDict()
    for link in subject_links:
        key = link.semester_id if link.semester_id else 0
        label = str(link.semester) if link.semester_id else 'Chưa phân kỳ'
        if key not in grouped:
            grouped[key] = {'semester': link.semester, 'label': label, 'links': []}
        grouped[key]['links'].append(link)

    # Danh sách kỳ học cho filter
    all_semesters = Semesters.objects.filter(is_active=True).order_by('-is_current', '-start_date')

    return render(request, 'classrooms/subjects.html', {
        'classroom': classroom,
        'subject_links': subject_links,
        'grouped_links': list(grouped.values()),
        'all_semesters': all_semesters,
        'semester_filter': semester_filter,
        'is_teacher': is_teacher,
        'can_manage_subjects': _can_manage_subjects(request.user, classroom),
        'assign_form': ClassroomSubjectForm() if is_teacher else None,
    })


@login_required
def classroom_subject_detail_view(request, pk, link_pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")
        
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)
    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    link = get_object_or_404(
        ClassroomSubjects.objects.select_related(
            'classroom', 'subject', 'subject__created_by', 'subject__approved_by', 'assigned_by', 'semester'
        ).prefetch_related('subject__languages'),
        pk=link_pk,
        classroom=classroom,
        is_active=True,
        subject__is_active=True,
    )
    if not is_teacher and link.subject.status != SubjectApprovalStatus.APPROVED:
        messages.error(request, 'Môn học này chưa được công bố cho học viên.')
        return redirect('classrooms:classroom_detail', pk=classroom.pk)

    from apps.assignments.models import Assignments
    from apps.submissions.models import Submissions

    query = request.GET.get('q', '').strip()
    assignment_type = request.GET.get('type', 'all').strip()
    if assignment_type not in ('all', 'assignment', 'exam', 'draft'):
        assignment_type = 'all'

    assignments_qs = Assignments.objects.filter(
        classroom=classroom,
        classroom_subject=link,
    ).select_related('classroom_subject', 'classroom_subject__subject', 'classroom_subject__semester')

    if not is_teacher:
        assignments_qs = assignments_qs.filter(is_published=True)
    elif assignment_type == 'draft':
        assignments_qs = assignments_qs.filter(is_published=False)

    if assignment_type == 'exam':
        assignments_qs = assignments_qs.filter(is_exam=True)
    elif assignment_type == 'assignment':
        assignments_qs = assignments_qs.filter(is_exam=False)

    if query:
        assignments_qs = assignments_qs.filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(instructions__icontains=query)
        )

    assignments = list(assignments_qs.order_by('-is_published', 'due_date', '-created_at', 'id'))
    assignment_ids = [assignment.pk for assignment in assignments]

    submissions_by_assignment = {}
    teacher_submission_counts = {}
    if assignment_ids:
        if is_teacher:
            counts = Submissions.objects.filter(
                assignment_id__in=assignment_ids,
            ).values('assignment_id').annotate(total=Count('id'), students=Count('student_id', distinct=True))
            teacher_submission_counts = {
                item['assignment_id']: {
                    'total': item['total'],
                    'students': item['students'],
                }
                for item in counts
            }
        else:
            latest_submissions = Submissions.objects.filter(
                assignment_id__in=assignment_ids,
                student=request.user,
            ).order_by('assignment_id', '-submitted_at')
            for submission in latest_submissions:
                submissions_by_assignment.setdefault(submission.assignment_id, submission)

    now = timezone.now()
    assignment_rows = []
    published_count = 0
    draft_count = 0
    exam_count = 0
    overdue_count = 0
    completed_count = 0
    for assignment in assignments:
        if assignment.is_published:
            published_count += 1
        else:
            draft_count += 1
        if assignment.is_exam:
            exam_count += 1
        if assignment.due_date and assignment.due_date < now:
            overdue_count += 1

        latest_submission = submissions_by_assignment.get(assignment.pk)
        is_completed = bool(latest_submission and latest_submission.status == 'finished')
        if is_completed:
            completed_count += 1

        assignment_rows.append({
            'assignment': assignment,
            'latest_submission': latest_submission,
            'is_completed': is_completed,
            'teacher_counts': teacher_submission_counts.get(assignment.pk, {'total': 0, 'students': 0}),
        })

    approved_members_count = ClassroomMembers.objects.filter(classroom=classroom, status='approved').count()
    completion_rate = round(completed_count / len(assignments) * 100, 1) if assignments and not is_teacher else None

    return render(request, 'classrooms/subject_detail.html', {
        'classroom': classroom,
        'link': link,
        'subject': link.subject,
        'assignment_rows': assignment_rows,
        'is_teacher': is_teacher,
        'is_member': is_member,
        'can_manage_subjects': _can_manage_subjects(request.user, classroom),
        'assign_form': ClassroomSubjectForm() if is_teacher else None,
        'breadcrumbs': [
            {'label': 'Lớp học', 'url': reverse('classrooms:classroom_list')},
            {'label': classroom.name, 'url': reverse('classrooms:classroom_detail', kwargs={'pk': classroom.pk})},
            {'label': link.subject.name},
        ],
        'assignment_type': assignment_type,
        'published_count': published_count,
        'draft_count': draft_count,
        'exam_count': exam_count,
        'overdue_count': overdue_count,
        'completed_count': completed_count,
        'completion_rate': completion_rate,
        'approved_members_count': approved_members_count,
    })


@teacher_required
def create_subject_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")

    if not _can_manage_subjects(request.user, classroom):
        messages.error(request, 'Bạn không có quyền tạo môn học cho lớp này.')
        return redirect('classrooms:classroom_detail', pk=pk)

    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.created_by = request.user
            if _is_admin_user(request.user):
                subject.status = SubjectApprovalStatus.APPROVED
                subject.approved_by = request.user
                subject.reviewed_at = timezone.now()
            else:
                subject.status = SubjectApprovalStatus.PENDING
            # Mã môn học luôn tự sinh — không cho user chọn.
            # Retry trên IntegrityError để xử lý race condition khi 2 request đồng thời.
            saved = False
            for _attempt in range(5):
                subject.code = _generate_subject_code()
                try:
                    with transaction.atomic():
                        subject.save()
                        form.save_m2m()
                    saved = True
                    break
                except IntegrityError:
                    continue
            if not saved:
                messages.error(request, 'Không sinh được mã môn học (thử lại sau).')
                return redirect('classrooms:subjects', pk=pk)
            ClassroomSubjects.objects.get_or_create(
                classroom=classroom,
                subject=subject,
                semester=None,
                defaults={
                    'assigned_by': request.user,
                    'is_active': True,
                },
            )
            if subject.status == SubjectApprovalStatus.PENDING:
                notify_admins(
                    title=f'Môn học mới chờ duyệt: {subject.name}',
                    message=f'{request.user.get_full_name() or request.user.username} vừa tạo môn học cho lớp {classroom.name}.',
                    link='/administration/subjects/?status=pending',
                    notification_type='subject_pending',
                    actor=request.user,
                    metadata={'subject_id': subject.pk, 'classroom_id': classroom.pk},
                )
            messages.success(
                request,
                f'Đã tạo môn học "{subject.name}".' + (' Môn đã được duyệt.' if subject.status == SubjectApprovalStatus.APPROVED else ' Môn đang chờ admin duyệt.')
            )
            return redirect('classrooms:subjects', pk=pk)
        # POST invalid — rơi xuống dưới để render lại với preview
        next_code_preview = _generate_subject_code()
    else:
        form = SubjectForm()
        next_code_preview = _generate_subject_code()

    # Danh sách môn đã tồn tại (hiển thị trong trang tạo)
    existing_subjects = Subjects.objects.filter(is_active=True).order_by('code').prefetch_related('languages')

    return render(request, 'classrooms/subject_form.html', {
        'form': form,
        'classroom': classroom,
        'is_edit': False,
        'back_url': 'classrooms:subjects',
        'existing_subjects': existing_subjects,
        'next_code_preview': next_code_preview,
    })


@teacher_required
def edit_subject_view(request, classroom_pk, subject_pk):
    classroom = get_object_or_404(Classrooms, pk=classroom_pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")
        
    subject = get_object_or_404(Subjects, pk=subject_pk)
    subject_is_linked_to_classroom = ClassroomSubjects.objects.filter(
        classroom=classroom,
        subject=subject,
        is_active=True,
    ).exists()
    can_edit_subject = (
        _is_admin_user(request.user)
        or subject.created_by == request.user
        or (_is_classroom_teacher(request.user, classroom) and subject_is_linked_to_classroom)
    )
    if not can_edit_subject:
        messages.error(request, 'Bạn không có quyền chỉnh sửa môn học này.')
        return redirect('classrooms:classroom_detail', pk=classroom_pk)

    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            subject = form.save(commit=False)
            # Giữ nguyên code cũ khi edit — không cho đổi code
            if not subject.code:
                subject.code = _generate_subject_code()
            if _is_admin_user(request.user):
                subject.status = SubjectApprovalStatus.APPROVED
                subject.approved_by = request.user
                subject.reviewed_at = timezone.now()
            elif subject.status in (SubjectApprovalStatus.APPROVED, SubjectApprovalStatus.REJECTED):
                subject.status = SubjectApprovalStatus.PENDING
                subject.approved_by = None
                subject.reviewed_at = None
            subject.save()
            form.save_m2m()
            if subject.status == SubjectApprovalStatus.PENDING:
                notify_admins(
                    title=f'Môn học cần duyệt lại: {subject.name}',
                    message=f'{request.user.get_full_name() or request.user.username} vừa chỉnh sửa môn học trong lớp {classroom.name}.',
                    link='/administration/subjects/?status=pending',
                    notification_type='subject_pending',
                    actor=request.user,
                    metadata={'subject_id': subject.pk, 'classroom_id': classroom.pk},
                )
            messages.success(request, 'Đã cập nhật môn học.')
            return redirect('classrooms:subjects', pk=classroom_pk)
    else:
        form = SubjectForm(instance=subject)

    existing_subjects = Subjects.objects.filter(is_active=True).exclude(pk=subject.pk).order_by('code').prefetch_related('languages')

    return render(request, 'classrooms/subject_form.html', {
        'form': form,
        'classroom': classroom,
        'subject': subject,
        'is_edit': True,
        'back_url': 'classrooms:subjects',
        'existing_subjects': existing_subjects,
        'next_code_preview': subject.code,  # hiển thị mã hiện tại trong mode edit
    })


@teacher_required
def check_subject_name_view(request):
    """AJAX endpoint: kiểm tra tên môn học có trùng với môn đã tồn tại hay không.

    Query params:
        name: tên muốn check
        exclude: pk môn đang edit (tuỳ chọn)
    Returns JSON: { available: bool, conflict: { code, name, status } | null }
    """
    name = (request.GET.get('name') or '').strip()
    exclude_pk = request.GET.get('exclude')
    if not name:
        return JsonResponse({'available': True, 'conflict': None})

    target = _normalize_subject_name(name)
    qs = Subjects.objects.filter(is_active=True)
    if exclude_pk and str(exclude_pk).isdigit():
        qs = qs.exclude(pk=int(exclude_pk))

    # So sánh chuẩn hóa — phải iterate (DB không có built-in unaccent ở mọi engine)
    for s in qs.only('id', 'code', 'name', 'status'):
        if _normalize_subject_name(s.name) == target:
            return JsonResponse({
                'available': False,
                'conflict': {
                    'id': s.id,
                    'code': s.code,
                    'name': s.name,
                    'status': s.status,
                },
            })
    return JsonResponse({'available': True, 'conflict': None})


@teacher_required
def delete_subject_view(request, classroom_pk, subject_pk):
    """Gỡ một môn khỏi lớp. Nếu có nhiều kỳ, gỡ theo link_id."""
    classroom = get_object_or_404(Classrooms, pk=classroom_pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")
        
    subject = get_object_or_404(Subjects, pk=subject_pk)
    link_id = request.GET.get('link') or request.POST.get('link')
    if link_id and str(link_id).isdigit():
        link = get_object_or_404(ClassroomSubjects, pk=int(link_id), classroom=classroom, subject=subject)
    else:
        link = ClassroomSubjects.objects.filter(classroom=classroom, subject=subject).order_by('-semester__is_current', '-semester__start_date').first()
        if not link:
            messages.error(request, 'Liên kết môn học không tồn tại.')
            return redirect('classrooms:subjects', pk=classroom_pk)
    if not _can_manage_subjects(request.user, classroom) and subject.created_by != request.user:
        messages.error(request, 'Bạn không có quyền xóa môn học này.')
        return redirect('classrooms:classroom_detail', pk=classroom_pk)

    if request.method == 'POST':
        name = subject.name
        sem = f' ({link.semester})' if link.semester_id else ''
        link.delete()
        messages.success(request, f'Đã gỡ môn học "{name}"{sem} khỏi lớp.')
        
        # Quay lại trang trước đó (detail hoặc subjects list)
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
        return redirect('classrooms:subjects', pk=classroom_pk)

    return render(request, 'classrooms/delete_confirm.html', {
        'classroom': classroom,
        'subject': subject,
        'link': link,
        'subject_mode': True,
        'back_url': 'classrooms:subjects',
    })


@teacher_required
def assign_subject_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")
        
    if not _can_manage_subjects(request.user, classroom):
        messages.error(request, 'Bạn không có quyền gán môn học cho lớp này.')
        return redirect('classrooms:classroom_detail', pk=pk)

    if request.method == 'POST':
        form = ClassroomSubjectForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            # Không cần lấy semester từ form nữa
            link, created = ClassroomSubjects.objects.get_or_create(
                classroom=classroom,
                subject=subject,
                defaults={
                    'assigned_by': request.user,
                    'is_active': True,
                },
            )
            if not created and not link.is_active:
                link.is_active = True
                link.assigned_by = request.user
                link.save(update_fields=['is_active', 'assigned_by', 'updated_at'])
            
            if created:
                messages.success(request, f'Đã gán môn học "{subject.name}" cho lớp.')
            else:
                messages.info(request, f'Môn học "{subject.name}" đã có trong lớp.')
            
            # Quay lại trang trước đó (thường là detail hoặc subjects list)
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
            if next_url:
                return redirect(next_url)
            return redirect('classrooms:classroom_detail', pk=pk)
    else:
        form = ClassroomSubjectForm()

    return render(request, 'classrooms/subject_assign.html', {
        'classroom': classroom,
        'form': form,
    })


@teacher_required
@require_POST
def pin_announcement_view(request, pk, announcement_id):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
        return redirect('classrooms:classroom_detail', pk=pk)

    announcement = get_object_or_404(Announcements, pk=announcement_id, classroom=classroom)
    announcement.is_pinned = not announcement.is_pinned
    announcement.save(update_fields=['is_pinned'])
    action = 'ghim' if announcement.is_pinned else 'bỏ ghim'
    messages.success(request, f'Đã {action} thông báo.')
    return redirect('classrooms:classroom_detail', pk=pk)


@teacher_required
@require_POST
def delete_announcement_view(request, pk, announcement_id):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom):
        messages.error(request, 'Bạn không có quyền thực hiện thao tác này.')
        return redirect('classrooms:classroom_detail', pk=pk)

    announcement = get_object_or_404(Announcements, pk=announcement_id, classroom=classroom)
    announcement.delete()
    messages.success(request, 'Đã xóa thông báo.')
    return redirect('classrooms:classroom_detail', pk=pk)


# ===================================================================
# SEMESTER MANAGEMENT (Admin)
# ===================================================================

@admin_required
def semester_list_view(request):
    semesters = Semesters.objects.all().order_by('-is_current', '-start_date', '-code')
    context = {
        'semesters': semesters,
        'current_page': 'semesters',
    }
    # Thêm admin base context nếu có
    try:
        from apps.administation.views import _admin_base_context
        context.update(_admin_base_context())
    except Exception:
        pass
    return render(request, 'classrooms/semester_list.html', context)


@admin_required
def semester_create_view(request):
    if request.method == 'POST':
        form = SemesterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã tạo kỳ học mới.')
            return redirect('classrooms:semester_list')
    else:
        form = SemesterForm()
    context = {
        'form': form,
        'is_edit': False,
        'current_page': 'semesters',
    }
    try:
        from apps.administation.views import _admin_base_context
        context.update(_admin_base_context())
    except Exception:
        pass
    return render(request, 'classrooms/semester_form.html', context)


@admin_required
def semester_edit_view(request, pk):
    semester = get_object_or_404(Semesters, pk=pk)
    if request.method == 'POST':
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật kỳ học.')
            return redirect('classrooms:semester_list')
    else:
        form = SemesterForm(instance=semester)
    context = {
        'form': form,
        'semester': semester,
        'is_edit': True,
        'current_page': 'semesters',
    }
    try:
        from apps.administation.views import _admin_base_context
        context.update(_admin_base_context())
    except Exception:
        pass
    return render(request, 'classrooms/semester_form.html', context)


@admin_required
def semester_delete_view(request, pk):
    semester = get_object_or_404(Semesters, pk=pk)
    if request.method == 'POST':
        # Nếu còn link hoặc assignment (qua classroom_subject) đang tham chiếu thì SET_NULL sẽ xử lý
        name = semester.name or semester.code
        semester.delete()
        messages.success(request, f'Đã xóa kỳ học "{name}".')
        return redirect('classrooms:semester_list')
    context = {
        'semester': semester,
        'current_page': 'semesters',
    }
    try:
        from apps.administation.views import _admin_base_context
        context.update(_admin_base_context())
    except Exception:
        pass
    return render(request, 'classrooms/semester_delete_confirm.html', context)


@login_required
def leaderboard_view(request, pk):
    classroom = get_object_or_404(Classrooms, pk=pk)
    if not _is_classroom_teacher(request.user, classroom) and not classroom.is_active:
        raise Http404("Lớp học không tồn tại hoặc chưa được duyệt.")
        
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    leaderboard = Leaderboard.objects.filter(
        classroom=classroom
    ).select_related('student').order_by('rank', '-total_score')

    context = {
        'classroom': classroom,
        'leaderboard': leaderboard,
        'is_teacher': is_teacher,
    }
    return render(request, 'classrooms/leaderboard.html', context)
