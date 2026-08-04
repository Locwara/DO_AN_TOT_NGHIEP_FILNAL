### 2.2. PHÂN TÍCH THIẾT KẾ
#### 2.2.1. Sơ đồ Usecase 

Các tác nhân (Actors):
- **Admin (Quản trị viên)**: Có quyền hạn cao nhất, quản lý toàn bộ hệ thống, phê duyệt các yêu cầu tạo tài khoản Giảng viên, Lớp học, Môn học, cấu hình máy chủ chấm code (Sandbox) và theo dõi lịch sử thao tác hệ thống (Logs).
- **Teacher (Giảng viên)**: Quản lý các lớp học do mình phụ trách, tạo bài tập/bài thi (Code, Trắc nghiệm, Tự luận), import testcase, thiết lập tiêu chí chấm điểm (Rubric), giám sát phòng thi và kiểm tra đạo văn.
- **Student (Học viên)**: Người dùng đã đăng ký thành công. Có quyền tham gia lớp học (thông qua mã code hoặc link), làm bài trên IDE trực tuyến, làm bài trắc nghiệm, nộp file bài tập, xem lịch sử nộp bài, xem thống kê điểm số và tham gia thảo luận.
- **Guest (Khách)**: Tác nhân chưa đăng nhập, chỉ có thể thực hiện chức năng đăng nhập, đăng ký tài khoản (hệ thống mặc định cấp quyền Student) và yêu cầu khôi phục mật khẩu.

---
#### 2.2.1.1. Biểu đồ Use Case Module Xác thực và Thông tin cá nhân
Mô tả: Module này cho phép tất cả các tác nhân thao tác với tài khoản và phiên làm việc của mình. Guest có thể đăng ký tài khoản mới (mặc định là Student). Các tác nhân đã có tài khoản hợp lệ có thể đăng nhập (bao gồm đăng nhập Google), đăng xuất, quên mật khẩu và cập nhật thông tin cá nhân. Học viên có thể gửi yêu cầu nâng cấp lên quyền Giảng viên (trạng thái chờ duyệt).

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE XÁC THỰC VÀ THÔNG TIN CÁ NHÂN TẠI ĐÂY]
Hình 3.1. Biểu đồ Use Case Module Xác thực và Thông tin cá nhân

Danh sách chức năng chi tiết:
- Đăng nhập (Login)
- Đăng ký (Register)
- Khôi phục mật khẩu (Forgot Password)
- Đổi mật khẩu (Change Password)
- Quản lý hồ sơ (Profile)
- Đăng ký Giảng viên (Teacher Registration)
- Xem Dashboard

**Đặc tả chi tiết các Use Case:**

Bảng 3.1. Đặc tả Use Case "Đăng nhập"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Đăng nhập hệ thống |
| Tác nhân | Admin, Teacher, Student |
| Mô tả | Cho phép người dùng đã có tài khoản truy cập vào hệ thống. |
| Tiền điều kiện | Người dùng đã tạo tài khoản và không bị khóa. |
| Hậu điều kiện | Đăng nhập thành công, khởi tạo session, chuyển hướng tới Dashboard. |
| Luồng sự kiện chính | 1. Chọn Đăng nhập. 2. Nhập Username/Password hoặc chọn Đăng nhập Google. 3. Nhấn "Đăng nhập". 4. Hệ thống kiểm tra. 5. Chuyển hướng Dashboard. |
| Luồng rẽ nhánh | - Sai thông tin → Thông báo lỗi. <br>- Tài khoản bị khóa → Cảnh báo. |

Bảng 3.2. Đặc tả Use Case "Đăng ký tài khoản"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Đăng ký tài khoản |
| Tác nhân | Guest |
| Mô tả | Cho phép người dùng tạo tài khoản mới. |
| Tiền điều kiện | Email chưa tồn tại trong hệ thống. |
| Hậu điều kiện | Tài khoản được tạo với quyền Student. |
| Luồng sự kiện chính | 1. Chọn Đăng ký. 2. Nhập Họ tên, Username, Email, Mật khẩu. 3. Hệ thống validate. 4. Lưu CSDL và tự động đăng nhập. |
| Luồng rẽ nhánh | - Email/Username đã tồn tại → Thông báo lỗi. |

Bảng 3.3. Đặc tả Use Case "Khôi phục mật khẩu"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Khôi phục mật khẩu (Forgot Password) |
| Tác nhân | Guest |
| Mô tả | Khôi phục mật khẩu qua Email khi người dùng quên. |
| Tiền điều kiện | Người dùng có Email hợp lệ đã đăng ký. |
| Hậu điều kiện | Mật khẩu mới được thiết lập. |
| Luồng sự kiện chính | 1. Chọn Quên mật khẩu. 2. Nhập Email. 3. Hệ thống gửi link khôi phục. 4. Người dùng bấm link, nhập mật khẩu mới. 5. Lưu CSDL. |
| Luồng rẽ nhánh | - Email không tồn tại → Thông báo không tìm thấy. |

