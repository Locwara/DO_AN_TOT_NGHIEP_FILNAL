# Kịch bản CSV theo bộ lọc hiện tại

> Mục tiêu: nâng cấp các dropdown CSV đã có trong `csv.md` để khi trang đang áp dụng bộ lọc, người dùng có lựa chọn chính là xuất đúng dữ liệu đang nhìn thấy theo bộ lọc hiện tại. Các biến thể CSV khác vẫn giữ lại và cũng phải tôn trọng bộ lọc đang áp dụng.

> Nguyên tắc ngắn gọn: "UI lọc ra gì, CSV mặc định xuất ra đúng tập dữ liệu đó".

## 0. Phạm vi kế thừa từ `csv.md`

- [x] Đối chiếu lại toàn bộ các endpoint CSV đã hoàn thành trong `csv.md`.
  > Ghi chú: Đã rà các nhóm CSV hiện có: admin users/subjects/classrooms/logs/exam-events, assignment statistics/late report, classroom gradebook, exam monitor.

- [x] Giữ nguyên các loại CSV đã có: đầy đủ, danh bạ, audit, thành viên, bảng điểm, bài trễ, bài thiếu, cảnh báo thi...
  > Ghi chú: Không xóa endpoint hay type CSV cũ; chỉ đổi nhãn/dropdown để rõ là xuất theo lọc hiện tại.

- [x] Bổ sung nhãn "theo lọc hiện tại" cho lựa chọn CSV chính ở từng trang có bộ lọc.
  > Ghi chú: Đã cập nhật dropdown CSV cho user/teacher/student, môn học, lớp học, activity logs, exam events, thống kê bài tập, sổ điểm, phòng thi và báo cáo bài trễ.

- [x] Các lựa chọn CSV phụ cũng phải nhận cùng query filter hiện tại, chỉ khác thêm tham số `type` khi cần.
  > Ghi chú: Admin đã dùng `csv_query_string`; sổ điểm/phòng thi đã thêm query sạch bỏ `page/type`, phòng thi export áp dụng filter `status` cho cả scores/warnings.

- [x] Không làm mất hành vi export toàn bộ khi người dùng chưa áp dụng bộ lọc.
  > Ghi chú: Khi query rỗng, link CSV chính không gắn query; CSV phụ chỉ gắn `type` nếu cần. `python manage.py check` không lỗi.

## 1. Quy chuẩn chung cho dropdown CSV

- [x] Mỗi dropdown CSV có một mục đầu tiên là mục chính theo ngữ cảnh trang.
  > Ghi chú: Mục đầu tiên của các dropdown CSV hiện là export chính: người dùng, môn học, lớp học, log, sự kiện thi, bài nộp, sổ điểm, phiên thi.

- [x] Nếu có bộ lọc đang áp dụng, nhãn mục đầu tiên dùng mẫu: `Xuất ... theo lọc hiện tại`.
  > Ghi chú: Các template dùng `has_active_filters` hoặc `csv_query_string` để đổi nhãn sang "theo lọc hiện tại".

- [x] Nếu chưa có bộ lọc, nhãn mục đầu tiên dùng mẫu: `Xuất toàn bộ ...` hoặc giữ nhãn rõ nghĩa như `Danh sách ...`.
  > Ghi chú: Đã thêm nhãn không lọc như "Xuất toàn bộ người dùng/lớp học/môn học/log/sự kiện thi/sổ điểm/phiên thi".

- [x] Mục chính trong dropdown nên đặt icon `filter_alt` hoặc `table_rows` và đứng trên cùng.
  > Ghi chú: Mục chính dùng `filter_alt` và nằm đầu tiên trong các dropdown đã rà.

- [x] Hiển thị badge nhỏ trong dropdown hoặc summary: `Đang lọc` khi `csv_query_string`/`querystring` không rỗng.
  > Ghi chú: Đã thêm `.csv-filter-badge` và render badge trong summary khi có filter.

- [x] Không để dropdown có hai link cùng ý nghĩa, ví dụ `Đầy đủ` và `Xuất theo lọc hiện tại` trỏ y hệt nhưng nhãn gây hiểu nhầm.
  > Ghi chú: Đã bỏ nhãn chung chung kiểu `Đầy đủ`, `Danh sách lớp/môn`, thay bằng nhãn chính theo ngữ cảnh.

- [x] Dropdown phải dùng style hiện có của design system: `csv-dropdown`, `csv-menu`, `btn`, icon Material Symbols.
  > Ghi chú: Tiếp tục dùng class/design system hiện có, chỉ bổ sung badge nhỏ cùng bảng màu primary.

