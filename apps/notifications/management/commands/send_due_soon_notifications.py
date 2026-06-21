from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from apps.assignments.models import Assignments
from apps.classrooms.models import ClassroomMembers
from apps.submissions.models import Submissions
from apps.notifications.models import Notifications
from apps.notifications.services import notify_users
from apps.administation.utils import get_bool_setting, get_int_setting

class Command(BaseCommand):
    help = 'Send email and system notifications for assignments due soon (e.g. in 24 hours)'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=None, help='Due window in hours (default 24)')
        parser.add_argument('--dry-run', action='store_true', help='Print instead of sending emails')

    def handle(self, *args, **options):
        # Check if feature is enabled in system settings
        if not get_bool_setting('notifications.email_due_soon_enabled', True):
            self.stdout.write(self.style.WARNING('Email notifications are disabled in SystemSettings.'))
            return

        now = timezone.now()
        hours = options['hours']
        if hours is None:
            hours = get_int_setting('notifications.due_soon_hours', 24)
        
        due_soon_limit = now + timedelta(hours=hours)
        
        # Find published assignments due within the window
        assignments = Assignments.objects.filter(
            is_published=True,
            due_date__gt=now,
            due_date__lte=due_soon_limit
        ).select_related('classroom', 'classroom__teacher')

        self.stdout.write(f"Found {assignments.count()} assignments due in {hours} hours.")

        for assignment in assignments:
            # Marker to prevent double-sending notifications for the same state
            marker = f'due_soon:{assignment.pk}:{assignment.due_date.isoformat()}:{hours}'
            
            # Find students who haven't submitted
            members = ClassroomMembers.objects.filter(
                classroom=assignment.classroom,
                status='approved'
            ).select_related('student')
            
            notified_students_ids = []
            
            for member in members:
                student = member.student
                
                # Check if system notification already sent for this marker
                if Notifications.objects.filter(
                    recipient=student,
                    notification_type='assignment_due_soon',
                    metadata__marker=marker,
                ).exists():
                    continue

                has_submission = Submissions.objects.filter(
                    assignment=assignment,
                    student=student
                ).exclude(status='error').exists()

                if not has_submission:
                    # 1. Send Email
                    if student.email:
                        subject = f'[DevLearn] Sắp hết hạn nộp bài: {assignment.title}'
                        due_str = timezone.localtime(assignment.due_date).strftime('%H:%M %d/%m/%Y')
                        message = f"""Chào {student.get_full_name() or student.username},

Bài tập "{assignment.title}" của lớp {assignment.classroom.name} sẽ hết hạn vào {due_str}.

Bạn chưa nộp bài tập này. Vui lòng hoàn thành và nộp bài trước thời hạn.

Link bài tập: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/assignments/{assignment.pk}/

Trân trọng,
Đội ngũ DevLearn"""
                        
                        if options['dry_run']:
                            self.stdout.write(f"[DRY-RUN] Would send email to {student.email} for assignment {assignment.pk}")
                        else:
                            try:
                                send_mail(
                                    subject,
                                    message,
                                    settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@devlearn.local',
                                    [student.email],
                                    fail_silently=False,
                                )
                                self.stdout.write(self.style.SUCCESS(f"Sent email notification to {student.email}"))
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"Failed to send email to {student.email}: {str(e)}"))
                    
                    # 2. Add to internal notification queue
                    if not options['dry_run']:
                        notified_students_ids.append(student.pk)

            # 3. Bulk Create System Notifications
            if notified_students_ids:
                notify_users(
                    notified_students_ids,
                    title=f'Sắp đến hạn: {assignment.title}',
                    message=f'Bài trong lớp {assignment.classroom.name} sẽ đến hạn lúc {timezone.localtime(assignment.due_date):%d/%m/%Y %H:%M}.',
                    link=f'/assignments/{assignment.pk}/',
                    notification_type='assignment_due_soon',
                    actor=assignment.classroom.teacher,
                    metadata={'assignment_id': assignment.pk, 'classroom_id': assignment.classroom_id, 'marker': marker},
                )
                self.stdout.write(self.style.SUCCESS(f"Sent {len(notified_students_ids)} internal notifications for assignment {assignment.pk}"))