Bảng 3.4. Đặc tả Use Case "Đổi mật khẩu"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Đổi mật khẩu |
| Tác nhân | Admin, Teacher, Student |
| Mô tả | Người dùng đổi mật khẩu khi đang đăng nhập để bảo mật. |
| Tiền điều kiện | Đã đăng nhập. |
| Hậu điều kiện | Mật khẩu được cập nhật. |
| Luồng sự kiện chính | 1. Vào Profile. 2. Nhập mật khẩu cũ, mật khẩu mới, xác nhận mật khẩu. 3. Nhấn Lưu. 4. Hệ thống cập nhật. |
| Luồng rẽ nhánh | - Mật khẩu cũ sai → Thông báo lỗi. |

Bảng 3.5. Đặc tả Use Case "Quản lý hồ sơ"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý hồ sơ (Profile) |
| Tác nhân | Admin, Teacher, Student |
| Mô tả | Chỉnh sửa thông tin cá nhân và Avatar. |
| Tiền điều kiện | Đã đăng nhập. |
| Hậu điều kiện | Thông tin/Avatar mới được lưu lên DB/Cloudinary. |
| Luồng sự kiện chính | 1. Vào trang Cá nhân. 2. Đổi Họ tên, SĐT, up Avatar. 3. Nhấn Lưu. 4. Hệ thống cập nhật. |
| Luồng rẽ nhánh | - File ảnh quá lớn/sai định dạng → Báo lỗi upload. |

Bảng 3.6. Đặc tả Use Case "Đăng ký Giảng viên"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Đăng ký Giảng viên |
| Tác nhân | Student |
| Mô tả | Nộp đơn yêu cầu cấp quyền Giảng viên. |
| Tiền điều kiện | Quyền hiện tại là Student. |
| Hậu điều kiện | Đơn được gửi cho Admin chờ duyệt. |
| Luồng sự kiện chính | 1. Bấm Đăng ký Giảng viên. 2. Điền thông tin chuyên môn. 3. Gửi đơn. 4. Trạng thái chuyển sang "Chờ duyệt". |
| Luồng rẽ nhánh | - Đã gửi đơn trước đó → Hệ thống báo đơn đang chờ duyệt. |

Bảng 3.7. Đặc tả Use Case "Xem Dashboard"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Xem Dashboard |
| Tác nhân | Teacher, Student |
| Mô tả | Xem thống kê cá nhân (Tiến độ học tập, lớp quản lý). |
| Tiền điều kiện | Đã đăng nhập. |
| Hậu điều kiện | Giao diện Dashboard được hiển thị. |
| Luồng sự kiện chính | 1. Truy cập trang chủ. 2. Hệ thống query dữ liệu thống kê. 3. Render biểu đồ và danh sách. |
| Luồng rẽ nhánh | - Lỗi query DB → Thông báo hệ thống bận. |

---
#### 2.2.1.2. Biểu đồ Use Case Module Quản trị Hệ thống (Chỉ dành cho Admin)
Mô tả: Chức năng dành riêng cho Admin nhằm kiểm soát quyền truy cập và tài nguyên. Admin có thể xem Dashboard, phê duyệt yêu cầu, quản lý người dùng, lớp học, cấu hình Sandbox và xem Logs.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE QUẢN TRỊ HỆ THỐNG TẠI ĐÂY]
Hình 3.2. Biểu đồ Use Case Module Quản trị Hệ thống

Danh sách chức năng chi tiết:
- Xem Dashboard Quản trị
- Quản lý Phê duyệt (Approvals)
- Quản lý Người dùng toàn cục
- Quản lý Lớp học/Môn học toàn cục
- Quản lý Ngôn ngữ lập trình
- Quản lý Sandbox
- Quản lý Cấu hình (Settings) & Lịch sử (Logs)

**Đặc tả chi tiết các Use Case:**

Bảng 3.8. Đặc tả Use Case "Xem Dashboard Quản trị"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Xem Dashboard Quản trị |
| Tác nhân | Admin |
| Mô tả | Trực quan hóa số liệu hệ thống. |
| Tiền điều kiện | Đăng nhập bằng quyền Admin. |
| Hậu điều kiện | Hiển thị biểu đồ thống kê. |
| Luồng sự kiện chính | 1. Vào Dashboard. 2. Xem các chỉ số: tổng user, lớp học, tải server Sandbox. |
| Luồng rẽ nhánh | - Không có quyền Admin → Từ chối truy cập (403). |