- [x] Trên mobile, dropdown không tràn màn hình và các nhãn dài tự xuống dòng đẹp.
  > Ghi chú: `.csv-menu` có `max-width` theo viewport, link cho phép xuống dòng và icon không co.

## 2. Quy chuẩn query string

- [x] Tạo/chuẩn hóa biến context dùng chung: `csv_query_string`.
  > Ghi chú: Đã thêm helper `csv_query_context()` trong `apps/administation/utils.py`; admin vẫn dùng `admin_filter_context()` có `csv_query_string`.

- [x] Với các trang frontend ngoài admin đang dùng `querystring`, chuẩn hóa thêm alias `csv_query_string` để template dễ dùng.
  > Ghi chú: Assignment statistics, classroom gradebook và exam monitor đã dùng/nhận `csv_query_string`; gradebook vẫn giữ alias `querystring` để không phá code cũ.

- [x] Khi tạo query CSV, luôn loại bỏ `page` để export toàn bộ kết quả theo lọc, không chỉ trang phân trang hiện tại.
  > Ghi chú: `csv_query_context()` và `admin_filter_context()` đều remove `page`; smoke test URL có `page` không còn `page=` trong link CSV.

- [x] Khi tạo query CSV, luôn loại bỏ `type` cũ để tránh URL bị `type=scores&type=warnings`.
  > Ghi chú: Helper remove `type`; smoke test các dropdown phụ không có link nào chứa nhiều hơn một `type=`.

- [x] Link CSV chính dùng dạng: `export_url?{{ csv_query_string }}` nếu có filter.
  > Ghi chú: Các link chính admin, assignment statistics, gradebook và exam monitor đều theo pattern này.

- [x] Link CSV phụ dùng dạng: `export_url?type=...&{{ csv_query_string }}` nếu có filter.
  > Ghi chú: Các link có `type` như contacts/audit/members/classrooms/compact/sessions/scores/warnings đều giữ filter hiện tại phía sau.

- [x] Nếu `csv_query_string` rỗng, link CSV phụ chỉ có `?type=...`, không dư dấu `&`.
  > Ghi chú: Template dùng `{% if csv_query_string %}&{{ csv_query_string }}{% endif %}`; không render dấu `&` khi query rỗng.

## 3. Backend: dữ liệu CSV phải khớp với UI

- [x] Tất cả view export phải tái sử dụng cùng helper lọc với trang danh sách tương ứng.
  > Ghi chú: Đã đối chiếu các export chính; admin dùng cùng `_apply_*_filters`, gradebook dùng `_build_gradebook_data`, exam monitor dùng `_filtered_exam_monitor_sessions`.

- [x] Admin user export dùng đúng bộ lọc của `user_management`, `teacher_management`, `student_management`.
  > Ghi chú: `user_export_view` dùng `_user_filter_values` + `_apply_user_filters`; trang giáo viên/học sinh đã tự thêm `role=teacher/student` vào CSV query.

- [x] Admin subject export dùng đúng bộ lọc của `subject_management`.
  > Ghi chú: `subject_export_view` dùng `_subject_filter_values` + `_apply_subject_filters`; type `classrooms` dùng `_subject_classroom_links_for_export`.

- [x] Admin classroom export dùng đúng bộ lọc của `classroom_management`.
  > Ghi chú: `classroom_export_view` dùng `_classroom_filter_values` + `_apply_classroom_filters`; type `members` lấy thành viên từ tập lớp đã lọc.

- [x] Activity logs export dùng đúng bộ lọc của `activity_logs`.
  > Ghi chú: `activity_logs_export_view` dùng `_filtered_activity_logs_from_request`.

- [x] Exam events export dùng đúng bộ lọc của `exam_events`.
  > Ghi chú: `exam_events_export_view` dùng `_exam_event_filter_values`; type `sessions` dùng `_apply_exam_session_filters`.

- [x] Classroom gradebook export dùng đúng bộ lọc của `gradebook`.
  > Ghi chú: `gradebook_export`, `members_export`, `gradebook_missing_export` đều dùng chung `_build_gradebook_data(classroom, request)`.

- [x] Exam monitor export dùng đúng bộ lọc trạng thái phiên thi hiện tại.
  > Ghi chú: Đã tách `_filtered_exam_monitor_sessions`; summary/scores/warnings đều bám `status` hiện tại.

- [x] Assignment statistics export chuẩn bị sẵn cơ chế nhận query filter dù hiện tại trang chưa có nhiều bộ lọc.
  > Ghi chú: Các export assignment đã nhận filter dự phòng `status`, `language`, `student_id`, `late`; status không hợp lệ bị bỏ qua để tránh lỗi enum PostgreSQL.

