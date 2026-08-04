# CẤU TRÚC DATABASE THEO MODULE (SƠ ĐỒ LỚP)

Tài liệu này đặc tả chi tiết cấu trúc các bảng (Table), các cột (Column), kiểu dữ liệu (Data Type) và mối quan hệ (Relationships) được chia theo 5 Module nghiệp vụ cốt lõi của hệ thống DevLearn. Phục vụ cho việc vẽ Class Diagram và thiết kế CSDL trong Khóa luận.

---

## 1. MODULE LỚP HỌC & MÔN HỌC (Classrooms & Subjects)

Trọng tâm của module này là quản lý thông tin người dùng, hồ sơ, lớp học, môn học và danh sách sinh viên tham gia lớp.

### Các bảng (Tables) và Thuộc tính (Columns)

**1. auth_user** (Bảng User cốt lõi của Django)
- `id`: integer (Primary Key)
- `username`: varchar (Unique)
- `password`: varchar
- `email`: varchar
- `first_name`: varchar
- `last_name`: varchar
- `is_active`: boolean
- `is_staff`: boolean
- `is_superuser`: boolean
- `last_login`: timestamp
- `date_joined`: timestamp

**2. profiles** (Hồ sơ mở rộng của User)
- `id`: integer (Primary Key, Foreign Key -> auth_user.id)
- `role`: user_role (student, teacher...)
- `avatar_url`: text
- `bio`: text
- `phone`: text
- `status`: approval_status
- `last_login`: timestamp
- `created_at`: timestamp
- `updated_at`: timestamp

**3. classrooms** (Lớp học)
- `id`: integer (Primary Key)
- `name`: text
- `description`: text
- `invite_code`: varchar (Unique)
- `teacher_id`: integer (Foreign Key -> auth_user.id)
- `max_students`: integer
- `is_active`: boolean
- `settings`: jsonb
- `status`: varchar
- `school_year`: varchar
- `semester_term`: varchar
- `approved_by_id`: integer (Foreign Key -> auth_user.id)
- `created_at`: timestamp
- `updated_at`: timestamp

**4. classroom_members** (Thành viên của lớp học - Bảng trung gian N-N)
- `id`: integer (Primary Key)
- `classroom_id`: integer (Foreign Key -> classrooms.id)
- `student_id`: integer (Foreign Key -> auth_user.id)
- `status`: approval_status
- `joined_at`: timestamp

**5. subjects** (Môn học hệ thống)
- `id`: bigint (Primary Key)
- `code`: varchar (Unique)
- `name`: text
- `description`: text
- `status`: varchar
- `is_active`: boolean
- `created_by_id`: integer (Foreign Key -> auth_user.id)
- `approved_by_id`: integer (Foreign Key -> auth_user.id)
- `created_at`: timestamp
- `updated_at`: timestamp

**6. semesters** (Học kỳ)
- `id`: bigint (Primary Key)
- `code`: varchar (Unique)
- `name`: varchar
- `start_date`: date
- `end_date`: date
- `is_current`: boolean
- `is_active`: boolean
- `created_at`: timestamp

**7. classroom_subjects** (Môn học được dạy trong Lớp - Bảng trung gian)
- `id`: bigint (Primary Key)
- `classroom_id`: bigint (Foreign Key -> classrooms.id)
- `subject_id`: bigint (Foreign Key -> subjects.id)
- `semester_id`: bigint (Foreign Key -> semesters.id)
- `assigned_by_id`: integer (Foreign Key -> auth_user.id)
- `is_active`: boolean

---

## 2. MODULE BÀI TẬP & CHỐNG ĐẠO VĂN (Assignments)

Quản lý chi tiết thông số của một đề bài (Code, File), các testcase kiểm thử và báo cáo đạo văn.

### Các bảng (Tables) và Thuộc tính (Columns)

