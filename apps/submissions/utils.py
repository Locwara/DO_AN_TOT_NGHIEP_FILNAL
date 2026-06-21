"""Shared utility functions for the submissions app."""

import hashlib
import mimetypes
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone


DANGEROUS_UPLOAD_EXTENSIONS = {
    '.app', '.apk', '.bat', '.bin', '.cmd', '.com', '.dll', '.dmg', '.exe',
    '.gadget', '.hta', '.jar', '.js', '.jse', '.msi', '.msp', '.php', '.ps1',
    '.scr', '.sh', '.vb', '.vbe', '.vbs', '.ws', '.wsf',
}


def sanitize_upload_filename(file_name, fallback='file'):
    """Return a display-safe filename while preserving the useful extension."""
    base_name = os.path.basename(file_name or '').replace('\x00', '').strip()
    if not base_name:
        base_name = fallback
    name, ext = os.path.splitext(base_name)
    safe_name = ''.join(ch if ch.isalnum() or ch in '._- ' else '_' for ch in name).strip(' ._-')
    safe_ext = ''.join(ch if ch.isalnum() or ch == '.' else '' for ch in ext.lower())[:16]
    if not safe_name:
        safe_name = fallback
    return f'{safe_name[:120]}{safe_ext}'


def storage_public_id(user, original_name, prefix='upload'):
    """Build a non-guessable storage id instead of trusting the user's filename."""
    safe_name = sanitize_upload_filename(original_name, fallback=prefix)
    name, _ext = os.path.splitext(safe_name)
    user_part = getattr(user, 'pk', None) or 'anon'
    return f'{prefix}/{user_part}/{uuid.uuid4().hex}-{name[:60]}'


def cloudinary_is_configured():
    config = getattr(settings, 'CLOUDINARY_STORAGE', {}) or {}
    return bool(
        config.get('CLOUD_NAME')
        and config.get('API_KEY')
        and config.get('API_SECRET')
    )


def upload_to_configured_storage(uploaded_file, *, folder, user, safe_name, prefix):
    """Upload to Cloudinary when configured, otherwise save through Django storage."""
    public_id = storage_public_id(user, safe_name, prefix=prefix)
    if cloudinary_is_configured():
        import cloudinary.uploader

        result = cloudinary.uploader.upload(
            uploaded_file,
            folder=folder,
            public_id=public_id,
            unique_filename=False,
            use_filename=False,
            resource_type='auto',
        )
        return {
            'url': result.get('secure_url', ''),
            'public_id': result.get('public_id', public_id),
            'resource_type': result.get('resource_type', ''),
            'storage_provider': 'cloudinary',
        }

    uploaded_file.seek(0)
    _name, ext = os.path.splitext(safe_name)
    relative_path = os.path.join(
        folder.strip('/'),
        f'{public_id.replace("/", "-")}{ext}',
    )
    saved_path = default_storage.save(relative_path, uploaded_file)
    return {
        'url': default_storage.url(saved_path),
        'public_id': saved_path,
        'resource_type': 'file',
        'storage_provider': 'django',
    }


def file_checksum(uploaded_file):
    hasher = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        hasher.update(chunk)
    uploaded_file.seek(0)
    return hasher.hexdigest()


def _normalized_extensions(extensions):
    return {
        ext.strip().lower() if ext.strip().startswith('.') else f'.{ext.strip().lower()}'
        for ext in (extensions or [])
        if ext and ext.strip()
    }


def _normalized_mime_types(mime_types):
    return {
        mime.strip().lower()
        for mime in (mime_types or [])
        if mime and mime.strip()
    }


