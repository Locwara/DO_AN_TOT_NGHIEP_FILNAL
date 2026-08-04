### 2.2. PHÂN TÍCH THIẾT KẾ

#### 2.2.1. Mô tả hệ thống

Hệ thống Website dạy và học lập trình được thiết kế với mục tiêu tạo ra một nền tảng học tập tập trung, hỗ trợ toàn diện quá trình giảng dạy và thực hành viết mã (code). Thay vì sử dụng các nền tảng rời rạc để giao bài, thu bài nén (zip) và chấm điểm thủ công, hệ thống cung cấp một môi trường tích hợp cho phép tự động hóa quy trình từ lúc ra đề, làm bài, đến chấm điểm thông qua máy chấm độc lập (Sandbox), giúp tiết kiệm thời gian, nhân lực và đảm bảo tính công bằng tuyệt đối.

* **Quản trị hệ thống & Người dùng**: Quản lý toàn bộ thông tin tài khoản, xét duyệt quyền Giảng viên, theo dõi lịch sử hoạt động hệ thống (Audit logs) và cấu hình giới hạn biên dịch (Time Limit, Memory Limit) cho từng ngôn ngữ lập trình.
* **Quản lý lớp học & môn học**: Cung cấp công cụ tổ chức lớp học, import danh sách sinh viên hàng loạt từ file Excel/CSV, quản lý các học kỳ, gán môn học vào lớp, quản lý thông báo, và thống kê sổ điểm (Gradebook).
* **Quản lý bài tập & bài thi**: Hỗ trợ đa dạng thể loại ra đề (Lập trình, Trắc nghiệm, Tự luận/Nộp file). Nổi bật là khả năng cấu hình bộ dữ liệu kiểm thử (Testcase), thiết lập tiêu chí chấm điểm (Rubric) và tự động quét đạo văn (Plagiarism) bằng cách so sánh độ tương đồng mã nguồn.
* **Môi trường làm bài & chấm điểm (IDE & Sandbox)**: Cung cấp trình biên dịch trực tuyến (Web-based IDE) ngay trên trình duyệt. Sandbox sẽ tự động tiếp nhận, biên dịch và chạy thử code của sinh viên đối chiếu với Testcase, sau đó trả về kết quả (Pass, Fail, Time Limit Exceeded...) theo thời gian thực.
* **Tương tác & Thảo luận**: Tích hợp diễn đàn hỏi đáp cho từng chủ đề, tính năng bình luận trực tiếp trên từng dòng code của bài nộp và hệ thống thông báo đẩy (Notifications) giúp kết nối chặt chẽ giữa học viên và giảng viên.

Hệ thống hướng đến 4 nhóm người dùng chính:
- **Quản trị viên (Admin)**: Nắm quyền hạn cao nhất, quản lý tài nguyên, thiết lập tham số hệ thống, giám sát cấu hình Sandbox và toàn bộ dữ liệu.
- **Giảng viên (Teacher)**: Trực tiếp điều hành lớp học, ra đề, cấu hình Testcase, chấm điểm bằng Rubric và giám sát tiến độ trong phòng thi.
- **Học viên (Student)**: Trực tiếp tham gia học tập, viết code trên giao diện IDE, làm bài trắc nghiệm và theo dõi bảng xếp hạng của lớp.
- **Khách (Guest)**: Người dùng chưa đăng nhập, sử dụng các tính năng cơ bản như xem giới thiệu, đăng ký và khôi phục mật khẩu.

#### 2.2.2. Mô tả chức năng

*Yêu cầu chức năng:*

Trong quá trình thiết kế và triển khai hệ thống, việc phân quyền người dùng đóng vai trò vô cùng quan trọng nhằm đảm bảo tính bảo mật, minh bạch và hiệu quả trong vận hành. Hệ thống được xây dựng trên nguyên tắc phân cấp quyền hạn rõ ràng, phù hợp với nghiệp vụ của từng đối tượng sử dụng.

