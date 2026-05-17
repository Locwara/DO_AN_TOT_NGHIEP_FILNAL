from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.administation.utils import get_int_setting
from apps.notifications.services import notify_admins
from apps.submissions.models import Submissions


class Command(BaseCommand):
    help = 'Notify admins about submissions stuck in running state.'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=None, help='Running threshold in minutes.')

    def handle(self, *args, **options):
        threshold_minutes = options['minutes'] or get_int_setting(
            'sandbox.zombie_threshold_minutes',
            default=15,
            minimum=1,
            maximum=1440,
        )
        cutoff = timezone.now() - timedelta(minutes=threshold_minutes)
        zombies = Submissions.objects.filter(status='running', submitted_at__lt=cutoff).select_related('assignment', 'student')
        count = zombies.count()
        for submission in zombies[:20]:
            notify_admins(
                title='Sandbox task có thể bị treo',
                message=f'Submission #{submission.pk} của {submission.student} đang running quá {threshold_minutes} phút.',
                link='/administration/sandbox-monitor/',
                notification_type='sandbox_zombie_detected',
                metadata={'submission_id': submission.pk, 'assignment_id': submission.assignment_id},
            )
        self.stdout.write(self.style.SUCCESS(f'Detected {count} possible zombie submission(s).'))