Bảng 3.9. Đặc tả Use Case "Quản lý Phê duyệt"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Phê duyệt |
| Tác nhân | Admin |
| Mô tả | Duyệt/Từ chối cấp quyền Giảng viên, tạo Lớp. |
| Tiền điều kiện | Có yêu cầu chờ duyệt. |
| Hậu điều kiện | Yêu cầu được chuyển trạng thái. |
| Luồng sự kiện chính | 1. Vào danh sách chờ duyệt. 2. Bấm "Duyệt" hoặc "Từ chối". 3. Hệ thống đổi Role/Tạo lớp. 4. Gửi thông báo cho người yêu cầu. |
| Luồng rẽ nhánh | - Không có dữ liệu → Hiển thị danh sách rỗng. |

Bảng 3.10. Đặc tả Use Case "Quản lý Người dùng toàn cục"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Người dùng toàn cục |
| Tác nhân | Admin |
| Mô tả | Thêm/sửa/xóa/khóa tài khoản, reset mật khẩu người dùng. |
| Tiền điều kiện | Đăng nhập Admin. |
| Hậu điều kiện | Dữ liệu người dùng được cập nhật. |
| Luồng sự kiện chính | 1. Vào Quản lý User. 2. Tìm kiếm User. 3. Click nút Khóa/Reset Pass. 4. Xác nhận. 5. Hệ thống thực thi. |
| Luồng rẽ nhánh | - Khóa chính mình → Hệ thống chặn thao tác. |

Bảng 3.11. Đặc tả Use Case "Quản lý Lớp học/Môn học toàn cục"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Lớp học/Môn học toàn cục |
| Tác nhân | Admin |
| Mô tả | Khóa, xóa hoặc xem bất kỳ lớp học/môn học nào. |
| Tiền điều kiện | Đăng nhập Admin. |
| Hậu điều kiện | Lớp/Môn bị tác động. |
| Luồng sự kiện chính | 1. Vào DS Lớp/Môn. 2. Bấm Khóa/Xóa. 3. Hệ thống kiểm tra ràng buộc. 4. Xóa/Khóa thành công. |
| Luồng rẽ nhánh | - Lớp đang có thi → Không cho phép xóa. |

Bảng 3.12. Đặc tả Use Case "Quản lý Ngôn ngữ lập trình"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Ngôn ngữ lập trình |
| Tác nhân | Admin |
| Mô tả | Bật/tắt ngôn ngữ hỗ trợ biên dịch, set Time/Memory Limit. |
| Tiền điều kiện | Đăng nhập Admin. |
| Hậu điều kiện | Giới hạn ngôn ngữ được cập nhật vào Sandbox. |
| Luồng sự kiện chính | 1. Vào Cấu hình Ngôn ngữ. 2. Đổi Time Limit (vd Python: 2s, C++: 1s). 3. Nhấn Lưu. |
| Luồng rẽ nhánh | - Nhập số âm → Cảnh báo lỗi validate. |

Bảng 3.13. Đặc tả Use Case "Quản lý Sandbox"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Sandbox |
| Tác nhân | Admin |
| Mô tả | Theo dõi, test kết nối, kill tiến trình Sandbox bị treo. |
| Tiền điều kiện | Sandbox Server đang bật. |
| Hậu điều kiện | Tiến trình zombie bị diệt, hàng đợi được thông. |
| Luồng sự kiện chính | 1. Vào Quản lý Sandbox. 2. Bấm Test Connection. 3. Xem danh sách tiến trình. 4. Bấm "Kill" tiến trình treo. |
| Luồng rẽ nhánh | - Sandbox mất kết nối → Báo lỗi offline. |

Bảng 3.14. Đặc tả Use Case "Quản lý Cấu hình & Logs"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Cấu hình & Lịch sử (Logs) |
| Tác nhân | Admin |
| Mô tả | Xem Audit logs và cài đặt chung. |
| Tiền điều kiện | Đăng nhập Admin. |
| Hậu điều kiện | N/A (Chủ yếu là thao tác xem/read). |
| Luồng sự kiện chính | 1. Vào System Logs. 2. Lọc log theo ngày, hành động, mức độ. |
| Luồng rẽ nhánh | - Log quá lớn → Tự động phân trang hoặc tải báo cáo CSV. |

---
#### 2.2.1.3. Biểu đồ Use Case Module Quản lý Lớp học và Môn học
Mô tả: Vận hành và tổ chức lớp. Teacher tạo lớp, quản lý thành viên, đăng thông báo, sổ điểm. Student tham gia lớp và xem điểm.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE QUẢN LÝ LỚP HỌC TẠI ĐÂY]
Hình 3.3. Biểu đồ Use Case Module Quản lý Lớp học và Môn học

