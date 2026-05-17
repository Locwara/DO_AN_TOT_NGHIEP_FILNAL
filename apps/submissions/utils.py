"""Shared utility functions for the submissions app."""

from django.utils import timezone


def submission_final_score(submission):
    """Return the score that should be shown in gradebook/statistics."""
    if submission is None:
        return None
    if submission.manual_score is not None:
        return submission.manual_score
    return submission.total_score


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

    submissions = Submissions.objects.filter(assignment=assignment)
    total = submissions.count()
    if total == 0:
        return

    unique_students = submissions.values('student').distinct().count()
    scores = [submission_final_score(sub) or 0 for sub in submissions]
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    pass_count = sum(1 for s in scores if s >= assignment.max_score * 0.5)
    pass_rate = (pass_count / total * 100) if total > 0 else 0
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