**1. assignments** (Bài tập / Bài thi)
- `id`: integer (Primary Key)
- `classroom_id`: integer (Foreign Key -> classrooms.id)
- `title`: text
- `description`: text
- `instructions`: text
- `type`: assignment_type
- `difficulty`: text
- `allowed_languages`: array
- `start_date`: timestamp
- `due_date`: timestamp
- `max_score`: float
- `max_attempts`: integer
- `is_published`: boolean
- `is_exam`: boolean
- `exam_duration_minutes`: integer
- `grading_mode`: varchar
- `submission_mode`: varchar (code/quiz/file)
- `starter_code`: text
- `solution_code`: text
- `created_by`: integer (Foreign Key -> auth_user.id)

**2. testcases** (Bộ dữ liệu kiểm thử mã nguồn)
- `id`: integer (Primary Key)
- `assignment_id`: integer (Foreign Key -> assignments.id)
- `name`: text
- `input_data`: text
- `expected_output`: text
- `is_hidden`: boolean
- `is_sample`: boolean
- `weight`: float
- `order_index`: integer
- `timeout_override`: integer

**3. assignment_file_requirements** (Cấu hình yêu cầu nộp file)
- `id`: bigint (Primary Key)
- `assignment_id`: bigint (Foreign Key -> assignments.id, Unique)
- `allowed_extensions`: array
- `allowed_mime_types`: array
- `max_file_size_mb`: integer
- `max_files`: integer
- `require_comment`: boolean
- `allow_resubmit`: boolean
- `scan_required`: boolean

**4. assignment_files** (Tài liệu đính kèm của bài tập)
- `id`: integer (Primary Key)
- `assignment_id`: integer (Foreign Key -> assignments.id)
- `file_name`: text
- `file_url`: text
- `file_size`: bigint
- `mime_type`: text

**5. plagiarism_reports** (Báo cáo chống đạo văn)
- `id`: bigint (Primary Key)
- `assignment_id`: bigint (Foreign Key -> assignments.id)
- `status`: varchar
- `threshold`: float
- `language`: varchar
- `result`: jsonb (Chứa data mã nguồn trùng lặp)
- `suspicious_count`: integer

---

## 3. MODULE THI TRẮC NGHIỆM (Quiz)

Lưu trữ cấu hình bài thi trắc nghiệm, ngân hàng câu hỏi, đáp án và lượt làm bài của sinh viên.

### Các bảng (Tables) và Thuộc tính (Columns)

**1. quiz_settings** (Cấu hình bài thi trắc nghiệm)
- `id`: bigint (Primary Key)
- `assignment_id`: bigint (Foreign Key -> assignments.id, Unique)
- `question_order_mode`: varchar
- `choice_order_mode`: varchar
- `show_score_after_submit`: boolean
- `show_correct_answers`: boolean
- `time_limit_minutes`: integer
- `passing_score`: float

**2. quiz_questions** (Câu hỏi trắc nghiệm)
- `id`: bigint (Primary Key)
- `assignment_id`: bigint (Foreign Key -> assignments.id)
- `question_text`: text
- `question_type`: varchar
- `points`: float
- `order_index`: integer
- `difficulty`: text
- `media_url`: text

**3. quiz_choices** (Các đáp án lựa chọn của câu hỏi)
- `id`: bigint (Primary Key)
- `question_id`: bigint (Foreign Key -> quiz_questions.id)
- `choice_text`: text
- `is_correct`: boolean
- `order_index`: integer
- `explanation`: text

**4. quiz_attempts** (Lượt làm bài trắc nghiệm của sinh viên)
- `id`: bigint (Primary Key)
- `assignment_id`: bigint (Foreign Key -> assignments.id)
- `student_id`: integer (Foreign Key -> auth_user.id)
- `attempt_no`: integer
- `status`: varchar
- `started_at`: timestamp
- `submitted_at`: timestamp
- `score`: float
- `duration_seconds`: integer

**5. quiz_answers** (Bài làm chi tiết từng câu của sinh viên)
- `id`: bigint (Primary Key)
- `attempt_id`: bigint (Foreign Key -> quiz_attempts.id)
- `question_id`: bigint (Foreign Key -> quiz_questions.id)
- `selected_choice_ids`: jsonb
- `text_answer`: text
- `is_correct`: boolean
- `score_awarded`: float
- `ai_suggested_score`: float

