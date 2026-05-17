import os

from django.core.management.base import BaseCommand

from apps.administation.models import ServerMetrics
from apps.submissions.models import Submissions


class Command(BaseCommand):
    help = 'Collect lightweight server/sandbox metrics for the admin dashboard.'

    def handle(self, *args, **options):
        try:
            load_1m = os.getloadavg()[0]
        except (AttributeError, OSError):
            load_1m = 0
        running = Submissions.objects.filter(status='running').count()
        pending = Submissions.objects.filter(status='pending').count()
        ServerMetrics.objects.create(
            cpu_usage=round(load_1m, 2),
            active_containers=running,
            queue_length=pending,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Recorded metrics: load={load_1m:.2f}, running={running}, pending={pending}.'
        ))
