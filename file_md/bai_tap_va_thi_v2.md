# Kịch bản Bài tập & Bài thi V2: Nộp file và Trắc nghiệm

> Mục tiêu: mở rộng hệ thống bài tập/bài thi hiện tại từ dạng lập trình chấm tự động sang hai nhóm lớn mới:
>
> 1. Bài tập/bài thi nộp file: Word, PDF, file code, file nén, tài liệu thực hành...
> 2. Bài tập/bài thi trắc nghiệm: làm nhiều lần cho bài tập, một lần cho bài thi, hỗ trợ import câu hỏi từ CSV.
>
> Nguyên tắc lõi: `is_exam` chỉ nói đây là bài thi hay bài tập; `submission_mode` mới nói học sinh nộp/làm theo kiểu nào: `code`, `file`, `quiz`. Như vậy không phá logic bài lập trình hiện tại.

## 0. Hiện trạng hệ thống cần kế thừa

- [x] Giữ nguyên luồng bài lập trình hiện tại: tạo bài, testcase, IDE, run code, submit code, chấm tự động, lịch sử nộp.
  > Ghi chú: Đã rà `apps.assignments` và `apps.submissions`; luồng code hiện nằm ở `AssignmentForm`, `Testcases`, `solve_problem_view`, `run_test_view`, `submit_code_view`, `submission_history_view`. Các phase sau phải mở rộng bằng `submission_mode` thay vì sửa lệch luồng code cũ.

- [x] Kế thừa model `Assignments` đang có: lớp, môn trong lớp, kỳ học, `is_exam`, lịch mở/đóng, điểm tối đa, số lần nộp, deadline.
  > Ghi chú: `Assignments` đã có `classroom`, `classroom_subject`, `start_date`, `due_date`, `max_score`, `max_attempts`, `is_exam`, `exam_*`. V2 sẽ thêm field mới nhưng không thay nghĩa các field này.

- [x] Kế thừa model `Submissions` làm bản ghi điểm trung tâm cho gradebook, statistics, leaderboard, export CSV.
  > Ghi chú: `Submissions` đang là nguồn điểm cho detail, history, gradebook, statistics, CSV export, dashboard học sinh/giáo viên. File/quiz V2 vẫn phải tạo `Submissions` để không phải viết lại gradebook.

- [x] Kế thừa luồng chấm tay hiện tại: `manual_score`, `teacher_comment`, `graded_by`, `graded_at`, rubric, feedback templates.
  > Ghi chú: Đã có `GradeSubmissionForm`, `grade_submission_view`, `Rubrics`, `RubricScores`, `FeedbackTemplates`; file submission và quiz cần chấm tay sẽ tái dùng màn hình/logic này theo layout phù hợp từng mode.

- [x] Kế thừa `ExamSessions` cho bài thi có thời gian, trạng thái phiên thi, log sự kiện, cảnh báo, gia hạn, force submit.
  > Ghi chú: `ExamSessions`/`ExamEvents` hiện phục vụ lobby, start, monitor, extend, force submit, export phòng thi. File exam và quiz exam sẽ dispatch theo `submission_mode` nhưng vẫn dùng cùng session/event layer.

- [x] Không tích hợp AI ngay trong phase này; chỉ chừa hook dữ liệu để sau này AI hỗ trợ chấm/nhận xét.
  > Ghi chú: Không thêm service/API AI trong phần 0. Kịch bản V2 chỉ ghi rõ hook tương lai ở section 19 để sau này có thể lưu gợi ý AI mà giáo viên vẫn là người quyết định điểm.

## 1. Chuẩn hóa mô hình loại bài

- [x] Thêm trường `submission_mode` vào `Assignments`.
  > Ghi chú: Đã thêm choices `code`, `file`, `quiz`; migration `assignments.0009` đã applied. Dữ liệu cũ mặc định `code`.

- [x] Thêm trường `grading_mode` vào `Assignments`.
  > Ghi chú: Đã thêm choices `auto`, `manual`, `mixed`; data migration map `auto_grade -> auto`, `manual_grade/project -> manual`.

- [x] Giữ `is_exam` độc lập với `submission_mode`.
  > Ghi chú: Form/model cho phép `is_exam=True` đi cùng `code/file/quiz`; backend chỉ ép mặc định an toàn cho exam nhưng không trộn nghĩa hai field.

- [x] Không dùng `type` hiện tại để gánh thêm quá nhiều ý nghĩa mới.
  > Ghi chú: UI mới dùng `submission_mode` + `grading_mode`; `type` được giữ hidden để backward compatible với các view cũ, và form tự sync `type` từ 2 field mới.

- [x] Cập nhật `AssignmentForm` để có segmented control: `Lập trình`, `Nộp file`, `Trắc nghiệm`.
  > Ghi chú: Template `_assignment_form.html` đã có segmented control dùng Material Symbols, border/ring/button style theo DevLearn design system.

- [x] Khi đổi loại bài, form chỉ hiện nhóm trường liên quan.
  > Ghi chú: JS trong form ẩn nhóm ngôn ngữ/testcase/run options khi chọn `file`/`quiz`; hiện panel placeholder cho cấu hình file/quiz ở các phase sau.

- [x] Với bài thi, tự ép các mặc định an toàn.
  > Ghi chú: `AssignmentForm.clean()` ép `max_attempts=1` cho `file/quiz` exam, tắt các option code-only như custom input/sample run/run count; form test đã phủ behavior này.

## 2. Bài tập/Bài thi dạng nộp file - Data model

- [x] Thêm model `AssignmentFileRequirements`.
  > Ghi chú: Đã thêm OneToOne với `Assignments`; lưu `allowed_extensions`, `allowed_mime_types`, `max_file_size_mb`, `max_files`, `require_comment`, `allow_resubmit`, `require_all_files_before_submit`, `scan_required`. Admin có inline cấu hình trực tiếp trong assignment.

- [x] Thêm model `SubmissionFiles`.
  > Ghi chú: Đã thêm FK tới `Submissions`; lưu `uploaded_by`, `file_name`, `file_url`, `file_size`, `mime_type`, `extension`, `checksum`, `uploaded_at`, `storage_provider`, `scan_status`, `metadata`.

- [x] Cân nhắc thêm `submission_text` vào `Submissions`.
  > Ghi chú: Đã thêm `submission_text` để học sinh ghi chú khi nộp file, link GitHub, mô tả bài làm; không dùng chung với `code_content`.

- [x] Cập nhật `Submissions.code_content` và `language` để không bắt buộc với mode `file`/`quiz`.
  > Ghi chú: Đã cho `blank=True`, default chuỗi rỗng `''` để mode `file`/`quiz` tạo submission không cần code/language nhưng vẫn giữ an toàn với dữ liệu cũ.

- [x] Thêm trường `source_mode` hoặc `submission_mode_snapshot` vào `Submissions`.
  > Ghi chú: Đã thêm `submission_mode_snapshot` với choices theo `Assignments.SUBMISSION_MODE_CHOICES` để submission cũ vẫn đọc đúng nếu giáo viên chỉnh mode bài sau này.

- [x] Thêm model `SubmissionFileFeedbacks` nếu cần trả file nhận xét.
  > Ghi chú: Đã thêm model lưu file phản hồi của giáo viên gồm `uploaded_by`, `file_name`, `file_url`, `file_size`, `mime_type`, `note`, `uploaded_at`; admin có inline trong submission.

- [x] Thêm chỉ mục DB cho file submission.
  > Ghi chú: Đã thêm index cho `submission/uploaded_at`, `checksum`, `scan_status/uploaded_at`, `extension/uploaded_at`, `submission_mode_snapshot/status/submitted_at`, và file feedback theo `submission/uploaded_at`.

## 3. Bài tập/Bài thi dạng nộp file - Luồng giáo viên

