# 🧪 QUY TRÌNH KIỂM THỬ THỦ CÔNG TOÀN DIỆN (MANUAL TEST PLAN)
**Dự án**: DevLearn - Hệ thống chấm bài tự động
**Trọng tâm**: Đảm bảo hệ thống đáp ứng 100% các yêu cầu của giáo viên (Tham chiếu: `danh_gia.md`).

---

## 🔑 0. CHUẨN BỊ (PREPARATION)
Trước khi test, hãy đảm bảo bạn có ít nhất 2 tài khoản:
1.  **Tài khoản Giáo viên (`gv_demo`)**: Để cấu hình bài tập, tạo testcase, chấm điểm và xem báo cáo.
2.  **Tài khoản Học sinh (`hs_demo`)**: Để nộp bài và xem kết quả.

---

## 🛠️ 1. THỰC THI MÃ, SANDBOX & NGÔN NGỮ (YÊU CẦU 1)
**Mục tiêu**: Đảm bảo hệ thống chạy được đa ngôn ngữ, giới hạn tài nguyên và trả đúng trạng thái.

*   **1.1 Hỗ trợ đa ngôn ngữ và nộp file**:
    *   **Quy trình**: Đăng nhập `hs_demo`, tạo bài code bằng Python, C++, và C#. Nộp bài bằng cách copy/paste code hoặc tải file `.cs`, `.cpp` lên IDE.
    *   **Kết quả mong đợi**: IDE nạp đúng code từ file; code biên dịch và chạy thành công, trả về kết quả Accepted (nếu logic đúng).
*   **1.2 Giới hạn tài nguyên (Timeout & Memory)**:
    *   **Quy trình**: Cấu hình timeout bài tập là 2s. Học sinh nộp code chứa vòng lặp vô hạn (VD Python: `while True: pass`).
    *   **Kết quả mong đợi**: Trạng thái báo `Time Limit Exceeded` (TLE).
*   **1.3 Các lỗi thực thi**:
    *   **Quy trình**: Học sinh nộp code lỗi cú pháp (sai dấu, thiếu thư viện) và code lỗi runtime (chia cho 0).
    *   **Kết quả mong đợi**: Trả về đúng trạng thái `Compilation Error` (CE) và `Runtime Error` (RE).

---

## ⚙️ 2. QUẢN LÝ TESTCASE VÀ ĐIỂM SỐ (YÊU CẦU 2 & 3)
**Mục tiêu**: Testcase ẩn/hiện, trọng số điểm.

*   **2.1 Bảo mật Testcase Ẩn**:
    *   **Quy trình**: Tạo 2 testcase: TC1 là Sample, TC2 là Hidden. `hs_demo` nộp code sai.
    *   **Kết quả mong đợi**: TC1 hiển thị đầy đủ Input/Output. TC2 **chỉ hiện trạng thái Pass/Fail**, tuyệt đối không lộ Input/Output.
*   **2.2 Trọng số Testcase (Weight)**:
    *   **Quy trình**: Cài đặt bài tập có 2 testcase: TC1 (weight 2), TC2 (weight 8). Điểm tối đa bài là 10. Học sinh nộp code chỉ đúng TC1.
    *   **Kết quả mong đợi**: Điểm hệ thống chấm là 2.0/10.0 (tính theo trọng số).

---

## ⏱️ 3. QUẢN LÝ PHIÊN THI VÀ TÍNH ĐIỂM (YÊU CẦU 4)
**Mục tiêu**: Thời gian mở/đóng, giới hạn nộp và chế độ điểm.

*   **3.1 Thời gian và Giới hạn lần nộp**:
    *   **Quy trình**: Cài đặt bài tập có `max_attempts = 2` và đóng lúc 10:00 AM.
    *   **Kết quả mong đợi**: Sau khi nộp 2 lần, nút Nộp bài bị khóa. Sau 10:00 AM, học sinh không thể truy cập hoặc nộp bài.
*   **3.2 Chế độ tổng hợp điểm (Aggregation Mode)**:
    *   **Quy trình**: `hs_demo` nộp bài 3 lần với điểm lần lượt: 5, 9, 7. `gv_demo` thay đổi chế độ tính điểm của bài tập sang `Best`, `Latest`, `First`, `Average`.
    *   **Kết quả mong đợi**: Sổ điểm hiển thị lần lượt: 9.0 (Best), 7.0 (Latest), 5.0 (First), 7.0 (Average).

---

## 📈 4. DASHBOARD & THỐNG KÊ (YÊU CẦU 5 & 6)
**Mục tiêu**: Sổ điểm realtime, xuất Excel, đồ thị.

