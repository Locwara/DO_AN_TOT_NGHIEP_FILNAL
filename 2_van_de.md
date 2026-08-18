# Phân tích 2 vấn đề trọng tâm cho buổi bảo vệ đồ án

Tài liệu này phân tích 2 khía cạnh quan trọng của hệ thống: **Chi phí triển khai (Deployment Cost)** và **Luồng hoạt động của Thuật toán phát hiện đạo văn (Plagiarism Detection)**. Bạn có thể sử dụng các luận điểm này để trả lời trước Hội đồng.

---

## 1. Chi phí triển khai hệ thống (Sử dụng Docker)

Hệ thống hiện tại được thiết kế theo kiến trúc Microservices/Containerization (sử dụng Docker), bao gồm các thành phần: Web App (Django), Database (PostgreSQL), Message Broker (Redis/RabbitMQ cho Celery) và đặc biệt là hệ thống Sandbox để chấm code độc lập.

Việc chạy Sandbox (chạy code C++, Python của sinh viên trực tiếp trên server) đòi hỏi tài nguyên hệ thống (RAM, CPU) khá khắt khe để đảm bảo an toàn và không bị sập. Dưới đây là ước tính chi phí triển khai:

### A. Chi phí Máy chủ (VPS/Cloud Server) - Khoảng 300.000đ - 600.000đ / tháng
Để hệ thống chạy mượt mà cùng lúc các container Docker trên, cấu hình tối thiểu và đề xuất như sau:
*   **Cấu hình tối thiểu (Dành cho demo/vận hành nhỏ):** 
    *   CPU: 2 Cores
    *   RAM: 4GB (Vì Docker và Sandbox ngốn khá nhiều RAM)
    *   Ổ cứng: 40GB SSD
    *   *Giá tham khảo:* Khoảng $10 - $15/tháng (DigitalOcean, Vultr, Linode) hoặc các nhà cung cấp VN như Vietnix, AZDigi.
*   **Cấu hình khuyên dùng (Dành cho quy mô trường học):**
    *   CPU: 4 Cores
    *   RAM: 8GB (Đảm bảo Celery worker xử lý chấm bài đồng thời không bị tràn RAM)
    *   *Giá tham khảo:* Khoảng $20 - $30/tháng.

### B. Chi phí Tên miền (Domain) - Khoảng 300.000đ / năm
*   Tên miền quốc tế (`.com`, `.net`, `.edu.vn`) dùng để public ra internet.
*   SSL (HTTPS) thì hoàn toàn miễn phí nhờ tích hợp Let's Encrypt hoặc Cloudflare.

### C. Chi phí Dịch vụ bên thứ ba (Third-party) - Đa số Miễn phí
*   **Email SMTP (Gửi mail thông báo/quên mật khẩu):** Sử dụng các gói Free của SendGrid, Mailgun hoặc Brevo (đủ cho 300 mail/ngày).
*   **Google OAuth2 (Đăng nhập Google):** Hoàn toàn miễn phí từ Google Cloud Console.

**=> Tổng kết chi phí:** Để duy trì hệ thống chạy 24/7 ổn định bằng Docker, bạn chỉ tốn khoảng **~400.000 VNĐ/tháng** (chưa tính công bảo trì). Đây là mức chi phí cực kỳ rẻ nhờ việc tối ưu hóa Container thay vì phải thuê nhiều server vật lý rời rạc.

---

## 2. Luồng hoạt động chi tiết của Thuật toán Check Đạo văn

Hệ thống không chỉ so sánh text thông thường mà áp dụng kết hợp **4 thuật toán phân tích mã nguồn** để chống lại các kỹ thuật "che giấu đạo văn" (như đổi tên biến, xóa comment, thêm dấu cách). 

Quá trình quét đạo văn chạy ngầm (Background Task bằng Celery) với luồng hoạt động $O(N^2)$ (so sánh chéo tất cả các bài nộp) như sau:

### Bước 1: Thu thập & Tiền xử lý dữ liệu
*   Hệ thống lấy toàn bộ bài nộp có trạng thái `finished` của bài tập đó.
*   Lọc ra bài nộp **cuối cùng (latest)** của mỗi học sinh để tránh so sánh bài của chính học sinh đó với các lần nộp trước.

### Bước 2: Chuẩn hóa Mã nguồn (Normalization)
Đây là bước cực kỳ quan trọng để lật tẩy thủ thuật đổi tên biến của sinh viên.
*   **Đối với Python:** Hệ thống phân tích code thành Cây cú pháp trừu tượng (AST). Nó sẽ tìm toàn bộ các biến, tên hàm, tên class do sinh viên tự đặt và **đổi tên hàng loạt** về các định dạng chuẩn (ví dụ: `_v0`, `_v1`), chỉ giữ lại các từ khóa hệ thống (print, int, True, False...).
*   **Đối với C++/Khác:** Hệ thống dùng Regex để xóa toàn bộ chú thích (Comments) và chuẩn hóa khoảng trắng (xóa tab, dòng trống).
*   => Kết quả: Code của 2 sinh viên copy nhau dù đổi tên biến hay thêm chú thích cũng sẽ biến thành 1 đoạn code y hệt nhau sau bước này.