- [x] Form tạo bài có mode `Nộp file`.
  > Ghi chú: `_assignment_form.html` đã có segmented control `Lập trình/Nộp file/Trắc nghiệm`; mode file tự chuyển grading sang thủ công và lưu legacy `type=project`.

- [x] Giáo viên chọn loại file cho phép bằng checkbox.
  > Ghi chú: Đã thêm checkbox cho PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, ZIP/RAR, PY, CPP, JAVA, JS, HTML/CSS, TXT, MD và lưu vào `AssignmentFileRequirements.allowed_extensions`.

- [x] Giáo viên nhập dung lượng tối đa mỗi file.
  > Ghi chú: Form có `file_max_size_mb`, validate 1-100MB, default 20MB; giai đoạn upload học sinh sẽ reuse cấu hình này ở phần 4.

- [x] Giáo viên nhập số lượng file tối đa.
  > Ghi chú: Form có `file_max_files`, validate 1-20 file và hiển thị lại ở trang chi tiết bài.

- [x] Giáo viên bật/tắt yêu cầu ghi chú khi nộp.
  > Ghi chú: Lưu bằng `AssignmentFileRequirements.require_comment`; detail hiển thị trạng thái để học sinh/giáo viên biết.

- [x] Giáo viên bật/tắt cho phép nộp lại.
  > Ghi chú: Lưu bằng `allow_resubmit`; nếu tắt thì form ép `max_attempts=1`, bài thi file cũng tự ép 1 lần và tắt resubmit.

- [x] Giáo viên có thể đính kèm đề bài/file mẫu như hiện tại qua `AssignmentFiles`.
  > Ghi chú: Giữ nguyên khu `Tài liệu đính kèm` ở assignment detail; clone assignment cũng copy file mẫu như trước.

- [x] Trang chi tiết bài có tab `Yêu cầu nộp file`.
  > Ghi chú: Đã thêm section `Yêu cầu nộp file` cho mode file, hiển thị định dạng, số file, dung lượng, ghi chú, nộp lại, scan file; sidebar cũng có tóm tắt file tối đa.

- [x] Trang danh sách bài nộp của giáo viên hỗ trợ preview nhanh file.
  > Ghi chú: `templates/submissions/list_teacher.html` hiển thị file từng submission; PDF mở iframe modal, ảnh mở preview, định dạng khác có nút mở tab mới.

- [x] Giáo viên có nút tải tất cả bài nộp dạng ZIP.
  > Ghi chú: Thêm route `submissions:download_files_zip`; ZIP theo lớp/bài, mỗi học sinh một thư mục, nếu tải file remote lỗi sẽ kèm file `.url.txt` và `_download_errors.txt`.

- [x] Giáo viên có filter bài nộp file: đã nộp/chưa nộp, chấm/chưa chấm, trễ, loại file, điểm.
  > Ghi chú: Danh sách bài nộp có filter `submitted`, `status`, `grade`, `late`, `file_ext`, `score_min`, `score_max`; mode `chưa nộp` hiển thị danh sách học sinh chưa có submission.

- [x] Giáo viên chấm thủ công từng bài.
  > Ghi chú: `grade_submission_view` nhận diện file submission, thay code viewer bằng danh sách file, ghi chú học sinh và panel chấm thủ công.

- [x] Giáo viên chấm nhanh nhiều bài trong bảng.
  > Ghi chú: Trang `teacher_list` có checkbox chọn nhiều, nhập điểm/nhận xét inline và lưu hàng loạt bằng action `quick_grade`.

- [x] Giáo viên dùng rubric cho bài nộp file.
  > Ghi chú: Rubric hiện có được reuse trong màn hình chấm file; có thể dùng tổng điểm rubric làm điểm cuối cùng.

- [x] Giáo viên dùng feedback template cho nhận xét file.
  > Ghi chú: Feedback template hiện có vẫn hiển thị ở grade view và chèn vào nhận xét tổng quan cho file submission.

- [x] Giáo viên có thể trả file nhận xét.
  > Ghi chú: `SubmissionFileFeedbacks` đã được nối vào grade view; giáo viên upload file phản hồi riêng hoặc kèm lúc lưu điểm, học sinh xem lại ở submission detail.

## 4. Bài tập/Bài thi dạng nộp file - Luồng học sinh

- [x] Học sinh thấy bài nộp file trong lớp/môn giống bài lập trình nhưng icon/label khác.
  > Ghi chú: Đã cập nhật `assignments/list.html`, `classrooms/subject_detail.html`, `classrooms/detail.html`, `assignments/detail.html` để mode file dùng icon `upload_file`, label `Nộp file`, CTA `Nộp file`.

- [x] Trang làm bài file không hiển thị IDE.
  > Ghi chú: `solve_problem_view` render `submissions/submit_file.html` cho `submission_mode=file`; UI có vùng drag-drop, danh sách file đã chọn, ghi chú, nút nộp, tài liệu đề bài và lịch sử nộp.

- [x] Validate file phía client trước khi upload.
  > Ghi chú: JS kiểm tra extension, số file, dung lượng, yêu cầu đủ file và yêu cầu ghi chú; backend validate lại bằng `_validate_submission_files()`.

- [x] Hỗ trợ autosave file nháp nếu hợp lý.
  > Ghi chú: Không tự upload file nháp để tránh lưu file rác/chưa final; đã autosave ghi chú nộp bài vào localStorage theo assignment, file chỉ upload khi bấm `Nộp bài`.

- [x] Học sinh xem lịch sử các lần nộp file.
  > Ghi chú: Trang nộp file hiển thị lịch sử ngay bên dưới; `history.html` cũng hiển thị số file thay cho testcase/ngôn ngữ với file submission.

- [x] Học sinh biết rõ còn được nộp mấy lần.
  > Ghi chú: `_submission_attempt_context()` tính số lần đã nộp và số lượt còn lại; header trang nộp file hiển thị `Còn N lần nộp`.

- [x] Học sinh không được thay file sau khi bài thi file đã final submit.
  > Ghi chú: Route `submit_file_view` chặn `assignment.is_exam` khỏi luồng submit thường; file exam sẽ đi qua phòng thi ở phần 5, tránh đường vòng thay file sau final submit.

- [x] Học sinh xem điểm, nhận xét, rubric, file feedback sau khi giáo viên chấm.
  > Ghi chú: `submission_detail.html` đã hiển thị file đã nộp, điểm, nhận xét, rubric breakdown và file phản hồi từ `SubmissionFileFeedbacks`.

- [x] Nếu quá hạn, hệ thống áp dụng logic trễ/phạt giống bài lập trình.
  > Ghi chú: `submit_file_view` dùng `assignment_open_error`, `due_date`, `late_submission_allowed`, `late_penalty_percent` giống code submission và lưu `is_late`, `penalty_applied`.

## 5. Bài thi dạng nộp file - Luồng phòng thi

- [x] File exam dùng `ExamSessions` để start, running, submitted, expired.
  > Ghi chú: `start_exam_view` tạo session `running`; `submit_file_view` cập nhật `final_submission`, `submitted_at`, `status=submitted`; `_expire_session_if_needed()` đánh dấu `expired` khi quá giờ + grace.

- [x] Khi vào phòng thi file, học sinh qua lobby giống exam lập trình.
  > Ghi chú: `exam_lobby.html` hiển thị mode `Nộp file`, thời lượng, mở/đóng phòng, quy chế, định dạng/dung lượng/số file từ `AssignmentFileRequirements`.

- [x] Trang làm bài file exam có timer và ping giữ phiên.
  > Ghi chú: `exam_ide_view` render `submit_file.html` cho file exam; template có timer server-side, gọi `exam_ping`, và ghi event rời tab/focus/fullscreen.

- [x] File exam chỉ cho một lần nộp chính thức.
  > Ghi chú: `submit_file_view` chặn nếu session đã có `final_submission` hoặc học sinh đã có submission trước đó; bài thi file không dùng `allow_resubmit`.