- [x] Nếu kết quả lọc không có dòng nào, CSV vẫn trả file có header thay vì báo lỗi.
  > Ghi chú: Smoke test các endpoint CSV với filter không khớp dữ liệu đều trả HTTP 200, BOM UTF-8 và ít nhất dòng header.

## 4. Admin - Quản lý người dùng

- [x] Dropdown CSV của trang `Quản lý người dùng` đổi mục chính thành `Xuất người dùng theo lọc hiện tại`.
  > Ghi chú: Trang tổng mặc định hiển thị `Xuất toàn bộ người dùng`; khi có filter sẽ chuyển sang nhãn theo lọc hiện tại.

- [x] Khi ở tab học sinh, mục chính đổi thành `Xuất học sinh theo lọc hiện tại`.
  > Ghi chú: Trang `/administration/students/` tự gắn `role=student` vào CSV query và render đúng nhãn.

- [x] Khi ở tab giáo viên, mục chính đổi thành `Xuất giáo viên theo lọc hiện tại`.
  > Ghi chú: Trang `/administration/teachers/` tự gắn `role=teacher` vào CSV query và render đúng nhãn.

- [x] Khi ở tab admin hoặc bị khóa, mục chính đổi theo đúng ngữ cảnh: `Xuất admin theo lọc hiện tại`, `Xuất tài khoản bị khóa theo lọc hiện tại`.
  > Ghi chú: Đã thêm scope label theo `role=admin` và `status=inactive`; trạng thái bị khóa được ưu tiên nếu có cả role/status.

- [x] Các mục phụ `Danh bạ` và `Audit tài khoản` cũng giữ nguyên filter hiện tại.
  > Ghi chú: Link phụ dùng cùng `csv_query_string`; forced role học sinh/giáo viên cũng được giữ.

- [x] CSV danh bạ theo lọc chỉ xuất các user nằm trong kết quả lọc hiện tại.
  > Ghi chú: `user_export_view` type `contacts` dùng cùng queryset `_apply_user_filters`; smoke test nhiều filter trả HTTP 200/BOM.

- [x] CSV audit theo lọc chỉ xuất các user nằm trong kết quả lọc hiện tại.
  > Ghi chú: `user_export_view` type `audit` dùng cùng queryset `_apply_user_filters`; đã kiểm với role teacher/admin và status inactive.

- [x] Kiểm tra với filter lớp học, môn học, đăng nhập, trạng thái profile, bài nộp.
  > Ghi chú: Đã smoke test contacts CSV với `classroom_id`, `subject_id`, `last_login`, `profile_status`, `has_submissions`, `submission_status`; status rác được bỏ qua để tránh lỗi enum.

## 5. Admin - Quản lý giáo viên và học sinh

- [x] Trang quản lý giáo viên kế thừa đầy đủ dropdown CSV của quản lý người dùng.
  > Ghi chú: `/administration/teachers/` render cùng dropdown gồm CSV chính, danh bạ và audit.

- [x] Trang quản lý giáo viên có mục chính `Xuất giáo viên theo lọc hiện tại`.
  > Ghi chú: Đã smoke test UI có nhãn này và các link CSV đều giữ `role=teacher`.

- [x] Trang quản lý học sinh kế thừa đầy đủ dropdown CSV của quản lý người dùng.
  > Ghi chú: `/administration/students/` render cùng dropdown gồm CSV chính, danh bạ và audit.

- [x] Trang quản lý học sinh có mục chính `Xuất học sinh theo lọc hiện tại`.
  > Ghi chú: Đã smoke test UI có nhãn này và các link CSV đều giữ `role=student`.

- [x] Các link CSV không làm mất forced role `teacher` hoặc `student`.
  > Ghi chú: Link CSV teacher/student lần lượt render `/users/export/?role=teacher` và `/users/export/?role=student`, cả contacts/audit cũng giữ role.

- [x] Kiểm tra export sau khi lọc theo lớp, môn, trạng thái tham gia, trạng thái bài nộp.
  > Ghi chú: Đã smoke test `classroom_id`, `subject_id`, `has_teaching_classes`, `has_joined_class`, `has_submissions`, `submission_status`; CSV trả đúng role teacher/student.

## 6. Admin - Quản lý môn học

- [x] Dropdown CSV của trang môn học đổi mục chính thành `Xuất môn học theo lọc hiện tại`.
  > Ghi chú: Template `subject_management.html` render đúng nhãn khi có filter, không filter thì là `Xuất toàn bộ môn học`.

