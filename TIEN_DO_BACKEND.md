# 📋 TIẾN ĐỘ XÂY DỰNG BACKEND - Website Dạy và Học Lập Trình

> File này theo dõi tiến độ xây dựng backend. Mỗi phần hoàn thành sẽ được đánh dấu ✅.
> Các mục cần bạn (chủ dự án) cung cấp sẽ được ghi chú 🔑.

---

## PHẦN 0: CẤU HÌNH DỰ ÁN
- [x] **0.1** requirements.txt - Khai báo tất cả thư viện cần thiết ✅
- [x] **0.2** settings.py - Cấu hình Cloudinary, Email SMTP, Media, Login URL, Celery ✅
- [x] **0.3** celery.py - Cấu hình Celery cho task bất đồng bộ (chấm bài) ✅
- [x] **0.4** Middleware - Tạo middleware logging activity (core/middleware.py) ✅
- [x] **0.5** Decorators/Mixins - Tạo decorators phân quyền (core/decorators.py) ✅
- [x] **0.6** core/urls.py - Wire up tất cả app URLs ✅

> ✅ **ĐÃ CẤU HÌNH:**
> - Email SMTP: Gmail (lethanhloc2612004@gmail.com)
> - Cloudinary: cloud_name=dddpqvxzg (cho file upload)
> - Celery: ALWAYS_EAGER=True (chạy đồng bộ, không cần Redis cho dev)

---

## PHẦN 1: ACCOUNTS APP (Đăng ký, Đăng nhập, Profile)
- [x] **1.1** forms.py - RegisterForm, LoginForm, ProfileForm, TeacherRegistrationForm, PasswordResetForm ✅
- [x] **1.2** views.py - register, login, logout, forgot_password ✅
- [x] **1.3** views.py - view_profile, edit_profile ✅
- [x] **1.4** views.py - teacher_registration (gửi đơn đăng ký giáo viên) ✅
- [x] **1.5** urls.py - Routing cho accounts app ✅
- [x] **1.6** admin.py - Đăng ký Profiles, TeacherRegistrations ✅
- [x] **1.7** decorators.py - role_required, teacher_required, admin_required (core/decorators.py) ✅
- [x] **1.8** Templates - login, register, profile, edit_profile, teacher_register, password_reset (4 pages) ✅
- [x] **1.9** base.html + navbar + footer - Layout chung theo phong cách stitch design ✅
- [x] **1.10** home.html - Landing page ✅

### Chức năng tương ứng:
| STT | Chức năng | Trạng thái |
|-----|-----------|------------|
| 1 | Đăng ký tài khoản | ✅ |
| 2 | Đăng nhập | ✅ |
| 3 | Đăng xuất | ✅ |
| 4 | Quên mật khẩu | ✅ |
| 5 | Xem Profile | ✅ |
| 6 | Chỉnh sửa Profile | ✅ |
| 7 | Đăng ký làm Giáo viên | ✅ |

---

## PHẦN 2: CLASSROOMS APP (Quản lý Lớp học)
- [x] **2.1** forms.py - ClassroomForm, JoinClassroomForm, AnnouncementForm ✅
- [x] **2.2** views.py - create_classroom, edit_classroom, delete_classroom (Giáo viên) ✅
- [x] **2.3** views.py - classroom_list, classroom_detail, search_classroom ✅
- [x] **2.4** views.py - join_classroom, leave_classroom (Sinh viên) ✅
- [x] **2.5** views.py - approve_member, remove_member (Giáo viên) ✅
- [x] **2.6** views.py - create_announcement, pin_announcement, delete_announcement ✅
- [x] **2.7** views.py - leaderboard_view ✅
- [x] **2.8** urls.py - Routing cho classrooms app (14 routes) ✅
- [x] **2.9** admin.py - Đăng ký Classrooms, ClassroomMembers, Announcements, Leaderboard ✅
- [x] **2.10** Templates - list, detail, create, edit, delete_confirm, join, search, create_announcement, leaderboard ✅