- [x] Khi hết giờ, nếu có file nháp đã upload thì cấu hình admin/giáo viên quyết định auto submit hay đánh dấu hết giờ.
  > Ghi chú: Phase này không upload file nháp lên server trước final submit, nên khi hết giờ session được đánh dấu `expired`; event expired ghi `exam.file.auto_submit_uploaded_draft` và `server_file_draft=false` để sau này bật auto submit file draft nếu bổ sung upload nháp server-side.

- [x] Ghi `ExamEvents` cho upload file, remove file, submit, autosubmit, tab hidden/fullscreen nếu bật.
  > Ghi chú: Ghi `file_selected`, `file_selection_cleared`, `upload_file`, `submit_clicked`, `submitted`, `tab_hidden`, `focus_lost`, `fullscreen_exit`, `expired`, `teacher_force_submit_empty`.

- [x] Giáo viên monitor file exam trong trang phòng thi.
  > Ghi chú: `exam_monitor_view` prefetch `final_submission.files`; template hiển thị cột `File` thay `Run` cho file exam, trạng thái running/submitted/expired và link bài nộp.

- [x] Giáo viên có thể gia hạn/force submit file exam giống exam lập trình.
  > Ghi chú: Gia hạn dùng lại `extend_exam_session_view`; force submit với file exam không có draft server-side nên đánh dấu hết giờ và log `teacher_force_submit_empty` thay vì tạo submission rỗng.

- [x] Admin xem sự kiện file exam trong `exam_events`.
  > Ghi chú: Tất cả event file exam ghi vào `ExamEvents`, dùng lại trang/admin exam events hiện có để audit.

## 6. Bảo mật upload file

- [x] Backend validate extension và MIME type.
  > Ghi chú: Đã gom rule vào `validate_uploaded_files()`; bài nộp file kiểm tra `allowed_extensions` + `allowed_mime_types`, file đề/feedback cũng dùng cùng validator.

- [x] Backend validate dung lượng từng file và tổng dung lượng mỗi submission.
  > Ghi chú: Validator kiểm tra `max_file_size_mb`, `max_files` và tổng dung lượng tối đa theo `max_file_size_mb * max_files`.

- [x] Không tin tên file gốc của người dùng.
  > Ghi chú: Dùng `sanitize_upload_filename()` cho tên hiển thị và `storage_public_id()` UUID cho Cloudinary; lưu `original_name` trong metadata bài nộp.

- [x] Lưu checksum SHA-256 để phát hiện file trùng.
  > Ghi chú: `file_checksum()` tính SHA-256 trước khi upload và lưu vào `SubmissionFiles.checksum`.

- [x] Chặn file thực thi nguy hiểm nếu không nằm trong danh sách cho phép.
  > Ghi chú: `DANGEROUS_UPLOAD_EXTENSIONS` chặn `.exe`, `.sh`, `.bat`, `.php`, `.ps1`, `.vbs`, `.jar`... nếu không có trong allowlist.

- [x] Nếu dùng Cloudinary/storage ngoài, URL phải đúng quyền truy cập.
  > Ghi chú: Template không mở trực tiếp `file_url`; chuyển qua route proxy quyền `assignments:open_file`, `submissions:open_file`, `submissions:open_feedback_file`.

- [x] Thêm scan status để sau này tích hợp antivirus.
  > Ghi chú: `SubmissionFiles.scan_status` đã có `pending/skipped/clean/failed/blocked`; upload set `pending` nếu `scan_required`, ngược lại `skipped`.

- [x] Log upload/download quan trọng.
  > Ghi chú: Upload file đề/bài nộp ghi logger; bài thi file ghi `ExamEvents` cho upload, submit, download file bài nộp/feedback/tài liệu đề.

- [x] Học sinh chỉ tải file của chính mình và file đề được phép xem.
  > Ghi chú: Route `open_submission_file_view` chỉ cho chủ bài nộp; route file đề dùng `can_solve_assignment()` nên học sinh phải thuộc lớp và bài đã publish.

- [x] Giáo viên chỉ xem/tải bài nộp của lớp mình.
  > Ghi chú: Route mở file bài nộp/feedback kiểm tra `_is_classroom_teacher()` theo lớp của assignment.

- [x] Admin có quyền audit toàn hệ thống.
  > Ghi chú: `_is_admin_user()` cho phép superuser/staff/role admin mở file để kiểm tra; access được log qua logger và `ExamEvents` nếu là bài thi.

## 7. Trắc nghiệm - Data model

- [x] Thêm model `QuizSettings`.
  > Ghi chú: OneToOne với `Assignments`; lưu `question_order_mode`, `choice_order_mode`, `show_score_after_submit`, `show_correct_answers`, `show_explanation`, `time_limit_minutes`, `passing_score`, `allow_review`.

- [x] Thêm model `QuizQuestions`.
  > Ghi chú: FK `assignment`; fields: `question_text`, `question_type`, `points`, `order_index`, `explanation`, `is_active`, `media_url`, `tags`, `difficulty`, `metadata`.

- [x] Hỗ trợ question type `single_choice`.
  > Ghi chú: Đã khai báo `TYPE_SINGLE_CHOICE`.

- [x] Hỗ trợ question type `multiple_choice`.
  > Ghi chú: Đã khai báo `TYPE_MULTIPLE_CHOICE`; scoring rule chi tiết sẽ triển khai ở phase luồng làm bài.

- [x] Hỗ trợ question type `true_false`.
  > Ghi chú: Đã khai báo `TYPE_TRUE_FALSE`.

- [x] Chuẩn bị hook cho question type `short_text` nhưng chưa cần làm ngay.
  > Ghi chú: Đã khai báo `TYPE_SHORT_TEXT`; `QuizAnswers.text_answer` sẵn chỗ lưu câu trả lời.

- [x] Thêm model `QuizChoices`.
  > Ghi chú: FK question; fields: `choice_text`, `is_correct`, `order_index`, `explanation`, `metadata`.

- [x] Thêm model `QuizAttempts`.
  > Ghi chú: FK assignment, student, submission; fields: `attempt_no`, `status`, `started_at`, `submitted_at`, `score`, `max_score`, `duration_seconds`, `ip_address`, `user_agent`, `random_seed`, `metadata`.

- [x] Thêm model `QuizAnswers`.
  > Ghi chú: FK attempt, question; lưu `selected_choice_ids` JSON, M2M `selected_choices`, `text_answer`, `is_correct`, `score_awarded`, `answered_at`.

- [x] Với quiz exam, liên kết `QuizAttempts` với `ExamSessions`.
  > Ghi chú: `QuizAttempts.exam_session` nullable FK tới `ExamSessions`.

- [x] `Submissions` vẫn là bản ghi điểm cuối cùng để gradebook không phải viết lại.
  > Ghi chú: `QuizAttempts.submission` liên kết bản ghi điểm cuối; test xác nhận `submission_mode_snapshot='quiz'`, `language='quiz'`.

## 8. Trắc nghiệm - Luồng giáo viên

- [x] Form tạo bài có mode `Trắc nghiệm`.
  > Ghi chú: `_assignment_form.html` có mode `quiz`; form không còn khóa publish vì “phase sau”, và trang detail có nút `Quản lý quiz`.

- [x] Giáo viên cấu hình số lần làm cho quiz assignment.
  > Ghi chú: Dùng lại `max_attempts`; quiz assignment có thể để trống hoặc nhập số lần làm tối đa.

- [x] Giáo viên cấu hình quiz exam luôn một lần làm.
  > Ghi chú: `AssignmentForm.clean()` force `max_attempts=1`, tắt hiện điểm/đáp án/review cho quiz exam.

- [x] Giáo viên cấu hình random câu hỏi.
  > Ghi chú: `quiz_random_questions` lưu vào `QuizSettings.question_order_mode`.

