from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from apps.assignments.models import Assignments
from apps.classrooms.models import ClassroomMembers
from apps.submissions.models import Submissions
from apps.administation.utils import get_bool_setting

class Command(BaseCommand):
    help = 'Send email notifications for assignments due in 24 hours'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Print instead of sending emails')

    def handle(self, *args, **options):
        # Check if feature is enabled in system settings
        if not get_bool_setting('notifications.email_due_soon_enabled', True):
            self.stdout.write(self.style.WARNING('Email notifications are disabled in SystemSettings.'))
            return

        now = timezone.now()
        due_soon_limit = now + timedelta(hours=24)
        
        # Find published assignments due within 24h
        assignments = Assignments.objects.filter(
            is_published=True,
            due_date__gt=now,
            due_date__lte=due_soon_limit
        ).select_related('classroom')

        self.stdout.write(f"Found {assignments.count()} assignments due soon.")

        for assignment in assignments:
            # Find students who haven't submitted
            members = ClassroomMembers.objects.filter(
                classroom=assignment.classroom,
                status='approved'
            ).select_related('student')
            
            for member in members:
                student = member.student
                if not student.email:
                    continue
                
                has_submission = Submissions.objects.filter(
                    assignment=assignment,
                    student=student
                ).exclude(status='error').exists()

                if not has_submission:
                    subject = f'[DevLearn] Sắp hết hạn nộp bài: {assignment.title}'
                    message = f"""Chào {student.get_full_name() or student.username},

Bài tập "{assignment.title}" của lớp {assignment.classroom.name} sẽ hết hạn vào {assignment.due_date.strftime('%H:%M %d/%m/%Y')}.

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
                                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@devlearn.edu.vn',
                                [student.email],
                                fail_silently=False,
                            )
                            self.stdout.write(self.style.SUCCESS(f"Sent notification to {student.email}"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Failed to send email to {student.email}: {str(e)}"))