- [x] Mục phụ `Gán lớp/môn/kỳ` đổi nhãn thành `Xuất gán lớp/môn/kỳ theo lọc hiện tại`.
  > Ghi chú: Đã đổi nhãn phụ thành `Xuất gán lớp/môn/kỳ...` ở template chính và template legacy.

- [x] Link CSV giữ các filter: trạng thái duyệt, lớp học, giáo viên, kỳ học, ngôn ngữ, hiển thị.
  > Ghi chú: Smoke test link CSV giữ `status`, `classroom_id`, `teacher_id`, `semester_id`, `language_id`, `is_active`; không giữ `page/type` cũ.

- [x] Link CSV giữ các filter nâng cao: có bài tập, có bài thi, sandbox, ngày tạo.
  > Ghi chú: `subject_export_view` dùng cùng `_subject_filter_values`; đã smoke test `has_assignments`, `has_exams`, `sandbox_status` trả CSV 200/BOM.

- [x] Kiểm tra trường hợp lọc môn thuộc lớp A thì CSV chỉ có môn thuộc lớp A.
  > Ghi chú: Đã kiểm `type=classrooms&classroom_id=25`; CSV mapping chỉ có lớp `Python co ban K18`.

- [x] Kiểm tra trường hợp lọc môn chưa có bài tập thì CSV phụ cũng chỉ xuất mapping của nhóm môn đó.
  > Ghi chú: `has_assignments=no` trả CSV mapping hợp lệ với header-only khi không có link phù hợp, không lỗi.

## 7. Admin - Quản lý lớp học

- [x] Dropdown CSV của trang lớp học đổi mục chính thành `Xuất lớp học theo lọc hiện tại`.
  > Ghi chú: Template `classroom_management.html` render đúng nhãn khi có filter, không filter thì là `Xuất toàn bộ lớp học`.

- [x] Mục phụ `Thành viên theo lớp` đổi nhãn thành `Xuất thành viên của các lớp đang lọc`.
  > Ghi chú: Đã đổi nhãn phụ thành `Xuất thành viên của các lớp đang lọc`; không filter thì là `Xuất thành viên theo lớp`.

- [x] Link CSV giữ các filter: trạng thái duyệt, hoạt động, môn học, giáo viên, kỳ học.
  > Ghi chú: Smoke test link CSV giữ `status`, `is_active`, `subject_id`, `teacher_id`, `semester_id`; không giữ `page/type` cũ.

- [x] Link CSV giữ các filter nâng cao: sĩ số, sức chứa, tình trạng môn, bài tập, bài thi, học sinh chờ duyệt, ngày tạo.
  > Ghi chú: `classroom_export_view` dùng cùng `_classroom_filter_values`; đã smoke test `member_count`, `capacity_status`, `has_subjects`, `has_assignments`, `has_exams`, `has_pending_members`.

- [x] Kiểm tra lọc lớp thuộc môn ABC thì CSV danh sách lớp và CSV thành viên chỉ lấy các lớp thuộc môn ABC.
  > Ghi chú: Đã kiểm `subject_id=17`; CSV danh sách lớp chỉ có lớp thuộc môn đó, CSV thành viên chỉ lấy thành viên từ tập lớp đã lọc.

- [x] Link CSV thành viên theo từng dòng lớp vẫn giữ là thao tác riêng `CSV thành viên lớp này`, không nhập nhằng với lọc toàn trang.
  > Ghi chú: Link theo từng dòng vẫn trỏ `/classrooms/<id>/members/export/`, tách biệt với dropdown toàn trang `/administration/classrooms/export/?type=members`.

## 8. Admin - Nhật ký hoạt động

- [x] Dropdown CSV của activity logs đổi mục chính thành `Xuất log theo lọc hiện tại`.
  > Ghi chú: Template `activity_logs.html` render đúng nhãn khi có filter, không filter thì là `Xuất toàn bộ log`.

- [x] Mục phụ `Bản gọn` đổi nhãn thành `Xuất bản gọn theo lọc hiện tại`.
  > Ghi chú: Đã đổi nhãn phụ; dropdown CSV vẫn hiển thị cả khi bộ lọc hiện tại không có log nào để có thể xuất header-only.

- [x] Link CSV giữ các filter: preset, user text, user_id, role, date_from, date_to.
  > Ghi chú: Smoke test link export giữ `preset`, `user`, `user_id`, `role`, `date_from`, `date_to`; không giữ `page`.

- [x] Link CSV giữ các filter nâng cao: action, action_group, resource_type, resource_id, ip_address.
  > Ghi chú: Link export giữ đủ filter nâng cao; parser URL xác nhận chỉ có `type=compact` ở link phụ và không có `page`.