def validate_uploaded_files(
    uploaded_files,
    *,
    allowed_extensions=None,
    allowed_mime_types=None,
    max_file_size_mb=20,
    max_files=1,
    require_files=True,
    require_all_files_before_submit=False,
    label='file',
):
    """Validate file count, extension, MIME and per-submission total size."""
    errors = []
    uploaded_files = list(uploaded_files or [])
    max_files = max_files or 1
    max_file_size_mb = max_file_size_mb or 20
    max_size = max_file_size_mb * 1024 * 1024
    max_total_size = max_size * max_files
    allowed_extensions = _normalized_extensions(allowed_extensions)
    allowed_mime_types = _normalized_mime_types(allowed_mime_types)

    if require_files and not uploaded_files:
        errors.append('Vui lòng chọn file để nộp.')
        return errors
    if len(uploaded_files) > max_files:
        errors.append(f'Bạn chỉ được nộp tối đa {max_files} file.')
    if require_all_files_before_submit and len(uploaded_files) < max_files:
        errors.append(f'Bài này yêu cầu nộp đủ {max_files} file.')

    total_size = sum(getattr(uploaded_file, 'size', 0) or 0 for uploaded_file in uploaded_files)
    if total_size > max_total_size:
        total_mb = max_total_size // (1024 * 1024)
        errors.append(f'Tổng dung lượng {label} tối đa {total_mb}MB.')

    for uploaded_file in uploaded_files:
        safe_name = sanitize_upload_filename(getattr(uploaded_file, 'name', ''), fallback='file')
        ext = os.path.splitext(safe_name.lower())[1]
        content_type = (getattr(uploaded_file, 'content_type', '') or '').split(';')[0].strip().lower()
        guessed_mime = (mimetypes.guess_type(safe_name)[0] or '').lower()

        if not ext:
            errors.append(f'File "{safe_name}" thiếu phần mở rộng.')
            continue
        if allowed_extensions and ext not in allowed_extensions:
            errors.append(f'File "{safe_name}" không đúng định dạng cho phép.')
        if ext in DANGEROUS_UPLOAD_EXTENSIONS and (not allowed_extensions or ext not in allowed_extensions):
            errors.append(f'File "{safe_name}" thuộc nhóm thực thi nguy hiểm và chưa được cho phép.')
        if (getattr(uploaded_file, 'size', 0) or 0) > max_size:
            errors.append(f'File "{safe_name}" vượt quá {max_file_size_mb}MB.')
        if allowed_mime_types:
            if content_type and content_type not in allowed_mime_types:
                errors.append(f'File "{safe_name}" không đúng MIME type cho phép.')
            elif not content_type and guessed_mime and guessed_mime not in allowed_mime_types:
                errors.append(f'File "{safe_name}" không đúng MIME type cho phép.')

    return errors


def can_reveal_testcase_io(testcase, viewer, assignment):
    """Determine if a testcase's input/output/error should be visible to the viewer."""
    if not testcase or not viewer or not assignment:
        return False

    from apps.classrooms.views import _is_classroom_teacher
    if _is_classroom_teacher(viewer, assignment.classroom):
        return True

    # Students can see sample testcases
    if getattr(testcase, 'is_sample', False):
        return True

    # Students can only see non-hidden testcases if assignment allows it
    if not getattr(testcase, 'is_hidden', True) and assignment.show_testcase_result:
        return True

    return False


def get_assignment_final_score(assignment, student):
    """Calculate the final score for a student in an assignment based on the aggregation mode."""
    from django.db.models import Max, Avg
    from apps.submissions.models import Submissions

    submissions = Submissions.objects.filter(
        assignment=assignment,
        student=student
    ).exclude(status='error')

    if not submissions.exists():
        return 0

    mode = getattr(assignment, 'score_aggregation_mode', 'best')

    if mode == 'best':
        return submissions.aggregate(Max('total_score'))['total_score__max'] or 0
    elif mode == 'latest':
        latest = submissions.order_by('-submitted_at').first()
        return latest.total_score if latest else 0
    elif mode == 'first':
        first = submissions.order_by('submitted_at').first()
        return first.total_score if first else 0
    elif mode == 'average':
        return submissions.aggregate(Avg('total_score'))['total_score__avg'] or 0

    return 0


def submission_final_score(submission):
    """Return the score that should be shown in gradebook/statistics."""
    if submission is None:
        return None
    if submission.manual_score is not None:
        return submission.manual_score
    return submission.total_score


