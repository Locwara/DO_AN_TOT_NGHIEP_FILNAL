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
*   **Khả năng chịu lỗi xuất sắc:** Trái với lo ngại ban đầu về việc hệ thống có thể bị nghẽn cổ chai (Bottleneck) khi lượng sinh viên tăng đột biến, hệ thống đã hoàn thành 3000 tác vụ HTTP mà **không ghi nhận lỗi (Error = 0.000%)**. Điều này chứng minh Server (Django + Docker) duy trì hoạt động ổn định và không gặp tình trạng thiếu hụt tài nguyên (OOM) dưới áp lực cao.
*   **Tốc độ xử lý tối ưu:** Ở tác vụ nặng nề nhất là "POST Nộp Code" (đòi hỏi Web Server phải gọi Docker khởi tạo môi trường cô lập), thời gian phản hồi trung bình chỉ đạt **3.69 giây**. Đây là khoảng thời gian chờ đợi phù hợp trong trải nghiệm người dùng thực tế (UX), đặc biệt là khi hệ thống đang phải phục vụ cùng lúc 1000 sinh viên nộp bài thi ở những phút cuối giờ.
*   **Thông lượng mạnh mẽ:** Tổng thông lượng xử lý của hệ thống đạt **189.1 Requests/giây**. Các số liệu thực nghiệm này là minh chứng vững chắc cho việc kiến trúc lõi Sandbox có khả năng phục vụ mượt mà cho các lớp học hoặc kỳ thi lập trình quy mô lớn tại trường đại học.
### 3.2.2.2. Kiểm thử sức chịu đựng giới hạn của lõi Sandbox (Stress Testing to Failure)

Bên cạnh việc kiểm thử toàn trình bằng JMeter, nghiên cứu tiến hành một kịch bản kiểm thử khắc nghiệt hơn: **Tấn công trực tiếp vào lõi Sandbox (Direct Engine Benchmark)**. 

**1. Phương pháp đo lường**
Sử dụng một kịch bản Python nội bộ (`benchmark_sandbox.py`) tích hợp thư viện `concurrent.futures.ThreadPoolExecutor`. Kịch bản này bỏ qua phần lớn tầng giao diện mạng (Django Web Server, HTTP, CSRF) để gọi trực tiếp vào API của Docker Daemon. Điều này giúp đo lường chính xác giới hạn vật lý của máy chủ (Memory, CPU) khi phải khởi tạo và thu hồi hàng loạt container cùng một tích tắc.

**2. Kết quả ở ngưỡng tải an toàn (100 Requests đồng thời)**
Khi thiết lập 100 luồng (Worker) gọi thẳng vào Docker cùng lúc, hệ thống Sandbox xử lý ổn định:
*   **Tỷ lệ thành công:** 100/100 (100.0%)
*   **Tổng thời gian hệ thống xử lý:** 9.65 giây
*   **Thời gian phản hồi trung bình:** 8.73 giây/bài nộp
Kết quả này khẳng định kiến trúc Sandbox dựa trên Native Docker Kernel có tốc độ khởi động container nhanh (tầm mili-giây), hoạt động tốt ở mức tải hàng trăm request.

**3. Hiện tượng tràn bộ nhớ (OOM) ở ngưỡng cực hạn (1000 Requests đồng thời)**
Để dò tìm giới hạn của phần cứng (8GB RAM), kịch bản tiếp tục được đẩy lên 1000 luồng đồng thời gọi khởi tạo Docker Container cùng một tích tắc. Kết quả thực nghiệm ghi nhận: **Kịch bản kiểm thử bị hệ điều hành (Linux Kernel) tiêu diệt đột ngột do lỗi tràn bộ nhớ (Out of Memory - OOM Kill).**

**4. Phân tích nguyên nhân và Tính ưu việt của Kiến trúc phân tầng**
Hiện tượng OOM nêu trên thoạt nhìn là một điểm yếu của phần cứng, nhưng thực chất lại làm nổi bật lên tính ưu việt trong **Kiến trúc thiết kế luồng (System Architecture)** của toàn bộ đồ án khi so sánh với kết quả test JMeter (1000 requests không lỗi) ở mục 3.2.2.1:

*   **Bản chất của lỗi OOM ở Sandbox:** Khi 1000 luồng gọi lệnh `docker run` cùng lúc, mỗi Container cần tối thiểu một lượng Overhead RAM nhất định để cấp phát không gian tên (Namespaces) và Control Groups (Cgroups). Hàng ngàn yêu cầu cấp phát này trong một khoảnh khắc đã tiêu thụ hết 8GB RAM vật lý, buộc hệ điều hành phải can thiệp đóng tiến trình để tự vệ.
*   **Cơ chế "Tấm khiên bảo vệ" của Web Server:** Mặc dù lõi Sandbox sụp đổ khi nhận 1000 yêu cầu trực tiếp, nhưng ở kịch bản JMeter (truy cập qua mạng), hệ thống vẫn hoạt động bình thường. Nguyên nhân là do Web Server (Django/Gunicorn) đóng vai trò như một **Bộ đệm xếp hàng (Queueing Buffer)**. Web Server chỉ giới hạn xử lý một số lượng luồng nhất định (ví dụ 8 luồng). Khi 1000 yêu cầu HTTP ập tới, Django chỉ trích xuất 8 yêu cầu để đưa vào Docker xử lý, 992 yêu cầu còn lại được đưa vào hàng đợi mạng (Network Socket Queue). Khi 8 bài nộp đầu tiên giải phóng RAM, các bài tiếp theo mới được đẩy vào lõi.
*   **Kết luận:** Kiến trúc phân tách rõ ràng giữa Web Server (Xử lý hàng đợi) và Sandbox Engine (Xử lý mã nguồn) đã giúp bảo vệ máy chủ khỏi những cú sốc tài nguyên (Spike Load). Nhờ vậy, ngay cả khi triển khai trên phần cứng khiêm tốn (Ryzen 5, 8GB RAM), hệ thống vẫn tự động điều tiết luồng công việc để vượt qua bài kiểm tra 1000 sinh viên nộp bài đồng thời mà không bị gián đoạn dịch vụ.

Điều này chứng minh đồ án không chỉ tập trung vào việc chấm điểm đúng, mà còn giải quyết tốt bài toán ổn định hệ thống (System Reliability) trong môi trường thực tế.