- [x] Kiểm tra preset 7 ngày export đúng 7 ngày và không bị ảnh hưởng bởi phân trang.
  > Ghi chú: `/administration/logs/export/?preset=7d&page=99` trả CSV 200/BOM, các dòng nằm trong cutoff 7 ngày và bỏ qua phân trang.

## 9. Admin - Sự kiện thi

- [x] Dropdown CSV của exam events đổi mục chính thành `Xuất sự kiện thi theo lọc hiện tại`.
  > Ghi chú: Template `exam_events.html` render đúng nhãn khi có filter, không filter thì là `Xuất toàn bộ sự kiện thi`.

- [x] Mục phụ `Phiên thi` đổi nhãn thành `Xuất phiên thi theo lọc hiện tại`.
  > Ghi chú: Đã đổi nhãn phụ; không filter thì là `Xuất toàn bộ phiên thi`.

- [x] Link CSV giữ các filter: từ khóa, bài thi, loại sự kiện, trạng thái phiên, cảnh báo từ.
  > Ghi chú: Smoke test link export giữ `search`, `assignment_id`, `event_type`, `status`, `min_warnings`; không giữ `page/type` cũ.

- [x] Link CSV giữ các filter nâng cao: lớp học, môn học, giáo viên, học sinh, bài nộp cuối, thời lượng phiên, ngày.
  > Ghi chú: Link export giữ `classroom_id`, `subject_id`, `teacher_id`, `student_id`, `has_final_submission`, `session_duration`, `date_from`, `date_to`.

- [x] Kiểm tra lọc theo học sinh A thì cả CSV sự kiện và CSV phiên thi chỉ liên quan học sinh A.
  > Ghi chú: Smoke test với học sinh `locwara2`; CSV sự kiện và CSV phiên thi đều chỉ có học sinh này.

- [x] Kiểm tra lọc `min_warnings` thì CSV không xuất phiên/sự kiện ngoài ngưỡng cảnh báo.
  > Ghi chú: Smoke test `min_warnings=1`; mọi dòng CSV sự kiện/phiên đều có cảnh báo từ 1 trở lên. Đồng thời CSV phiên thi đã lọc đúng `event_type`.

## 10. Assignment - Trang thống kê bài tập

- [x] Dropdown CSV của trang thống kê đổi mục chính thành `Xuất bài nộp theo lọc hiện tại`.
  > Ghi chú: Template `statistics.html` render đúng nhãn khi URL có filter và hiển thị badge `Đang lọc`.

- [x] Nếu trang thống kê chưa có form lọc, mục chính có thể là `Xuất tất cả bài nộp`.
  > Ghi chú: Khi chưa có filter, mục chính giữ nhãn `Xuất tất cả bài nộp`.

- [x] Chuẩn bị query `csv_query_string` để sau này thêm filter trạng thái, ngôn ngữ, điểm, nộp trễ không cần sửa dropdown.
  > Ghi chú: `csv_query_context()` giữ `status`, `language`, `student_id`, `late`, `score_min`, `score_max` và loại `page/type` khỏi link export.

- [x] Mục `Bài nộp trễ` đổi nhãn thành `Xuất bài nộp trễ theo lọc hiện tại` khi có filter.
  > Ghi chú: Đã chuẩn hóa nhãn có/không filter thành `Xuất bài nộp trễ theo lọc hiện tại` và `Xuất bài nộp trễ`.

- [x] Mục `Bảng điểm sinh viên` đổi nhãn thành `Xuất bảng điểm theo lọc hiện tại`.
  > Ghi chú: Đã chuẩn hóa nhãn có/không filter thành `Xuất bảng điểm theo lọc hiện tại` và `Xuất bảng điểm sinh viên`.

- [x] Mục `Sinh viên chưa nộp` đổi nhãn thành `Xuất sinh viên chưa nộp theo lọc hiện tại`.
  > Ghi chú: Đã chuẩn hóa nhãn có/không filter thành `Xuất sinh viên chưa nộp theo lọc hiện tại` và `Xuất sinh viên chưa nộp`.

- [x] Nếu thêm filter ở trang thống kê, các view `export_late`, `export_scores`, `export_submissions`, `export_missing` đều phải nhận filter đó.
  > Ghi chú: 4 export đều dùng `_assignment_submissions(..., request)`/`_assignment_approved_members(..., request)`; đã bổ sung lọc điểm `score_min/score_max` và smoke test 4 endpoint trả CSV 200.

## 11. Assignment - Báo cáo bài nộp trễ/In PDF

- [x] Link CSV trong trang báo cáo bài trễ dùng nhãn `Xuất CSV báo cáo hiện tại`.
  > Ghi chú: Template `late_report_print.html` đã đổi nhãn nút và gắn `csv_query_string` để giữ bộ lọc hiện tại.