### Chức năng tương ứng:
| STT | Chức năng | Trạng thái |
|-----|-----------|------------|
| 8 | Tìm kiếm lớp học | ✅ |
| 9 | Tham gia lớp học | ✅ |
| 24 | Xem Bảng xếp hạng | ✅ |
| 25 | Tạo lớp học mới | ✅ |
| 26 | Phê duyệt sinh viên | ✅ |
| 27 | Đăng thông báo lớp | ✅ |
| 28 | Ghim thông báo | ✅ |

---

## PHẦN 3: ASSIGNMENTS APP (Quản lý Bài tập)
- [x] **3.1** forms.py - AssignmentForm, TestcaseForm ✅
- [x] **3.2** views.py - create_assignment, edit_assignment, delete_assignment (Giáo viên) ✅
- [x] **3.3** views.py - assignment_list, assignment_detail (Sinh viên) ✅
- [x] **3.4** views.py - add_testcase, edit_testcase, delete_testcase (Giáo viên) ✅
- [x] **3.5** views.py - upload_assignment_file, delete_assignment_file (Cloudinary) ✅
- [x] **3.6** views.py - assignment_statistics, toggle_publish (Giáo viên) ✅
- [x] **3.7** urls.py - Routing cho assignments app (12 routes) ✅
- [x] **3.8** admin.py - Đăng ký Assignments, Testcases, AssignmentFiles, AssignmentStatistics ✅
- [x] **3.9** Templates - list, detail, create, edit, delete_confirm, testcase_form, statistics ✅

### Chức năng tương ứng:
| STT | Chức năng | Trạng thái |
|-----|-----------|------------|
| 10 | Xem danh sách bài tập | ✅ |
| 11 | Đọc đề bài | ✅ |
| 12 | Tải file đính kèm | ✅ |
| 29 | Tạo bài tập mới | ✅ |
| 30 | Đăng tải học liệu | ✅ |
| 31 | Thêm Testcase mẫu | ✅ |
| 32 | Thêm Testcase ẩn | ✅ |
| 33 | Thiết lập trọng số | ✅ |
| 37 | Xem thống kê bài tập | ✅ |

---

## PHẦN 4: SUBMISSIONS APP (Nộp bài, Chấm điểm, Code Editor)
- [x] **4.1** forms.py - GradeSubmissionForm, CodeCommentForm ✅
- [x] **4.2** views.py - solve_problem (Web IDE page với CodeMirror editor) ✅
- [x] **4.3** views.py - save_draft (AJAX autosave mỗi 5 giây) ✅
- [x] **4.4** views.py - run_test (chạy thử code qua subprocess sandbox) ✅
- [x] **4.5** views.py - submit_code (nộp bài chính thức, tính is_late, penalty) ✅
- [x] **4.6** views.py - submission_history, submission_detail ✅
- [x] **4.7** views.py - grade_submission, add_code_comment (Giáo viên) ✅
- [x] **4.8** views.py - submission_list_teacher (Giáo viên xem tất cả bài nộp) ✅
- [x] **4.9** urls.py - Routing cho submissions app (10 routes) ✅
- [x] **4.10** admin.py - Đăng ký Submissions, SubmissionDetails, CodeComments, CodeDrafts ✅
- [x] **4.11** docker_service.py - Code execution sandbox (subprocess, hỗ trợ Python/C++/Java/JS) ✅
- [x] **4.12** Templates - solve_problem (Web IDE), history, detail, list_teacher, grade ✅

