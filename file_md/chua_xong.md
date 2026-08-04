# 📋 TỔNG HỢP CÁC YÊU CẦU CHƯA HOÀN THIỆN HOẶC KHÁC VỚI THIẾT KẾ GỐC

Tài liệu này tổng hợp các tính năng chưa hoàn thành hoặc đã hoàn thành nhưng sử dụng công nghệ thay thế so với yêu cầu thiết kế ban đầu (`Phan_tich_chuc_nang_He_thong_Day_Hoc_Lap_Trinh.docx`). Phục vụ cho việc báo cáo và trao đổi định hướng với giảng viên hướng dẫn.

---

## 1️⃣ CÁC TÍNH NĂNG CHƯA HOÀN THIỆN (Còn thiếu)

### Thuộc nhóm tính năng "Nên có" (Ưu tiên 9.2)
1. **Thanh toán khóa học:**
   - **Yêu cầu:** Tích hợp cổng thanh toán (VNPay / Momo / Stripe) để mua khóa học.
   - **Thực tế:** Hệ thống hiện tại chưa tích hợp luồng thanh toán (Payment Gateway).

2. **Cấp chứng chỉ hoàn thành (Certificate):**
   - **Yêu cầu:** Tự động phát sinh và cấp chứng chỉ (PDF/Hình ảnh) khi sinh viên hoàn thành 100% khóa học.
   - **Thực tế:** Mới chỉ có theo dõi tiến độ (Pass rate) và bảng xếp hạng, chưa có tính năng render và cấp chứng chỉ.

### Thuộc nhóm tính năng "Báo cáo" (Phần 5)
3. **Báo cáo đạo văn toàn hệ thống:**
   - **Yêu cầu:** Báo cáo đạo văn ở cấp độ toàn hệ thống (xem tổng quát chéo theo nhiều lớp/nhiều giảng viên).
   - **Thực tế:** Tính năng đạo văn (AST + Winnowing) hiện đang hoạt động cực kỳ mạnh mẽ nhưng scope (phạm vi) đang giới hạn ở mức **từng bài tập trong một lớp học cụ thể**. Chưa có một Dashboard tổng hợp báo cáo đạo văn toàn hệ thống cho Admin.

---

## 2️⃣ CÁC YÊU CẦU ĐẠT ĐƯỢC NHƯNG SỬ DỤNG CÔNG NGHỆ THAY THẾ (Khác thiết kế gốc)

### 1. Trạng thái thời gian thực (Real-time Cập nhật điểm/Trạng thái chấm)
- **Thiết kế gốc (Phần 8):** Yêu cầu sử dụng **WebSocket (Socket.IO)** để cập nhật trạng thái chấm bài tức thời.
- **Công nghệ triển khai thực tế:** Đang sử dụng cơ chế **Polling (JS setInterval + Fetch API)**.
- **Lý do thay thế (để giải thích với cô):** Polling vẫn đáp ứng tốt trải nghiệm cập nhật dữ liệu tự động mà không cần tải lại trang (VD: Dashboard giám sát thi tự động refresh mỗi 10s-30s). Việc dùng Polling giúp kiến trúc hệ thống nhẹ nhàng, dễ bảo trì hơn và tránh overhead/bug phức tạp khi phải setup WebSockets / Redis PubSub trong giai đoạn ưu tiên tính ổn định này.

### 2. Lưu trữ tệp tin (File Storage)
- **Thiết kế gốc (Phần 8):** Đề xuất dùng Cloud Storage như **AWS S3 / MinIO** để lưu trữ video bài giảng và file mã nguồn sinh viên nộp.
- **Công nghệ triển khai thực tế:** Hiện đang lưu trữ trực tiếp (Local Storage) trong thư mục `media/` của server gốc.
- **Lý do thay thế (để giải thích với cô):** Phù hợp với chi phí và quy mô triển khai hiện tại của đồ án ở dạng MVP (sản phẩm khả thi tối thiểu). Kiến trúc code đã tách biệt nên hoàn toàn có thể dễ dàng scale (mở rộng) gắn với AWS S3 trong tương lai nếu có ngân sách và lượng người dùng tăng cao.

---

## 3️⃣ CÁC TÍNH NĂNG ĐỊNH HƯỚNG TƯƠNG LAI (Phần 9.3 - Bỏ ngỏ)
*(Ghi chú thêm nếu giảng viên hỏi về các mục mở rộng)*
Hệ thống chưa triển khai các tính năng thuộc nhóm định hướng phát triển (Phần 9.3), bao gồm:
- Livestream lớp học.
- Chatbot AI hỗ trợ học tập.
- Đa ngôn ngữ giao diện.
- Ứng dụng di động (Mobile App riêng biệt).

> **💡 Lời khuyên trao đổi với giảng viên:** 
> Do quỹ thời gian làm đồ án có hạn, team đã dồn 100% nguồn lực và sự tập trung để xử lý thật chỉn chu phần lõi khó nhất là **Hệ thống chấm bài cô lập (Sandbox Docker)** và **Thuật toán kiểm tra đạo văn (AST)**. Các tính năng về thanh toán, chứng chỉ hay WebSocket là các tính năng vệ tinh, hoàn toàn có thể đề xuất đưa vào mục *"Hướng phát triển trong tương lai"* của quyển báo cáo đồ án.