- [x] CSV bài trễ phải khớp đúng assignment và các filter báo cáo nếu sau này có thêm.
  > Ghi chú: Trang in/PDF và CSV đều dùng `_assignment_submissions(..., request)`, hỗ trợ `status`, `language`, `student_id`, `late`, `score_min/score_max`.

- [x] Nếu báo cáo đang hiển thị `Không có bài nộp trễ`, CSV trả header-only hợp lệ.
  > Ghi chú: Smoke test filter không khớp dữ liệu trả CSV 200 với header và 0 dòng dữ liệu.

- [x] Tên file CSV nên đồng bộ với báo cáo PDF để giáo viên dễ đối chiếu.
  > Ghi chú: CSV dùng prefix `bao_cao_nop_bai_<assignment_id>_<slug>`; title trang in/PDF dùng cùng prefix.

## 12. Classroom - Sổ điểm lớp học

- [x] Dropdown CSV của sổ điểm đổi mục chính thành `Xuất sổ điểm theo lọc hiện tại`.
  > Ghi chú: Template `gradebook.html` render đúng nhãn khi có filter, không filter thì là `Xuất toàn bộ sổ điểm`.

- [x] Mục `Danh sách học sinh` đổi nhãn thành `Xuất học sinh theo lọc hiện tại`.
  > Ghi chú: Đã chuẩn hóa nhãn có/không filter thành `Xuất học sinh theo lọc hiện tại` và `Xuất danh sách học sinh`.

- [x] Mục `Bài còn thiếu` đổi nhãn thành `Xuất bài còn thiếu theo lọc hiện tại`.
  > Ghi chú: Đã chuẩn hóa nhãn có/không filter thành `Xuất bài còn thiếu theo lọc hiện tại` và `Xuất bài còn thiếu`.

- [x] Link CSV giữ các filter: công bố, môn học, học kỳ, trạng thái học sinh.
  > Ghi chú: Smoke test link export giữ `published`, `cs`, `semester`, `status`; không giữ `page/type` cũ.

- [x] CSV sổ điểm theo lọc chỉ có các assignment đang hiển thị theo môn/kỳ/công bố.
  > Ghi chú: Smoke test với lớp `Python co ban K18`, `cs=17`, `semester=11`; số cột assignment CSV khớp đúng tập assignment đang hiển thị.

- [x] CSV danh sách học sinh theo lọc chỉ có học sinh còn nằm trong tập lọc trạng thái hiện tại.
  > Ghi chú: Smoke test `status=missing`; CSV học sinh có đúng tập username từ `_build_gradebook_data()`.

- [x] CSV bài còn thiếu theo lọc chỉ tính các bài trong tập assignment đang hiển thị.
  > Ghi chú: Smoke test số dòng bài thiếu khớp dữ liệu UI; tên bài thiếu là subset của các assignment đang lọc.

## 13. Submission - Theo dõi phòng thi

- [x] Dropdown CSV của exam monitor đổi mục chính thành `Xuất phiên thi theo lọc hiện tại`.
  > Ghi chú: Template `exam_monitor.html` render đúng nhãn khi có filter, không filter thì là `Xuất toàn bộ phiên thi`.

- [x] Mục `Điểm bài thi` đổi nhãn thành `Xuất điểm bài thi theo lọc hiện tại`.
  > Ghi chú: Đã chuẩn hóa nhãn có/không filter thành `Xuất điểm bài thi theo lọc hiện tại` và `Xuất điểm bài thi`.

- [x] Mục `Cảnh báo thi` đổi nhãn thành `Xuất cảnh báo theo lọc hiện tại`.
  > Ghi chú: Đã chuẩn hóa nhãn có/không filter thành `Xuất cảnh báo theo lọc hiện tại` và `Xuất cảnh báo thi`; CSV warnings chỉ xuất event thuộc nhóm cảnh báo.

- [x] Link CSV giữ filter `status` hiện tại: tất cả, đang làm, đã nộp, hết giờ.
  > Ghi chú: Smoke test các export `summary`, `scores`, `warnings` với `all/running/submitted/expired` đều trả CSV 200 và bám filter.

- [x] Nếu sau này thêm filter học sinh/cảnh báo/thời gian, dropdown phải tự giữ các filter đó.
  > Ghi chú: `csv_query_context()` giữ các query tương lai như `student_id`, `min_warnings`, `date_from`, `date_to` và bỏ `page/type` cũ.

