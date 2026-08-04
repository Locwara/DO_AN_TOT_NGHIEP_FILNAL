### Xác định các Use Case của hệ thống (chia theo Module):

1. Module Xác thực và Thông tin cá nhân (Authentication & Profile)
• Đăng ký tài khoản: (Guest) – Khách đăng ký, hệ thống mặc định cấp quyền Học viên (Student).
• Đăng nhập / Đăng xuất: (Admin, Teacher, Student, Guest) – Hỗ trợ đăng nhập thường và qua Google.
• Quên mật khẩu (Khôi phục qua Email): (Guest) – Khách yêu cầu gửi link khôi phục mật khẩu khi không thể đăng nhập.
• Đổi mật khẩu: (Admin, Teacher, Student) – Người dùng thay đổi mật khẩu trong mục Profile của mình sau khi đã đăng nhập.
• Xem & Chỉnh sửa thông tin cá nhân (Profile): (Admin, Teacher, Student) – Hỗ trợ cập nhật thông tin cá nhân và đổi Avatar.
• Đăng ký làm Giảng viên (Teacher Registration): (Student) – Học viên nộp đơn đăng ký làm giảng viên, chờ Admin phê duyệt.
• Xem Dashboard cá nhân: (Student, Teacher) – Theo dõi tiến độ học tập (Student) hoặc quản lý thống kê lớp học (Teacher).

2. Module Quản trị Hệ thống (Administration - Chỉ dành cho Admin)
• Xem Dashboard Quản trị: Theo dõi tổng quan người dùng, khóa học và hoạt động máy chủ.
• Quản lý Phê duyệt: Xét duyệt yêu cầu làm Giảng viên, xét duyệt Lớp học và Môn học mới do Giảng viên tạo.
• Quản lý Người dùng: Xem danh sách, thêm, sửa, reset mật khẩu thay cho người dùng, khóa/mở khóa tài khoản (có hỗ trợ thao tác hàng loạt).
• Quản lý Lớp học toàn cục: Xem danh sách toàn bộ lớp học, duyệt, khóa, xóa và xuất dữ liệu hàng loạt.
• Quản lý Môn học toàn cục: Quản lý danh mục môn học, thêm, sửa, xóa, khóa môn học.
• Quản lý Ngôn ngữ lập trình: Bật/tắt, cấu hình các tham số (time limit, memory limit) cho các ngôn ngữ hỗ trợ để chấm code.
• Quản lý Môi trường Sandbox: Test cấu hình máy chủ chấm điểm, giám sát và dọn dẹp các tiến trình bị treo.
• Quản lý Cấu hình hệ thống: Thiết lập các tham số chung của website.
• Xem Lịch sử hệ thống (Logs): Lưu vết hoạt động và truy xuất sự kiện hệ thống.

3. Module Quản lý Lớp học và Môn học (Classrooms & Subjects)
• Tìm kiếm & Xem danh sách Lớp học: (Tất cả) – Hỗ trợ tìm kiếm thông minh (có tự động gợi ý) và lưu lịch sử tìm kiếm.
• Quản lý Lớp học: (Teacher, Admin) – Tạo mới, sửa thông tin, xóa lớp học.
• Tham gia & Rời Lớp học: (Student) – Có chức năng tham gia nhanh (quick join) qua link/mã.
• Quản lý Thành viên Lớp học: (Teacher, Admin) – Phê duyệt học viên, xóa học viên, import danh sách học viên từ file.
• Quản lý Môn học: (Teacher, Admin) – Tạo môn học, gán môn học vào lớp.
• Quản lý Học kỳ: (Admin) – Khởi tạo và chỉnh sửa các học kỳ trong năm học.
• Quản lý Thông báo (Announcements): (Teacher, Admin) – Đăng bài, ghim thông báo trong lớp.
• Sổ điểm & Bảng xếp hạng (Gradebook): (Admin, Teacher, Student) – Xem thứ hạng, xuất báo cáo điểm ra file Excel.

4. Module Bài tập và Chống đạo văn (Assignments & Plagiarism)
• Quản lý Bài tập (Code/Tự luận): (Teacher, Admin) – Tạo, sửa, nhân bản (clone), xóa, đặt giới hạn nộp bài, ẩn/hiện đề. (Hỗ trợ định dạng Markdown cho đề bài).
• Quản lý File đính kèm: (Teacher, Admin, Student) - Tải lên và tải xuống các tài liệu đính kèm cho bài tập.
• Quản lý Testcase: (Teacher, Admin) – Thêm, sửa, xóa, nhập (import) bộ input/output để tự động chấm code.
• Quản lý Tiêu chí chấm (Rubric): (Teacher, Admin) – Tạo và xóa bộ tiêu chí để dùng cho việc chấm điểm thủ công.
• Quản lý Bài thi Trắc nghiệm (Quiz): (Teacher, Admin) – Tạo câu hỏi, nhập/xuất file CSV câu hỏi, xem trước đề.
• Kiểm tra Đạo văn (Plagiarism): (Teacher, Admin) – Quét tự động để phát hiện code giống nhau, so sánh mã nguồn trực quan giữa các bài nộp.

5. Module Làm bài và Chấm điểm (Submissions & Grading)
• Làm bài & Nộp bài: (Student)
  - Lập trình (Code): Giao diện IDE viết và chạy thử code trực tuyến (Hỗ trợ tùy chỉnh Theme Sáng/Tối - Dark Mode).
  - Trắc nghiệm (Quiz): Làm bài trắc nghiệm (có tính năng auto-save lưu nháp tự động).
  - Nộp file (File Submission): Tải file lên hệ thống (Backend xử lý ép nộp 1 lần duy nhất đối với bài thi).
• Phòng chờ thi (Lobby): (Student) – Màn hình chờ mở đề thi đếm ngược thời gian (áp dụng cho cả 3 hình thức thi).
• Giám sát phòng thi (Exam Monitor): (Teacher, Admin) – Quản lý trạng thái làm bài real-time, ép nộp bài (force submit) hoặc gia hạn thêm giờ cho học viên.
• Chấm điểm tự động: Hệ thống Sandbox tự biên dịch code, đối chiếu Testcase và tính điểm.
• Chấm điểm thủ công & Phản hồi: (Teacher, Admin) – Chấm theo Rubric, ghi chú/comment thẳng vào dòng code của sinh viên, chấm lại hàng loạt (regrade).
• Xem Lịch sử bài nộp: (Student, Teacher, Admin) – Tra cứu lịch sử các lần nộp bài và kết quả.

6. Module Thảo luận & Q&A (Discussions)
• Quản lý Diễn đàn / Chủ đề: (Student, Teacher, Admin) – Tạo bài đăng thảo luận, sửa, xóa bài.
• Tương tác Bài viết: (Student, Teacher, Admin) – Bình chọn (Vote), Đánh dấu câu trả lời đúng (Mark as answer), Ghim bài viết.

7. Module Thông báo (Notifications)
• Quản lý Thông báo: (Tất cả người dùng đã đăng nhập) – Nhận thông báo hệ thống, đánh dấu đã đọc một phần hoặc toàn bộ.