- [x] Giáo viên cấu hình random đáp án.
  > Ghi chú: `quiz_random_choices` lưu vào `QuizSettings.choice_order_mode`.

- [x] Giáo viên cấu hình hiện điểm ngay sau khi nộp.
  > Ghi chú: `quiz_show_score_after_submit`; bài thi quiz tự tắt để tránh lộ điểm ngay.

- [x] Giáo viên cấu hình hiện đáp án đúng/giải thích sau hạn.
  > Ghi chú: `quiz_show_correct_answers`, `quiz_show_explanation`, `quiz_allow_review` đã có trong form và `QuizSettings`.

- [x] Giáo viên thêm câu hỏi thủ công.
  > Ghi chú: Trang `assignments:quiz_manage` có form thêm câu hỏi, nhập đáp án theo từng dòng và đáp án đúng dạng `A`/`A;C`/`1;3`.

- [x] Giáo viên sửa/xóa/ẩn câu hỏi.
  > Ghi chú: Có route sửa, toggle ẩn/hiện và “xóa” mềm bằng `is_active=False`; attempt cũ vẫn giữ dữ liệu.

- [x] Giáo viên xem preview đề quiz trước khi publish.
  > Ghi chú: `assignments:quiz_preview` render đề, đáp án đúng và giải thích cho giáo viên.

- [x] Giáo viên import câu hỏi từ CSV.
  > Ghi chú: `assignments:import_quiz_questions` có upload/dán CSV, preview lỗi theo dòng rồi confirm ghi DB; phần 9 sẽ tinh chỉnh sâu format/import history.

- [x] Giáo viên tải file CSV mẫu.
  > Ghi chú: `assignments:sample_quiz_csv` xuất template có single/multiple choice mẫu.

- [x] Giáo viên export câu hỏi quiz ra CSV để chỉnh hàng loạt.
  > Ghi chú: `assignments:export_quiz_questions` xuất câu hỏi + tối đa 6 lựa chọn + correct_answers + tags/difficulty.

- [x] Giáo viên xem thống kê từng câu.
  > Ghi chú: Trang quản lý quiz tính số lượt trả lời và tỉ lệ đúng từng câu từ `QuizAnswers`.

- [x] Giáo viên xem danh sách attempt của học sinh.
  > Ghi chú: `assignments:quiz_attempts` liệt kê attempts, lọc trạng thái, link tới submission để chấm/điều chỉnh.

- [x] Giáo viên có thể chấm tay/điều chỉnh điểm quiz.
  > Ghi chú: Attempt nối `Submissions`; danh sách attempts link sang `/submissions/grade/<id>/` để dùng `manual_score`/comment hiện có.

## 9. Trắc nghiệm - CSV import câu hỏi

- [x] Định nghĩa format CSV chuẩn.
  > Ghi chú: Header chuẩn: `question_text,question_type,points,choice_a...choice_f,choices_json,correct_answers,explanation,tags,difficulty`; parser cũng nhận thêm `choice_g...choice_z` hoặc `choice_1...`.

- [x] `correct_answers` hỗ trợ nhiều đáp án.
  > Ghi chú: Hỗ trợ `A`, `A;C`, `1;3` và cả dấu phẩy rồi normalize về danh sách token.

- [x] Hỗ trợ thêm nhiều hơn 4 đáp án.
  > Ghi chú: Hỗ trợ `choice_e`, `choice_f`, các cột choice mở rộng và `choices_json` dạng JSON array.

- [x] Validate question text không rỗng.
  > Ghi chú: `_parse_quiz_csv_rows()` báo lỗi theo dòng nếu thiếu `question_text`.

- [x] Validate points > 0.
  > Ghi chú: Parser ép `float`, nếu lỗi hoặc `<=0` thì báo `points phải lớn hơn 0`.

- [x] Validate question type hợp lệ.
  > Ghi chú: Chỉ nhận các type trong `QuizQuestions.QUESTION_TYPE_CHOICES`.

- [x] Validate đáp án đúng tồn tại trong các lựa chọn.
  > Ghi chú: `correct_answers` được đổi sang index và báo token không tồn tại như `Z`.

- [x] Validate single choice chỉ có một đáp án đúng.
  > Ghi chú: `single_choice`/`true_false` bắt buộc đúng một đáp án.

- [x] Validate multiple choice có ít nhất một đáp án đúng.
  > Ghi chú: `multiple_choice` bắt buộc có ít nhất một đáp án đúng hợp lệ.

- [x] Cho phép `clear_existing` trước khi import.
  > Ghi chú: Confirm import có checkbox `Ẩn câu hỏi hiện có`; hệ thống soft-hide bằng `is_active=False`.

- [x] Cho phép `append` thêm câu hỏi mới.
  > Ghi chú: Mặc định append câu hỏi mới vào cuối theo `order_index` hiện có.

- [x] Hiển thị preview số câu hợp lệ/lỗi trước khi import.
  > Ghi chú: Trang import hiển thị tổng dòng, số dòng hợp lệ, số dòng lỗi trước khi confirm.

- [x] Báo lỗi theo dòng CSV.
  > Ghi chú: Preview table hiển thị lỗi theo từng dòng; errors có `line_no`.

- [x] Lưu lịch sử import.
  > Ghi chú: Đã thêm model `QuizQuestionImports` với `file_name`, `imported_by`, `total_rows`, `success_rows`, `error_rows`, `clear_existing`, `metadata`, `created_at`; trang import hiển thị lịch sử gần đây.

## 10. Trắc nghiệm - Luồng học sinh

- [x] Học sinh thấy quiz assignment trong lớp/môn với icon trắc nghiệm.
  > Ghi chú: Trang detail giữ badge `quiz` và action chuyển sang lobby `/submissions/quiz/<assignment_pk>/` thay vì màn code.

- [x] Trang quiz assignment hiển thị số lần đã làm/còn lại.
  > Ghi chú: `quiz_lobby.html` và sidebar detail hiển thị đã làm, còn lại, thời gian, quyền xem điểm/xem lại.

- [x] Bài tập quiz cho phép làm nhiều lần theo cấu hình giáo viên.
  > Ghi chú: Dùng `Assignments.max_attempts`; nếu để trống thì không giới hạn, nếu có số thì chặn khi hết lượt.

- [x] Học sinh có thể bắt đầu attempt mới nếu còn lượt.
  > Ghi chú: Thêm route `submissions:start_quiz`, tạo `QuizAttempts` với seed/order snapshot và tiếp tục attempt đang dở nếu có.

- [x] Trong lúc làm quiz, câu trả lời được autosave.
  > Ghi chú: `quiz_take.html` gọi `quiz_autosave` bằng fetch, lưu `QuizAnswers.selected_choice_ids/text_answer` theo từng câu.

- [x] Học sinh có thể chuyển câu nhanh qua sidebar câu hỏi.
  > Ghi chú: Sidebar sticky có grid số câu, click nhảy đến từng câu.

- [x] Hiển thị trạng thái câu đã trả lời/chưa trả lời.
  > Ghi chú: Badge trên từng câu và ô sidebar đổi trạng thái realtime khi chọn/nhập đáp án.

- [x] Khi nộp, hệ thống chấm tự động câu khách quan.
  > Ghi chú: `_grade_quiz_attempt()` chấm single/multiple/true-false all-or-nothing, tạo `Submissions` mode `quiz` để gradebook/statistics dùng lại.

- [x] Sau khi nộp, học sinh thấy điểm theo cấu hình.
  > Ghi chú: `quiz_result.html` chỉ hiện điểm khi `QuizSettings.show_score_after_submit=True`; nếu tắt thì hiện trạng thái chờ công bố.

- [x] Học sinh xem lại attempt cũ nếu giáo viên cho phép.
  > Ghi chú: Lịch sử lobby link đến `quiz_result`; nếu `allow_review=False` thì khóa chi tiết và chỉ hiện tổng quan cho phép.

