### 3.2. PHÂN TÍCH, ĐÁNH GIÁ ĐỀ TÀI/ NỘI DUNG THỰC TẬP
#### 3.2.1. Xây dựng sơ đồ Use Case

Các tác nhân (Actors):
• Admin (Quản trị viên): Có quyền hạn cao nhất, quản lý toàn bộ hệ thống, phê duyệt các yêu cầu tạo tài khoản Giảng viên, Lớp học, Môn học, cấu hình máy chủ chấm code (Sandbox) và theo dõi lịch sử thao tác hệ thống (Logs).
• Teacher (Giảng viên): Quản lý các lớp học do mình phụ trách, tạo bài tập/bài thi (Code, Trắc nghiệm, Tự luận), import testcase, thiết lập tiêu chí chấm điểm (Rubric), giám sát phòng thi và kiểm tra đạo văn.
• Student (Học viên): Người dùng đã đăng ký thành công. Có quyền tham gia lớp học (thông qua mã code hoặc link), làm bài trên IDE trực tuyến, làm bài trắc nghiệm, nộp file bài tập, xem lịch sử nộp bài, xem thống kê điểm số và tham gia thảo luận.
• Guest (Khách): Tác nhân chưa đăng nhập, chỉ có thể thực hiện chức năng đăng nhập, đăng ký tài khoản (hệ thống mặc định cấp quyền Student) và yêu cầu khôi phục mật khẩu.
──────
#### 1. Biểu đồ Use Case Module Xác thực và Thông tin cá nhân
Mô tả: Module này cho phép tất cả các tác nhân thao tác với tài khoản và phiên làm việc của mình. Guest có thể đăng ký tài khoản mới (mặc định là Student). Các tác nhân đã có tài khoản hợp lệ có thể đăng nhập (bao gồm đăng nhập Google), đăng xuất, quên mật khẩu và cập nhật thông tin cá nhân. Học viên có thể gửi yêu cầu nâng cấp lên quyền Giảng viên (trạng thái chờ duyệt).

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE XÁC THỰC VÀ THÔNG TIN CÁ NHÂN TẠI ĐÂY]
Hình 3.x. Biểu đồ Use Case Module Xác thực và Thông tin cá nhân

Danh sách chức năng chi tiết:
- Đăng nhập (Login): Hỗ trợ đăng nhập bằng form truyền thống và qua tài khoản Google (OAuth).
- Đăng ký (Register): Cấp mặc định quyền Student.
- Khôi phục mật khẩu (Forgot Password): Gửi link đặt lại mật khẩu qua Email.
- Đổi mật khẩu (Change Password): Bảo mật tài khoản cá nhân.
- Quản lý hồ sơ (Profile): Chỉnh sửa thông tin cơ bản, thay đổi Avatar cá nhân (lưu trữ trên Cloudinary).
- Đăng ký Giảng viên (Teacher Registration): Nộp đơn đăng ký và xem trạng thái phê duyệt từ Admin.
- Xem Dashboard: Thống kê tiến độ học tập (Student) hoặc các lớp học đang phụ trách (Teacher).

Đặc tả chi tiết các Use Case:
Bảng 3.x. Đặc tả Use Case "Đăng ký tài khoản"
 Mục                 | Nội dung
---------------------|---------------------------------
 Tên Use Case        | Đăng ký tài khoản
 Tác nhân            | Guest
 Mô tả               | Cho phép người dùng chưa có tài khoản tạo tài khoản mới để truy cập hệ thống học tập.
 Tiền điều kiện      | Hệ thống hoạt động bình thường. Email chưa được đăng ký trong hệ thống.
 Hậu điều kiện       | Tài khoản được tạo thành công, lưu vào CSDL với quyền mặc định là Student và tự động đăng nhập.
 Luồng sự kiện chính | 1. Người dùng chọn chức năng "Đăng ký". 2. Hệ thống hiển thị Form đăng ký (Họ tên, Username, Email, Mật khẩu). 3. Người dùng điền thông tin và nhấn "Đăng ký". 4. Hệ thống kiểm tra tính hợp lệ và sự tồn tại của dữ liệu. 5. Hệ thống lưu tài khoản vào CSDL, khởi tạo session và điều hướng sang trang Dashboard.
 Luồng rẽ nhánh      | - Nếu Username hoặc Email đã tồn tại → Thông báo lỗi: "Tên đăng nhập hoặc Email đã được sử dụng". - Nếu mật khẩu không khớp hoặc quá ngắn → Hiển thị cảnh báo lỗi tại trường tương ứng.

