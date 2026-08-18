# Kịch Bản Thuyết Trình Đồ Án Tốt Nghiệp
**Đề tài:** Xây Dựng Hệ Thống Dạy Và Học Lập Trình Trực Tuyến
**Sinh viên thực hiện:** Lê Thành Lộc
**Giảng viên hướng dẫn:** ThS. Lê Hoàng Minh

---

## Slide 1: Trang bìa (Giới thiệu)
**[Thao tác]** Mở đầu bài thuyết trình, nhìn về phía Hội đồng.
**[Lời nói]**
"Dạ em xin kính chào quý thầy cô trong Hội đồng đánh giá Đồ án tốt nghiệp. Em tên là Lê Thành Lộc. Hôm nay, em xin phép được trình bày báo cáo đồ án tốt nghiệp với đề tài: **'Xây Dựng Hệ Thống Dạy Và Học Lập Trình Trực Tuyến'**. Đồ án này được em thực hiện dưới sự hướng dẫn của ThS. Lê Hoàng Minh."

---

## Slide 2: Nội dung báo cáo
**[Thao tác]** Chuyển sang slide Nội dung báo cáo.
**[Lời nói]**
"Bài báo cáo của em gồm 6 phần chính:
1. Lý do chọn đề tài.
2. Mục tiêu, đối tượng và phạm vi nghiên cứu.
3. Kiến trúc và công nghệ sử dụng.
4. Kết quả triển khai thực tế.
5. Kiểm thử và đánh giá hiệu năng.
6. Kết luận và định hướng phát triển."

---

## Slide 3: 01 - Lý do chọn đề tài
**[Thao tác]** Chuyển slide Lý do chọn đề tài.
**[Lời nói]**
"Phần đầu tiên là lý do chọn đề tài. Hiện nay có hai nhóm hệ thống hỗ trợ giáo dục lập trình nhưng đều có điểm hạn chế:
- Các hệ thống thi đấu thuật toán (như HackerRank, LeetCode) có khả năng chấm code tốt nhưng lại thiếu các tính năng quản lý lớp học (LMS).
- Ngược lại, các hệ thống LMS (như Moodle, Teams) quản lý lớp học tốt nhưng không có môi trường viết code trực tiếp và thiếu công cụ chống đạo văn cho mã nguồn.
Từ đó, em xây dựng đề tài này nhằm tích hợp cả LMS, hệ thống chấm điểm tự động và công cụ phát hiện đạo văn vào một nền tảng duy nhất, tạo thành vòng lặp: Học – Hành – Đánh giá."

---

## Slide 4: 02 - Mục tiêu nghiên cứu
**[Thao tác]** Chuyển slide Mục tiêu.
**[Lời nói]**
"Đề tài của em hướng đến 4 mục tiêu chính:
1. Tự động hóa đánh giá: Giúp chấm điểm code tự động, trả kết quả tức thì để tiết kiệm thời gian cho giảng viên.
2. Giảm rào cản kỹ thuật: Sinh viên có thể viết và chạy code trực tiếp trên trình duyệt mà không cần cài đặt môi trường.
3. Kiểm soát gian lận: Ứng dụng thuật toán Winnowing để quét và phát hiện đạo văn trong mã nguồn.
4. Số hóa toàn diện: Hỗ trợ giảng viên tạo lớp, giao bài, tổ chức thi và theo dõi điểm số dễ dàng."

---

## Slide 5: 02 - Đối tượng & Phạm vi
**[Thao tác]** Chuyển slide Phạm vi.
**[Lời nói]**
"Về phạm vi, hệ thống tập trung vào các chức năng quản lý lớp, thi trực tuyến và quét đạo văn.
Môi trường chấm tự động (Sandbox) hiện hỗ trợ 3 ngôn ngữ phổ biến là C/C++, Python và Java.
Hệ thống cũng có tính năng giám sát phòng thi như: vô hiệu hóa copy/paste, cảnh báo khi sinh viên chuyển tab hoặc ghi nhận thao tác bàn phím."

---

## Slide 6: 03 - Kiến trúc nghiên cứu
**[Thao tác]** Chuyển slide Kiến trúc.
**[Lời nói]**
"Tiếp theo là phần Kiến trúc hệ thống. Hệ thống có 4 thành phần chính kết nối với nhau:
1. Nền tảng LMS để quản lý tài khoản và khóa học.
2. Web IDE tích hợp để thao tác mã nguồn.
3. Sandbox ảo hóa để chấm code một cách an toàn.
4. Module Quét đạo văn để so sánh AST và vân tay mã nguồn."