Danh sách chức năng chi tiết:
- Tìm kiếm Lớp học
- Tham gia Lớp học (Join)
- Quản lý Lớp học (Tạo, sửa, xóa)
- Quản lý Thành viên (Duyệt, xóa)
- Import danh sách học viên
- Quản lý Môn học & Học kỳ
- Bảng tin (Stream) & Thông báo
- Sổ điểm & Bảng xếp hạng

**Đặc tả chi tiết các Use Case:**

Bảng 3.15. Đặc tả Use Case "Tìm kiếm Lớp học"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Tìm kiếm Lớp học |
| Tác nhân | Student |
| Mô tả | Tìm lớp bằng Auto-suggest. |
| Tiền điều kiện | Đã đăng nhập. |
| Hậu điều kiện | Hiển thị kết quả lớp học. |
| Luồng sự kiện chính | 1. Nhập từ khóa vào ô tìm kiếm. 2. Hệ thống gọi API auto-suggest. 3. Hiển thị danh sách khớp. |
| Luồng rẽ nhánh | - Không tìm thấy → Báo "Không có kết quả". |

Bảng 3.16. Đặc tả Use Case "Tham gia Lớp học"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Tham gia Lớp học (Join) |
| Tác nhân | Student |
| Mô tả | Tham gia qua Mã Code hoặc Link mời. |
| Tiền điều kiện | Mã/Link hợp lệ. |
| Hậu điều kiện | Student trở thành thành viên (Member) của lớp. |
| Luồng sự kiện chính | 1. Nhập Mã lớp hoặc click Link mời. 2. Hệ thống xác thực mã. 3. Thêm bản ghi vào `classroom_members`. 4. Chuyển vào trang Bảng tin lớp. |
| Luồng rẽ nhánh | - Mã sai/hết hạn → Báo lỗi mã không hợp lệ. |

Bảng 3.17. Đặc tả Use Case "Quản lý Lớp học"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Lớp học |
| Tác nhân | Teacher |
| Mô tả | Tạo, sửa, xóa lớp học do mình phụ trách. |
| Tiền điều kiện | Có quyền Teacher. |
| Hậu điều kiện | Lớp được cập nhật trong DB. |
| Luồng sự kiện chính | 1. Bấm Tạo lớp. 2. Nhập Tên lớp, Mô tả. 3. Nhấn Lưu. 4. Hệ thống sinh mã Invite Code và lưu. |
| Luồng rẽ nhánh | - Thiếu Tên lớp → Form yêu cầu nhập lại. |

Bảng 3.18. Đặc tả Use Case "Quản lý Thành viên"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Thành viên |
| Tác nhân | Teacher |
| Mô tả | Duyệt, xóa sinh viên khỏi lớp. |
| Tiền điều kiện | Lớp đang có sinh viên tham gia. |
| Hậu điều kiện | Danh sách sinh viên được cập nhật. |
| Luồng sự kiện chính | 1. Vào Tab Thành viên. 2. Bấm Xóa/Duyệt user. 3. Hệ thống đổi trạng thái `status` trong DB. |
| Luồng rẽ nhánh | - N/A |

Bảng 3.19. Đặc tả Use Case "Import danh sách học viên"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Import danh sách học viên |
| Tác nhân | Teacher, Admin |
| Mô tả | Thêm hàng loạt học viên qua file Excel/CSV. |
| Tiền điều kiện | File đúng định dạng. |
| Hậu điều kiện | Các học viên được tự động gán vào lớp. |
| Luồng sự kiện chính | 1. Chọn Import. 2. Upload file CSV. 3. Hệ thống đọc và đối chiếu Email. 4. Lưu vào CSDL và báo số lượng thành công. |
| Luồng rẽ nhánh | - Lỗi sai định dạng → Từ chối file. - User chưa đăng ký tài khoản → List ra danh sách lỗi. |

Bảng 3.20. Đặc tả Use Case "Quản lý Môn học & Học kỳ"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Môn học & Học kỳ |
| Tác nhân | Admin, Teacher |
| Mô tả | Thêm môn, gán môn vào học kỳ. |
| Tiền điều kiện | Đăng nhập quyền hợp lệ. |
| Hậu điều kiện | Môn/Học kỳ được lưu. |
| Luồng sự kiện chính | 1. Vào Quản lý Môn. 2. Khai báo Môn mới. 3. Gán Môn vào Lớp học. 4. Lưu. |
| Luồng rẽ nhánh | - Trùng mã môn → Báo lỗi. |