### Bước 3: So sánh chéo bằng 4 Thuật toán (Multi-layered Comparison)
Hệ thống lấy Code A và Code B (đã chuẩn hóa) đưa qua 4 thước đo với các công thức toán học cụ thể:

1.  **Text Similarity (Độ tương đồng văn bản):** Dùng `SequenceMatcher` để đo tỷ lệ giống nhau về mặt ký tự.
    *   **Công thức (Ratcliff/Obershelp):** $S_{text} = \frac{2 \times M}{T}$
    *   *(Trong đó: $M$ là số lượng ký tự khớp nhau, $T$ là tổng số ký tự của cả 2 bài).*
    *   **Ví dụ:** Bài A có 100 ký tự, Bài B có 120 ký tự. Có 90 ký tự khớp chuỗi với nhau $\Rightarrow S_{text} = \frac{2 \times 90}{100 + 120} = 0.818$ (81.8%).

2.  **Token Similarity (Độ tương đồng Token):** Bóc tách code thành mảng các Token (từ khóa, toán tử).
    *   **Công thức:** Giống như Text Similarity nhưng áp dụng trên mảng Token: $S_{token} = \frac{2 \times M_{token}}{T_{token}}$
    *   *(Giúp chống lại việc sinh viên thêm nhiều khoảng trắng hoặc dòng trống).*
    *   **Ví dụ:** Bài A có 50 token, Bài B có 50 token. Khớp nhau 45 token $\Rightarrow S_{token} = \frac{2 \times 45}{50 + 50} = 0.90$ (90%).

3.  **Structural Similarity (Độ tương đồng Cấu trúc - Bag of Tokens):** Đếm tần suất xuất hiện của các từ khóa (như đếm số vòng lặp `for`, lệnh `if`).
    *   **Công thức (Tương tự Cosine Similarity):** $S_{struct} = \frac{\sum \min(f_A(t), f_B(t))}{\sqrt{\sum f_A(t) \times \sum f_B(t)}}$
    *   *(Trong đó: $f_A(t)$ và $f_B(t)$ là số lần xuất hiện của token $t$ trong bài A và bài B).*
    *   **Ví dụ:** 
        *   Bài A có 3 chữ `for`, 2 chữ `if` (tổng = 5). 
        *   Bài B có 2 chữ `for`, 3 chữ `if` (tổng = 5).
        *   Tử số (giao thoa): $\min(3,2) + \min(2,3) = 2 + 2 = 4$.
        *   Mẫu số: $\sqrt{5 \times 5} = 5$.
        *   $\Rightarrow S_{struct} = \frac{4}{5} = 0.80$ (80%).

4.  **Winnowing Similarity (Độ tương đồng Dấu vân tay Code):** Sử dụng thuật toán cắt k-grams (Winnowing).
    *   **Công thức (Jaccard Index trên Fingerprints):** $S_{winnowing} = \frac{|H_A \cap H_B|}{|H_A \cup H_B|}$
    *   *(Trong đó: $H_A$ và $H_B$ là tập hợp các mã băm "dấu vân tay" trích xuất từ 2 đoạn code. Thuật toán này cực mạnh trong việc phát hiện đạo văn từng phần / copy-paste ngắt quãng).*
    *   **Ví dụ:** Bài A tạo ra 100 dấu vân tay (Hash), Bài B tạo ra 110 dấu vân tay. Phần giao nhau (giống nhau) là 80 vân tay. Phần hợp (tổng số vân tay duy nhất của cả 2) là 130. $\Rightarrow S_{winnowing} = \frac{80}{130} \approx 0.615$ (61.5%).

### Bước 4: Tính điểm Trọng số & Kết luận
Sau khi có 4 điểm số, hệ thống không lấy trung bình cộng mà **nhân với trọng số (Weights)** để ra kết quả cuối cùng:
*   Trọng số: **40% Winnowing + 30% Token + 20% Cấu trúc + 10% Text thô**.
*   (Nếu server không cài được Winnowing, hệ thống tự động backup dùng: 50% Token + 30% Cấu trúc + 20% Text).

Nếu tổng điểm **từ 85% trở lên (Ngưỡng Threshold)**, cặp bài nộp đó sẽ bị hệ thống gắn cờ là `is_suspicious` (Nghi vấn đạo văn) và hiện đỏ trên bảng điều khiển của Giảng viên.

---
*Chúc bạn có một buổi bảo vệ Đồ án xuất sắc và tự tin thuyết trình về hệ thống này!*
