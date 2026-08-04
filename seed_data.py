import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Profiles
from apps.classrooms.models import Classrooms, ClassroomMembers
from apps.assignments.models import Assignments, Testcases

def create_seed_data():
    print("Seeding database...")
    
    # 1. Create Teacher
    gv_user, created = User.objects.get_or_create(username='gv_demo', defaults={'email': 'gv@demo.com'})
    if created: gv_user.set_password('123456')
    gv_user.save()
    
    gv_profile, _ = Profiles.objects.get_or_create(id=gv_user)
    gv_profile.role = 'teacher'
    gv_profile.status = 'approved'
    gv_profile.save()

    # 2. Create Student
    hs_user, created = User.objects.get_or_create(username='hs_demo', defaults={'email': 'hs@demo.com'})
    if created: hs_user.set_password('123456')
    hs_user.save()

    hs_profile, _ = Profiles.objects.get_or_create(id=hs_user)
    hs_profile.role = 'student'
    hs_profile.status = 'approved'
    hs_profile.save()

    # Create Second Student (for plagiarism)
    hs2_user, created = User.objects.get_or_create(username='hs_demo2', defaults={'email': 'hs2@demo.com'})
    if created: hs2_user.set_password('123456')
    hs2_user.save()

    hs2_profile, _ = Profiles.objects.get_or_create(id=hs2_user)
    hs2_profile.role = 'student'
    hs2_profile.status = 'approved'
    hs2_profile.save()

    # 3. Create Classroom
    classroom, created = Classrooms.objects.get_or_create(
        invite_code='DEMO123',
        defaults={
            'name': 'Lớp học Tự động hóa',
            'teacher': gv_user,
            'status': 'approved',
            'is_active': True,
        }
    )
    
    # Add student to classroom
    ClassroomMembers.objects.get_or_create(
        classroom=classroom,
        student=hs_user,
        defaults={'status': 'approved'}
    )
    ClassroomMembers.objects.get_or_create(
        classroom=classroom,
        student=hs2_user,
        defaults={'status': 'approved'}
    )

    # 4. Create Assignment
    assignment, created = Assignments.objects.get_or_create(
        classroom=classroom,
        title='Bài tập Test Tự động',
        defaults={
            'description': 'Viết chương trình in ra số bạn vừa nhập',
            'submission_mode': 'code',
            'grading_mode': 'auto',
            'score_aggregation_mode': 'best',
            'max_score': 10.0,
            'exam_start_time': timezone.now() - timedelta(days=1),
            'exam_end_time': timezone.now() + timedelta(days=1),
            'allowed_languages': ['python'],
            'is_published': True,
        }
    )

    # 5. Create Testcases
    Testcases.objects.get_or_create(
        assignment=assignment,
        input_data='1',
        expected_output='1',
        defaults={
            'is_sample': True,
            'is_hidden': False,
            'weight': 5,
        }
    )
    
    Testcases.objects.get_or_create(
        assignment=assignment,
        input_data='99',
        expected_output='99',
        defaults={
            'is_sample': False,
            'is_hidden': True,
            'weight': 5,
        }
    )

    print(f"✅ Data seeded successfully!")
    print(f"Teacher: gv_demo / 123456")
    print(f"Student: hs_demo / 123456")
    print(f"Assignment URL ID: {assignment.id}")

if __name__ == '__main__':
    create_seed_data()
