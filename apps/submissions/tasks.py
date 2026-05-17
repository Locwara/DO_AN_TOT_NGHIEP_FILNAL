"""Celery tasks for asynchronous submission grading.

When CELERY_TASK_ALWAYS_EAGER is True (default in dev), tasks run
synchronously inside the request cycle — no Redis / worker required.
In production set CELERY_ALWAYS_EAGER=False and start a Celery worker.
"""
import logging
from celery import shared_task
from django.db import DataError

logger = logging.getLogger(__name__)


def _sanitize_text_for_db(value):
    if isinstance(value, str):
        return value.replace('\x00', '')
    return value


def _create_submission_detail_with_fallback(submission, testcase, tc_result, score_earned):
    from apps.submissions.models import SubmissionDetails

    raw_status = _sanitize_text_for_db(tc_result.get('status'))
    is_passed = bool(tc_result.get('passed'))

    candidate_statuses = [raw_status, 'passed' if is_passed else 'failed', None]
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


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def grade_submission_task(self, submission_id):
    """Grade a submission by running all testcases.

    This is the async equivalent of the grading logic in submit_code_view.
    """
    from django.utils import timezone
    from apps.assignments.models import Testcases, AssignmentStatistics
    from apps.administation.models import SandboxConfigs
    from apps.submissions.models import Submissions
    from apps.notifications.services import notify_user
    from services.docker_service import run_testcase

    try:
        submission = Submissions.objects.select_related('assignment').get(pk=submission_id)
    except Submissions.DoesNotExist:
        logger.error('Submission %s not found', submission_id)
        return

    assignment = submission.assignment
    if submission.status == 'finished':
        logger.info('Submission %s already graded, skipping', submission_id)
        return

    submission.status = 'running'
    submission.save(update_fields=['status'])

    all_testcases = Testcases.objects.filter(assignment=assignment).order_by('order_index')
    total_weight = sum(tc.weight for tc in all_testcases)

    if total_weight == 0:
        submission.status = 'finished'
        submission.total_score = 0
        submission.total_testcases = 0
        submission.passed_testcases = 0
        submission.save()
        return

    config = SandboxConfigs.objects.filter(
        language=submission.language, is_active=True
    ).first()
    timeout = config.timeout_seconds if config else 5
    memory = config.memory_limit_mb if config else 256
    docker_image = config.docker_image if config else None
    cpu_limit = config.cpu_limit if config else 1.0

    passed_count = 0
    total_score = 0
    total_exec_time = 0
    max_memory = 0

    for tc in all_testcases:
        tc_result = run_testcase(
            submission.code_content,
            submission.language,
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

        try:
            _create_submission_detail_with_fallback(
                submission=submission,
                testcase=tc,
                tc_result=tc_result,
                score_earned=score_earned,
            )
        except DataError:
            logger.exception('DataError creating SubmissionDetails for submission=%s testcase=%s', submission_id, tc.pk)
            submission.status = 'error'
            submission.save(update_fields=['status'])
            return

        total_score += score_earned
        total_exec_time += tc_result['execution_time']
        max_memory = max(max_memory, tc_result['memory_usage'])

    if submission.is_late and submission.penalty_applied > 0:
        penalty_amount = total_score * (submission.penalty_applied / 100)
        total_score = max(0, total_score - penalty_amount)

    submission.status = 'finished'
    submission.total_score = round(total_score, 2)
    submission.passed_testcases = passed_count
    submission.total_testcases = all_testcases.count()
    submission.execution_time = round(total_exec_time, 2)
    submission.memory_usage = round(max_memory, 2)
    try:
        submission.save()
    except Exception as exc:
        logger.exception('Failed to save submission %s', submission_id)
        raise self.retry(exc=exc)

    try:
        from .utils import update_assignment_statistics
        update_assignment_statistics(assignment)
    except Exception:
        logger.exception('Failed to update statistics for assignment %s', assignment.pk)

    try:
        notify_user(
            submission.student,
            title=f'Bài nộp đã được chấm: {assignment.title}',
            message=f'Điểm của bạn: {submission.total_score}/{submission.max_score}.',
            link=f'/submissions/detail/{submission.pk}/',
            notification_type='submission_graded',
            actor=assignment.classroom.teacher if assignment.classroom_id else None,
            metadata={'submission_id': submission.pk, 'assignment_id': assignment.pk},
        )
    except Exception:
        logger.exception('Failed to create grading notification for submission %s', submission.pk)

    logger.info(
        'Submission %s graded: %s/%s testcases passed, score=%.2f',
        submission_id, passed_count, all_testcases.count(), total_score,
    )


@shared_task
def check_plagiarism_task(assignment_id, report_id=None, threshold=0.85):
    """Run plagiarism check on all submissions for an assignment."""
    from django.utils import timezone
    from apps.assignments.models import Assignments, PlagiarismReports
    from apps.submissions.models import Submissions
    from services.plagiarism_service import check_plagiarism_batch

    try:
        assignment = Assignments.objects.get(pk=assignment_id)
    except Assignments.DoesNotExist:
        logger.error('Assignment %s not found', assignment_id)
        return []

    report = None
    if report_id:
        report = PlagiarismReports.objects.filter(pk=report_id, assignment=assignment).first()
    if report is None:
        report = PlagiarismReports.objects.create(
            assignment=assignment,
            status='running',
            threshold=threshold,
        )
    else:
        report.status = 'running'
        report.threshold = threshold
        report.error_message = ''
        report.finished_at = None
        report.save(update_fields=['status', 'threshold', 'error_message', 'finished_at'])

    submissions = Submissions.objects.filter(
        assignment=assignment, status='finished'
    ).select_related('student').order_by('-submitted_at')

    seen_students = set()
    latest_submissions = []
    for sub in submissions:
        if not sub.student_id or sub.student_id in seen_students:
            continue
        if not (sub.code_content or '').strip():
            continue
        seen_students.add(sub.student_id)
        latest_submissions.append({
            'id': sub.pk,
            'student_id': sub.student_id,
            'code': sub.code_content or '',
        })

    if len(latest_submissions) < 2:
        report.status = 'finished'
        report.result = []
        report.submissions_count = len(latest_submissions)
        report.pairs_count = 0
        report.suspicious_count = 0
        report.error_message = ''
        report.finished_at = timezone.now()
        report.save(update_fields=[
            'status', 'result', 'submissions_count', 'pairs_count',
            'suspicious_count', 'error_message', 'finished_at',
        ])
        return []

    first_sub = submissions.first()
    language = first_sub.language if first_sub else 'python'
    try:
        results = check_plagiarism_batch(latest_submissions, language)
        for result in results:
            result['is_suspicious'] = result['similarity_score'] >= threshold

        suspicious = [r for r in results if r['is_suspicious']]
        report.status = 'finished'
        report.language = language
        report.result = results
        report.submissions_count = len(latest_submissions)
        report.pairs_count = len(results)
        report.suspicious_count = len(suspicious)
        report.finished_at = timezone.now()
        report.save(update_fields=[
            'status', 'language', 'result', 'submissions_count',
            'pairs_count', 'suspicious_count', 'finished_at',
        ])
    except Exception as exc:
        logger.exception('Failed plagiarism task assignment=%s report=%s', assignment_id, report.pk)
        report.status = 'error'
        report.error_message = str(exc)[:1000]
        report.finished_at = timezone.now()
        report.save(update_fields=['status', 'error_message', 'finished_at'])
        return []
    logger.info(
        'Plagiarism check for assignment %s: %d/%d pairs suspicious',
        assignment_id, len(suspicious), len(results),
    )
    return results
