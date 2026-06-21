# 🧪 QUY TRÌNH KIỂM THỬ THỦ CÔNG (MANUAL TEST PLAN)
**Dự án**: DevLearn - Hệ thống chấm bài tự động
**Trọng tâm**: Hệ thống Đánh giá, Chấm điểm và UX (Theo `plan_fix_danh_gia.md`)

---

## 🔑 0. CHUẨN BỊ (PREPARATION)
Trước khi test, hãy đảm bảo bạn có ít nhất 2 tài khoản:
1.  **Tài khoản Giáo viên (`gv_demo`)**: Để cấu hình bài tập và xem báo cáo.
2.  **Tài khoản Học sinh (`hs_demo`)**: Để nộp bài và xem kết quả.

---

## 🛡️ 1. BẢO MẬT: CHỐNG RÒ RỈ TESTCASE ẨN (TASK 1.1)
**Mục tiêu**: Học sinh không được thấy Input/Output của testcase ẩn.

*   **Dữ liệu Test (Data)**:
    *   Tạo 1 bài tập có 2 testcases:
        *   TC1: `is_sample=True` (Test mẫu), Input: `1`, Output: `1`.
        *   TC2: `is_hidden=True` (Test ẩn), Input: `99`, Output: `99`.
*   **Quy trình**:
    1.  Dùng `hs_demo` nộp bài code sai (ví dụ: `print(0)`).
    2.  Vào trang **Chi tiết bài nộp**.
*   **Kết quả mong đợi**:
    *   Tại TC1: Hiện đầy đủ "Input: 1", "Expected: 1", "Actual: 0".
    *   Tại TC2: Chỉ hiện trạng thái "Thất bại" (Fail). **KHÔNG** hiện số `99` hay bất kỳ thông tin nào khác.

---

## 📊 2. LOGIC: CHẾ ĐỘ TÍNH ĐIỂM (TASK 1.2)
**Mục tiêu**: Kiểm tra 4 chế độ: Cao nhất, Mới nhất, Đầu tiên, Trung bình.

*   **Dữ liệu Test (Data)**:
    *   Học sinh `hs_demo` nộp 3 lần cho cùng 1 bài tập:
        *   Lần 1: 5.0 điểm.
        *   Lần 2: 9.0 điểm.
        *   Lần 3: 7.0 điểm.
*   **Quy trình**:
    1.  Dùng `gv_demo` vào chỉnh sửa bài tập, thay đổi field **"Cách tính điểm"**.
    2.  Mỗi lần đổi, hãy vào trang **Sổ điểm (Gradebook)** của lớp đó để xem điểm hiển thị.
*   **Kết quả mong đợi**:
    *   Chọn `Best`: Sổ điểm hiện **9.0**.
    *   Chọn `Latest`: Sổ điểm hiện **7.0**.
    *   Chọn `First`: Sổ điểm hiện **5.0**.
    *   Chọn `Average`: Sổ điểm hiện **7.0** (Trung bình cộng).

---

## 💻 3. TÍNH NĂNG: HỖ TRỢ C# & UPLOAD CODE (TASK 2.1, 2.3)
**Mục tiêu**: Biên dịch được C# và nạp code từ file vào IDE.

*   **Dữ liệu Test (Data)**:
    *   File `hello.cs` nội dung:
        ```csharp
        using System;
        class Program {
            static void Main() { Console.WriteLine("Hello DevLearn"); }
        }
        ```
*   **Quy trình**:
    1.  Vào trang làm bài (IDE). Nhấn nút **"📂 Tải file lên"**. Chọn file `hello.cs`.
    2.  Kiểm tra xem code có tự nhảy vào khung soạn thảo không.
    3.  Chọn ngôn ngữ **C#** và nhấn **Nộp bài**.
*   **Kết quả mong đợi**:
    *   IDE nạp code đúng.
    *   Hệ thống chấm bài và trả về kết quả "Hoàn thành" (nếu bài tập yêu cầu in ra Hello DevLearn).

---

## 📑 4. BÁO CÁO: XUẤT EXCEL & THỐNG KÊ (TASK 1.4, 2.2)
**Mục tiêu**: Dữ liệu xuất ra đúng định dạng và trực quan.

*   **Quy trình**:
    1.  Dùng `gv_demo` vào trang **Sổ điểm**. Nhấn nút **"Xuất Excel (.xlsx)"**.
    2.  Mở file bằng Excel/Google Sheets.
    3.  Vào trang **Thống kê bài tập** xem biểu đồ.
*   **Kết quả mong đợi**:
    *   File Excel: Có cột Họ tên, Email, Điểm từng bài. Các ô điểm thấp có màu đỏ, điểm cao màu xanh. Không lỗi font tiếng Việt.
    *   Biểu đồ: Hiện đúng tỉ lệ % người đạt (Pass) và chưa đạt (Fail).

---

## 🔍 5. CHỐNG GIAN LẬN: ĐẠO VĂN (TASK 3.1)
**Mục tiêu**: Phát hiện code giống nhau dù đã đổi tên biến.

*   **Dữ liệu Test (Data)**:
    *   Bài nộp 1 (HS A): `int a = 5; int b = 10; print(a + b);`
    *   Bài nộp 2 (HS B): `int so_thu_nhat = 5; int so_thu_hai = 10; print(so_thu_nhat + so_thu_hai);`
*   **Quy trình**:
    1.  Sau khi HS B nộp bài, GV vào mục **"Kiểm tra đạo văn"**.
*   **Kết quả mong đợi**:
    *   Tỉ lệ đạo văn (Similarity) phải báo cao (> 80%) vì cấu trúc logic hoàn toàn giống hệt nhau, chỉ khác tên biến.

---

## 📧 6. THÔNG BÁO: NHẮC DEADLINE (TASK 2.5)
**Mục tiêu**: Gửi mail cho người chưa nộp bài.

*   **Quy trình**:
    1.  Tạo bài tập có deadline là ngày mai (còn khoảng < 24h).
    2.  Chạy lệnh terminal: `python manage.py send_due_soon_notifications`.
*   **Kết quả mong đợi**:
    *   Kiểm tra tab Terminal hoặc Mail log, thấy hệ thống báo "Sent email to [email học sinh]".

---

## ✅ CHECKLIST HOÀN TẤT
- [ ] Testcase ẩn đã bị giấu hoàn toàn?
- [ ] Điểm trung bình/Cao nhất nhảy đúng khi đổi mode?
- [ ] File Excel mở lên đẹp, không lỗi?
- [ ] Code C# chạy được?
- [ ] Đổi tên biến vẫn bị phát hiện đạo văn?