Bảng 3.21. Đặc tả Use Case "Bảng tin & Thông báo"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Bảng tin |
| Tác nhân | Teacher |
| Mô tả | Đăng bài, ghim bài quan trọng trong lớp. |
| Tiền điều kiện | Lớp học đã được tạo. |
| Hậu điều kiện | Bài viết xuất hiện trên luồng sự kiện (Stream). |
| Luồng sự kiện chính | 1. Ở trang chủ lớp, nhập thông báo. 2. Đính kèm file (nếu có). 3. Bấm Đăng. 4. Hệ thống đẩy Post lên Stream. |
| Luồng rẽ nhánh | - Nội dung rỗng → Không cho bấm Đăng. |

Bảng 3.22. Đặc tả Use Case "Sổ điểm & Bảng xếp hạng"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Sổ điểm & Bảng xếp hạng |
| Tác nhân | Teacher, Student |
| Mô tả | Hiển thị điểm thi và thứ hạng. Teacher có thể Export CSV. |
| Tiền điều kiện | Đã có bài thi được chấm điểm. |
| Hậu điều kiện | Hiển thị Grid điểm số trực quan. |
| Luồng sự kiện chính | 1. Vào Tab Sổ điểm. 2. Hệ thống tính toán tổng điểm từ các Assignments. 3. Xếp hạng giảm dần. 4. Teacher bấm "Xuất Excel". |
| Luồng rẽ nhánh | - Lớp chưa có bài tập → Bảng rỗng. |

---
#### 2.2.1.4. Biểu đồ Use Case Module Bài tập và Chống đạo văn
Mô tả: Hỗ trợ ra đa dạng các loại bài tập (Lập trình, Trắc nghiệm, Upload file), thiết lập Testcase, tiêu chí Rubric và quét đạo văn mã nguồn.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE BÀI TẬP VÀ CHỐNG ĐẠO VĂN TẠI ĐÂY]
Hình 3.4. Biểu đồ Use Case Module Bài tập và Chống đạo văn

Danh sách chức năng chi tiết:
- Tạo bài tập/bài thi
- Quản lý Bài tập/Bài thi (Sửa, xóa, nhân bản)
- Quản lý File đính kèm
- Quản lý Testcase
- Quản lý Tiêu chí chấm (Rubric)
- Quản lý Quiz
- Kiểm tra Đạo văn (Plagiarism)

**Đặc tả chi tiết các Use Case:**

Bảng 3.23. Đặc tả Use Case "Tạo bài tập/bài thi"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Tạo bài tập/bài thi |
| Tác nhân | Teacher |
| Mô tả | Tạo đề bài (Code/Quiz/File) với thời gian và thang điểm. |
| Tiền điều kiện | Đang quản lý lớp học. |
| Hậu điều kiện | Bài tập được tạo và hiển thị lên Stream lớp. |
| Luồng sự kiện chính | 1. Chọn Tạo bài tập. 2. Nhập Tiêu đề, Mô tả (Markdown), Hạn nộp. 3. Lưu và chuyển sang cấu hình Testcase/Quiz. |
| Luồng rẽ nhánh | - Thiếu tiêu đề → Cảnh báo. |

Bảng 3.24. Đặc tả Use Case "Quản lý Bài tập/Bài thi"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Bài tập/Bài thi |
| Tác nhân | Teacher |
| Mô tả | Sửa, Xóa, Nhân bản (Clone) bài tập. |
| Tiền điều kiện | Bài tập đã được tạo. |
| Hậu điều kiện | Bài tập được cập nhật dữ liệu. |
| Luồng sự kiện chính | 1. Chọn Menu thao tác ở góc bài tập. 2. Chọn Clone/Sửa. 3. Lưu. |
| Luồng rẽ nhánh | - Đang có học viên thi → Chặn thao tác Sửa/Xóa. |

Bảng 3.25. Đặc tả Use Case "Quản lý File đính kèm"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý File đính kèm |
| Tác nhân | Teacher, Student |
| Mô tả | Teacher up tài liệu, Student tải xuống. |
| Tiền điều kiện | Có bài tập. |
| Hậu điều kiện | File được lưu Storage và gán vào ID bài tập. |
| Luồng sự kiện chính | 1. Teacher chọn Upload file cho bài tập. 2. Sinh viên vào bài tập, nhấn Download. |
| Luồng rẽ nhánh | - Vượt dung lượng cho phép → Lỗi upload. |

Bảng 3.26. Đặc tả Use Case "Quản lý Testcase"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Testcase |
| Tác nhân | Teacher |
| Mô tả | Thêm, sửa, xóa, import hàng loạt Input/Output mẫu. |
| Tiền điều kiện | Bài tập loại Lập trình (Code). |
| Hậu điều kiện | Bộ Testcase được gắn vào Bài tập. |
| Luồng sự kiện chính | 1. Mở Cấu hình Testcase. 2. Nhập thủ công hoặc Import file ZIP. 3. Lưu hệ số điểm (weight) từng case. 4. Đánh dấu Ẩn/Hiện. |
| Luồng rẽ nhánh | - File ZIP không đúng cấu trúc thư mục → Báo lỗi định dạng. |

