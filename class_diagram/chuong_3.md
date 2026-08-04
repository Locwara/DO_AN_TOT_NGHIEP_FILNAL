# CHƯƠNG 3: KẾT QUẢ VÀ THẢO LUẬN

## 3.1. KẾT QUẢ TRIỂN KHAI GIAO DIỆN VÀ CHỨC NĂNG

Sau quá trình phân tích, thiết kế và lập trình, hệ thống "Website dạy và học lập trình trực tuyến" đã được hoàn thiện và triển khai thử nghiệm. Dưới đây là các kết quả đạt được, minh họa thông qua các giao diện chức năng cốt lõi của hệ thống, tập trung vào trải nghiệm người dùng và tính năng chuyên sâu.

### 3.1.1. Chức năng Đăng nhập và Xác thực

[CHÈN HÌNH ẢNH 1: Giao diện Đăng nhập / Đăng ký]
*Hình 3.1. Giao diện Đăng nhập và Đăng ký tài khoản*

Giao diện đăng nhập được thiết kế theo phong cách tối giản (minimalism) nhưng vẫn đảm bảo đầy đủ các tính năng bảo mật. Người dùng có thể đăng nhập bằng tài khoản truyền thống (nhập Email/Username và Mật khẩu) hoặc sử dụng tính năng đăng nhập nhanh thông qua nền tảng bên thứ ba (Google OAuth). Việc tích hợp Google Login giúp rút ngắn đáng kể thời gian thao tác, giảm tỷ lệ quên mật khẩu và tăng tính xác thực cho tài khoản. Khi người dùng nhập sai thông tin, hệ thống lập tức hiển thị thông báo lỗi (Validation) ngay trên màn hình mà không cần tải lại trang, giúp cải thiện trải nghiệm người dùng (User Experience - UX).

### 3.1.2. Quản lý Lớp học và Môn học

[CHÈN HÌNH ẢNH 2: Giao diện Danh sách Lớp học và Tham gia lớp]
*Hình 3.2. Giao diện Quản lý và Tham gia lớp học*

Đối với giảng viên, màn hình quản lý lớp học hiển thị dưới dạng các thẻ (Card) trực quan, liệt kê thông tin cơ bản như tên lớp, mã môn học, số lượng sinh viên và ảnh bìa đại diện. Giảng viên có thể dễ dàng tạo mới một lớp học, hệ thống sẽ tự động sinh ra một mã tham gia (Class code) ngẫu nhiên và duy nhất.

Đối với học viên, để tham gia vào lớp, họ chỉ cần nhập đúng mã lớp học do giảng viên cung cấp vào ô tìm kiếm. Nếu mã hợp lệ, hệ thống sẽ tự động ghi danh học viên vào danh sách lớp; ngược lại, sẽ có thông báo lỗi "Mã lớp không tồn tại". Việc sử dụng mã code giúp bảo mật thông tin lớp học, ngăn chặn người lạ truy cập trái phép.

### 3.1.3. Môi trường Thực hành Lập trình (IDE) và Chấm điểm tự động

[CHÈN HÌNH ẢNH 3: Giao diện làm bài lập trình với IDE web]
*Hình 3.3. Môi trường phát triển tích hợp (IDE) trên nền tảng web*

Đây là một trong những tính năng cốt lõi và phức tạp nhất của hệ thống. Giao diện làm bài lập trình cung cấp một môi trường phát triển tích hợp (IDE - Integrated Development Environment) trực tiếp trên trình duyệt. Trình soạn thảo mã nguồn được trang bị tính năng làm nổi bật cú pháp (Syntax highlighting), tự động thụt lề (Auto-indent) và hỗ trợ giao diện nền tối (Dark mode) giúp bảo vệ mắt sinh viên khi lập trình trong thời gian dài. Ngoài ra, tính năng tự động lưu (Auto-save) liên tục lưu lại các bản nháp (Draft) sau mỗi vài giây, đảm bảo sinh viên không bị mất code khi gặp sự cố mất mạng hoặc vô tình đóng trình duyệt.

[CHÈN HÌNH ẢNH 4: Giao diện kết quả chấm điểm từ Sandbox]
*Hình 3.4. Kết quả chấm bài tự động qua máy chủ cách ly (Sandbox)*

Khi sinh viên nhấn nút "Nộp bài" (Submit), mã nguồn sẽ được đóng gói và gửi đến một máy chủ chấm điểm độc lập và an toàn (Sandbox). Tại đây, mã nguồn được biên dịch (Compile) và thực thi (Execute) với các bộ dữ liệu thử nghiệm (Testcases) do giảng viên thiết lập sẵn. Sandbox giúp cách ly hoàn toàn mã độc, bảo vệ an toàn cho máy chủ chính. Ngay sau khi xử lý xong, kết quả sẽ được trả về trực tiếp trên màn hình của sinh viên, hiển thị chi tiết số lượng testcase đã vượt qua (Passed), thời gian chạy (Execution time) và dung lượng bộ nhớ sử dụng (Memory usage), cùng với số điểm đạt được.

### 3.1.4. Chức năng Kiểm tra Đạo văn (Plagiarism Detection)

[CHÈN HÌNH ẢNH 5: Giao diện so sánh mã nguồn đạo văn]
*Hình 3.5. Giao diện báo cáo và so sánh mã nguồn đạo văn*

