import os
import django
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.classrooms.models import Classrooms, ClassroomSubjects, SubjectMaterials

def seed_materials():
    cls = Classrooms.objects.filter(invite_code="VIPCLASS").first()
    if not cls:
        print("Không tìm thấy lớp VIPCLASS")
        return
        
    teacher = cls.teacher
    links = ClassroomSubjects.objects.filter(classroom=cls)
    
    if not links:
        print("Lớp chưa có môn học nào")
        return

    # Dummy file content
    dummy_pdf_content = b"%PDF-1.4\n%...\n(This is a dummy PDF file for testing)\n"
    dummy_doc_content = b"This is a dummy DOCX file content."
    
    for link in links:
        subject_name = link.subject.name.lower()
        if "cấu trúc" in subject_name:
            # Tạo tài liệu môn CTDL
            SubjectMaterials.objects.create(
                classroom_subject=link,
                title="Slide Bài 1: Tổng quan về CTDL",
                description="Khái niệm cơ bản về cấu trúc dữ liệu, độ phức tạp thuật toán O(n).",
                uploaded_by=teacher,
                file=ContentFile(dummy_pdf_content, name="Bai1_TongQuanCTDL.pdf")
            )
            SubjectMaterials.objects.create(
                classroom_subject=link,
                title="Tài liệu tham khảo: Ngăn xếp & Hàng đợi",
                description="Tài liệu đọc thêm hướng dẫn chi tiết cách cài đặt Stack, Queue bằng mảng và danh sách liên kết.",
                uploaded_by=teacher,
                file=ContentFile(dummy_doc_content, name="TaiLieu_StackQueue.docx")
            )
            SubjectMaterials.objects.create(
                classroom_subject=link,
                title="Slide Bài 2: Cây nhị phân",
                description="Phân loại cây, cách duyệt cây nhị phân (Preorder, Inorder, Postorder).",
                uploaded_by=teacher,
                file=ContentFile(dummy_pdf_content, name="Bai2_CayNhiPhan.pdf")
            )
            print(f"Đã thêm tài liệu cho môn: {link.subject.name}")
            
        elif "đối tượng" in subject_name:
            # Tạo tài liệu môn OOP
            SubjectMaterials.objects.create(
                classroom_subject=link,
                title="Slide Chương 1: Giới thiệu OOP",
                description="4 tính chất cơ bản của lập trình hướng đối tượng (Tính đóng gói, Kế thừa, Đa hình, Trừu tượng).",
                uploaded_by=teacher,
                file=ContentFile(dummy_pdf_content, name="Chuong1_GioiThieuOOP.pdf")
            )
            SubjectMaterials.objects.create(
                classroom_subject=link,
                title="Bài giảng: Tính Đa hình (Polymorphism)",
                description="Cách sử dụng Overriding và Overloading trong thực tế.",
                uploaded_by=teacher,
                file=ContentFile(dummy_pdf_content, name="BaiGiang_DaHinh.pdf")
            )
            print(f"Đã thêm tài liệu cho môn: {link.subject.name}")

    print("Hoàn tất thêm tài liệu mẫu!")

if __name__ == '__main__':
    seed_materials()