---

## Slide 7: 03 - Công nghệ nghiên cứu (Ngăn xếp)
**[Thao tác]** Chuyển slide Ngăn xếp công nghệ.
**[Lời nói]**
"Để xây dựng hệ thống, em sử dụng các công nghệ sau:
- Backend dùng Framework Django (Python).
- Sandbox chấm code được xây dựng trên nền ảo hóa Docker.
- Trình soạn thảo Web sử dụng Monaco và CodeMirror.
- Chống đạo văn sử dụng thuật toán Winnowing.
- Cơ sở dữ liệu Postgres trên Supabase và Cloudinary để lưu trữ ảnh.
- AJAX và HTMX được dùng cho các thao tác cần tính thời gian thực (như nộp bài, tự động lưu)."

---

## Slide 8: 03 - Chi phí triển khai
**[Thao tác]** Chuyển slide Chi phí.
**[Lời nói]**
"Về bài toán chi phí triển khai, em xin phép đặt ra một giả định thực tế: Hệ thống phục vụ quy mô cấp Khoa hoặc một Trung tâm đào tạo với khoảng 500 đến 1.000 sinh viên sử dụng.

Để đáp ứng được lượng người dùng này, đặc thù của hệ thống là sử dụng ảo hóa Docker để chấm code. Mỗi khi sinh viên nộp bài, hệ thống phải tạo một Container riêng biệt nên sẽ tiêu tốn khá nhiều tài nguyên RAM và CPU. 

Do đó, chi phí lớn nhất nằm ở **Máy chủ (VPS/Cloud)**: Cấu hình khuyên dùng để hệ thống chạy mượt mà với 4 Cores và 8GB RAM sẽ có mức giá thuê khoảng 500.000 đến 750.000 VNĐ/tháng. Tuy nhiên, nếu ngân sách eo hẹp, chúng ta hoàn toàn có thể sử dụng cấu hình tối thiểu 2 Cores 4GB RAM với chi phí chỉ khoảng 250.000 đến 350.000 VNĐ/tháng mà vẫn có thể gánh được tải cơ bản.

Tiếp đến là **Tên miền (Domain)**: Chi phí khoảng 300.000 VNĐ/năm cho đuôi .com hoặc .edu.vn (tức là chưa tới 30.000 VNĐ/tháng). Đi kèm với đó là bảo mật SSL HTTPS hoàn toàn miễn phí thông qua Let's Encrypt hoặc Cloudflare.

Đối với **Các dịch vụ bên thứ ba** như: Gửi Email nhắc nhở nộp bài (qua SendGrid, Mailgun) hay Xác thực đăng nhập Google, hệ thống tận dụng các gói miễn phí (Free Tier) vốn đã quá đủ dùng cho quy mô trường học.

Như vậy, tổng kết lại, nhờ việc tối ưu hóa kiến trúc chạy toàn bộ trên các Docker Container thay vì phải thuê nhiều server vật lý rời rạc, tổng chi phí vận hành toàn hệ thống chỉ dao động khoảng **400.000 đến 600.000 VNĐ/tháng**. Đây là một con số rất tối ưu và hoàn toàn khả thi để duy trì hệ thống 24/7."

---

## Slide 9: 04 - Kết quả triển khai (Luồng chống đạo văn)
**[Thao tác]** Chuyển slide Luồng quét đạo văn.
**[Lời nói]**
"Đối với kết quả triển khai, em xin nhấn mạnh vào tính năng Quét đạo văn. Quá trình này chạy ngầm qua 4 bước:
1. Thu thập các bài nộp hợp lệ.
2. Chuẩn hóa mã nguồn bằng Cây cú pháp trừu tượng (AST).
3. So sánh chéo các cặp bài nộp bằng thuật toán.
4. Hệ thống sẽ tính điểm trọng số, nếu độ tương đồng từ 85% trở lên sẽ đánh dấu nghi ngờ đạo văn."

---

## Slide 10: 04 - Bốn thuật toán so khớp
**[Thao tác]** Chuyển slide 4 thuật toán.
**[Lời nói]**
"Thuật toán quét đạo văn của hệ thống là sự kết hợp của 4 phương pháp với các mức trọng số:
- 10% cho Text Similarity (so sánh ký tự).
- 30% cho Token Similarity (chống việc thêm dòng trống, khoảng trắng).
- 20% cho Structural Similarity (so sánh cấu trúc khối lệnh).
- Và quan trọng nhất là 40% cho Winnowing Similarity, giúp phát hiện hiệu quả hành vi copy-paste từng đoạn nhỏ."

