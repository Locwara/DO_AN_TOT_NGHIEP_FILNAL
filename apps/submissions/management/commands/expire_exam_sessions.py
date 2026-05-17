from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.submissions.models import ExamEvents, ExamSessions, Submissions
from apps.submissions.tasks import grade_submission_task


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Expire running exam sessions and optionally auto-submit the latest draft.'

    def add_arguments(self, parser):
        parser.add_argument('--auto-submit', action='store_true', help='Create a submission from latest draft when possible.')

    def handle(self, *args, **options):
        now = timezone.now()
        expired_count = 0
        submitted_count = 0
        sessions = ExamSessions.objects.filter(status=ExamSessions.STATUS_RUNNING).select_related('assignment', 'student')
        for session in sessions:
            try:
                assignment = session.assignment
                grace = assignment.exam_grace_seconds or 30
                if not session.ends_at or now <= session.ends_at + timedelta(seconds=grace):
                    continue

                if options['auto_submit'] and session.latest_draft and not session.final_submission_id:
                    submission = Submissions.objects.create(
                        assignment=assignment,
                        student=session.student,
                        code_content=session.latest_draft,
                        language=session.current_language or (assignment.allowed_languages or ['python'])[0],
                        status='pending',
                        max_score=assignment.max_score,
                    )
                    session.final_submission = submission
                    session.status = ExamSessions.STATUS_AUTO_SUBMITTED
                    session.submitted_at = now
                    session.save(update_fields=['final_submission', 'status', 'submitted_at', 'updated_at'])
                    ExamEvents.objects.create(
                        session=session,
                        event_type='auto_submitted_by_command',
                        metadata={'submission_id': submission.pk},
                    )
                    grade_submission_task.delay(submission.pk)
                    submitted_count += 1
                else:
                    session.status = ExamSessions.STATUS_EXPIRED
                    session.save(update_fields=['status', 'updated_at'])
                    ExamEvents.objects.create(session=session, event_type='expired_by_command', metadata={})
                    expired_count += 1
            except Exception as exc:
                logger.exception('Failed to expire exam session %s', session.pk)
                ExamEvents.objects.create(
                    session=session,
                    event_type='expire_command_error',
                    metadata={'error': str(exc)[:1000]},
                )

        self.stdout.write(self.style.SUCCESS(
            f'Expired {expired_count} session(s), auto-submitted {submitted_count} session(s).'
        ))