Bảng 3.x. Đặc tả Use Case "Đăng nhập"
 Mục                 | Nội dung
---------------------|---------------------------------
 Tên Use Case        | Đăng nhập hệ thống
 Tác nhân            | Admin, Teacher, Student
 Mô tả               | Cho phép người dùng đã có tài khoản truy cập vào các chức năng của hệ thống theo đúng phân quyền.
 Tiền điều kiện      | Người dùng đã tạo tài khoản thành công và tài khoản không bị khóa.
 Hậu điều kiện       | Đăng nhập thành công, khởi tạo phiên làm việc (session) và chuyển hướng tới Trang chủ / Dashboard.
 Luồng sự kiện chính | 1. Người dùng truy cập trang Đăng nhập. 2. Hệ thống hiển thị Form đăng nhập và nút Đăng nhập qua Google. 3. Người dùng nhập Username và Password, nhấn "Đăng nhập". 4. Hệ thống kiểm tra đối chiếu thông tin trong CSDL. 5. Đăng nhập thành công, phân quyền Actor tương ứng và chuyển hướng người dùng đến Dashboard.
 Luồng rẽ nhánh      | - Nếu nhập sai Username hoặc Password → Thông báo: "Tên đăng nhập hoặc mật khẩu không đúng". - Nếu tài khoản bị Admin khóa → Thông báo lỗi truy cập.
──────
#### 2. Biểu đồ Use Case Module Quản trị Hệ thống (Chỉ dành cho Admin)
Mô tả: Chức năng dành riêng cho Admin nhằm kiểm soát quyền truy cập và tài nguyên của toàn bộ hệ thống. Admin có thể xem Dashboard tổng quan, phê duyệt các yêu cầu (Giảng viên, Lớp học, Môn học), quản lý tài khoản người dùng hàng loạt, cấu hình máy chủ chấm điểm (Sandbox) và theo dõi log hệ thống.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE QUẢN TRỊ HỆ THỐNG TẠI ĐÂY]
Hình 3.x. Biểu đồ Use Case Module Quản trị Hệ thống

Danh sách chức năng chi tiết:
- Xem Dashboard Quản trị: Trực quan hóa số liệu người dùng, lớp học, hoạt động máy chủ qua biểu đồ.
- Quản lý Phê duyệt (Approvals): Xem danh sách chờ, duyệt/từ chối cấp quyền Giảng viên, tạo Lớp/Môn học mới.
- Quản lý Người dùng toàn cục: Tìm kiếm, lọc, phân trang, thêm mới, chỉnh sửa thông tin, khóa/mở khóa tài khoản, reset mật khẩu thay người dùng, xuất dữ liệu.
- Quản lý Lớp học/Môn học toàn cục: Khóa, xóa, xem danh sách toàn bộ các lớp và môn học trên hệ thống.
- Quản lý Ngôn ngữ lập trình: Bật/tắt các ngôn ngữ code, cấu hình Time Limit, Memory Limit cho máy chấm.
- Quản lý Sandbox: Test kết nối API máy chấm, giám sát luồng chạy, thao tác kill/requeue các tiến trình chấm điểm bị treo (zombie tasks).
- Quản lý Cấu hình (Settings) & Lịch sử (Logs): Chỉnh tham số website, lưu vết hoạt động (Audit logs).

Đặc tả chi tiết các Use Case:
Bảng 3.x. Đặc tả Use Case "Phê duyệt yêu cầu"
 Mục                 | Nội dung
