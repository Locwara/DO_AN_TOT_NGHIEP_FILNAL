# Kế hoạch Hoàn thiện Số liệu Báo cáo Đồ án (Final Report Plan)

Bản kế hoạch này liệt kê chi tiết các bước cần lập trình và thực thi nhằm thu thập số liệu thực tế (định lượng), đáp ứng các yêu cầu khắt khe từ Giảng viên hướng dẫn trước khi đưa vào file Word báo cáo.

---

## 1. Giai đoạn 1: Đo lường khả năng chịu tải của Sandbox (Benchmark)
**Mục tiêu:** Trả lời câu hỏi *"Thời gian phản hồi trung bình của Sandbox khi có N submission đồng thời?"*

*   **Bước 1.1:** Cài đặt công cụ benchmark chuyên dụng (ví dụ: `locust` hoặc viết kịch bản Python đa luồng `concurrent.futures` thực sự gọi vào hàm `execute_code`).
    *   *Đã hoàn thành:* Script được lưu tại `quyen_bao_cao/plan_final_report/giai_doan_1/benchmark_sandbox.py`.
*   **Bước 1.2:** Chuẩn bị payload (mã nguồn) đa dạng:
    *   Mã nguồn thực thi nhanh (in Hello World).
    *   Mã nguồn tốn thời gian (sắp xếp mảng, vòng lặp lớn nhưng không quá timeout).
*   **Bước 1.3:** Thực thi kịch bản giả lập 10, 50, và 100 lượt nộp bài (concurrent requests) cùng lúc vào Sandbox.
    *   *Cách chạy:* Mở Terminal, trỏ vào thư mục gốc `src/Websitedayvahoclaptrinh`, kích hoạt môi trường ảo và gõ lệnh:
    *   Chạy 50 submission đồng thời (Python): `python quyen_bao_cao/plan_final_report/giai_doan_1/benchmark_sandbox.py -c 20 -n 50 -l python`
    *   Chạy 20 submission đồng thời (C++): `python quyen_bao_cao/plan_final_report/giai_doan_1/benchmark_sandbox.py -c 10 -n 20 -l cpp`
*   **Bước 1.4:** Đo lường và ghi nhận số liệu:
    *   Tỉ lệ nộp bài thành công (Pass rate).
    *   Thời gian phản hồi trung bình (Average Response Time).
    *   Lưu lại các biểu đồ/log kết quả để chèn vào báo cáo.

## 2. Giai đoạn 2: Đánh giá độ chính xác Thuật toán Đạo văn (Winnowing)
**Mục tiêu:** Trả lời câu hỏi *"Độ chính xác (Precision/Recall) của thuật toán Winnowing? Số trường hợp dương tính giả?"*

*   **Bước 2.1:** Tạo một bộ dữ liệu (Dataset) nhỏ thực tế gồm các file code (đã tích hợp sẵn trong script).
*   **Bước 2.2:** Chạy file script Python quét chéo: 
    *   *Cách chạy:* `python quyen_bao_cao/plan_final_report/giai_doan_2/evaluate_plagiarism.py`
*   **Bước 2.3:** Thống kê kết quả phân loại từ hệ thống so với thực tế (ngưỡng nghi ngờ >= 80%):
    *   **True Positive (TP):** Máy báo đạo văn, thực tế CÓ đạo văn.
    *   **False Positive (FP):** Máy báo đạo văn, thực tế KHÔNG đạo văn (Dương tính giả).
    *   **False Negative (FN):** Máy báo KHÔNG đạo văn, thực tế CÓ đạo văn.
*   **Bước 2.4:** Tính toán chỉ số Precision, Recall và lập Bảng ma trận nhầm lẫn (Confusion Matrix) để đưa vào báo cáo.

## 3. Giai đoạn 3: Chứng minh Sandbox bắt lỗi TLE/MLE và Lỗi Biên dịch
**Mục tiêu:** Trả lời câu hỏi *"Bao nhiêu testcase đã chạy, khả năng bắt lỗi biên dịch, vượt thời gian, tràn bộ nhớ ra sao?"*

*   **Bước 3.1:** Chạy file script test giới hạn (đã được tạo):
    *   *Cách chạy:* `python quyen_bao_cao/plan_final_report/giai_doan_3/test_sandbox_limits.py`
    *   Các lỗi được giả lập bao gồm:
        *   *Compilation Error (CE) / Syntax Error:* Code sai cú pháp (thiếu dấu hai chấm, thụt lề sai).
        *   *Time Limit Exceeded (TLE):* Lặp vô hạn `while True: pass`.
        *   *Memory Limit Exceeded (MLE):* Cấp phát mảng động khổng lồ vượt quá giới hạn RAM (ví dụ `[0] * 10**8`).
*   **Bước 3.2:** Ghi nhận log màn hình kết quả chạy. Chứng minh Sandbox tự động ngắt tiến trình (kill process) bằng cơ chế của Docker và trả về chính xác tên loại lỗi mà không làm sập máy chủ.

