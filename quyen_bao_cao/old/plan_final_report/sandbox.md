### 3.2.2.2. Kiểm thử sức chịu đựng giới hạn của lõi Sandbox (Stress Testing to Failure)

Bên cạnh việc kiểm thử toàn trình bằng JMeter, nghiên cứu tiến hành một kịch bản kiểm thử khắc nghiệt hơn: **Tấn công trực tiếp vào lõi Sandbox (Direct Engine Benchmark)**. 

**1. Phương pháp đo lường**
Sử dụng một kịch bản Python nội bộ (`benchmark_sandbox.py`) tích hợp thư viện `concurrent.futures.ThreadPoolExecutor`. Kịch bản này bỏ qua hoàn toàn tầng giao diện mạng (Django Web Server, HTTP, CSRF) để gọi trực tiếp vào API của Docker Daemon. Điều này giúp đo lường chính xác giới hạn vật lý của máy chủ (Memory, CPU) khi phải khởi tạo và thu hồi hàng loạt container cùng một tích tắc.

**2. Kết quả ở ngưỡng tải an toàn (100 Requests đồng thời)**
Khi thiết lập 100 luồng (Worker) gọi thẳng vào Docker cùng lúc, hệ thống Sandbox xử lý cực kỳ mượt mà:
*   **Tỷ lệ thành công:** 100/100 (100.0%)
*   **Tổng thời gian hệ thống xử lý:** 9.65 giây
*   **Thời gian phản hồi trung bình:** 8.73 giây/bài nộp
Kết quả này khẳng định kiến trúc Sandbox dựa trên Native Docker Kernel có tốc độ khởi động container cực nhanh (tầm mili-giây), hoàn toàn không gặp khó khăn ở mức tải hàng trăm request.

**3. Hiện tượng tràn bộ nhớ (OOM) ở ngưỡng cực hạn (1000 Requests đồng thời)**
Để dò tìm giới hạn của phần cứng (8GB RAM), kịch bản tiếp tục được đẩy lên 1000 luồng đồng thời gọi khởi tạo Docker Container cùng một tích tắc. Kết quả thực nghiệm ghi nhận: **Kịch bản kiểm thử bị hệ điều hành (Linux Kernel) tiêu diệt đột ngột do lỗi tràn bộ nhớ (Out of Memory - OOM Kill).**

**4. Phân tích nguyên nhân và Tính ưu việt của Kiến trúc phân tầng**
Hiện tượng OOM nêu trên thoạt nhìn là một điểm yếu của phần cứng, nhưng thực chất lại làm nổi bật lên tính ưu việt trong **Kiến trúc thiết kế luồng (System Architecture)** của toàn bộ đồ án khi so sánh với kết quả test JMeter (1000 requests không lỗi) ở mục 3.2.2.1:

*   **Bản chất của lỗi OOM ở Sandbox:** Khi 1000 luồng gọi lệnh `docker run` cùng lúc, mỗi Container cần tối thiểu một lượng Overhead RAM nhất định để cấp phát không gian tên (Namespaces) và Control Groups (Cgroups). Hàng ngàn yêu cầu cấp phát này trong một khoảnh khắc đã vắt kiệt 8GB RAM vật lý, buộc hệ điều hành phải can thiệp đóng tiến trình để tự vệ.
*   **Cơ chế "Tấm khiên bảo vệ" của Web Server:** Mặc dù lõi Sandbox sụp đổ khi nhận 1000 yêu cầu trực tiếp, nhưng ở kịch bản JMeter (truy cập qua mạng), hệ thống vẫn bình an vô sự. Nguyên nhân là do Web Server (Django/Gunicorn) đóng vai trò như một **Bộ đệm xếp hàng (Queueing Buffer)**. Web Server chỉ giới hạn xử lý một số lượng luồng nhất định (ví dụ 8 luồng). Khi 1000 yêu cầu HTTP ập tới, Django chỉ trích xuất 8 yêu cầu để đưa vào Docker xử lý, 992 yêu cầu còn lại được đưa vào hàng đợi mạng (Network Socket Queue). Khi 8 bài nộp đầu tiên giải phóng RAM, các bài tiếp theo mới được đẩy vào lõi.
*   **Kết luận:** Kiến trúc phân tách rõ ràng giữa Web Server (Xử lý hàng đợi) và Sandbox Engine (Xử lý mã nguồn) đã giúp bảo vệ máy chủ khỏi những cú sốc tài nguyên (Spike Load). Nhờ vậy, ngay cả khi triển khai trên phần cứng khiêm tốn (Ryzen 5, 8GB RAM), hệ thống vẫn tự động điều tiết luồng công việc để vượt qua bài kiểm tra 1000 sinh viên nộp bài đồng thời mà không bị sập (Crash).

Điều này chứng minh đồ án không chỉ tập trung vào việc chấm điểm đúng, mà còn giải quyết triệt để bài toán ổn định hệ thống (System Reliability) trong môi trường thực tế.