def build_ai_grading_context(submission):
    """Build a clean, offline-only payload for future teacher-assist AI features."""
    if submission is None:
        return {}

    assignment = submission.assignment
    rubric_items = []
    for score in submission.rubric_scores.select_related('rubric').all():
        rubric = score.rubric
        rubric_items.append({
            'rubric_id': rubric.pk if rubric else None,
            'name': rubric.name if rubric else '',
            'description': rubric.description if rubric else '',
            'max_points': rubric.max_points if rubric else None,
            'score': score.score,
            'comment': score.comment or '',
        })

    files = []
    for uploaded in submission.files.all().order_by('uploaded_at'):
        files.append({
            'file_id': uploaded.pk,
            'file_name': uploaded.file_name,
            'extension': uploaded.extension,
            'file_size': uploaded.file_size,
            'mime_type': uploaded.mime_type,
            'checksum': uploaded.checksum,
            'scan_status': uploaded.scan_status,
            'text_extraction_status': uploaded.text_extraction_status,
            'extracted_text': (uploaded.extracted_text or '')[:12000],
            'metadata': uploaded.metadata or {},
        })

    quiz_answers = []
    for attempt in submission.quiz_attempts.prefetch_related(
        'answers',
        'answers__question',
        'answers__selected_choices',
    ).all():
        for answer in attempt.answers.all():
            question = answer.question
            quiz_answers.append({
                'attempt_id': attempt.pk,
                'answer_id': answer.pk,
                'question_id': question.pk if question else None,
                'question_text': question.question_text if question else '',
                'question_type': question.question_type if question else '',
                'points': question.points if question else None,
                'selected_choice_ids': answer.selected_choice_ids or [],
                'text_answer': answer.text_answer or '',
                'score_awarded': answer.score_awarded,
                'ai_suggested_score': answer.ai_suggested_score,
                'ai_suggestion_status': answer.ai_suggestion_status,
            })

    feedback_files = [
        {
            'file_id': feedback.pk,
            'file_name': feedback.file_name,
            'note': feedback.note or '',
            'uploaded_at': feedback.uploaded_at.isoformat() if feedback.uploaded_at else None,
        }
        for feedback in submission.feedback_files.all().order_by('-uploaded_at')
    ]

    return {
        'submission': {
            'id': submission.pk,
            'mode': submission.submission_mode_snapshot,
            'status': submission.status,
            'student_id': submission.student_id,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
            'submission_text': submission.submission_text or '',
            'code_content': submission.code_content or '',
            'language': submission.language or '',
            'total_score': submission.total_score,
            'manual_score': submission.manual_score,
            'max_score': submission.max_score,
            'teacher_comment': submission.teacher_comment or '',
        },
        'assignment': {
            'id': assignment.pk if assignment else None,
            'title': assignment.title if assignment else '',
            'submission_mode': assignment.submission_mode if assignment else submission.submission_mode_snapshot,
            'grading_mode': assignment.grading_mode if assignment else '',
            'is_exam': assignment.is_exam if assignment else False,
            'max_score': assignment.max_score if assignment else submission.max_score,
        },
        'rubrics': rubric_items,
        'files': files,
        'quiz_answers': quiz_answers,
        'feedback_files': feedback_files,
    }


def assignment_allowed_languages(assignment):
    return assignment.allowed_languages or []


def validate_submission_language(assignment, language):
    language = (language or '').strip()
    if not language:
        return False
    allowed = assignment_allowed_languages(assignment)
    return not allowed or language in allowed


def can_access_assignment(user, assignment):
    from apps.classrooms.views import _is_classroom_teacher, _is_classroom_member

    classroom = assignment.classroom
    return _is_classroom_teacher(user, classroom) or _is_classroom_member(user, classroom)


def can_solve_assignment(user, assignment):
    from apps.classrooms.views import _is_classroom_teacher, _is_classroom_member

    classroom = assignment.classroom
    if _is_classroom_teacher(user, classroom):
        return True
    return assignment.is_published and _is_classroom_member(user, classroom)


def assignment_open_error(assignment, user, now=None):
    from apps.classrooms.views import _is_classroom_teacher

    if _is_classroom_teacher(user, assignment.classroom):
        return None
    now = now or timezone.now()
    if not assignment.is_published:
        return 'Bài tập chưa được công bố.'
    if assignment.start_date and now < assignment.start_date:
        return 'Bài tập chưa đến thời gian bắt đầu.'
    if assignment.due_date and now > assignment.due_date and not assignment.late_submission_allowed:
        return 'Đã quá hạn nộp bài.'
    return None