---

## 4. MODULE LÀM BÀI & CHẤM ĐIỂM (Submissions & Grading)

Quản lý thông tin bài làm (code, file), điểm số, nhận xét của giảng viên và kết quả chạy từng Testcase (Sandbox).

### Các bảng (Tables) và Thuộc tính (Columns)

**1. submissions** (Bài nộp tổng quát)
- `id`: integer (Primary Key)
- `assignment_id`: integer (Foreign Key -> assignments.id)
- `student_id`: integer (Foreign Key -> auth_user.id)
- `code_content`: text
- `language`: text
- `status`: submission_status
- `total_score`: float
- `passed_testcases`: integer
- `total_testcases`: integer
- `execution_time`: float
- `memory_usage`: float
- `is_late`: boolean
- `manual_score`: float
- `teacher_comment`: text
- `submitted_at`: timestamp

**2. submission_details** (Chi tiết chạy Sandbox cho từng Testcase)
- `id`: integer (Primary Key)
- `submission_id`: integer (Foreign Key -> submissions.id)
- `testcase_id`: integer (Foreign Key -> testcases.id)
- `result_status`: enum (Passed, Failed, TLE, MLE...)
- `actual_output`: text
- `error_message`: text
- `execution_time`: float
- `memory_usage`: float
- `score_earned`: float

**3. submission_files** (Các file thực tế sinh viên nộp lên)
- `id`: bigint (Primary Key)
- `submission_id`: bigint (Foreign Key -> submissions.id)
- `file_name`: text
- `file_url`: text
- `file_size`: bigint
- `mime_type`: text
- `scan_status`: varchar
- `uploaded_at`: timestamp

**4. code_comments** (Bình luận trực tiếp trên dòng code của giảng viên)
- `id`: integer (Primary Key)
- `submission_id`: integer (Foreign Key -> submissions.id)
- `teacher_id`: integer (Foreign Key -> auth_user.id)
- `line_number`: integer
- `comment_text`: text
- `is_resolved`: boolean

**5. rubrics** (Tiêu chí chấm điểm tự luận)
- `id`: bigint (Primary Key)
- `assignment_id`: bigint (Foreign Key -> assignments.id)
- `name`: varchar
- `description`: text
- `max_points`: float
- `order_index`: integer

**6. rubric_scores** (Điểm chấm thực tế theo tiêu chí Rubric)
- `id`: bigint (Primary Key)
- `submission_id`: bigint (Foreign Key -> submissions.id)
- `rubric_id`: bigint (Foreign Key -> rubrics.id)
- `score`: float
- `comment`: text

---

## 5. MODULE TƯƠNG TÁC (Discussions & Notifications)

Hỗ trợ diễn đàn hỏi đáp cho từng bài tập và hệ thống đẩy thông báo.

### Các bảng (Tables) và Thuộc tính (Columns)

**1. discussions** (Bài đăng thảo luận / Bình luận)
- `id`: integer (Primary Key)
- `assignment_id`: integer (Foreign Key -> assignments.id)
- `user_id`: integer (Foreign Key -> auth_user.id)
- `parent_id`: integer (Foreign Key -> discussions.id) - *Cho phép Reply lồng nhau (Đệ quy)*
- `content`: text
- `is_pinned`: boolean
- `is_answer`: boolean
- `upvotes`: integer
- `created_at`: timestamp

**2. discussion_votes** (Lượt bình chọn Upvote/Downvote)
- `id`: integer (Primary Key)
- `discussion_id`: integer (Foreign Key -> discussions.id)
- `user_id`: integer (Foreign Key -> auth_user.id)
- `vote_type`: integer (+1 hoặc -1)

**3. notifications** (Thông báo hệ thống)
- `id`: bigint (Primary Key)
- `recipient_id`: integer (Foreign Key -> auth_user.id)
- `actor_id`: integer (Foreign Key -> auth_user.id)
- `notification_type`: varchar
- `title`: text
- `message`: text
- `link`: text
- `is_read`: boolean
- `created_at`: timestamp
