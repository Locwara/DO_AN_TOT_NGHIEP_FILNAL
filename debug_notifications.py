import os
import sys

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from datetime import timedelta
from django.utils import timezone
from apps.assignments.models import Assignments
from apps.classrooms.models import ClassroomMembers
from apps.submissions.models import Submissions

now = timezone.now()
due_soon_limit = now + timedelta(hours=24)
        
# Find published assignments due within 24h
assignments = Assignments.objects.filter(
    is_published=True,
    due_date__gt=now,
    due_date__lte=due_soon_limit
).select_related('classroom')

print(f"Found {assignments.count()} assignments due soon.")

for assignment in assignments:
    print(f"Processing assignment: {assignment.title} (ID: {assignment.pk})")
    # Find students who haven't submitted
    members = ClassroomMembers.objects.filter(
        classroom=assignment.classroom,
        status='approved'
    ).select_related('student')
    
    print(f"  Approved members: {members.count()}")
    for member in members:
        student = member.student
        print(f"  Checking student: {student.username} ({student.email})")
        
        has_submission = Submissions.objects.filter(
            assignment=assignment,
            student=student
        ).exclude(status='error').exists()
        
        print(f"    Has submission: {has_submission}")

        if not has_submission and student.email:
            print(f"    WOULD SEND EMAIL TO {student.email}")