- [x] Học sinh không xem đáp án đúng trước thời điểm được phép.
  > Ghi chú: Đáp án đúng/giải thích chỉ render khi `show_correct_answers/show_explanation` bật hoặc người xem là giáo viên/admin.

## 11. Bài thi trắc nghiệm - Luồng phòng thi

- [x] Quiz exam dùng lobby + start giống exam lập trình.
  > Ghi chú: Dùng lại `/submissions/exam/<assignment_pk>/` và `/start/`; `exam_ide` dispatch sang màn làm quiz.

- [x] Quiz exam tạo `ExamSessions` khi bắt đầu.
  > Ghi chú: `start_exam_view` tạo/tiếp tục `ExamSessions` như code/file exam.

- [x] Quiz exam tạo một `QuizAttempts` duy nhất cho mỗi học sinh.
  > Ghi chú: `_ensure_quiz_exam_attempt()` tạo attempt `attempt_no=1` gắn `exam_session`; start lại chỉ tiếp tục attempt cũ.

- [x] Quiz exam khóa làm lại.
  > Ghi chú: Sau khi session có `final_submission`, start/lobby chuyển sang kết quả; không tạo attempt thứ hai.

- [x] Quiz exam dùng server-side timer.
  > Ghi chú: `_quiz_attempt_time_remaining()` ưu tiên `ExamSessions.ends_at` cho bài thi; client timer chỉ là hiển thị/phụ trợ.

- [x] Khi hết giờ, hệ thống auto submit attempt hiện tại.
  > Ghi chú: `_expire_session_if_needed()` tự chấm `QuizAttempts` đang chạy và finalize session `auto_submitted`; autosave/submit cũng xử lý timer về 0.

- [x] Autosave từng đáp án trong quá trình làm.
  > Ghi chú: Dùng route autosave của quiz, kiểm tra phiên thi running trước khi lưu.

- [x] Ghi `ExamEvents` cho start, answer_saved, submit, auto_submit, tab_hidden, fullscreen_exit.
  > Ghi chú: Start/continue, autosave, submit/auto_submit/force_submit đều ghi event; UI quiz exam gửi thêm tab/focus/fullscreen event.

- [x] Giáo viên monitor quiz exam.
  > Ghi chú: `exam_monitor.html` hiển thị mode trắc nghiệm, số câu đã trả lời và điểm attempt sau khi nộp.

- [x] Giáo viên có thể gia hạn/force submit quiz exam.
  > Ghi chú: Gia hạn dùng logic session sẵn có; force submit quiz chấm các đáp án đã autosave và set session `auto_submitted`.

- [x] Admin xem sự kiện quiz exam trong trang exam events.
  > Ghi chú: Quiz exam ghi vào `ExamEvents` chung nên trang admin exam events/audit hiện có đọc được cùng nguồn dữ liệu.

## 12. Chấm điểm và công bố điểm

- [x] File submission mặc định `manual`.
  > Ghi chú: `AssignmentForm.clean()` ép file mode từ `auto` sang `manual`, type legacy thành `project`.

- [x] Quiz submission mặc định `auto`.
  > Ghi chú: Quiz không có câu tự luận giữ `grading_mode='auto'`; attempt submit tạo `Submissions` mode `quiz` với điểm tự động.

- [x] Quiz có câu short text thì chuyển sang `mixed` hoặc cần chấm tay phần tự luận.
  > Ghi chú: `_sync_quiz_grading_mode()` chuyển quiz có `short_text` sang `mixed`; màn chấm bài hiển thị câu tự luận là “Cần chấm tay”.

- [x] `manual_score` luôn override điểm tự động nếu giáo viên nhập.
  > Ghi chú: Tiếp tục dùng `submission_final_score()`; test rubric/gradebook xác nhận manual score override điểm tự động.

- [x] Rubric dùng được cho code, file, quiz tự luận.
  > Ghi chú: Trang chấm điểm dùng chung `RubricScores` cho mọi slàmubmission mode; quiz có panel đáp án riêng và vẫn dùng rubric/điểm thủ công.

- [x] Giáo viên có lịch sử chỉnh điểm.
  > Ghi chú: Đã thêm `GradeChangeLogs`, admin inline/list và panel “Lịch sử chỉnh điểm” trên trang chấm.

- [x] Học sinh nhận notification khi bài được chấm/công bố điểm.
  > Ghi chú: Chấm thường/chấm nhanh gửi `submission_graded`; công bố điểm gửi `grades_released` cho học sinh có bài nộp.

- [x] Thêm trạng thái công bố điểm.
  > Ghi chú: Đã thêm `Assignments.grades_released_at`, `show_feedback_after_release` và action `assignments:release_grades`; học sinh chưa thấy điểm/feedback cho tới khi công bố.

## 13. Gradebook, thống kê và CSV export

- [x] Gradebook hiển thị đúng cả `code`, `file`, `quiz`.
  > Ghi chú: `_build_gradebook_data()` dùng `submission_mode` của assignment, manual score override qua `_submission_grade_value()` nên code/file/quiz cùng lên một sổ điểm.

- [x] Gradebook có icon/mode cho từng cột bài.
  > Ghi chú: `gradebook.html` hiển thị icon `code/upload_file/quiz`, label mode ở header cột và từng ô điểm; CSV sổ điểm cũng thêm mode vào header bài.

- [x] Statistics bài file có tổng nộp, chưa nộp, đã chấm, chưa chấm, trễ, phân bố điểm.
  > Ghi chú: `statistics_view()` tính `file_stats`, số file, đã/chưa chấm và dùng `submission_final_score()` cho phổ điểm.

- [x] Statistics quiz có điểm trung bình, attempt trung bình, tỉ lệ hoàn thành, câu khó nhất.
  > Ghi chú: Thống kê quiz đọc `QuizAttempts`/`QuizAnswers`, tính điểm TB, attempt TB, completion rate và bảng câu hỏi có tỷ lệ sai cao.

- [x] CSV bài file xuất danh sách file, điểm, nhận xét, trạng thái chấm.
  > Ghi chú: `export_assignment_submissions_view()` thêm số file, tên/link file, scan status, feedback file và trạng thái chấm cho file mode.

- [x] CSV quiz xuất điểm từng attempt.
  > Ghi chú: Thêm route `assignments:export_quiz_attempts`, dropdown thống kê quiz có mục xuất attempt theo bộ lọc hiện tại.

- [x] CSV quiz xuất phân tích từng câu.
  > Ghi chú: Thêm route `assignments:export_quiz_question_analysis`, xuất số lượt trả lời, đúng/sai, tỷ lệ đúng/sai, điểm TB và đáp án đúng từng câu.

- [x] CSV thiếu bài áp dụng đúng cho file/quiz.
  > Ghi chú: Missing CSV của assignment và gradebook thêm `Loại bài`, vẫn dựa trên submission thực tế nên áp dụng chung cho file/quiz.

- [x] Báo cáo bài trễ áp dụng đúng cho file/quiz.
  > Ghi chú: Late report/CSV dùng `submission_final_score()`, hiển thị mode file/quiz và không ép cột testcase cho bài không phải code.

- [x] Export ZIP bài file có log người tải.
  > Ghi chú: ZIP file submissions đã có route `submissions:download_files_zip`; bổ sung log actor, README trong ZIP ghi người tải/thời điểm và nút tải ZIP trên thống kê file.

## 14. Admin - Cấu hình hệ thống

- [x] Admin cấu hình extension file được phép toàn hệ thống.
  > Ghi chú: Thêm setting `uploads.submission_allowed_extensions` dạng JSON array; `AssignmentForm` tự lấy làm default cho bài nộp file.

- [x] Admin cấu hình dung lượng tối đa mặc định.
  > Ghi chú: Thêm setting `uploads.submission_default_max_mb`; form tạo bài file dùng giá trị này nếu giáo viên chưa có cấu hình riêng.