Để đảm bảo tính công bằng trong học tập, hệ thống tích hợp công cụ kiểm tra đạo văn tự động. Giảng viên có thể kích hoạt tính năng này cho bất kỳ bài tập lập trình nào. Hệ thống sẽ so sánh chéo mã nguồn của tất cả các sinh viên trong lớp dựa trên cấu trúc thuật toán thay vì chỉ so sánh văn bản thuần túy. 

Kết quả trả về là một danh sách các cặp sinh viên có mức độ tương đồng cao (tính bằng phần trăm). Khi giảng viên nhấp vào xem chi tiết, giao diện sẽ hiển thị màn hình chia đôi (Split-view code diff), bôi màu nổi bật những đoạn code giống nhau giữa hai bài làm. Nhờ đó, giảng viên có được bằng chứng trực quan và chính xác để đưa ra kết luận về việc gian lận.

### 3.1.5. Giám sát Phòng thi Trực tuyến (Exam Monitor)

[CHÈN HÌNH ẢNH 6: Giao diện Giám sát phòng thi thời gian thực]
*Hình 3.6. Bảng điều khiển giám sát phòng thi trực tuyến*

Đối với các bài kiểm tra hoặc kỳ thi quan trọng, tính năng giám sát phòng thi cung cấp cho giảng viên quyền kiểm soát toàn diện. Giao diện (Dashboard) hiển thị danh sách toàn bộ thí sinh theo thời gian thực (Real-time). Giảng viên có thể theo dõi chính xác trạng thái của từng người: đang trực tuyến (Online), đã nộp bài (Submitted) hoặc mất kết nối (Offline).

Đặc biệt, hệ thống ghi nhận và cảnh báo ngay lập tức nếu sinh viên có hành vi chuyển tab (chuyển sang cửa sổ trình duyệt khác) để tra cứu tài liệu. Nếu cần thiết, giảng viên có thể sử dụng tính năng cộng thêm giờ (Add time) cho từng cá nhân bị sự cố, hoặc nhấn nút ép nộp bài (Force submit) đối với các trường hợp vi phạm quy chế thi.

### 3.1.6. Sổ điểm và Báo cáo Thống kê (Gradebook & Analytics)

[CHÈN HÌNH ẢNH 7: Giao diện Sổ điểm và xuất file Excel]
*Hình 3.7. Giao diện Sổ điểm lớp học và Thống kê*

Chức năng Sổ điểm (Gradebook) giúp tự động tổng hợp điểm số từ tất cả các bài tập, bài thi trắc nghiệm và bài tự luận vào một bảng duy nhất. Giảng viên có thể cái nhìn tổng quan về tình hình học tập của cả lớp, tính toán điểm trung bình và tỷ lệ hoàn thành bài tập. Hệ thống hỗ trợ bộ lọc thông minh theo tên, trạng thái nộp bài.

Điểm nổi bật là chức năng xuất dữ liệu (Export CSV). Với một thao tác nhấp chuột, toàn bộ bảng điểm sẽ được tải xuống dưới dạng file Excel, giúp giảng viên dễ dàng lưu trữ, in ấn hoặc báo cáo lên nhà trường mà không cần nhập liệu thủ công, loại bỏ hoàn toàn sai sót trong khâu làm điểm.

### 3.1.7. Thảo luận và Hỗ trợ Học tập (Q&A Forum)

[CHÈN HÌNH ẢNH 8: Giao diện khu vực Thảo luận bài tập]
*Hình 3.8. Giao diện khu vực hỏi đáp và thảo luận*

Mỗi bài tập đều được đính kèm một khu vực thảo luận (Forum) riêng biệt. Tại đây, sinh viên có thể đặt câu hỏi về những điểm chưa hiểu trong đề bài. Các sinh viên khác hoặc giảng viên có thể tham gia trả lời. Để tăng tính tương tác, hệ thống tích hợp chức năng bình chọn (Vote up/down) cho các câu trả lời hữu ích. Giảng viên cũng có quyền ghim (Pin) các thông báo quan trọng lên đầu hoặc đánh dấu "Câu trả lời đúng nhất" (Mark as Answer), giúp các sinh viên vào sau nhanh chóng tìm được hướng giải quyết mà không bị trôi tin nhắn.

## 3.2. THẢO LUẬN

Hệ thống "Website dạy và học lập trình trực tuyến" đã đáp ứng tốt các mục tiêu đề ra ban đầu. Việc ứng dụng kiến trúc vi dịch vụ ở mức độ nhẹ (tách biệt Web Server và máy chủ chấm điểm Sandbox) đã chứng minh được tính hiệu quả trong việc đảm bảo an toàn bảo mật và khả năng chịu tải (Load balancing) khi có nhiều sinh viên nộp bài cùng lúc. 

Giao diện người dùng được tối ưu hóa cho trải nghiệm học tập, các thao tác dư thừa được giảm thiểu tối đa. Các công nghệ hiện đại như nền tảng web linh hoạt (Responsive web design), giao tiếp thời gian thực (WebSockets/AJAX polling cho phần giám sát thi) và bộ so sánh mã nguồn (Code diff) đã được tích hợp thành công, tạo ra một sản phẩm có tính ứng dụng cao, hoàn toàn có khả năng triển khai thực tế tại các cơ sở giáo dục.