---------------------|---------------------------------
 Tên Use Case        | Phê duyệt yêu cầu làm Giảng viên
 Tác nhân            | Admin
 Mô tả               | Admin xem danh sách học viên nộp đơn xin cấp quyền Giảng viên và quyết định phê duyệt.
 Tiền điều kiện      | Admin đã đăng nhập. Có ít nhất 1 đơn đăng ký ở trạng thái chờ duyệt.
 Hậu điều kiện       | Người dùng được nâng cấp lên quyền Teacher (nếu duyệt) hoặc giữ nguyên quyền Student (nếu từ chối).
 Luồng sự kiện chính | 1. Admin truy cập mục Quản lý Phê duyệt. 2. Hệ thống hiển thị danh sách đơn đăng ký chờ duyệt. 3. Admin nhấn "Duyệt" (Approve) hoặc "Từ chối" (Reject). 4. Hệ thống cập nhật Role của tài khoản trong CSDL. 5. Hệ thống gửi thông báo (Notification) kết quả cho người dùng.
──────
#### 3. Biểu đồ Use Case Module Quản lý Lớp học và Môn học
Mô tả: Vận hành và tổ chức các lớp học thực tế. Cho phép Teacher và Admin tạo lớp, quản lý thành viên, đăng thông báo và xem sổ điểm. Student có thể tìm kiếm, tham gia lớp và theo dõi thứ hạng.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE QUẢN LÝ LỚP HỌC TẠI ĐÂY]
Hình 3.x. Biểu đồ Use Case Module Quản lý Lớp học và Môn học

Danh sách chức năng chi tiết:
- Tìm kiếm Lớp học: Hỗ trợ tìm kiếm thông minh (Auto-suggest), lưu lại và quản lý lịch sử tìm kiếm.
- Tham gia Lớp học (Join): Student có thể join nhanh thông qua mã Code lớp hoặc link mời.
- Quản lý Lớp học: Tạo mới, cập nhật thông tin, xóa lớp.
- Quản lý Thành viên: Duyệt yêu cầu vào lớp, xóa thành viên, Import danh sách học viên hàng loạt từ file CSV/Excel.
- Quản lý Môn học & Học kỳ: Tạo môn học, gán môn học vào các lớp, thiết lập học kỳ.
- Bảng tin (Stream) & Thông báo: Đăng thông báo, ghim (pin) bài viết quan trọng.
- Sổ điểm & Bảng xếp hạng (Gradebook): Tính toán điểm tổng, hiển thị Leaderboard thứ hạng sinh viên, Export báo cáo bảng điểm ra file Excel.

Đặc tả chi tiết các Use Case:
Bảng 3.x. Đặc tả Use Case "Import danh sách học viên"
 Mục                 | Nội dung
---------------------|---------------------------------
 Tên Use Case        | Import danh sách học viên
 Tác nhân            | Teacher, Admin
 Mô tả               | Cho phép Giảng viên thêm hàng loạt học viên vào lớp học thông qua file dữ liệu CSV/Excel.
 Tiền điều kiện      | Giảng viên đang quản lý lớp học. File tải lên phải đúng định dạng mẫu.
 Hậu điều kiện       | Các học viên có trong file được tự động gán vào lớp học.
 Luồng sự kiện chính | 1. Tác nhân vào trang Quản lý thành viên lớp, chọn "Import". 2. Hệ thống hiển thị popup tải file và cung cấp file mẫu (Template). 3. Tác nhân tải file CSV lên và nhấn "Xác nhận". 4. Hệ thống đọc file, kiểm tra sự tồn tại của các Username/Email. 5. Hệ thống gán các học viên hợp lệ vào lớp và thông báo số lượng thành công/thất bại.
 Luồng rẽ nhánh      | - Nếu file sai định dạng hoặc quá dung lượng → Cảnh báo lỗi tải file. - Nếu có học viên chưa tạo tài khoản trên hệ thống → Hiển thị danh sách các tài khoản không thể import.
──────
#### 4. Biểu đồ Use Case Module Bài tập và Chống đạo văn
Mô tả: Module hỗ trợ công tác ra đề và kiểm định chất lượng bài làm. Giảng viên có thể ra đa dạng các loại bài tập (Lập trình, Trắc nghiệm, Tự luận upload file), thiết lập các Testcase hoặc tiêu chí Rubric. Đặc biệt tích hợp hệ thống quét mã nguồn phát hiện gian lận.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE BÀI TẬP VÀ CHỐNG ĐẠO VĂN TẠI ĐÂY]
Hình 3.x. Biểu đồ Use Case Module Bài tập và Chống đạo văn