### Chức năng tương ứng:
| STT | Chức năng | Trạng thái |
|-----|-----------|------------|
| 13 | Viết code (Editor) | ✅ |
| 14 | Lưu nháp (Autosave) | ✅ |
| 15 | Chọn ngôn ngữ | ✅ |
| 16 | Chạy thử (Run Test) | ✅ |
| 17 | Nộp bài (Submit) | ✅ |
| 18 | Xem lịch sử nộp | ✅ |
| 19 | Xem chi tiết chấm điểm | ✅ |
| 20 | Xem nhận xét của thầy | ✅ |
| 34 | Xem danh sách bài nộp | ✅ |
| 35 | Chấm bài trực tiếp | ✅ |
| 36 | Note lỗi trên code | ✅ |

---

## PHẦN 5: DISCUSSIONS APP (Thảo luận)
- [x] **5.1** forms.py - DiscussionForm (title + content), ReplyForm (content) ✅
- [x] **5.2** views.py - discussion_list (tabs: all/unanswered/my/popular, search, pagination) ✅
- [x] **5.3** views.py - discussion_detail (thread view + inline reply) ✅
- [x] **5.4** views.py - create_discussion, edit_discussion, delete_discussion ✅
- [x] **5.5** views.py - vote_discussion (AJAX upvote/downvote toggle) ✅
- [x] **5.6** views.py - mark_answer, pin_discussion (AJAX, Giáo viên) ✅
- [x] **5.7** urls.py - Routing cho discussions app (8 routes) ✅
- [x] **5.8** admin.py - Đăng ký Discussions, DiscussionVotes ✅
- [x] **5.9** Templates - list (forum table), detail (thread + voting), create, edit ✅

> ✅ **GHI CHÚ:**
> - Title được lưu dạng `# Title\n\nBody` trong content field (model không có title riêng)
> - Voting AJAX với reload page, N+1 queries đã tối ưu bằng annotation + prefetch

### Chức năng tương ứng:
| STT | Chức năng | Trạng thái |
|-----|-----------|------------|
| 21 | Đăng câu hỏi thảo luận | ✅ |
| 22 | Bình luận/Trả lời | ✅ |
| 23 | Vote thảo luận | ✅ |
| 38 | Xác nhận đáp án đúng | ✅ |

---

## PHẦN 6: ADMINISTRATION APP (Quản trị hệ thống)
- [x] **6.1** forms.py - ProgrammingLanguageForm, SandboxConfigForm, SystemSettingForm ✅
- [x] **6.2** views.py - admin_dashboard (tổng quan hệ thống, metrics, pending teachers) ✅
- [x] **6.3** views.py - approve_teacher, reject_teacher (POST + select_related) ✅
- [x] **6.4** views.py - sandbox CRUD (list, create, edit, delete) ✅
- [x] **6.5** views.py - languages CRUD (list, create, edit, delete, toggle active) ✅
- [x] **6.6** views.py - server_metrics (xem CPU, RAM, containers, queue) ✅
- [x] **6.7** views.py - system_settings CRUD (JSON key-value) ✅
- [x] **6.8** views.py - activity_logs (filter user/action/date, pagination) ✅
- [x] **6.9** urls.py - Routing cho administration app (21 routes) ✅
- [x] **6.10** admin.py - Đăng ký 5 models (ProgrammingLanguages, SandboxConfigs, ServerMetrics, ActivityLogs, SystemSettings) ✅
- [x] **6.11** base_admin.html - Admin sidebar layout với active page highlighting ✅
- [x] **6.12** Templates - dashboard, teacher_approvals, languages, language_form, sandboxes, sandbox_form, system_settings, setting_form, server_metrics, activity_logs (11 templates) ✅

### Chức năng tương ứng:
| STT | Chức năng | Trạng thái |
|-----|-----------|------------|
| 39 | Duyệt đơn giáo viên | ✅ |
| 40 | Cấu hình Sandbox | ✅ |
| 41 | Quản lý Container | ✅ |
| 42 | Quản lý Ngôn ngữ | ✅ |
| 43 | Quản trị Hệ thống | ✅ |
| 44 | Kiểm tra Log | ✅ |

---