- [x] Kiểm tra CSV warnings khi filter `status=running` chỉ lấy cảnh báo của các phiên đang làm.
  > Ghi chú: Smoke test `status=running` trả header-only khi không có phiên đang làm; tập trạng thái trong CSV là rỗng/không lẫn phiên khác. `status=submitted` chỉ ra phiên đã nộp và event thuộc `EXAM_WARNING_EVENTS`.

## 14. Component/partial dùng chung

- [x] Xem xét tạo partial `templates/includes/csv_dropdown.html` để giảm lặp HTML.
  > Ghi chú: Đã tạo partial dùng chung `templates/includes/csv_dropdown.html` và chuyển các dropdown CSV chính sang include này.

- [x] Partial nhận danh sách item gồm: `url`, `type`, `icon`, `label`, `primary`.
  > Ghi chú: Các view truyền `csv_items` dạng dict có đủ `url`, `type`, `icon`, `label`, `primary`; partial render theo danh sách này.

- [x] Partial tự nối query filter hiện tại và tránh trùng `type`.
  > Ghi chú: Đã thêm template tag `csv_export_href` để nối `csv_query_string`, loại `type` cũ và chỉ thêm đúng một `type` theo item.

- [x] Partial hỗ trợ trạng thái `has_active_filters` để đổi nhãn hoặc hiện badge.
  > Ghi chú: Partial nhận `csv_dropdown_has_filters` để hiện badge `Đang lọc`; nhãn filtered/all được chuẩn bị trong `csv_items`.

- [x] Nếu chưa tạo partial ngay, ít nhất phải thống nhất pattern link ở mọi template.
  > Ghi chú: Đã thống nhất pattern dropdown qua partial; `rg` chỉ còn `csv-dropdown/csv-menu` trong partial, không còn link `?type=...&{{ csv_query_string }}` viết tay.

## 15. Tên file CSV

- [x] File CSV chính khi có lọc nên có hậu tố `filtered` hoặc `theo-loc`.
  > Ghi chú: Đã thêm helper `csv_filename()`; các export chính có filter sẽ sinh tên dạng `..._filtered_YYYYMMDD_HHMM.csv`.

- [x] File CSV phụ vẫn giữ tên rõ loại: `contacts`, `audit`, `members`, `scores`, `warnings`.
  > Ghi chú: Smoke test xác nhận các file phụ giữ type trong tên như `users_contacts_filtered...`, `classrooms_members_filtered...`, `assignment_45_scores_filtered...`, `exam_47_warnings_filtered...`.

- [x] Thêm timestamp cho các CSV dễ nhầm lẫn như logs, exam events, monitor.
  > Ghi chú: Admin logs, exam events, assignment, gradebook và exam monitor đều có timestamp `YYYYMMDD_HHMM`; exam monitor đã đổi từ tên tĩnh sang `exam_<id>_<type>_<timestamp>.csv`.

- [x] Không đưa nguyên query dài vào tên file.
  > Ghi chú: Tên file chỉ dùng base/type/filtered/timestamp; smoke test không thấy các chuỗi `role=`, `status=`, `preset=`, `type=` trong filename.

## 16. Kiểm thử thủ công

- [x] Admin users: lọc `role=student`, export chính chỉ ra học sinh.
  > Ghi chú: Smoke test CSV `/administration/users/export/?role=student`; role trong file chỉ gồm `student`, số dòng khớp queryset lọc.

- [x] Admin teachers: lọc `approval_status=pending`, export chính chỉ ra giáo viên đang chờ duyệt.
  > Ghi chú: Đã sửa export user để nhận `approval_status`; smoke test CSV `role=teacher&approval_status=pending` khớp danh sách `TeacherRegistrations(status=pending)`.

- [x] Admin subjects: lọc theo lớp, export môn và mapping đều khớp.
  > Ghi chú: Smoke test export môn và `type=classrooms` với `classroom_id`; số dòng và tên lớp mapping khớp bộ lọc.

- [x] Admin classrooms: lọc theo môn, export lớp và thành viên đều khớp.
  > Ghi chú: Smoke test export lớp và `type=members` với `subject_id`; thành viên chỉ thuộc các lớp sau lọc.

- [x] Activity logs: lọc preset 24h và role admin, CSV khớp tổng số lọc.
  > Ghi chú: Smoke test CSV `/administration/logs/export/?preset=24h&role=admin`; số dòng khớp `_filtered_activity_logs_from_request`.

- [x] Exam events: lọc bài thi + học sinh, CSV sự kiện và phiên thi khớp.
  > Ghi chú: Smoke test export sự kiện và `type=sessions` với `assignment_id` + `student_id`; số dòng khớp queryset lọc.

