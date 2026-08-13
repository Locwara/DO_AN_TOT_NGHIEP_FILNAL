### 3.2.2. Đánh giá tốc độ xử lý của hệ thống Sandbox
#### 3.2.2.1. Kiểm thử chịu tải toàn trình (End-to-End Load Testing) bằng Apache JMeter

**1. Thông số cấu hình và Phương pháp đo lường (Benchmark Methodology)**
Để giải quyết bài toán đánh giá hiệu năng chịu tải dưới góc độ của người dùng cuối (End-user) và đảm bảo tính minh bạch, khoa học cho các số liệu thực nghiệm, nghiên cứu đã thiết lập một kịch bản đo lường với các thông số nghiêm ngặt như sau:

*   **Cấu hình máy chủ (Server Hardware):** Hệ thống được triển khai theo mô hình On-Premise trên máy chủ chạy hệ điều hành Arch Linux. Phần cứng sử dụng vi xử lý AMD Ryzen 5 5600H, bộ nhớ RAM 8GB DDR4, và môi trường ảo hóa Docker Engine v29 (chạy Native).
*   **Công cụ Benchmark:** Sử dụng công cụ kiểm thử hiệu năng chuyên dụng **Apache JMeter**. Việc sử dụng JMeter nhằm tạo ra các luồng truy cập HTTP thực tế đi qua toàn bộ kiến trúc mạng (Internet -> Reverse Proxy -> Web Server -> Django -> Docker Sandbox).
*   **Số lượng Concurrent Users / Workers:** Khởi tạo **1000 Luồng (Threads/Workers)** tương đương với việc mô phỏng 1000 sinh viên đồng thời thao tác trên hệ thống. 
*   **Loại chương trình test và Testcase:** Mã nguồn được nộp là một đoạn mã nguồn Python cơ bản, không có vòng lặp phức tạp hay file đầu vào (I/O). Mục đích là để tập trung đo lường độ trễ (Overhead) trong việc khởi tạo/thu hồi Docker Container và xử lý giao thức HTTP của Server thay vì đo lường tốc độ biên dịch.
*   **Số lần lặp (Iterations) & Quy mô test:** Kịch bản chạy 1 vòng lặp (Loop Count = 1) cho mỗi người dùng. Tổng cộng hệ thống phải tiếp nhận **3000 Requests** trong một khoảng thời gian rất ngắn.
*   **Cách tính thời gian (Time Measurement):** Thời gian phản hồi (Response Time) được tính toán theo cơ chế Round Trip Time (RTT). Nghĩa là tính từ thời điểm tính mili-giây (ms) khi Client gửi Request đi, cho đến khi Client nhận được trọn vẹn gói tin HTTP Response trả về (Đã bao gồm thời gian xác thực Session, thời gian Sandbox xử lý code và thời gian truy xuất Database).

**2. Kịch bản thực nghiệm**
Kịch bản mô phỏng hành vi thực tế của 1000 sinh viên truy cập vào hệ thống làm bài thi. Các luồng người dùng ảo (Virtual Users) sử dụng chung thông tin xác thực của một tài khoản sinh viên đã được cấp quyền tham gia lớp học từ trước. Mỗi luồng sẽ thực hiện tuần tự 3 tác vụ chính (tương ứng với 3 HTTP Requests):

1.  **Truy cập trang đăng nhập (GET):** Hệ thống điều hướng đến giao diện đăng nhập để khởi tạo phiên kết nối và trích xuất mã bảo mật chống tấn công giả mạo (CSRF Token) do Django cung cấp.
2.  **Đăng nhập hệ thống (POST):** Gửi thông tin tài khoản xác thực kèm CSRF Token để máy chủ cấp phát Phiên làm việc hợp lệ (Session).
3.  **Nộp bài mã nguồn (POST):** Sau khi đăng nhập thành công, người dùng truy cập vào trang làm bài và gửi trực tiếp đoạn mã nguồn Python vào hệ thống Sandbox thông qua URL của bài tập tương ứng, sau đó chờ quá trình phân tích và trả về kết quả điểm số.

**3. Kết quả và Đánh giá**
Kết quả đo lường được trích xuất trực tiếp từ Báo cáo tổng hợp (Summary Report) của công cụ Apache JMeter.

**Bảng 3.x. Kết quả kiểm thử chịu tải toàn trình hệ thống với 1000 Sinh viên đồng thời**

| Nhãn tác vụ (Label) | Số lượt truy cập (Samples) | Tỷ lệ lỗi (Error %) | Thời gian phản hồi Trung bình | Thông lượng (Throughput) |
| :--- | :--- | :--- | :--- | :--- |
| 1. GET Trang Đăng Nhập | 1000 | 0.000% | 3.63 giây | ~104.9 Req/s |
| 2. POST Đăng Nhập | 1000 | 0.000% | 4.23 giây | ~72.9 Req/s |
| 3. POST Nộp Code (Sandbox)| 1000 | 0.000% | 3.69 giây | ~63.3 Req/s |
| **TỔNG CỘNG** | **3000** | **0.000%** | **3.85 giây** | **~189.1 Req/s** |

**Nhận xét và Phân tích:**
*   **Khả năng chịu lỗi xuất sắc:** Trái với lo ngại ban đầu về việc hệ thống có thể bị nghẽn cổ chai (Bottleneck) khi lượng sinh viên tăng đột biến, hệ thống đã hoàn tất trọn vẹn 3000 tác vụ HTTP mà **không ghi nhận bất kỳ một lỗi nào (Error = 0.000%)**. Điều này chứng minh Server (Django + Docker) hoàn toàn không bị sập hay cạn kiệt tài nguyên (OOM) dưới áp lực cực lớn.
*   **Tốc độ xử lý tối ưu:** Ở tác vụ nặng nề nhất là "POST Nộp Code" (đòi hỏi Web Server phải gọi Docker khởi tạo môi trường cô lập), thời gian phản hồi trung bình chỉ đạt **3.69 giây**. Đây là khoảng thời gian chờ đợi hoàn toàn có thể chấp nhận được trong trải nghiệm người dùng thực tế (UX), đặc biệt là khi hệ thống đang phải phục vụ cùng lúc 1000 sinh viên nộp bài thi ở những phút cuối giờ.
*   **Thông lượng mạnh mẽ:** Tổng thông lượng xử lý của hệ thống đạt **189.1 Requests/giây**. Các số liệu thực nghiệm này là minh chứng vững chắc cho việc kiến trúc lõi Sandbox hoàn toàn có khả năng phục vụ mượt mà cho các lớp học hoặc kỳ thi lập trình quy mô lớn tại trường đại học.
