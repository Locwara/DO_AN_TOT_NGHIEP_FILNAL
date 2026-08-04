import os
import django
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Profiles
from apps.classrooms.models import Classrooms, ClassroomMembers, Subjects, ClassroomSubjects, Semesters
from apps.assignments.models import Assignments, Testcases

def update_and_seed():
    print("Bắt đầu cập nhật và sinh dữ liệu...")

    # 1. Update Teacher Names
    teachers = User.objects.filter(profiles__role='teacher')
    for idx, t in enumerate(teachers):
        t.first_name = "Giáo viên"
        t.last_name = str(idx + 1)
        t.save()
        print(f"Cập nhật GV: {t.username} -> {t.first_name} {t.last_name}")

    # Cập nhật cả học sinh để có tên thật thay vì chỉ username
    students = User.objects.filter(profiles__role='student')
    student_names = [("Nguyễn Văn", "A"), ("Trần Thị", "B"), ("Lê Hoàng", "C"), ("Phạm Ngọc", "D"), ("Vũ Đức", "E")]
    for idx, s in enumerate(students):
        if idx < len(student_names):
            s.first_name = student_names[idx][0]
            s.last_name = student_names[idx][1]
        else:
            s.first_name = "Sinh viên"
            s.last_name = str(idx + 1)
        s.save()

    # 2. Update existing subjects & classrooms
    # Tên môn học chuyên ngành
    subject_names = [
        "Nhập môn lập trình",
        "Cấu trúc dữ liệu và giải thuật",
        "Lập trình hướng đối tượng",
        "Cơ sở dữ liệu",
        "Phát triển ứng dụng Web",
        "Trí tuệ nhân tạo",
        "Lập trình di động"
    ]
    
    # Cập nhật các môn hiện có
    existing_subjects = list(Subjects.objects.all())
    for idx, sub in enumerate(existing_subjects):
        if idx < len(subject_names):
            sub.name = subject_names[idx]
            sub.code = f"CT{100 + idx}"
            sub.save()

    # Thêm môn mới
    while len(existing_subjects) < len(subject_names):
        idx = len(existing_subjects)
        new_sub = Subjects.objects.create(
            name=subject_names[idx],
            code=f"CT{100 + idx}",
            description="Môn học chuyên ngành CNTT",
            status='approved'
        )
        existing_subjects.append(new_sub)

    # 3. Create Semesters if not exists
    semester, _ = Semesters.objects.get_or_create(
        code="HK1-2024",
        defaults={
            "name": "Học kỳ 1 năm học 2024-2025",
            "start_date": timezone.now() - timedelta(days=60),
            "end_date": timezone.now() + timedelta(days=120)
        }
    )

    # 4. Update Classrooms
    classroom_names = [
        "Lớp CT101 - Nhóm 01",
        "Lớp CT102 - Nhóm 02",
        "Lớp CT103 - Nhóm 01",
        "Lớp Lập trình Web nâng cao",
        "Lớp Thuật toán chuyên sâu"
    ]
    
    teacher_users = list(User.objects.filter(profiles__role='teacher'))
    if not teacher_users:
        print("Không có giáo viên nào để tạo lớp!")
        return
        
    existing_classrooms = list(Classrooms.objects.all())
    for idx, cls in enumerate(existing_classrooms):
        if idx < len(classroom_names):
            cls.name = classroom_names[idx]
            cls.semester = semester
            cls.save()

    # Thêm lớp mới
    while len(existing_classrooms) < 5:
        idx = len(existing_classrooms)
        new_cls = Classrooms.objects.create(
            name=classroom_names[idx],
            invite_code=f"CODE{random.randint(1000, 9999)}",
            teacher=random.choice(teacher_users),
            status='approved',
            is_active=True,
            semester=semester
        )
        existing_classrooms.append(new_cls)

    # Gắn tất cả học sinh vào các lớp
    for cls in existing_classrooms:
        for student in students:
            ClassroomMembers.objects.get_or_create(
                classroom=cls,
                student=student,
                defaults={'status': 'approved'}
            )
        # Gắn ngẫu nhiên 1-2 môn cho lớp
        for _ in range(random.randint(1, 2)):
            ClassroomSubjects.objects.get_or_create(
                classroom=cls,
                subject=random.choice(existing_subjects)
            )

    # 5. Update and Create Assignments
    assignment_titles = [
        "Bài tập 1: Làm quen với cú pháp",
        "Bài tập 2: Cấu trúc rẽ nhánh và vòng lặp",
        "Thực hành: Mảng và Chuỗi",
        "Đồ án: Quản lý sinh viên",
        "Kiểm tra giữa kỳ: Thuật toán sắp xếp",
        "Bài tập: Lập trình hướng đối tượng cơ bản",
        "Quiz 1: Trắc nghiệm kiến thức nền tảng",
        "Bài tập: Đọc ghi file",
        "Bài tập: Đệ quy",
        "Thi cuối kỳ"
    ]

    existing_assignments = list(Assignments.objects.all())
    for idx, asg in enumerate(existing_assignments):
        if idx < len(assignment_titles):
            asg.title = assignment_titles[idx]
            asg.save()

    # Tạo thêm rất nhiều bài tập vào các lớp
    for cls in existing_classrooms:
        count = Assignments.objects.filter(classroom=cls).count()
        while count < random.randint(3, 6):
            title = random.choice(assignment_titles)
            Assignments.objects.create(
                classroom=cls,
                title=f"{title} - {cls.name}",
                description="Yêu cầu: Hoàn thành đầy đủ các testcase. Mã nguồn phải được tối ưu và trình bày rõ ràng.",
                submission_mode=random.choice(['code', 'file', 'quiz']),
                grading_mode='auto',
                score_aggregation_mode='best',
                max_score=10.0,
                exam_start_time=timezone.now() - timedelta(days=random.randint(1, 10)),
                exam_end_time=timezone.now() + timedelta(days=random.randint(1, 10)),
                allowed_languages=['python', 'c', 'cpp', 'java'],
                is_published=True
            )
            count += 1

    print("✅ Cập nhật và sinh dữ liệu thành công!")

if __name__ == '__main__':
    update_and_seed()