Danh sách chức năng chi tiết:
- Quản lý Bài tập/Bài thi: Tạo, sửa, xóa, nhân bản (Clone) bài tập. Trình soạn thảo đề bài hỗ trợ định dạng Markdown trực quan. Thiết lập thời gian mở/đóng, thời gian làm bài, điểm tối đa.
- Quản lý File đính kèm: Cho phép đính kèm tài liệu vào đề bài, người dùng có thể tải xuống (Download).
- Quản lý Testcase: Thêm, sửa, xóa các bộ Input/Output. Hỗ trợ tính năng Import Testcase hàng loạt.
- Quản lý Tiêu chí chấm (Rubric): Tạo các thang điểm (cấu trúc thành phần) để chấm bài tự luận.
- Quản lý Quiz: Tạo các câu hỏi trắc nghiệm, Import/Export ngân hàng câu hỏi qua file CSV.
- Kiểm tra Đạo văn (Plagiarism): Tự động quét và đối chiếu toàn bộ các bài nộp, so sánh mã nguồn (Code) trực quan hai cột để highlight các đoạn code giống hệt nhau, hiển thị tỷ lệ % gian lận.

Đặc tả chi tiết các Use Case:
Bảng 3.x. Đặc tả Use Case "Tạo bài tập/bài thi"
 Mục                 | Nội dung
---------------------|---------------------------------
 Tên Use Case        | Tạo bài tập/bài thi
 Tác nhân            | Teacher, Admin
 Mô tả               | Cho phép Giảng viên tạo một bài tập mới (Code/Quiz/File) với các thiết lập về thời gian và thang điểm.
 Tiền điều kiện      | Giảng viên có quyền quản lý môn học/lớp học.
 Hậu điều kiện       | Bài tập được khởi tạo thành công và hiển thị trên Bảng tin của lớp học.
 Luồng sự kiện chính | 1. Giảng viên chọn "Tạo bài tập". 2. Hệ thống hiển thị form nhập liệu (Tiêu đề, Mô tả bằng Markdown, Thể loại nộp bài, Hạn nộp). 3. Giảng viên điền thông tin và chọn trạng thái là "Bài thi" (nếu có). 4. Hệ thống kiểm tra validate dữ liệu. 5. Hệ thống lưu bài tập vào CSDL và điều hướng sang trang cấu hình Testcase hoặc cấu hình Yêu cầu file.
──────
#### 5. Biểu đồ Use Case Module Làm bài và Chấm điểm (Submissions & Grading)
Mô tả: Module cốt lõi phục vụ trải nghiệm thi và học. Sinh viên được cung cấp môi trường làm bài mượt mà. Hệ thống tự động biên dịch, chạy thử mã nguồn và trả về kết quả hoặc hỗ trợ Giảng viên chấm thủ công cực kỳ trực quan.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE LÀM BÀI VÀ CHẤM ĐIỂM TẠI ĐÂY]
Hình 3.x. Biểu đồ Use Case Module Làm bài và Chấm điểm