- [x] Gradebook: lọc theo môn/kỳ, CSV chỉ có cột bài tập của môn/kỳ đó.
  > Ghi chú: Smoke test export gradebook với `cs` và `semester_id`; cột bài tập khớp `_build_gradebook_data` theo môn/kỳ, header CSV có kèm điểm tối đa.

- [x] Exam monitor: lọc `status=running`, CSV phiên/điểm/cảnh báo không lẫn phiên đã nộp.
  > Ghi chú: Smoke test summary/scores/warnings với `status=running`; status chỉ là `Đang làm`, cảnh báo chỉ thuộc session đang lọc.

## 17. Kiểm thử kỹ thuật

- [x] `python manage.py check` không lỗi.
  > Ghi chú: Đã chạy `python manage.py check`; Django báo `System check identified no issues`.

- [x] Smoke test tất cả endpoint CSV trả HTTP 200.
  > Ghi chú: Đã smoke test admin users/subjects/classrooms/logs/exam-events, assignment exports, gradebook/member exports và exam monitor exports; tất cả endpoint hợp lệ trả `200` + `text/csv`.

- [x] Kiểm tra response CSV có BOM UTF-8.
  > Ghi chú: Smoke test xác nhận các response CSV bắt đầu bằng BOM UTF-8 `EF BB BF`.

- [x] Kiểm tra URL CSV không chứa `page=`.
  > Ghi chú: Đã render các trang có dropdown CSV với query `page=2`; mọi link export đã bỏ `page`.

- [x] Kiểm tra URL CSV không chứa nhiều hơn một tham số `type`.
  > Ghi chú: Đã render các trang với query đang có `type`; link export chỉ giữ tối đa một tham số `type`.

- [x] Kiểm tra CSV export không vượt quyền: học sinh không gọi được endpoint giáo viên/admin.
  > Ghi chú: Smoke test học sinh gọi admin export, assignment export, gradebook export và exam monitor export đều không nhận được CSV `200`.

- [x] Kiểm tra giáo viên chỉ export lớp/bài thuộc quyền của mình.
  > Ghi chú: Smoke test giáo viên export bài của mình được; tạo dữ liệu tạm cho giáo viên khác rồi xác nhận export bài ngoài quyền bị chặn, sau đó xóa dữ liệu tạm.

- [x] Kiểm tra admin export được toàn hệ thống theo filter.
  > Ghi chú: Smoke test admin export `/administration/users/export/?role=all&type=audit` trả CSV hợp lệ có BOM.

## 18. Thứ tự triển khai đề xuất

- [x] Bước 1: Chuẩn hóa context `csv_query_string`/`has_active_filters` cho các trang có CSV.
  > Ghi chú: Đã có `csv_query_context()`/`admin_filter_context()` và các trang admin, assignment statistics, gradebook, exam monitor đều truyền `csv_query_string` + trạng thái đang lọc cho dropdown.

- [x] Bước 2: Sửa dropdown CSV nhóm admin trước vì đang có nhiều filter nhất.
  > Ghi chú: Đã sửa dropdown CSV cho user/teacher/student, subject, classroom, activity logs và exam events; link giữ filter hiện tại, bỏ `page/type` cũ.

- [x] Bước 3: Sửa dropdown CSV nhóm lớp học/bài tập/phòng thi.
  > Ghi chú: Đã sửa assignment statistics, late report, classroom gradebook/members/missing và exam monitor; các nhãn chính/phụ đều đổi theo trạng thái có filter.

- [x] Bước 4: Kiểm tra backend export có dùng cùng queryset lọc với UI chưa.
  > Ghi chú: Đã đối chiếu và smoke test: admin export dùng `_apply_*_filters`, gradebook dùng `_build_gradebook_data`, assignment export dùng `_assignment_submissions/_assignment_approved_members`, exam monitor dùng `_filtered_exam_monitor_sessions`.

- [x] Bước 5: Thêm test/smoke test cho từng endpoint CSV.
  > Ghi chú: Đã chạy smoke test admin users/subjects/classrooms/logs/exam-events, assignment exports, gradebook/member exports và exam monitor exports; kiểm cả HTTP 200, `text/csv`, BOM UTF-8, quyền student/teacher/admin.

- [x] Bước 6: Review giao diện dropdown theo `devlearn-design-system.md`.
  > Ghi chú: Đã gom dropdown qua `templates/includes/csv_dropdown.html`, dùng class `csv-dropdown/csv-menu`, nút `btn`, Material Symbols, badge `Đang lọc` và CSS responsive trong `static/css/base.css`.

- [x] Bước 7: Tick lại file này sau khi mỗi trang đã được làm và test.
  > Ghi chú: Các section 0-18 đã được tick; mỗi hạng mục có ghi chú kết quả triển khai/test tương ứng.
