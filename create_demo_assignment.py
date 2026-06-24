import os
import sys
from datetime import timedelta
from django.utils import timezone

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.classrooms.models import Classrooms
from apps.assignments.models import Assignments, Testcases
from apps.administation.models import ProgrammingLanguages
from django.contrib.auth import get_user_model

User = get_user_model()

def create_demo_assignment():
    try:
        # Find the classroom
        classroom = Classrooms.objects.filter(name__icontains='DSK19DMO').first()
        if not classroom:
            classroom = Classrooms.objects.first()
            if not classroom:
                print("No classroom found.")
                return
            print(f"Classroom DSK19DMO not found. Using {classroom.name} instead.")

        teacher = User.objects.filter(is_superuser=True).first()
        if not teacher:
            teacher = User.objects.first()

        # Create the assignment
        assignment = Assignments.objects.create(
            classroom=classroom,
            created_by=teacher,
            title='[Demo] Bài tập In ra Hello World C#',
            description='Hãy viết chương trình in ra chữ "Hello, World!" bằng ngôn ngữ C#.',
            instructions='Sử dụng `Console.WriteLine` để in ra chuỗi chính xác.',
            due_date=timezone.now() + timedelta(days=7),
            max_score=100.0,
            submission_mode='code',
            is_published=True,
        )

        # Allow C# and python languages
        assignment.allowed_languages = ['csharp', 'python']
        assignment.save()

        # Create a testcase
        Testcases.objects.create(
            assignment=assignment,
            name='Test Mẫu',
            input_data='',
            expected_output='Hello, World!',
            weight=1.0,
            is_hidden=False,
            is_sample=True,
            order_index=1
        )

        Testcases.objects.create(
            assignment=assignment,
            name='Test Ẩn',
            input_data='',
            expected_output='Hello, World!',
            weight=1.0,
            is_hidden=True,
            is_sample=False,
            order_index=2
        )

        print(f"Created assignment: {assignment.title} (ID: {assignment.pk}) in classroom {classroom.name}.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    create_demo_assignment()