- [x] Admin cấu hình số file tối đa mặc định.
  > Ghi chú: Thêm setting `uploads.submission_default_max_files`; áp dụng vào `file_max_files` khi tạo bài nộp file.

- [x] Admin cấu hình policy scan file.
  > Ghi chú: Thêm setting `uploads.submission_scan_required_default`; seed/demo và form đều đọc để bật/tắt scan mặc định.

- [x] Admin cấu hình quiz defaults.
  > Ghi chú: Thêm các setting `quiz.default_max_attempts`, `quiz.random_questions_default`, `quiz.random_choices_default`, `quiz.show_score_after_submit_default`, `quiz.show_correct_answers_default`, `quiz.allow_review_default`; form quiz đọc khi tạo mới.

- [x] Admin xem dashboard dung lượng upload.
  > Ghi chú: Dashboard admin có khối `Upload policy` hiển thị tổng file, tổng MB, file chờ scan và file bị chặn.

- [x] Admin xem top bài có nhiều file/attempt.
  > Ghi chú: Dashboard admin thêm `Top file` và `Top quiz`, link sang thống kê assignment tương ứng.

- [x] Admin có công cụ audit các bài thi file/quiz.
  > Ghi chú: Dashboard admin thêm bảng `Exam audit` cho bài thi file/quiz, hiển thị phiên thi, cảnh báo, file/attempt và link lọc sự kiện thi theo assignment.

- [x] Admin có quyền khóa bài/ẩn bài nếu phát hiện lỗi.
  > Ghi chú: Thêm route `administation:assignment_visibility_toggle`; admin có thể ẩn/mở lại bài từ dashboard audit, ghi `ActivityLogs` và thông báo giáo viên.

## 15. UI/UX theo DevLearn design system

- [x] Form tạo bài chuyển sang wizard hoặc segmented sections.
  > Ghi chú: `_assignment_form.html` có segmented navigation sticky 4 bước: Thông tin, Hình thức, Chính sách, Hoàn tất; click sẽ scroll tới section tương ứng.

- [x] Không nhồi tất cả field vào một màn hình dài khó hiểu.
  > Ghi chú: Các nhóm field được tách theo section, mode-specific panel chỉ hiện theo `submission_mode`, code-only field tự ẩn với file/quiz.

- [x] Mode selector dùng segmented control có icon.
  > Ghi chú: Mode selector đổi thành segmented control 3 ô icon `code/upload_file/quiz`, gọn hơn card mô tả dài.

- [x] Bài thi có vùng cấu hình riêng màu cảnh báo nhẹ nhưng không quá rối.
  > Ghi chú: Exam config chuyển sang vùng amber nhẹ, gọn trong panel riêng và vẫn tự ẩn/hiện bằng `exam-toggle`.
làm
- [x] Trang làm file assignment dùng drag-drop upload rõ ràng.
  > Ghi chú: `submit_file.html` dùng drop-zone dashed rõ ràng, text ngắn “Kéo thả hoặc chọn file”, validate file realtime và có sticky submit mobile.
làm
- [x] Trang quiz làm bài có layout ổn định.
  > Ghi chú: `quiz_take.html` có header sticky, sidebar tiến độ sticky desktop, bottom submit fixed mobile, timer/autosave nằm trên header.

- [x] Tránh text hướng dẫn quá dài trong UI.
  > Ghi chú: Rút gọn text mode summary, quiz header, submit copy và upload copy; mô tả dài được thay bằng label/tooltip ngắn.

- [x] Mobile không vỡ layout khi làm quiz/file upload.
  > Ghi chú: File upload/quiz dùng `px-4`, `pb-28`, grid responsive và fixed bottom submit trên mobile để không bị nút trôi khỏi màn hình.

- [x] Header/timer bài thi sticky rõ ràng.
  > Ghi chú: File exam và quiz exam có header sticky `top-16`; timer/remaining time luôn nằm ở vùng đầu màn hình khi cuộn.

- [x] Loading state khi upload file, import CSV, nộp quiz, chấm điểm.
  > Ghi chú: Thêm `data-loading-text` cho form tạo bài/import CSV/chấm điểm; file submit và quiz submit đổi nút sang trạng thái đang xử lý, disable tránh bấm lặp.

## 16. API/View/URL đề xuất

- [x] Assignment create/edit dùng chung form nhưng tách partial theo mode.
  > Ghi chú: Create/edit tiếp tục dùng chung `_assignment_form.html`; các summary partial theo mode được tách vào `templates/assignments/partials/mode_*_summary.html` để dễ mở rộng UI từng mode.

- [x] Thêm route quản lý yêu cầu file.
  > Ghi chú: Đã thêm `/assignments/<pk>/file-requirements/` với `AssignmentFileRequirementsForm`, template riêng và link từ trang chi tiết bài.

- [x] Thêm route nộp file.
  > Ghi chú: Đã thêm `/submissions/file/<assignment_pk>/`, alias rõ nghĩa cho trang nộp file; trang chi tiết bài file trỏ qua route này.

- [x] Thêm route xóa file nháp nếu cho phép.
  > Ghi chú: Đã thêm `/submissions/file/<assignment_pk>/draft/clear/`; hiện xóa server-side draft nếu có và dùng để ghi nhận thao tác clear file trong phòng thi file.

- [x] Thêm route tải toàn bộ bài nộp file.
  > Ghi chú: Đã thêm `/assignments/<pk>/download-submission-files/`, wrapper sang ZIP tải toàn bộ file nộp hiện có.

- [x] Thêm route quản lý câu hỏi quiz.
  > Ghi chú: Đã có route quản lý/thêm/sửa/ẩn/xóa mềm câu hỏi quiz trong `apps.assignments.urls`.

- [x] Thêm route import CSV câu hỏi.
  > Ghi chú: Đã có `/assignments/<pk>/quiz/import/` với preview/confirm/import history.

- [x] Thêm route tải CSV mẫu.
  > Ghi chú: Đã có route tải CSV mẫu câu hỏi quiz.

- [x] Thêm route bắt đầu quiz attempt.
  > Ghi chú: Đã có `/submissions/quiz/<assignment_pk>/start/`, tạo `QuizAttempts` và snapshot thứ tự câu/đáp án.

- [x] Thêm route autosave quiz answer.
  > Ghi chú: Đã có `/submissions/quiz/attempt/<attempt_pk>/autosave/`, nhận JSON và lưu `QuizAnswers`.

- [x] Thêm route submit quiz.
  > Ghi chú: Đã có `/submissions/quiz/attempt/<attempt_pk>/submit/`, lưu đáp án cuối và chấm tự động.

- [x] Thêm route review quiz attempt.
  > Ghi chú: Đã có `/submissions/quiz/attempt/<attempt_pk>/result/`, tôn trọng cấu hình hiện điểm/đáp án/giải thích.

- [x] Exam routes có thể tái sử dụng prefix `/submissions/exam/<assignment_pk>/...`.
  > Ghi chú: Prefix exam hiện dispatch theo `submission_mode`: code mở IDE, file mở trang nộp file trong phiên thi, quiz mở quiz attempt trong phiên thi.

## 17. Migration và tương thích dữ liệu cũ

- [x] Migration thêm `submission_mode` với default `code`.
  > Ghi chú: Đã có field `submission_mode` trong migration `assignments.0009`, default `code`; bổ sung `assignments.0014_backfill_v2_modes` để backfill idempotent dữ liệu cũ.

- [x] Migration thêm `grading_mode` dựa vào `Assignments.type`.
  > Ghi chú: `assignments.0009` seed mode theo `type`; `0014` chạy lại an toàn để sửa các record cũ còn lệch `grading_mode`.

