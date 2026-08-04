### CHƯƠNG 2: PHƯƠNG PHÁP NGHIÊN CỨU

#### 2.1. PHƯƠNG PHÁP NGHIÊN CỨU

Để xây dựng hệ thống Website dạy và học lập trình trực tuyến, nghiên cứu áp dụng phương pháp phân tích – thiết kế hệ thống thông tin theo hướng tiếp cận từ trên xuống (Top-down). Quy trình được thực hiện tuần tự từ khảo sát yêu cầu thực tế đến triển khai thử nghiệm, đảm bảo tính logic, tính toàn vẹn dữ liệu và khả năng mở rộng. Trước hết, tiến hành khảo sát, thu thập dữ liệu từ ba nhóm đối tượng chính: Quản trị viên (Admin), Giảng viên (Teacher) và Học viên (Student). Việc thu thập thông tin được thực hiện thông qua phỏng vấn trực tiếp, quan sát quy trình giảng dạy và học tập thực tế, nhằm nhận diện rõ nhu cầu cũng như những khó khăn trong việc vận hành các lớp học lập trình hiện tại (việc ra đề, nộp bài, chấm code thủ công, chống gian lận...).

Sau đó, dữ liệu thu thập được phân tích để xác định các nghiệp vụ trọng tâm, làm cơ sở cho giai đoạn thiết kế. Tiếp theo, hệ thống được phát triển theo phương pháp phân tích kết hợp với mô hình Use-case để tự động hóa tối đa các quy trình. Quy trình nghiên cứu và xây dựng hệ thống được triển khai qua 6 bước chính:

**Bước 1: Phân tích yêu cầu**

Tiến hành khảo sát và thu thập thông tin từ ba nhóm đối tượng người dùng. Từ dữ liệu khảo sát, xác định các nghiệp vụ trọng tâm mà hệ thống cần đáp ứng:
- Quản lý danh tính và phân quyền (Đăng nhập, đăng ký, xác thực, nâng cấp tài khoản).
- Quản lý lớp học và môn học (Tạo lớp, tham gia lớp, import danh sách học viên, quản lý sổ điểm).
- Quản lý bài tập và chống đạo văn (Tạo bài tập đa định dạng: Lập trình, Trắc nghiệm, Tự luận; cấu hình testcase; quét gian lận mã nguồn).
- Môi trường làm bài và chấm điểm (IDE lập trình trực tuyến, chấm điểm tự động qua Sandbox, chấm điểm thủ công bằng Rubric, bình luận trực tiếp vào code).
- Tương tác và thông báo (Diễn đàn thảo luận hỏi/đáp, hệ thống thông báo đẩy theo thời gian thực).

**Bước 2: Phân tích hệ thống**

- Xác định các tác nhân (actor) và phân quyền: Admin, Teacher, Student, Guest.
- Xây dựng biểu đồ Use-case (được trình bày ở mục 2.2) để mô tả và tài liệu hóa các chức năng của hệ thống theo từng góc độ người dùng.

**Bước 3: Thiết kế hệ thống**

- Thiết kế kiến trúc tổng thể của hệ thống, phân tách rõ ràng giữa Web Server (Backend) và máy chấm tự động (Sandbox).
- Thiết kế sơ đồ cơ sở dữ liệu (Sơ đồ Lớp / Class Diagram) nhằm liên kết tối ưu các thực thể: Người dùng, Bài tập, Lượt nộp bài, Testcase, Sổ điểm.
- Thiết kế giao diện người dùng (UI/UX) đảm bảo tính trực quan, thân thiện cho việc học và thi lập trình (có chế độ Dark mode, code highlight).

**Bước 4: Cài đặt và tích hợp**

- Lập trình các chức năng Frontend xây dựng giao diện tương tác linh hoạt.
- Xây dựng Backend xử lý bằng framework Django (Python), lưu trữ dữ liệu an toàn trên hệ quản trị cơ sở dữ liệu PostgreSQL.
- Xây dựng và cấu hình môi trường Sandbox (sử dụng Docker) cách ly để chạy mã nguồn của sinh viên một cách an toàn.
- Tích hợp các dịch vụ bên ngoài (Third-party API) như Google Login API (OAuth 2.0) để xác thực người dùng, và API gửi Email tự động.

**Bước 5: Kiểm thử**

Kiểm thử tích hợp các quy trình nghiệp vụ cốt lõi:
- Đăng nhập/Đăng ký - Quản lý tài khoản - Xác thực quyền.
- Quá trình biên dịch và chấm điểm tự động mã nguồn (Xử lý các lỗi biên dịch, vượt quá thời gian Time Limit, tràn bộ nhớ Memory Limit).
- Quá trình làm bài thi trắc nghiệm và nộp bài tập dạng file đính kèm.
- Tính chính xác của thuật toán quét tỷ lệ đạo văn.
- Kiểm thử sổ điểm, bảng xếp hạng và các tính năng tương tác (Bình luận, Thảo luận).

**Bước 6: Triển khai và đánh giá**

- Đưa hệ thống triển khai thực tế trên môi trường máy chủ (Server/Cloud).
- Đánh giá hiệu quả dựa trên các tiêu chí: Tốc độ xử lý của Sandbox khi có nhiều lượt nộp bài đồng thời, tính ổn định của hệ thống, độ bảo mật mã nguồn và mức độ đáp ứng nhu cầu thực tế của giảng viên, học viên.
- Ghi nhận các hạn chế và đề xuất cải tiến để hoàn thiện hệ thống trong tương lai.
