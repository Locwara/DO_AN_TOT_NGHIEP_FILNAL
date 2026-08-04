import os
import django
import random
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.classrooms.models import Classrooms, ClassroomMembers
from apps.assignments.models import Assignments
from apps.submissions.models import Submissions, QuizAttempts

classroom_id = 36
classroom = Classrooms.objects.get(pk=classroom_id)

members = ClassroomMembers.objects.filter(classroom=classroom, status='approved').select_related('student')
assignments = Assignments.objects.filter(classroom=classroom)

for member in members:
    for assignment in assignments:
        student = member.student
        
        if random.random() < 0.8:
            score = round(random.uniform(3.0, 10.0), 1)
            
            Submissions.objects.filter(student=student, assignment=assignment).delete()
            sub_status = random.choice(['finished', 'finished', 'finished', 'pending', 'error'])
            if sub_status == 'finished':
                Submissions.objects.create(
                    student=student,
                    assignment=assignment,
                    status='finished',
                    total_score=score,
                    submitted_at=timezone.now() - timezone.timedelta(days=random.randint(1, 10)),
                    graded_at=timezone.now() - timezone.timedelta(days=random.randint(0, 1))
                )
            else:
                Submissions.objects.create(
                    student=student,
                    assignment=assignment,
                    status=sub_status,
                    total_score=None,
                    submitted_at=timezone.now() - timezone.timedelta(days=random.randint(1, 10))
                )

print("Mock grades generated successfully!")