---

## Slide 11: 04 - Demo hệ thống
**[Thao tác]** Chuyển slide Video Demo (Nếu có chuẩn bị video/ảnh thì chiếu lên).
**[Lời nói]**
"Mời quý thầy cô xem nhanh các giao diện chính của hệ thống: từ màn hình giao bài của giảng viên, giao diện làm bài (IDE) của sinh viên, đến màn hình nhận kết quả chấm tự động từ Sandbox."

---

## Slide 12: 05 - Đánh giá hiệu năng (Độ chính xác)
**[Thao tác]** Chuyển slide Kiểm thử độ chính xác.
**[Lời nói]**
"Về phần kiểm thử, em đã đánh giá độ chính xác của thuật toán quét đạo văn. Bằng cách sử dụng 5 kịch bản sinh viên làm bài khác nhau (từ copy đổi tên biến, đến làm cách hoàn toàn khác), hệ thống phát hiện chính xác 100% các ca đạo văn có chủ ý che giấu, và không báo nhầm đối với các sinh viên tự làm bài độc lập."

---

## Slide 13: 05 - Đánh giá hiệu năng (Chịu tải)
**[Thao tác]** Chuyển slide Chịu tải JMeter.
**[Lời nói]**
"Về hiệu năng, em dùng công cụ JMeter giả lập 1.000 sinh viên nộp bài cùng lúc. Kết quả cho thấy tỷ lệ lỗi là 0%. Thời gian phản hồi xử lý nộp code trung bình chỉ 3.69 giây, tốc độ đạt hơn 63 bài/giây. Điều này cho thấy hệ thống có khả năng chịu tải tốt và đảm bảo ổn định."

---

## Slide 14: 06 - Kết luận (Kết quả)
**[Thao tác]** Chuyển slide Kết quả đạt được.
**[Lời nói]**
"Tổng kết lại, đồ án đã đạt được 4 kết quả cốt lõi:
1. Về hệ thống: Xây dựng nền tảng LMS hoàn chỉnh, phân quyền chặt chẽ giữa Giảng viên và Sinh viên.
2. Về công nghệ: Tích hợp thành công trình biên dịch trực tuyến ảo hóa, an toàn cho các ngôn ngữ C++, Python, Java.
3. Về kiểm định: Tự động hóa chấm điểm và phát hiện đạo văn chuẩn xác qua AST và vân tay mã nguồn.
4. Về giám sát: Thiết lập môi trường thi cử nghiêm ngặt, tự động ghi log và chặn các hành vi gian lận.

=> Qua 4 kết quả trên, đồ án đã giải quyết thành công bài toán thực tế: Giúp giảng viên tiết kiệm tối đa thời gian chấm bài thủ công, đồng thời kết hợp thành công LMS, hệ thống chấm điểm tự động và công cụ phát hiện đạo văn vào một nền tảng duy nhất, tạo ra một vòng lặp khép kín 'Học – Hành – Đánh giá' toàn diện và minh bạch."

---

## Slide 15: 06 - Hạn chế và hướng phát triển
**[Thao tác]** Chuyển slide Hạn chế & Hướng phát triển.
**[Lời nói]**
"Tuy nhiên, hệ thống vẫn còn hạn chế: như cần tài nguyên máy chủ mạnh hơn nếu triển khai thi quy mô toàn trường; hoặc chưa hỗ trợ chấm các project gồm nhiều file.
Hướng phát triển tương lai của em là đưa kiến trúc lên Cloud để tự động mở rộng tài nguyên (auto-scaling) và tích hợp thêm AI để làm trợ lý ảo gợi ý sửa lỗi code cho sinh viên."

---

## Slide 16: Lời cảm ơn
**[Thao tác]** Chuyển slide Cảm ơn, hơi cúi đầu.
**[Lời nói]**
"Dạ phần báo cáo đồ án của em xin được kết thúc tại đây. Em xin cảm ơn ThS. Lê Hoàng Minh và quý thầy cô trong Hội đồng đã lắng nghe. Em rất mong nhận được những góp ý từ quý thầy cô để đề tài được hoàn thiện hơn ạ."