Bảng 3.27. Đặc tả Use Case "Quản lý Tiêu chí chấm (Rubric)"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Rubric |
| Tác nhân | Teacher |
| Mô tả | Tạo các thang điểm chấm bài Tự luận. |
| Tiền điều kiện | Bài tập chưa cấu hình Rubric. |
| Hậu điều kiện | Rubric được lưu và phục vụ màn hình chấm tay. |
| Luồng sự kiện chính | 1. Tạo Tiêu chí (vd: Format Code, Thuật toán). 2. Định mức điểm tối đa. 3. Lưu lại. |
| Luồng rẽ nhánh | - Tổng điểm Rubric khác điểm bài tập → Hiện cảnh báo. |

Bảng 3.28. Đặc tả Use Case "Quản lý Quiz"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Quiz |
| Tác nhân | Teacher |
| Mô tả | Tạo câu hỏi, đáp án, Import ngân hàng câu hỏi. |
| Tiền điều kiện | Bài tập loại Quiz. |
| Hậu điều kiện | Bộ câu hỏi được tạo. |
| Luồng sự kiện chính | 1. Nhập câu hỏi, Thêm lựa chọn (A,B,C,D). 2. Tick chọn đáp án Đúng. 3. Lưu lại. |
| Luồng rẽ nhánh | - Chưa chọn đáp án đúng nào → Không cho lưu. |

Bảng 3.29. Đặc tả Use Case "Kiểm tra Đạo văn"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Kiểm tra Đạo văn (Plagiarism) |
| Tác nhân | Teacher |
| Mô tả | Tự động quét và đối chiếu toàn bộ các bài nộp code. |
| Tiền điều kiện | Có từ 2 sinh viên nộp bài trở lên. |
| Hậu điều kiện | Hiển thị bảng tỷ lệ % gian lận và Highlight code. |
| Luồng sự kiện chính | 1. Nhấn nút Quét Đạo Văn. 2. Hệ thống gọi thuật toán so sánh chuỗi (Moss). 3. Trả về kết quả các cặp sinh viên giống nhau. 4. Click vào để xem code đối chiếu 2 cột. |
| Luồng rẽ nhánh | - Chưa có bài nộp → Nút bị mờ (Disable). |

---
#### 2.2.1.5. Biểu đồ Use Case Module Làm bài và Chấm điểm (Submissions & Grading)
Mô tả: Trải nghiệm thi, biên dịch mã, chấm tự động qua Sandbox hoặc chấm tay qua Rubric.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE LÀM BÀI VÀ CHẤM ĐIỂM TẠI ĐÂY]
Hình 3.5. Biểu đồ Use Case Module Làm bài và Chấm điểm

Danh sách chức năng chi tiết:
- Làm bài Lập trình (IDE)
- Làm bài Trắc nghiệm (Quiz)
- Làm bài Nộp File (Upload)
- Phòng chờ thi (Exam Lobby)
- Giám sát phòng thi (Exam Monitor)
- Chấm điểm tự động (Auto-grade)
- Chấm điểm thủ công (Manual-grade)
- Xem Lịch sử bài nộp

**Đặc tả chi tiết các Use Case:**

Bảng 3.30. Đặc tả Use Case "Làm bài Lập trình (IDE)"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Làm bài trên IDE trực tuyến |
| Tác nhân | Student |
| Mô tả | Viết code, chạy thử và nộp bài. |
| Tiền điều kiện | Đang trong hạn nộp bài. |
| Hậu điều kiện | Mã nguồn gửi cho Sandbox chấm và lưu DB. |
| Luồng sự kiện chính | 1. Mở IDE trên web. 2. Viết Code. 3. Bấm "Run" để test nhanh nghiệm. 4. Bấm "Submit" để nộp. 5. Hệ thống khóa IDE, đợi kết quả. |
| Luồng rẽ nhánh | - Bấm Submit khi quá hạn → Báo hết giờ nộp bài. |

Bảng 3.31. Đặc tả Use Case "Làm bài Trắc nghiệm"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Làm bài Trắc nghiệm (Quiz) |
| Tác nhân | Student |
| Mô tả | Trả lời trắc nghiệm, có auto-save. |
| Tiền điều kiện | Thời gian mở Quiz bắt đầu. |
| Hậu điều kiện | Lưu câu trả lời, tự động chấm điểm ngay sau khi nộp. |
| Luồng sự kiện chính | 1. Tick chọn đáp án. 2. Hệ thống Auto-save mỗi 5s. 3. Bấm Nộp bài (hoặc hết giờ tự nộp). 4. Tính điểm. |
| Luồng rẽ nhánh | - Mất mạng → Auto-save lưu lại local, tự đồng bộ khi có mạng lại. |