- [x] Migration sửa `Submissions.code_content/language` để phù hợp mode file/quiz.
  > Ghi chú: `submissions.0006` cho `code_content/language` blank default và thêm `submission_mode_snapshot`; `submissions.0009` backfill snapshot theo mode bài, quiz submission dùng `language='quiz'`.

- [x] Không xóa cột `type` ngay.
  > Ghi chú: Giữ `type` trong model/form/admin để rollback và tránh phá template/view cũ; mode mới dùng `submission_mode/grading_mode` làm nguồn chính.

- [x] Seed demo data thêm bài file và quiz.
  > Ghi chú: `seed_demo_data` đã có bài nộp file thường, file exam, quiz luyện tập, quiz exam, kèm submission/attempt/file mẫu.

- [x] Cập nhật admin Django cho model mới.
  > Ghi chú: Admin đã quản lý `AssignmentFileRequirements`, quiz settings/questions/choices/imports, submission files/feedback, quiz attempts/answers, grade logs; bổ sung `classroom_subject` vào admin assignment.

- [x] Cập nhật indexes cho attempt/file.
  > Ghi chú: File submission có index theo submission/checksum/scan/extension; quiz attempt/answer có index theo assignment-student-status, exam session, submission và question correctness.

- [x] Test migration trên Supabase trước khi deploy.
  > Ghi chú: Đã chạy `python manage.py migrate --plan`, apply `assignments.0014` và `submissions.0009`, rồi xác nhận `showmigrations` đều `[X]`.

## 18. Notification và activity log

- [x] Notify học sinh khi có bài file/quiz mới.
  > Ghi chú: Notification publish đã phân loại theo `submission_mode`: file dùng tiêu đề "Bài nộp file mới", quiz dùng "Quiz mới", exam thêm tiền tố bài thi và metadata mode.

- [x] Notify giáo viên khi học sinh nộp file.
  > Ghi chú: `submit_file_view` gửi `submission_submitted` cho giáo viên kèm `submission_mode='file'`, assignment/submission id và link chi tiết bài nộp.

- [x] Notify giáo viên khi quiz exam có auto submit/hết giờ bất thường.
  > Ghi chú: `_finalize_quiz_exam_session` gửi `exam_auto_submitted` khi quiz exam auto-submit; `_expire_session_if_needed` cũng báo nếu hết giờ nhưng không tìm thấy attempt.

- [x] Notify học sinh khi điểm file/quiz được công bố.
  > Ghi chú: `release_grades_view` gửi `grades_released` kèm `submission_mode`/`is_exam`, áp dụng cho bài file/quiz và các mode khác khi giáo viên công bố.

- [x] Activity log khi giáo viên import CSV câu hỏi.
  > Ghi chú: Sau confirm import CSV, hệ thống ghi `QUIZ_CSV_IMPORT` với file name, tổng dòng, dòng hợp lệ/lỗi và `clear_existing`.

- [x] Activity log khi giáo viên chỉnh điểm thủ công.
  > Ghi chú: `grade_submission_view` ghi `SUBMISSION_MANUAL_GRADE` kèm điểm cũ/mới, status cũ/mới, mode bài nộp và thông tin rubric.

- [x] Activity log khi admin thay đổi policy upload/quiz.
  > Ghi chú: System setting create/update/delete/toggle với key thuộc `uploads.*` hoặc `quiz.*` ghi action `ADMIN_POLICY_SETTING_*` kèm policy category và giá trị cũ/mới.

## 19. Hook AI hỗ trợ giáo viên sau này

- [x] Không gọi AI trong phase đầu.
  > Ghi chú: Chỉ thêm schema, admin, context dữ liệu và UI hook ẩn; không thêm service/API call AI.

- [x] Chuẩn bị dữ liệu sạch để AI có thể đọc sau này.
  > Ghi chú: `build_ai_grading_context()` gom rubric, file metadata, extracted text, quiz answers, điểm hiện tại, nhận xét giáo viên và file phản hồi.

- [x] Với file PDF/DOCX, cân nhắc phase sau trích xuất text.
  > Ghi chú: `SubmissionFiles` đã có `text_extraction_status`, `extracted_text`, `extraction_error`, `extracted_at`; phase này chưa chạy extractor.

- [x] Với quiz tự luận, chừa trạng thái `ai_suggested_score` nhưng chưa dùng.
  > Ghi chú: `QuizAnswers` có `ai_suggested_score`, `ai_suggestion_status`, `ai_suggestion_metadata`; UI chấm vẫn không tự áp điểm AI.

- [x] Với chấm file, chừa model `AIScoringSuggestions`.
  > Ghi chú: Model lưu `suggestion`, `suggested_score`, `confidence`, `prompt_version`, `model_name`, `input_snapshot`, `accepted_by_teacher`; đã thêm admin/inline và migration `submissions.0010`.

- [x] UI chấm bài sau này có khu vực "Gợi ý AI" nhưng phase này ẩn.
  > Ghi chú: Trang chấm có panel ẩn `#ai-suggestions-panel[data-ai-hook="future"]`, giữ layout theo DevLearn và chưa hiện cho giáo viên.

## 20. Kiểm thử

- [x] Test tạo bài file assignment.
  > Ghi chú: `AssignmentFormTemplateTests.test_teacher_can_create_file_file_exam_and_quiz_assignments_from_route` tạo bài `file` qua route teacher và kiểm `AssignmentFileRequirements`.

- [x] Test tạo file exam.
  > Ghi chú: Cùng test route trên kiểm `is_exam=True`, `submission_mode=file`, ép `max_attempts=1`, tắt `allow_resubmit`.

- [x] Test học sinh nộp đúng định dạng file.
  > Ghi chú: `SubmissionPermissionTests.test_student_can_submit_file_assignment` phủ upload PDF hợp lệ, checksum, trạng thái scan và thông báo giáo viên.

- [x] Test học sinh bị chặn file sai định dạng/quá dung lượng.
  > Ghi chú: `test_file_assignment_rejects_invalid_extension`, `test_file_assignment_rejects_invalid_mime_type`, `test_file_assignment_rejects_oversized_file`.

- [x] Test giáo viên chỉ xem file submission của lớp mình.
  > Ghi chú: `test_file_download_routes_enforce_owner_and_teacher_permissions` kiểm giáo viên lớp khác bị chặn, giáo viên đúng lớp mở được.

- [x] Test học sinh không tải được file submission của người khác.
  > Ghi chú: `test_file_download_routes_enforce_owner_and_teacher_permissions` kiểm học sinh khác không redirect tới URL file thật.

- [x] Test chấm tay file submission.
  > Ghi chú: `test_teacher_can_manually_grade_file_submission_with_feedback_file` phủ rubric score, manual score, feedback file và grade log.

- [x] Test tạo quiz assignment.
  > Ghi chú: `AssignmentFormTemplateTests.test_teacher_can_create_file_file_exam_and_quiz_assignments_from_route` tạo quiz qua route và kiểm `QuizSettings`.

- [x] Test import quiz CSV hợp lệ.
  > Ghi chú: `AssignmentFormTemplateTests.test_quiz_import_preview_and_confirm_writes_history` phủ preview, confirm, tạo câu hỏi và ghi lịch sử import.

- [x] Test import quiz CSV lỗi báo đúng dòng.
  > Ghi chú: `test_quiz_csv_parser_supports_choices_json_and_validates_answers` kiểm lỗi ở dòng 2/3 và nội dung lỗi đáp án.

- [x] Test quiz assignment làm nhiều lần theo max attempts.
  > Ghi chú: `SubmissionPermissionTests.test_quiz_assignment_respects_max_attempts` phủ chặn khi hết lượt.

- [x] Test quiz exam chỉ làm một lần.
  > Ghi chú: `SubmissionPermissionTests.test_quiz_exam_uses_exam_session_single_attempt_autosave_and_force_submit` kiểm start lại không tạo attempt thứ hai.