## 4. Giai đoạn 4: Cập nhật Báo cáo (Word)
Sau khi có toàn bộ số liệu thực tế từ 3 giai đoạn trên, tiến hành viết lại các phần trong file Word:
*   Viết lại mục 1.7 (Lý do chọn công nghệ) với lời văn học thuật, trích dẫn bài báo nghiên cứu (IEEE, ACM) về hệ thống Online Judge, MOSS.
*   Bổ sung Sequence Diagram (Sơ đồ tuần tự) mô tả luồng nộp bài và luồng quét đạo văn.
*   Bổ sung bảng thống kê số liệu Benchmark (Thời gian chờ, Tỷ lệ TLE/MLE) và Bảng Precision/Recall vào Chương 3.

---

### Ghi chú quan trọng để bảo vệ trước Hội đồng

**Về câu hỏi: "Tại sao tự viết Sandbox mà không dùng nền tảng có sẵn như Judge0?" (GV hay xoáy)**

Việc tự viết một wrapper chạy `docker run` là một điểm cộng lớn nếu biết cách bảo vệ. Lý do bạn phải tự viết thay vì dùng Judge0 là:

*   **Kiểm soát tài nguyên và Bảo mật tối đa:** Bằng việc tự viết Sandbox dựa trên Docker, hệ thống làm chủ hoàn toàn luồng thực thi: chặn được quyền mạng (network=none), giới hạn quyền ghi (read-only), kiểm soát nghiêm ngặt CPU, RAM, và số lượng tiến trình (pids-limit). 
*   **Tối ưu kiến trúc:** Hệ thống được tích hợp trực tiếp vào Django thay vì phải cài đặt, cấu hình và bảo trì thêm một cụm server API trung gian cồng kềnh (như Judge0 yêu cầu). Điều này làm giảm độ trễ giao tiếp mạng giữa Web Server và Judge Server.
*   **Tùy biến cao:** Việc sở hữu mã nguồn Sandbox giúp dễ dàng tùy biến môi trường ảo hóa, thêm bớt ngôn ngữ lập trình, hoặc tinh chỉnh cách tính điểm đặc thù mà không bị phụ thuộc vào giới hạn API của bên thứ ba.
*   *Lưu ý:* Để tự tin trả lời câu này, Sandbox bắt buộc phải có số liệu benchmark chứng minh tính ổn định (đã lên kế hoạch ở Giai đoạn 1).

**Về câu hỏi: "Đề tài này khác gì so với các nền tảng đã có sẵn?" (HackerRank, Moodle, DOMjudge...)**

1. **Nhóm hệ thống thi đấu thuật toán (HackerRank, LeetCode, DOMjudge):** Các nền tảng này sở hữu hệ thống Online Judge rất mạnh mẽ, nhưng lại được thiết kế chuyên biệt cho việc luyện tập cá nhân hoặc thi đấu (ACM/ICPC). Chúng thiếu vắng hoàn toàn các tính năng quản lý lớp học cốt lõi (LMS) như: giao bài tập tự luận, làm bài trắc nghiệm lý thuyết, hệ thống chấm điểm theo tiêu chí (Rubric) hay không gian thảo luận trực tiếp giữa giảng viên và sinh viên.
2. **Nhóm hệ thống quản lý học tập đa năng (Moodle, Canvas, Microsoft Teams):** Moodle hay Teams quản lý lớp học rất tốt, nhưng lại là hệ thống đại trà cho mọi môn học. Chúng không hỗ trợ sẵn môi trường biên dịch mã nguồn trực tiếp (IDE tích hợp) và tính năng tự động chạy testcase (Auto-grader). Để chấm code, giảng viên thường phải tải từng file mã nguồn về máy cá nhân hoặc cài đặt thêm các plugin bên thứ ba rất phức tạp. Bên cạnh đó, các hệ thống này thiếu công cụ phát hiện đạo văn chuyên sâu dành riêng cho mã nguồn (Code Plagiarism) như thuật toán Winnowing.

**Điểm khác biệt và tính đột phá của Đồ án:**
Khác biệt hoàn toàn so với các giải pháp đơn lẻ nêu trên, hệ thống của em là một Nền tảng lai (Hybrid Platform), kết hợp hoàn hảo giữa Hệ thống quản lý học tập (LMS) và Hệ thống chấm điểm tự động (Online Judge). Hệ thống không chỉ cung cấp một môi trường lớp học ảo toàn diện (điểm danh, thảo luận, giao bài tập, thi trắc nghiệm) mà còn tích hợp sẵn trình biên dịch mã nguồn (Web IDE), Sandbox chấm điểm tự động (TLE/MLE) và lõi phát hiện đạo văn mã nguồn. Sự kết hợp này tạo ra một vòng lặp khép kín "Học - Hành - Đánh giá", giải quyết triệt để bài toán đặc thù trong việc giảng dạy các bộ môn lập trình tại trường đại học hiện nay.