Danh sách chức năng chi tiết:
- Làm bài Lập trình (IDE): Trình biên dịch Code trực tuyến. Hỗ trợ tùy biến giao diện (Theme Sáng/Tối - Dark Mode), tự động thụt lề, tô màu cú pháp.
- Làm bài Trắc nghiệm (Quiz): Giao diện thi trắc nghiệm hỗ trợ tự động lưu nháp (Auto-save) sau mỗi lần chọn đáp án để chống mất bài khi rớt mạng.
- Làm bài Nộp File (Upload): Hỗ trợ validate định dạng và dung lượng file. Nếu là Bài thi, Backend sẽ ép buộc chỉ được nộp 1 lần duy nhất (không cho nộp lại).
- Phòng chờ thi (Exam/Quiz Lobby): Màn hình chờ mở đề, đếm ngược thời gian (áp dụng cho mọi hình thức thi).
- Giám sát phòng thi (Exam Monitor): Giám sát trạng thái sinh viên Real-time (Đang làm, Đã nộp, Bỏ thi). Hỗ trợ tác vụ ép nộp bài ngay lập tức (Force submit) hoặc cộng thêm giờ (Extend time) cho cá nhân.
- Chấm điểm tự động (Auto-grade): Hệ thống Sandbox độc lập tự động đóng gói code, biên dịch, chạy qua các Testcase và tính điểm.
- Chấm điểm thủ công (Manual-grade): Giảng viên chấm điểm bằng Rubric, bôi đen và để lại bình luận (Comment) trực tiếp trên từng dòng code của sinh viên, hỗ trợ chấm lại hàng loạt (Bulk Regrade).
- Xem Lịch sử bài nộp: Lưu và tra cứu chi tiết mọi lần nộp bài (submission history).

Đặc tả chi tiết các Use Case:
Bảng 3.x. Đặc tả Use Case "Làm bài trên trình biên dịch (IDE)"
 Mục                 | Nội dung
---------------------|---------------------------------
 Tên Use Case        | Làm bài trên IDE
 Tác nhân            | Student
 Mô tả               | Học viên sử dụng trình biên dịch tích hợp trên web để viết mã nguồn, chạy thử và nộp bài.
 Tiền điều kiện      | Bài tập đang trong thời gian cho phép nộp. Học viên đã vào màn hình làm bài.
 Hậu điều kiện       | Mã nguồn được gửi đi chấm tự động và lưu lịch sử nộp bài vào CSDL.
 Luồng sự kiện chính | 1. Học viên đọc đề bài (hiển thị định dạng Markdown) ở cột trái. 2. Học viên chọn ngôn ngữ lập trình và gõ code vào IDE ở cột phải (có thể bật Dark mode). 3. Học viên bấm "Chạy thử" (Run) để kiểm tra với Testcase mẫu. 4. Hệ thống gửi code đến Sandbox chạy thử và trả về kết quả output trực tiếp. 5. Học viên bấm "Nộp bài" (Submit). 6. Hệ thống khóa trình soạn thảo, đưa bài vào hàng đợi (Queue) để chấm điểm chính thức toàn bộ Testcase.
──────
#### 6. Biểu đồ Use Case Module Thảo luận & Q&A
Mô tả: Module tạo ra không gian tương tác giải đáp thắc mắc chuyên sâu cho từng chủ đề bài tập/môn học. 

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE THẢO LUẬN TẠI ĐÂY]
Hình 3.x. Biểu đồ Use Case Module Thảo luận & Q&A

Danh sách chức năng chi tiết:
- Quản lý Chủ đề: Tạo bài đăng hỏi đáp, chỉnh sửa, xóa bài viết cá nhân.
- Tương tác bình chọn (Voting): Click Vote-Up/Vote-Down để đẩy bài viết chất lượng lên đầu.
- Quản lý nâng cao: Tác giả có thể đánh dấu "Câu trả lời đúng" (Mark as answer - hiển thị icon check_circle màu xanh), Giảng viên có quyền ghim bài (Pin) lên đầu trang.
──────
#### 7. Biểu đồ Use Case Module Thông báo
Mô tả: Hệ thống Alert đẩy thông tin các sự kiện quan trọng đến người dùng kịp thời.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE THÔNG BÁO TẠI ĐÂY]
Hình 3.x. Biểu đồ Use Case Module Thông báo

Danh sách chức năng chi tiết:
- Nhận thông báo: Tự động gửi cảnh báo khi có bài tập mới, có điểm thi, có bình luận trong code, hoặc được duyệt vào lớp (Icon thông báo thay đổi linh hoạt theo ngữ cảnh).
- Lọc thông báo: Lọc các thông báo "Tất cả" hoặc "Chưa đọc" thông qua các Tabs.
- Quản lý trạng thái: Click vào một thông báo để đánh dấu đã đọc, hoặc sử dụng nút "Đánh dấu đã đọc tất cả" (Mark all read) để xử lý hàng loạt.
