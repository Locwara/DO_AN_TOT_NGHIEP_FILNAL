from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.assignments.models import Assignments
from apps.administation.utils import get_int_setting
from apps.classrooms.models import ClassroomMembers
from apps.notifications.models import Notifications
from apps.notifications.services import notify_users


class Command(BaseCommand):
    help = 'Send due-soon notifications for published assignments.'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=None, help='Due window in hours.')

    def handle(self, *args, **options):
        now = timezone.now()
        hours = options['hours']
        if hours is None:
            hours = get_int_setting('notifications.due_soon_hours', 24, minimum=1, maximum=336)
        hours = max(1, min(int(hours), 336))
        until = now + timedelta(hours=hours)
        sent = 0
        assignments = Assignments.objects.filter(
            is_published=True,
            due_date__gt=now,
            due_date__lte=until,
        ).select_related('classroom')

        for assignment in assignments:
            marker = f'due_soon:{assignment.pk}:{assignment.due_date.isoformat()}:{hours}'
            if Notifications.objects.filter(
                notification_type='assignment_due_soon',
                metadata__marker=marker,
            ).exists():
                continue
            student_ids = ClassroomMembers.objects.filter(
                classroom=assignment.classroom,
                status='approved',
            ).values_list('student_id', flat=True)
            notify_users(
                student_ids,
                title=f'Sắp đến hạn: {assignment.title}',
                message=f'Bài trong lớp {assignment.classroom.name} sẽ đến hạn lúc {timezone.localtime(assignment.due_date):%d/%m/%Y %H:%M}.',
                link=f'/assignments/{assignment.pk}/',
                notification_type='assignment_due_soon',
                actor=assignment.classroom.teacher,
                metadata={'assignment_id': assignment.pk, 'classroom_id': assignment.classroom_id, 'marker': marker},
            )
            sent += 1

        self.stdout.write(self.style.SUCCESS(f'Sent due-soon notifications for {sent} assignment(s).'))