Bảng 3.32. Đặc tả Use Case "Làm bài Nộp File"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Làm bài Nộp File |
| Tác nhân | Student |
| Mô tả | Nộp báo cáo PDF/Word/Zip. |
| Tiền điều kiện | Đang trong hạn nộp. |
| Hậu điều kiện | File được Upload thành công. |
| Luồng sự kiện chính | 1. Bấm Chọn file. 2. Chọn file đúng định dạng. 3. Bấm Nộp. 4. Hiển thị link file nộp. |
| Luồng rẽ nhánh | - File sai định dạng cấu hình bài tập → Báo lỗi không cho tải lên. |

Bảng 3.33. Đặc tả Use Case "Phòng chờ thi"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Phòng chờ thi (Exam Lobby) |
| Tác nhân | Student |
| Mô tả | Màn hình đếm ngược chờ đến giờ thi. |
| Tiền điều kiện | Đã vào link bài thi nhưng chưa đến giờ mở. |
| Hậu điều kiện | Hết giờ đếm ngược sẽ tự mở đề. |
| Luồng sự kiện chính | 1. Vào link. 2. Xem đồng hồ đếm ngược. 3. Hết giờ, trang tự Refresh và hiện nút "Bắt đầu làm bài". |
| Luồng rẽ nhánh | - N/A |

Bảng 3.34. Đặc tả Use Case "Giám sát phòng thi"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Giám sát phòng thi (Exam Monitor) |
| Tác nhân | Teacher |
| Mô tả | Theo dõi trạng thái thi realtime, ép nộp/cộng giờ. |
| Tiền điều kiện | Bài thi đang diễn ra. |
| Hậu điều kiện | Áp dụng thay đổi thời gian/trạng thái cho sinh viên. |
| Luồng sự kiện chính | 1. Mở trang Giám sát. 2. Xem các chấm màu (Đang làm/Đã nộp/Offline). 3. Click vào user, chọn "Force Submit" hoặc "Add Time". |
| Luồng rẽ nhánh | - Sinh viên đã nộp bài → Ẩn nút ép nộp. |

Bảng 3.35. Đặc tả Use Case "Chấm điểm tự động"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Chấm điểm tự động (Auto-grade) |
| Tác nhân | Hệ thống (Sandbox) |
| Mô tả | Biên dịch và chạy code để chấm điểm. |
| Tiền điều kiện | Message queue nhận lệnh chấm bài. |
| Hậu điều kiện | Cập nhật điểm, memory, runtime từng testcase vào DB. |
| Luồng sự kiện chính | 1. Daemon kéo bài từ Queue. 2. Đẩy vào Docker biên dịch. 3. Chạy các file Testcase. 4. Compare output. 5. Lưu kết quả Pass/Fail. |
| Luồng rẽ nhánh | - Code dính Infinite loop → Báo Time Limit Exceeded (TLE). - Compile lỗi → Báo Compile Error (CE). |

Bảng 3.36. Đặc tả Use Case "Chấm điểm thủ công"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Chấm điểm thủ công (Manual-grade) |
| Tác nhân | Teacher |
| Mô tả | Chấm bằng Rubric, comment trực tiếp vào code. |
| Tiền điều kiện | Có bài nộp. |
| Hậu điều kiện | Điểm được lưu, sinh viên thấy nhận xét. |
| Luồng sự kiện chính | 1. Mở bài sinh viên. 2. Click Rubric chấm điểm. 3. Bôi đen dòng code, gõ Comment. 4. Nhấn Hoàn tất chấm. |
| Luồng rẽ nhánh | - N/A |

Bảng 3.37. Đặc tả Use Case "Xem Lịch sử bài nộp"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Xem Lịch sử bài nộp |
| Tác nhân | Student, Teacher |
| Mô tả | Xem lại toàn bộ các lần đã Submit. |
| Tiền điều kiện | Có ít nhất 1 lần Submit. |
| Hậu điều kiện | Hiển thị bảng chi tiết các lần nộp. |
| Luồng sự kiện chính | 1. Nhấn tab Lịch sử. 2. Xem thời gian nộp, tổng điểm. 3. Click chi tiết để xem code đã nộp. |
| Luồng rẽ nhánh | - N/A |

---
#### 2.2.1.6. Biểu đồ Use Case Module Thảo luận & Q&A
Mô tả: Không gian tương tác giải đáp thắc mắc chuyên sâu cho từng chủ đề bài tập/môn học.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE THẢO LUẬN TẠI ĐÂY]
Hình 3.6. Biểu đồ Use Case Module Thảo luận & Q&A