- **Quản trị viên (Admin)** là người nắm quyền cao nhất. Admin thực hiện các chức năng thiết lập lõi như phê duyệt các đơn xin cấp quyền Giảng viên, khóa/mở khóa tài khoản người dùng, tạo mới môn học và thiết lập học kỳ hệ thống. Đặc biệt, Admin chịu trách nhiệm giám sát hệ thống máy chấm (Sandbox), xử lý các tiến trình biên dịch bị treo (zombie tasks) và kiểm tra log hoạt động bảo mật của hệ thống.
- **Giảng viên (Teacher)** đóng vai trò trung tâm trong quá trình đào tạo. Giảng viên được cấp quyền tạo lớp học mới, tạo hoặc nhân bản bài tập, tải lên các file tài liệu và cấu hình Testcase hàng loạt. Giảng viên có công cụ giám sát phòng thi theo thời gian thực, có quyền ép nộp bài ngay lập tức (Force submit) hoặc cộng thêm thời gian thi cho một cá nhân. Sau khi thi, giảng viên thực hiện chấm điểm tự luận bằng Rubric, để lại nhận xét ngay trên dòng code bị lỗi của sinh viên, và xem báo cáo tỷ lệ đạo văn.
- **Học viên (Student)** là đối tượng thụ hưởng trực tiếp các dịch vụ của nền tảng. Học viên truy cập để làm bài tập thông qua giao diện trình biên dịch trực tuyến (IDE có hỗ trợ tô màu cú pháp và Dark mode). Khi nhấn nút "Chạy thử", học viên nhận ngay phản hồi từ máy chấm. Ngoài ra, học viên làm bài trắc nghiệm, nộp file báo cáo, theo dõi Bảng xếp hạng (Leaderboard) thi đua cùng lớp, tra cứu sổ điểm và tham gia bình chọn (Vote) trên diễn đàn hỏi đáp.
- **Khách (Guest)** là lớp người dùng cơ bản nhất, được cung cấp tính năng tạo tài khoản (mặc định vào nhóm Học viên), đăng nhập tiện lợi qua Google Login API (OAuth 2.0) và thực hiện quy trình khôi phục mật khẩu qua Email tự động.

*Yêu cầu phi chức năng:*

- **Bảo mật**: Mật khẩu người dùng được băm (hash) an toàn trong cơ sở dữ liệu. Hệ thống áp dụng cơ chế xác thực phiên làm việc, chống các cuộc tấn công SQL Injection và Cross-Site Scripting (XSS). Dữ liệu mã nguồn tải lên hoặc nộp file được kiểm tra chặt chẽ về định dạng và dung lượng.
- **Hiệu năng và khả năng mở rộng**: Kiến trúc hệ thống tách biệt rõ ràng giữa Web Server (chạy website) và Sandbox Server (chấm bài). Sandbox ứng dụng công nghệ ảo hóa (Docker) để cách ly môi trường thực thi, chống mã độc, đồng thời giúp hệ thống xử lý mượt mà hàng trăm lượt nộp bài đồng thời thông qua cơ chế hàng đợi (Queue).
- **Tính tương thích**: Website được tối ưu hóa để hoạt động ổn định trên các trình duyệt phổ biến (Chrome, Edge, Safari). Riêng giao diện làm bài (IDE) được thiết kế ưu tiên hiển thị trên màn hình máy tính (PC/Laptop) để đảm bảo không gian thao tác viết code tốt nhất.
- **Trải nghiệm người dùng (UX)**: Giao diện trực quan, tối giản, hỗ trợ chế độ Dark mode giảm mỏi mắt cho lập trình viên. Các bài thi trắc nghiệm hoặc viết code đều có tính năng lưu nháp tự động (Auto-save) nhằm ngăn chặn việc mất dữ liệu khi gặp sự cố ngắt kết nối mạng.
