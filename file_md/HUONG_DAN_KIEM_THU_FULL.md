# 📑 Hướng Dẫn Quy Trình Kiểm Thử Hệ Thống DevLearn
> Tài liệu phục vụ báo cáo chức năng và demo tiến độ với giảng viên.

---

## 🛠 GIAI ĐOẠN 1: THIẾT LẬP (VAI TRÒ GIÁO VIÊN)

### Bước 1: Tạo Lớp học & Thêm Môn học
1. **Truy cập**: Dashboard Giáo viên -> **Tạo lớp học**.
2. **Dữ liệu mẫu**: 
   - **Tên lớp**: `Lập trình Python Thực chiến - Nhóm 01`
   - **Năm học**: `2024-2025` | **Học kỳ**: `Học kỳ 1`.
3. **Thêm Môn học**: Vào lớp vừa tạo -> Chọn mục **Môn học** -> Bấm **Gán môn học** -> Chọn `Lập trình cơ bản (PY101)`.

### Bước 2: Tạo Bài tập (Assignments)
1. **Thao tác**: Vào lớp -> **Bài tập** -> **Tạo bài tập**.
2. **Loại 1: Bài tập Code (Tính giai thừa)**:
   - **Hình thức**: `Lập trình`.
   - **Cách chấm**: `Tự động`.
   - **Đề bài**: Nhập nội dung yêu cầu tính n!.
   - **Mã nguồn mẫu**: Xem **Mục 1** phần Dữ liệu mẫu bên dưới.
   - **Testcase**: Thêm ít nhất 1 testcase (ví dụ: Input `5` -> Output `120`). **Lưu ý: Tích chọn "Test mẫu"**.
3. **Loại 2: Bài tập Quiz (Trắc nghiệm)**:
   - **Hình thức**: `Trắc nghiệm`.
   - **Đề bài**: Bấm **Tải mẫu Excel** -> Điền dữ liệu từ **Mục 2** bên dưới -> Upload file.
4. **Loại 3: Bài tập File (Báo cáo)**:
   - **Hình thức**: `Nộp file`.
   - **Yêu cầu**: Nhập mô tả yêu cầu nộp file `.zip` đồ án.

---

## 👨‍🎓 GIAI ĐOẠN 2: THỰC HIỆN (VAI TRÒ HỌC SINH)

### 1. Tham gia lớp
- Copy **Mã mời** từ lớp học (tài khoản GV).
- Tài khoản Học sinh: Bấm **Nhập mã mời** -> Gửi yêu cầu tham gia.
- Tài khoản Giáo viên: Vào mục **Thành viên** -> **Chờ duyệt** -> Bấm **Duyệt**.

### 2. Làm bài nộp
Học sinh truy cập vào từng bài tập đã tạo ở Giai đoạn 1:

#### 1. Bài tập Code (Tính giai thừa)
```python
import sys

def factorial(n):
    if n == 0: return 1
    return n * factorial(n-1)

if __name__ == "__main__":
    # Đọc dữ liệu từ testcase và in kết quả
    line = sys.stdin.read().strip()
    if line:
        print(factorial(int(line)))
```

#### 2. Bài tập Quiz (Trắc nghiệm)
- **Câu 1**: `Kết quả của biểu thức logic 5 > 3 and 2 < 1 là gì?` -> Chọn: **False**.
- **Câu 2**: `Hàm print() trong Python dùng để làm gì?` -> Chọn: **Xuất dữ liệu ra màn hình**.
- **Câu 3 (Nếu dùng mẫu Excel)**: `Kết quả của 2**3 là bao nhiêu?` -> Chọn: **8**.

#### 3. Bài tập File (Báo cáo/Đồ án)
- **Truy cập**: Tìm tên bài `Báo cáo thuật toán` từ thanh Search Header hoặc vào mục Bài tập của lớp.
- **Dữ liệu test**: 
  - Chuẩn bị 1 file `.zip` (nén một vài file code hoặc text bất kỳ).
  - Upload và bấm **Nộp bài**.

#### 4. Bài thi (Exam)
- Thực hiện tương tự. Lưu ý: Khi vào bài thi, hệ thống sẽ bật chế độ giám sát (Full screen/Tab focus). Nếu bạn thoát tab, giáo viên sẽ nhận được cảnh báo.

---

## ⚖️ GIAI ĐOẠN 3: CHẤM ĐIỂM & TỔNG KẾT (VAI TRÒ GIÁO VIÊN)

### 1. Xem kết quả Tự động (Code & Quiz)
- Vào mục **Bài nộp** của lớp.
- Hệ thống sẽ hiển thị ngay điểm số của HS cho các bài tự động (ví dụ: 10/10).

### 2. Chấm bài Thủ công (Dạng File)
- Click vào bài nộp của HS ở phần "Báo cáo thuật toán".
- Tải file về xem hoặc xem trực tiếp (nếu là PDF/Ảnh).
- Nhập điểm (ví dụ: 8.5) và ghi nhận xét.
- Bấm **Lưu & Chấm điểm**.

### 3. Báo cáo (Sổ điểm)
- Vào tab **Sổ điểm** của lớp để xem bảng tổng hợp kết quả của toàn bộ học sinh.
- Kiểm tra tính năng **Xuất CSV** để tải bảng điểm về Excel.

---

## 📋 DỮ LIỆU MẪU ĐỂ COPY (DATA TEST)

**Mục 1: Mã nguồn mẫu Giai thừa (Giáo viên)**
```python
import sys
def factorial(n):
    return 1 if n == 0 else n * factorial(n-1)
if __name__ == "__main__":
    line = sys.stdin.read().strip()
    if line:
        print(factorial(int(line)))
```

**Mục 2: Dữ liệu Trắc nghiệm (Excel)**
| question | type | points | choice_1 | choice_2 | choice_3 | choice_4 | correct_index |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 5 > 3 and 2 < 1 là? | single_choice | 1.0 | True | False | None | Error | 2 |
| Hàm print() dùng để? | single_choice | 1.0 | Nhập | Xuất | Xóa | Lưu | 2 |
| 2**3 bằng? | single_choice | 1.0 | 6 | 9 | 8 | 16 | 3 |

---

## 💡 ĐIỂM NHẤN TRÌNH BÀY (TIPS FOR DEMO)
1. **Fuzzy Search**: Gõ tìm kiếm lớp hoặc bài tập từ thanh Search ở Navbar để show tính năng tìm kiếm thông minh.
2. **Real-time Status**: Show phần "Duyệt học sinh" để thấy trạng thái 'Chờ duyệt' -> 'Đã duyệt' nhảy ngay, không đợi giáo viên.
3. **Tính minh bạch**: Show phần "Lịch sử tìm kiếm" để chứng minh hệ thống theo dõi hành vi người dùng tốt.
4. **Trải nghiệm**: Show phần "Loading Animation" khi chuyển giữa IDE và Bảng điểm để thấy web mượt mà.