Danh sách chức năng chi tiết:
- Quản lý Chủ đề
- Tương tác bình chọn (Voting)
- Quản lý nâng cao

**Đặc tả chi tiết các Use Case:**

Bảng 3.38. Đặc tả Use Case "Quản lý Chủ đề"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý Chủ đề |
| Tác nhân | Teacher, Student |
| Mô tả | Tạo bài đăng hỏi đáp, sửa, xóa. |
| Tiền điều kiện | Đã đăng nhập. |
| Hậu điều kiện | Bài viết hiển thị trên Forum. |
| Luồng sự kiện chính | 1. Chọn Tạo Thảo luận. 2. Gõ câu hỏi. 3. Bấm Đăng. |
| Luồng rẽ nhánh | - Xóa bài người khác (Student) → Không có quyền. |

Bảng 3.39. Đặc tả Use Case "Tương tác bình chọn"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Tương tác bình chọn (Voting) |
| Tác nhân | Teacher, Student |
| Mô tả | Vote Up/Down bài viết. |
| Tiền điều kiện | Có bài viết tồn tại. |
| Hậu điều kiện | Điểm Vote thay đổi trong DB. |
| Luồng sự kiện chính | 1. Click biểu tượng mũi tên lên/xuống. 2. Hệ thống cộng/trừ 1 điểm. |
| Luồng rẽ nhánh | - Click lần 2 vào nút đã vote → Hủy vote. |

Bảng 3.40. Đặc tả Use Case "Quản lý nâng cao"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý nâng cao |
| Tác nhân | Teacher, Tác giả bài đăng |
| Mô tả | Mark as answer, Ghim bài. |
| Tiền điều kiện | Bài viết có câu trả lời. |
| Hậu điều kiện | Bài được ghim lên Top, hoặc câu trả lời hiện màu xanh (Accepted). |
| Luồng sự kiện chính | 1. Tác giả câu hỏi nhấn dấu tick vào reply đúng. 2. Teacher nhấn "Pin" để ghim bài hỏi lên đầu forum. |
| Luồng rẽ nhánh | - N/A |

---
#### 2.2.1.7. Biểu đồ Use Case Module Thông báo
Mô tả: Hệ thống Alert đẩy thông tin các sự kiện quan trọng đến người dùng kịp thời.

(Hình ảnh minh họa)
[CHÈN HÌNH ẢNH SƠ ĐỒ USE CASE MODULE THÔNG BÁO TẠI ĐÂY]
Hình 3.7. Biểu đồ Use Case Module Thông báo

Danh sách chức năng chi tiết:
- Nhận thông báo
- Lọc thông báo
- Quản lý trạng thái

**Đặc tả chi tiết các Use Case:**

Bảng 3.41. Đặc tả Use Case "Nhận thông báo"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Nhận thông báo |
| Tác nhân | Teacher, Student |
| Mô tả | Tự động nhận Alert khi có sự kiện (Có điểm, có comment...). |
| Tiền điều kiện | Sự kiện phát sinh. |
| Hậu điều kiện | Icon Quả chuông hiển thị badge màu đỏ (số lượng). |
| Luồng sự kiện chính | 1. Sự kiện xảy ra (vd có người comment). 2. Hệ thống tạo record Notification. 3. Giao diện fetch và hiện chấm đỏ. |
| Luồng rẽ nhánh | - N/A |

Bảng 3.42. Đặc tả Use Case "Lọc thông báo"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Lọc thông báo |
| Tác nhân | Teacher, Student |
| Mô tả | Xem theo Tab Tất cả / Chưa đọc. |
| Tiền điều kiện | Đã mở Panel thông báo. |
| Hậu điều kiện | Danh sách hiển thị theo bộ lọc. |
| Luồng sự kiện chính | 1. Click icon chuông. 2. Chọn Tab "Chưa đọc". 3. Hệ thống render danh sách `is_read = false`. |
| Luồng rẽ nhánh | - Hết thông báo chưa đọc → Hiện "Bạn không có thông báo mới". |

Bảng 3.43. Đặc tả Use Case "Quản lý trạng thái"
| Mục | Nội dung |
| --- | --- |
| Tên Use Case | Quản lý trạng thái thông báo |
| Tác nhân | Teacher, Student |
| Mô tả | Đánh dấu đã đọc. |
| Tiền điều kiện | Có thông báo chưa đọc. |
| Hậu điều kiện | Trạng thái chuyển thành `is_read = true`, icon chuông giảm số lượng. |
| Luồng sự kiện chính | 1. Click vào thông báo cụ thể hoặc nhấn "Đánh dấu đã đọc tất cả". 2. Giao diện update trạng thái, tắt nền xám của thông báo. |
| Luồng rẽ nhánh | - N/A |