def update_assignment_statistics(assignment):
    """Recalculate assignment statistics after grading."""
    from apps.assignments.models import AssignmentStatistics
    from apps.submissions.models import Submissions
    from django.contrib.auth.models import User

    submissions = Submissions.objects.filter(assignment=assignment).exclude(status='error')
    total = submissions.count()
    if total == 0:
        return

    student_ids = submissions.values_list('student_id', flat=True).distinct()
    unique_students = len(student_ids)
    
    # Calculate final score for each student based on aggregation mode
    final_scores = []
    for student_id in student_ids:
        # Optimization: we could do this in memory if we fetch all submissions, 
        # but for simplicity and correctness we use the helper.
        # For large classes, this might need further optimization.
        student = User(pk=student_id)
        final_scores.append(get_assignment_final_score(assignment, student))

    avg_score = sum(final_scores) / len(final_scores) if final_scores else 0
    max_score = max(final_scores) if final_scores else 0
    min_score = min(final_scores) if final_scores else 0
    pass_count = sum(1 for s in final_scores if s >= assignment.max_score * 0.5)
    pass_rate = (pass_count / unique_students * 100) if unique_students > 0 else 0
    avg_attempts = total / unique_students if unique_students > 0 else 0

    stats, _ = AssignmentStatistics.objects.get_or_create(assignment=assignment)
    stats.total_submissions = total
    stats.unique_students = unique_students
    stats.avg_score = round(avg_score, 2)
    stats.max_score = max_score
    stats.min_score = min_score
    stats.pass_rate = round(pass_rate, 2)
    stats.avg_attempts = round(avg_attempts, 2)
    stats.save()
    update_classroom_leaderboard(assignment.classroom)


def update_classroom_leaderboard(classroom):
    """Recalculate leaderboard rows for a classroom from best finished submissions."""
    if classroom is None:
        return

    from django.db import transaction
    from apps.assignments.models import Assignments
    from apps.classrooms.models import ClassroomMembers, Leaderboard
    from apps.submissions.models import Submissions

    member_ids = list(ClassroomMembers.objects.filter(
        classroom=classroom,
        status='approved',
    ).values_list('student_id', flat=True))
    member_ids = [student_id for student_id in member_ids if student_id]

    if not member_ids:
        Leaderboard.objects.filter(classroom=classroom).delete()
        return

    assignments = Assignments.objects.filter(
        classroom=classroom,
        is_published=True,
    ).only('id')
    assignment_ids = list(assignments.values_list('id', flat=True))

    best_scores = {}
    if assignment_ids:
        submissions = Submissions.objects.filter(
            assignment_id__in=assignment_ids,
            student_id__in=member_ids,
            status='finished',
        ).select_related('assignment', 'student').order_by('student_id', 'assignment_id', '-submitted_at')

        for submission in submissions:
            key = (submission.student_id, submission.assignment_id)
            score = submission_final_score(submission) or 0
            current = best_scores.get(key)
            if current is None or score > current:
                best_scores[key] = score

    scores_by_student = {student_id: [] for student_id in member_ids}
    for (student_id, _assignment_id), score in best_scores.items():
        scores_by_student.setdefault(student_id, []).append(score)

    rows = []
    for student_id in member_ids:
        scores = scores_by_student.get(student_id, [])
        total_score = round(sum(scores), 2)
        completed = len(scores)
        avg_score = round(total_score / completed, 2) if completed else 0
        rows.append({
            'student_id': student_id,
            'total_score': total_score,
            'assignments_completed': completed,
            'avg_score': avg_score,
        })

    rows.sort(key=lambda item: (
        -item['total_score'],
        -item['avg_score'],
        -item['assignments_completed'],
        item['student_id'],
    ))

    with transaction.atomic():
        Leaderboard.objects.filter(classroom=classroom).exclude(student_id__in=member_ids).delete()
        for index, row in enumerate(rows, start=1):
            Leaderboard.objects.update_or_create(
                classroom=classroom,
                student_id=row['student_id'],
                defaults={
                    'total_score': row['total_score'],
                    'assignments_completed': row['assignments_completed'],
                    'avg_score': row['avg_score'],
                    'rank': index,
                },
            )