- [x] Test quiz autosave và submit.
  > Ghi chú: `SubmissionPermissionTests.test_student_can_start_autosave_and_submit_quiz_assignment` phủ lobby/start/autosave/submit/result.

- [x] Test hết giờ quiz exam auto submit.
  > Ghi chú: `SubmissionPermissionTests.test_quiz_exam_expired_session_auto_submits_attempt` phủ session quá giờ, tự chấm attempt, tạo final submission và log `auto_submit`.

- [x] Test random câu hỏi/đáp án không lộ đáp án đúng ở client.
  > Ghi chú: `test_student_can_start_autosave_and_submit_quiz_assignment` kiểm result không lộ block đáp án đúng khi setting ẩn; `test_quiz_exam_uses_exam_session_single_attempt_autosave_and_force_submit` phủ phòng thi quiz.

- [x] Test gradebook thống kê đúng cả code/file/quiz.
  > Ghi chú: `SubmissionPermissionTests.test_gradebook_combines_code_file_and_quiz_scores` phủ sổ điểm có đủ mode code/file/quiz và export CSV có label mode.

- [x] Test CSV export mới.
  > Ghi chú: `test_file_assignment_statistics_and_csv_include_file_grading_context`, `test_quiz_statistics_and_csv_exports_attempts_and_question_analysis`, `test_exam_session_lifecycle_from_start_to_monitor_export`, `test_gradebook_combines_code_file_and_quiz_scores`.

- [x] Test `python manage.py check`.
  > Ghi chú: Đã chạy, kết quả `System check identified no issues (0 silenced).`

- [x] Test migration trên database Supabase staging/local trước.
  > Ghi chú: Đã chạy `python manage.py migrate`, `showmigrations assignments submissions` đều `[X]` tới `assignments.0014` và `submissions.0010`; `makemigrations --check --dry-run` báo `No changes detected`.

## 21. Thứ tự triển khai đề xuất

- [x] Phase 1: Thêm field `submission_mode`, `grading_mode`, migration tương thích dữ liệu cũ.
  > Ghi chú: Đã thêm mode/grading vào `Assignments`, backfill dữ liệu cũ bằng `assignments.0014_backfill_v2_modes` và snapshot mode ở `Submissions`.

- [x] Phase 2: Làm UI tạo/sửa assignment theo mode, chưa làm logic submit mới.
  > Ghi chú: `_assignment_form.html` có chọn `code/file/quiz`, tự ẩn/hiện cấu hình file/quiz/exam và giữ DevLearn layout.

- [x] Phase 3: Làm nộp file cho assignment thường.
  > Ghi chú: Đã có `submit_file_view`, `submit_file.html`, validate định dạng/dung lượng/số file, fallback storage khi Cloudinary chưa cấu hình.

- [x] Phase 4: Làm chấm file thủ công, rubric, feedback, tải file/ZIP.
  > Ghi chú: `grade_submission_view` nhận diện file submission, hỗ trợ rubric/manual score/feedback file; có route mở file, tải feedback và tải ZIP file nộp.

- [x] Phase 5: Làm file exam dùng `ExamSessions`.
  > Ghi chú: File exam dùng `start_exam`, `exam_ide`, `ExamSessions`, chặn nộp lại sau `final_submission`; quá giờ file exam được đánh dấu expired theo server.

- [x] Phase 6: Làm model quiz question/choice/attempt/answer.
  > Ghi chú: Đã có `QuizSettings`, `QuizQuestions`, `QuizChoices`, `QuizAttempts`, `QuizAnswers` và migration `assignments.0011`/`submissions.0007`.

- [x] Phase 7: Làm CRUD câu hỏi quiz và import CSV.
  > Ghi chú: Đã xong ở phần 8-9: CRUD câu hỏi, preview, CSV mẫu, import/export và lịch sử import.

- [x] Phase 8: Làm học sinh làm quiz assignment nhiều lần.
  > Ghi chú: Đã xong ở phần 10: lobby, attempt nhiều lần, autosave, sidebar, submit, result/review.

- [x] Phase 9: Làm quiz exam một lần, timer, autosave, auto submit.
  > Ghi chú: Quiz exam đi qua `ExamSessions`, một attempt, timer server-side, autosave, submit/force submit/auto submit khi hết giờ; đã có test hết giờ tự nộp.

- [x] Phase 10: Cập nhật gradebook/statistics/CSV/notification/admin dashboard.
  > Ghi chú: Gradebook, thống kê assignment, CSV exports, notification publish/submit/grade/release và dashboard admin đã hiểu `code/file/quiz`.

- [x] Phase 11: Hardening bảo mật upload, quyền truy cập, audit log.
  > Ghi chú: Upload validate extension/MIME/size, tên file sanitize, quyền mở file theo owner/teacher lớp, audit log cho policy/import/manual grade.

- [x] Phase 12: QA full role student/teacher/admin và cập nhật demo data.
  > Ghi chú: `seed_demo_data` có file assignment/file exam/quiz assignment/quiz exam; đã chạy `apps.assignments.tests` + `apps.submissions.tests` tổng 40 tests OK.

## 22. Tiêu chí hoàn thành

- [x] Giáo viên tạo được bài tập nộp file.
  > Ghi chú: `AssignmentFormTemplateTests.test_teacher_can_create_file_file_exam_and_quiz_assignments_from_route` phủ tạo `submission_mode=file` qua route giáo viên và lưu `AssignmentFileRequirements`.

- [x] Học sinh nộp file đúng quy định và xem được lịch sử/điểm.
  > Ghi chú: `test_student_can_submit_file_assignment` phủ nộp file hợp lệ; `test_student_sees_file_submission_history_detail_and_released_score` phủ history/detail, file đã nộp, điểm công bố, feedback file.

- [x] Giáo viên chấm file thủ công bằng điểm, nhận xét, rubric.
  > Ghi chú: `test_teacher_can_manually_grade_file_submission_with_feedback_file` phủ manual score, nhận xét, rubric score, feedback file và grade log.

- [x] Giáo viên tạo được bài thi nộp file một lần có phòng thi.
  > Ghi chú: Route create ép file exam `max_attempts=1`; `test_file_exam_uses_exam_session_and_submits_once` phủ `ExamSessions`, phòng thi và chặn nộp lại.

- [x] Giáo viên tạo được bài tập trắc nghiệm nhiều lần.
  > Ghi chú: Form dùng `submission_mode=quiz` và `max_attempts`; phần học sinh đã tôn trọng số lượt.

- [x] Giáo viên tạo được bài thi trắc nghiệm một lần.
  > Ghi chú: `test_quiz_exam_uses_exam_session_single_attempt_autosave_and_force_submit` phủ quiz exam một attempt, start lại không tạo lượt thứ hai.

- [x] Giáo viên import được câu hỏi trắc nghiệm từ CSV.
  > Ghi chú: Import CSV có preview lỗi theo dòng, confirm ghi DB và lịch sử import.

- [x] Học sinh làm quiz, autosave, nộp bài, xem điểm theo cấu hình.
  > Ghi chú: Đã thêm 3 template học sinh và các route `quiz_lobby`, `quiz_take`, `quiz_result`.

- [x] Admin cấu hình được policy file/quiz và audit được hoạt động.
  > Ghi chú: `UserBulkActionSafetyTests.test_upload_and_quiz_policy_setting_changes_are_audited` phủ setting `uploads.*` và `quiz.*`, ghi `ADMIN_POLICY_SETTING_CREATE` với metadata policy.

- [x] Gradebook/statistics/export hoạt động thống nhất cho code/file/quiz.
  > Ghi chú: `test_gradebook_combines_code_file_and_quiz_scores`, `test_file_assignment_statistics_and_csv_include_file_grading_context`, `test_quiz_statistics_and_csv_exports_attempts_and_question_analysis` phủ gradebook, thống kê và CSV cho cả 3 mode.