*   **4.1 Sổ điểm (Gradebook) & Giám sát**:
    *   **Quy trình**: Mở trang Sổ điểm và trang Giám sát phiên thi (`gv_demo`) trên một trình duyệt. Đăng nhập `hs_demo` ở trình duyệt khác và nộp bài.
    *   **Kết quả mong đợi**: Sổ điểm và danh sách giám sát của giáo viên tự động nhảy kết quả mới (sau ~10-30s) mà không cần f5 tải lại trang.
*   **4.2 Xuất báo cáo Excel**:
    *   **Quy trình**: Tại trang Sổ điểm, nhấn "Xuất Excel".
    *   **Kết quả mong đợi**: File `.xlsx` có đầy đủ thông tin, màu sắc rõ ràng (xanh/đỏ), không lỗi font.
*   **4.3 Thống kê Testcase & Phổ điểm**:
    *   **Quy trình**: Vào trang "Thống kê" của bài tập.
    *   **Kết quả mong đợi**: Biểu đồ Pass/Fail hiển thị đúng tỉ lệ. Có thống kê cho thấy testcase nào bị học sinh sai nhiều nhất.

---

## 🕵️ 5. PHÁT HIỆN ĐẠO VĂN (YÊU CẦU 7)
**Mục tiêu**: Chống gian lận bằng AST và k-gram.

*   **5.1 Thuật toán đạo văn**:
    *   **Quy trình**: Học sinh A nộp code. Học sinh B nộp code tương tự nhưng đổi toàn bộ tên biến và thêm/xóa khoảng trắng/comment. `gv_demo` chạy kiểm tra đạo văn.
    *   **Kết quả mong đợi**: Hệ thống báo độ tương đồng (Similarity) rất cao (>80%), cảnh báo (highlight đỏ) danh sách cặp sinh viên vi phạm.

---

## 📝 6. HỖ TRỢ CHẤM BÀI (YÊU CẦU 8 & KHÁC)
**Mục tiêu**: Chấm thủ công và Email nhắc nhở.

*   **6.1 Chấm thủ công bằng Rubric**:
    *   **Quy trình**: Cài đặt bài tập có Rubric "Code sạch" (2 điểm). `hs_demo` nộp bài được tự động chấm 8 điểm (qua testcase). `gv_demo` vào trang chấm điểm, cho điểm Rubric là 1 và viết comment.
    *   **Kết quả mong đợi**: Điểm tổng của học sinh cập nhật thành 9 điểm. Học sinh xem được comment của giáo viên ngay trên dòng code tương ứng.
*   **6.2 Nhắc Deadline (Email Notification)**:
    *   **Quy trình**: Có bài tập sắp hết hạn (<24h) và `hs_demo` chưa nộp. Chạy lệnh cron/management command nhắc nhở.
    *   **Kết quả mong đợi**: Hệ thống gửi In-app notification và gửi Email thành công tới địa chỉ của học sinh.

---

## 🤖 7. TEST TỰ ĐỘNG END-TO-END BẰNG PLAYWRIGHT
**Mục tiêu**: Tự động hóa quá trình Login, truy cập bài tập và submit code để kiểm tra tốc độ phản hồi và logic của Sandbox.

*   **7.1 Chạy toàn bộ kịch bản tự động**:
    *   **Quy trình**: Mở terminal ở thư mục dự án và chạy duy nhất 1 lệnh:
        ```bash
        ./run_all.sh
        ```
    *   **Lệnh này sẽ tự động làm gì?**
        1. Gọi file `seed_data.py` để tạo Data: `gv_demo`, `hs_demo`, lớp học, và 1 bài tập có sẵn 2 testcases.
        2. Chạy server Django ngầm tại `127.0.0.1:8000`.
        3. Kích hoạt `e2e_test_playwright.py` mở trình duyệt Chromium lên.
        4. Tự động thao tác Login, vào làm bài, gõ code, ấn Confirm popup.
        5. Đợi kết quả từ Server qua API `/submissions/submit/` và bắt điểm 10/10.
        6. Chụp lại ảnh màn hình bằng chứng thành `test_result.png` và tắt server dọn dẹp.
    *   **Kết quả mong đợi**: Trình duyệt mở lên và tự thao tác, terminal in ra dòng chữ báo cáo `=> Submission completed successfully!` và điểm số `10/10`.

---

## ✅ CHECKLIST TỔNG KẾT
- [ ] Sandbox (Docker) ngắt lệnh thành công khi TLE?
- [ ] Testcase ẩn bị giấu hoàn toàn dữ liệu?
- [ ] Trọng số testcase tính điểm chính xác?
- [ ] Thay đổi cách tính điểm (Best/Latest...) tự động cập nhật sổ điểm?
- [ ] File Excel xuất ra đúng chuẩn format?
- [ ] Code C# (upload từ file) chạy đúng?
- [ ] Hệ thống bắt được code đạo văn đổi tên biến?
- [ ] Giáo viên chấm được điểm Rubric thủ công?
- [ ] 🤖 Chạy script tự động Playwright mượt mà, trả về kết quả đúng?