## PHẦN 7: SERVICES (Dịch vụ nền)
- [x] **7.1** docker_service.py - Docker container execution + subprocess fallback ✅
- [x] **7.2** plagiarism_service.py - Kiểm tra đạo văn code (difflib + AST normalization, batch pairwise) ✅
- [x] **7.3** supabase_service.py - File storage service (Cloudinary wrapper: upload, delete, list) ✅
- [x] **7.4** Celery tasks - grade_submission_task, check_plagiarism_task (shared_task, async khi có Redis) ✅
- [x] **7.5** Dockerfiles - Python 3.11, GCC 13 (C/C++), OpenJDK 17, Node 20 ✅
- [x] **7.6** core/__init__.py - Auto-import Celery app ✅
- [x] **7.7** submissions/views.py - Hỗ trợ async grading qua Celery khi CELERY_ALWAYS_EAGER=False ✅

> ✅ **GHI CHÚ:**
> - Docker: Nếu Docker không cài đặt, tự động fallback sang subprocess
> - Celery: ALWAYS_EAGER=True (dev) → chạy đồng bộ; ALWAYS_EAGER=False (prod) → cần Redis
> - File storage: Dùng Cloudinary (đã cấu hình), interface sẵn sàng đổi sang Supabase nếu cần

---

## PHẦN 8: DJANGO ADMIN PANEL
- [x] **8.1** accounts/admin.py — ProfilesInline trong User, bulk actions (make_teacher, approve, suspend), fieldsets, date_hierarchy ✅
- [x] **8.2** classrooms/admin.py — Inlines (Members, Announcements), actions (activate/deactivate), date_hierarchy ✅
- [x] **8.3** assignments/admin.py — Inlines (Testcases, Files, Statistics), actions (publish, duplicate), fieldsets ✅
- [x] **8.4** submissions/admin.py — Inlines (Details, Comments), actions (mark_graded, regrade via Celery), fieldsets ✅
- [x] **8.5** discussions/admin.py — Actions (pin/unpin, mark_answer), date_hierarchy ✅
- [x] **8.6** administation/admin.py — Actions (activate/deactivate, delete old logs/metrics), list_editable, save_model ✅
- [x] **8.7** Custom admin branding — site_header, site_title, index_title (LH Programming) ✅

> ✅ **GHI CHÚ:**
> - 21 models đã đăng ký với đầy đủ list_display, list_filter, search_fields, fieldsets
> - 6 inline models: ProfilesInline, ClassroomMembersInline, AnnouncementsInline, TestcasesInline, AssignmentFilesInline, SubmissionDetailsInline
> - 25+ custom admin actions (bulk approve, publish, regrade, delete old data...)
> - Readonly fields cho audit data, date_hierarchy cho time-based models

---

## 📊 TỔNG KẾT TIẾN ĐỘ

| Phần | Mô tả | Trạng thái |
|------|--------|------------|
| 0 | Cấu hình dự án | ✅ Hoàn thành |
| 1 | Accounts App | ✅ Hoàn thành |
| 2 | Classrooms App | ✅ Hoàn thành |
| 3 | Assignments App | ✅ Hoàn thành |
| 4 | Submissions App | ✅ Hoàn thành |
| 5 | Discussions App | ✅ Hoàn thành |
| 6 | Administration App | ✅ Hoàn thành |
| 7 | Services | ✅ Hoàn thành |
| 8 | Django Admin | ✅ Hoàn thành |

---

## 🔑 TỔNG HỢP NHỮNG GÌ CẦN BẠN CUNG CẤP

1. **Email SMTP** - Host, Port, Username, Password (cho chức năng quên mật khẩu)
2. **Supabase credentials** - Project URL, API Key, Service Role Key (cho file upload)
3. **Redis URL** - Cho Celery broker (hoặc xác nhận dùng database backend thay thế)
4. **Docker** - Xác nhận Docker đã cài đặt trên máy dev/server
5. **Domain/URL** - Domain hoặc localhost port để cấu hình ALLOWED_HOSTS
