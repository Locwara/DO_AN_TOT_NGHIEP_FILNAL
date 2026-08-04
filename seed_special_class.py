import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.classrooms.models import Classrooms, ClassroomMembers, Subjects, ClassroomSubjects, Semesters, Announcements
from apps.assignments.models import Assignments

def seed_special_class():
    # Lấy giáo viên
    teacher = User.objects.filter(profiles__role='teacher').first()
    if not teacher:
        print("Không tìm thấy giáo viên")
        return
    
    # Lấy học kỳ
    semester = Semesters.objects.first()

    # Tạo Lớp học mới
    cls = Classrooms.objects.create(
        name="Lớp CT201 - Lập trình OOP & Cấu trúc dữ liệu",
        description="Lớp học chuyên sâu về Lập trình hướng đối tượng và Cấu trúc dữ liệu, thuật toán.",
        invite_code="VIPCLASS",
        password="123",
        teacher=teacher,
        school_year="2024-2025",
        semester_term="Học kỳ 1",
        status="approved",
        is_active=True
    )
    print(f"Đã tạo lớp: {cls.name} (Mã: VIPCLASS)")

    # Thêm toàn bộ học sinh vào lớp
    students = User.objects.filter(profiles__role='student')
    for student in students:
        ClassroomMembers.objects.create(
            classroom=cls,
            student=student,
            status='approved'
        )

    # Lấy 2 môn học
    sub1 = Subjects.objects.filter(name__icontains="Cấu trúc").first()
    sub2 = Subjects.objects.filter(name__icontains="hướng đối tượng").first()
    
    if not sub1: sub1 = Subjects.objects.create(code="CT_CTDL", name="Cấu trúc dữ liệu", status='approved', is_active=True)
    if not sub2: sub2 = Subjects.objects.create(code="CT_OOP", name="Lập trình hướng đối tượng", status='approved', is_active=True)

    # Gán môn học cho lớp
    cs1 = ClassroomSubjects.objects.create(classroom=cls, subject=sub1, semester=semester, assigned_by=teacher)
    cs2 = ClassroomSubjects.objects.create(classroom=cls, subject=sub2, semester=semester, assigned_by=teacher)
    
    # Sinh bài tập cho Môn 1 (Cấu trúc dữ liệu)
    Assignments.objects.create(classroom=cls, classroom_subject=cs1, title="Bài tập 1: Mảng và Danh sách liên kết", submission_mode="code", grading_mode="auto", max_score=10, is_published=True, start_date=timezone.now(), due_date=timezone.now() + timedelta(days=7))
    Assignments.objects.create(classroom=cls, classroom_subject=cs1, title="Bài tập 2: Stack và Queue", submission_mode="code", grading_mode="auto", max_score=10, is_published=True, start_date=timezone.now(), due_date=timezone.now() + timedelta(days=7))
    Assignments.objects.create(classroom=cls, classroom_subject=cs1, title="Bài tập 3: Cây nhị phân tìm kiếm", submission_mode="code", grading_mode="auto", max_score=10, is_published=True, start_date=timezone.now(), due_date=timezone.now() + timedelta(days=7))
    Assignments.objects.create(classroom=cls, classroom_subject=cs1, title="Thi cuối kỳ: Thuật toán đồ thị", submission_mode="file", grading_mode="manual", max_score=10, is_published=True, start_date=timezone.now(), due_date=timezone.now() + timedelta(days=2))

    # Sinh bài tập cho Môn 2 (OOP)
    Assignments.objects.create(classroom=cls, classroom_subject=cs2, title="Bài tập 1: Lớp và Đối tượng", submission_mode="code", grading_mode="auto", max_score=10, is_published=True, start_date=timezone.now(), due_date=timezone.now() + timedelta(days=7))
    Assignments.objects.create(classroom=cls, classroom_subject=cs2, title="Bài tập 2: Tính kế thừa và Đa hình", submission_mode="code", grading_mode="auto", max_score=10, is_published=True, start_date=timezone.now(), due_date=timezone.now() + timedelta(days=7))
    Assignments.objects.create(classroom=cls, classroom_subject=cs2, title="Bài tập 3: Interface và Abstract Class", submission_mode="code", grading_mode="auto", max_score=10, is_published=True, start_date=timezone.now(), due_date=timezone.now() + timedelta(days=7))
    Assignments.objects.create(classroom=cls, classroom_subject=cs2, title="Đồ án môn học: Hệ thống quản lý Thư viện (OOP)", submission_mode="file", grading_mode="manual", max_score=10, is_published=True, start_date=timezone.now(), due_date=timezone.now() + timedelta(days=14))

    print("Đã tạo 8 bài tập/bài thi cho 2 môn học!")

    # Sinh Bảng tin
    Announcements.objects.create(
        classroom=cls,
        teacher=teacher,
        title="Chào mừng các em đến với lớp Lập trình CT201",
        content="Lớp chúng ta sẽ bắt đầu học từ tuần sau. Các em chú ý theo dõi lịch học và hoàn thành các bài tập cơ bản trên hệ thống để làm quen với môi trường chấm code tự động nhé.",
        is_pinned=True
    )
    Announcements.objects.create(
        classroom=cls,
        teacher=teacher,
        title="Thông báo: Thay đổi lịch nộp Đồ án OOP",
        content="Do tuần tới có lịch nghỉ lễ nên deadline nộp Đồ án môn OOP sẽ được gia hạn thêm 3 ngày. Chúc các em làm bài tốt!",
        is_pinned=False
    )
    Announcements.objects.create(
        classroom=cls,
        teacher=teacher,
        title="Tài liệu tham khảo Cấu trúc dữ liệu",
        content="Thầy vừa tải lên slide bài giảng chương Cây nhị phân. Các em vào phần Tài liệu môn học để tải về xem trước khi lên lớp nhé.",
        is_pinned=False
    )
    
    print("Đã tạo 3 thông báo bảng tin!")
    print("Hoàn tất!")

if __name__ == '__main__':
    seed_special_class()
