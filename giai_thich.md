# Giải thích cấu trúc dự án `Websitedayvahoclaptrinh` (Django)

Dự án này là một web app viết bằng **Django** (Python), tên project Django là `core` (xem `manage.py` và `core/settings.py`).
Các chức năng chính nhìn từ cấu trúc code:

- Tài khoản người dùng + hồ sơ + đăng ký giáo viên: `apps/accounts/`
- Lớp học (classroom), thành viên, thông báo, bảng xếp hạng: `apps/classrooms/`
- Bài tập (assignment), testcase, file đính kèm, thống kê: `apps/assignments/`
- Nộp bài (submission), chấm tự động (có Celery), comment theo dòng, lưu nháp: `apps/submissions/`
- Thảo luận theo bài tập: `apps/discussions/`
- Trang quản trị nội bộ (duyệt giáo viên, cấu hình sandbox/ngôn ngữ, logs/metrics/system settings): `apps/administation/`

Ghi chú:
- Thư mục `venv/` là môi trường ảo Python (thường **không** cần commit lên repo). Mình không liệt kê chi tiết từng file trong `venv/`.
- Các file dạng `__pycache__/*.pyc` là bytecode Python sinh tự động khi chạy; có thể xóa và sẽ tự sinh lại.
- `media/` thường chứa file upload runtime (có thể trống tùy môi trường).

---

## 1) Các file ở thư mục gốc

- `TIEN_DO_BACKEND.md`: Ghi chú/tiến độ phát triển phần backend.
- `manage.py`: Entry point để chạy lệnh Django (`runserver`, `migrate`, `createsuperuser`, ...); trỏ settings tới `core.settings`.
- `requirements.txt`: Danh sách thư viện Python cần cài (Django, Celery, Redis, Cloudinary, PostgreSQL...).

---

## 2) Project Django: `core/`

- `core/__init__.py`: Đánh dấu `core` là Python package.
- `core/asgi.py`: Entry point ASGI (dùng cho server async như Daphne/Uvicorn).
- `core/wsgi.py`: Entry point WSGI (dùng cho Gunicorn/uWSGI).
- `core/settings.py`: Cấu hình Django (INSTALLED_APPS, DB PostgreSQL, static/media, Cloudinary, email, cấu hình Celery...).  
  Lưu ý: file này đang chứa nhiều secret/credential hard-code; khi triển khai thật nên đưa sang biến môi trường (`.env`) và không commit lên git.
- `core/urls.py`: Router URL gốc, include URL của các app (`accounts/`, `classrooms/`, `assignments/`, `submissions/`, `discussions/`, `administration/`).
- `core/middleware.py`: `ActivityLogMiddleware` ghi log các request “quan trọng” (POST/PUT/PATCH/DELETE) vào bảng `ActivityLogs`.
- `core/decorators.py`: Decorator phân quyền theo role (`student/teacher/admin`) dựa trên `request.user.profiles.role`.
- `core/celery.py`: Khởi tạo app Celery, đọc config từ Django settings và auto-discover tasks.

---

## 3) Các app nghiệp vụ: `apps/`

### 3.1) `apps/accounts/` (Tài khoản, hồ sơ, đăng ký giáo viên)

- `apps/accounts/__init__.py`: Đánh dấu package.
- `apps/accounts/apps.py`: Khai báo `AppConfig` cho Django.
- `apps/accounts/models.py`: Model:
  - `Profiles`: hồ sơ mở rộng cho `django.contrib.auth.models.User` (role, avatar, bio, phone, status...).
  - `TeacherRegistrations`: đơn đăng ký giáo viên (trạng thái pending/approved/rejected, người duyệt...).
- `apps/accounts/forms.py`: Các form cho đăng ký/đăng nhập/cập nhật profile/đăng ký giáo viên + password reset form tuỳ biến.
- `apps/accounts/views.py`: Các view xử lý:
  - đăng ký/đăng nhập/đăng xuất
  - xem/sửa profile
  - gửi đơn đăng ký giáo viên
  - upload avatar lên Cloudinary khi sửa profile
- `apps/accounts/urls.py`: Map URL cho các view ở trên + luồng reset mật khẩu của Django auth.
- `apps/accounts/decorators.py`: Decorator phân quyền theo role (phiên bản riêng trong app accounts; các app khác chủ yếu dùng `core/decorators.py`).
- `apps/accounts/admin.py`: Đăng ký/tuỳ biến hiển thị model trên trang Django Admin (nếu có).
- `apps/accounts/tests.py`: Nơi viết test cho app accounts (hiện có file khung).
- `apps/accounts/migrations/__init__.py`: Đánh dấu package migrations.
- `apps/accounts/migrations/0001_initial.py`: Migration khởi tạo schema DB cho app accounts.

### 3.2) `apps/classrooms/` (Lớp học)

- `apps/classrooms/__init__.py`: Đánh dấu package.
- `apps/classrooms/apps.py`: Khai báo `AppConfig`.
- `apps/classrooms/models.py`: Model:
  - `Classrooms`: lớp học (tên, mô tả, invite_code, giáo viên, settings...).
  - `ClassroomMembers`: thành viên lớp (student, status approved/pending...).
  - `Announcements`: thông báo của lớp.
  - `Leaderboard`: bảng xếp hạng theo lớp.
- `apps/classrooms/forms.py`: Form tạo/sửa lớp, join lớp, tạo thông báo...
- `apps/classrooms/views.py`: View cho:
  - danh sách lớp, tìm kiếm lớp, tạo/sửa/xóa lớp
  - tham gia/rời lớp
  - duyệt/xóa thành viên (teacher)
  - tạo/pin/xóa thông báo
  - xem leaderboard
- `apps/classrooms/urls.py`: Map URL cho các view lớp học.
- `apps/classrooms/admin.py`: Cấu hình Django Admin cho model lớp học (nếu có).
- `apps/classrooms/tests.py`: Khung test cho app classrooms.
- `apps/classrooms/migrations/__init__.py`: Package migrations.
- `apps/classrooms/migrations/0001_initial.py`: Migration khởi tạo schema cho classrooms.

### 3.3) `apps/assignments/` (Bài tập + testcase + file + thống kê)

- `apps/assignments/__init__.py`: Đánh dấu package.
- `apps/assignments/apps.py`: Khai báo `AppConfig`.
- `apps/assignments/models.py`: Model:
  - `Assignments`: bài tập (classroom, mô tả, allowed_languages, hạn nộp, max_score, publish...).
  - `Testcases`: input/expected_output, hidden/sample, weight, giới hạn timeout/memory riêng...
  - `AssignmentFiles`: file đính kèm cho bài tập.
  - `AssignmentStatistics`: thống kê tổng hợp (avg/max/min/pass_rate...).
- `apps/assignments/forms.py`: Form tạo/sửa bài tập và testcase.
- `apps/assignments/views.py`: View cho:
  - danh sách/chi tiết bài tập theo lớp
  - tạo/sửa/xóa bài tập (teacher)
  - publish/unpublish
  - CRUD testcase
  - upload/xóa file đính kèm (hiện dùng Cloudinary uploader trực tiếp trong view)
  - trang thống kê
- `apps/assignments/urls.py`: Map URL cho các view assignments.
- `apps/assignments/admin.py`: Cấu hình Django Admin (nếu có).
- `apps/assignments/tests.py`: Khung test cho app assignments.
- `apps/assignments/migrations/__init__.py`: Package migrations.
- `apps/assignments/migrations/0001_initial.py`: Migration khởi tạo schema cho assignments.

### 3.4) `apps/submissions/` (Nộp bài + chấm tự động + nhận xét)

- `apps/submissions/__init__.py`: Đánh dấu package.
- `apps/submissions/apps.py`: Khai báo `AppConfig`.
- `apps/submissions/models.py`: Model:
  - `Submissions`: bài nộp (code_content, language, status, score, late penalty, graded_by...).
  - `SubmissionDetails`: kết quả theo từng testcase (output, error, time/memory, score_earned...).
  - `CodeComments`: comment của giáo viên theo dòng code, trạng thái resolved.
  - `CodeDrafts`: bản nháp code theo (assignment, student, language) để autosave.
- `apps/submissions/forms.py`: Form chấm tay (manual grade) và form comment code.
- `apps/submissions/utils.py`: Hàm tiện ích cập nhật `AssignmentStatistics` sau khi chấm.
- `apps/submissions/tasks.py`: Celery tasks:
  - `grade_submission_task`: chấm bài async bằng cách chạy testcases (dùng `services/docker_service.run_testcase`).
  - `check_plagiarism_task`: chạy kiểm tra đạo văn theo bài tập (dùng `services/plagiarism_service`).
- `apps/submissions/views.py`: View cho:
  - trang “solve” (editor) + load template/nháp + hiển thị sample testcases
  - autosave nháp qua JSON
  - chạy thử (run test) với sample testcase
  - submit code và chấm (sync hoặc async tùy `CELERY_TASK_ALWAYS_EAGER`)
  - xem lịch sử, xem chi tiết kết quả, danh sách bài nộp cho giáo viên
  - chấm tay, thêm comment, resolve comment
- `apps/submissions/urls.py`: Map URL cho submissions.
- `apps/submissions/admin.py`: Cấu hình Django Admin (nếu có).
- `apps/submissions/tests.py`: Khung test cho app submissions.
- `apps/submissions/migrations/__init__.py`: Package migrations.
- `apps/submissions/migrations/0001_initial.py`: Migration khởi tạo schema cho submissions.

### 3.5) `apps/discussions/` (Thảo luận)

- `apps/discussions/__init__.py`: Đánh dấu package.
- `apps/discussions/apps.py`: Khai báo `AppConfig`.
- `apps/discussions/models.py`: Model:
  - `Discussions`: topic/reply theo assignment (có `parent` để tạo chuỗi trả lời), pin, accepted answer, upvotes...
  - `DiscussionVotes`: lưu vote (1 hoặc -1) theo user/discussion.
- `apps/discussions/forms.py`: Form tạo topic và reply.
- `apps/discussions/views.py`: View cho:
  - danh sách thảo luận theo assignment (lọc tab: all/unanswered/my/popular)
  - chi tiết topic + replies
  - tạo/sửa/xóa topic hoặc reply
  - vote, đánh dấu answer, pin
- `apps/discussions/urls.py`: Map URL cho discussions.
- `apps/discussions/admin.py`: Cấu hình Django Admin (nếu có).
- `apps/discussions/tests.py`: Khung test cho app discussions.
- `apps/discussions/migrations/__init__.py`: Package migrations.
- `apps/discussions/migrations/0001_initial.py`: Migration khởi tạo schema cho discussions.

### 3.6) `apps/administation/` (Quản trị hệ thống nội bộ)

> Lưu ý: tên thư mục/app đang viết là `administation` (thiếu chữ “r” so với “administration”).

- `apps/administation/__init__.py`: Đánh dấu package.
- `apps/administation/apps.py`: Khai báo `AppConfig`.
- `apps/administation/models.py`: Model quản trị:
  - `ProgrammingLanguages`: danh sách ngôn ngữ (tên, extension, syntax mode, template mặc định...).
  - `SandboxConfigs`: cấu hình sandbox theo ngôn ngữ (docker image, timeout/memory/cpu...).
  - `ServerMetrics`: lưu số liệu hệ thống (cpu/memory/containers/queue...).
  - `ActivityLogs`: log hành động người dùng (được ghi bởi `core/middleware.py`).
  - `SystemSettings`: cấu hình chung dạng key/value (JSON).
- `apps/administation/forms.py`: Form CRUD cho programming languages, sandbox config, system settings.
- `apps/administation/views.py`: Trang admin nội bộ (yêu cầu role admin):
  - dashboard tổng quan
  - duyệt giáo viên (approve/reject)
  - CRUD languages, sandboxes, settings
  - xem metrics và logs
- `apps/administation/urls.py`: Map URL cho admin nội bộ (prefix `/administration/`).
- `apps/administation/admin.py`: Cấu hình Django Admin (nếu có).
- `apps/administation/tests.py`: Khung test cho app administation.
- `apps/administation/migrations/__init__.py`: Package migrations.
- `apps/administation/migrations/0001_initial.py`: Migration khởi tạo schema cho administation.

---

## 4) Services dùng chung: `services/`

- `services/__init__.py`: Đánh dấu package.
- `services/docker_service.py`: Dịch vụ chạy/chấm code:
  - ưu tiên chạy trong Docker (giới hạn CPU/RAM/timeout, network=none, read-only...)
  - fallback chạy local subprocess nếu Docker không available
  - dùng để `execute_code`/`run_testcase` (được gọi từ `apps/submissions/`)
- `services/plagiarism_service.py`: Dịch vụ kiểm tra đạo văn:
  - normalize code (xóa comment/whitespace, chuẩn hoá identifier Python)
  - so sánh bằng SequenceMatcher + token similarity + bag-of-tokens
  - batch compare để tìm cặp nghi vấn
- `services/supabase_service.py`: Dịch vụ lưu file qua Cloudinary:
  - upload/delete/get url/list files theo folder
  - có helper upload avatar và file bài tập

---

## 5) Dockerfiles cho sandbox: `docker/`

- `docker/python/Dockerfile`: Docker image/recipe cho chạy code Python trong sandbox.
- `docker/javascript/Dockerfile`: Docker image/recipe cho chạy code JavaScript/Node trong sandbox.
- `docker/java/Dockerfile`: Docker image/recipe cho compile/run Java trong sandbox.
- `docker/cpp/Dockerfile`: Docker image/recipe cho compile/run C/C++ trong sandbox.

---

## 6) Static assets: `static/`

- `static/css/base.css`: CSS nền tảng (layout chung, navbar/footer, style cơ bản).
- `static/css/accounts.css`: CSS cho các trang account (login/register/profile...).
- `static/css/assignments.css`: CSS cho trang bài tập/solve/chấm điểm...
- `static/js/main.js`: JS chung cho toàn site (tương tác UI cơ bản).
- `static/js/editor.js`: JS cho editor code (autosave, run test, submit, UI hiển thị kết quả...).

---

## 7) Templates (UI): `templates/`

### 7.1) Layout chung

- `templates/base.html`: Base layout (head, load static, block content).
- `templates/home.html`: Trang chủ.
- `templates/includes/navbar.html`: Navbar dùng chung.
- `templates/includes/footer.html`: Footer dùng chung.

### 7.2) Accounts

- `templates/accounts/login.html`: Form đăng nhập.
- `templates/accounts/register.html`: Form đăng ký tài khoản.
- `templates/accounts/profile.html`: Trang profile (hiển thị info + thống kê).
- `templates/accounts/edit_profile.html`: Trang sửa profile + upload avatar.
- `templates/accounts/teacher_register.html`: Gửi đơn đăng ký giáo viên.
- `templates/accounts/password_reset.html`: Nhập email để reset mật khẩu.
- `templates/accounts/password_reset_done.html`: Thông báo đã gửi email reset.
- `templates/accounts/password_reset_confirm.html`: Form nhập mật khẩu mới (link có token).
- `templates/accounts/password_reset_complete.html`: Hoàn tất reset mật khẩu.
- `templates/accounts/password_reset_email.html`: Nội dung email reset (template).
- `templates/accounts/password_reset_subject.txt`: Tiêu đề email reset.

### 7.3) Classrooms

- `templates/classrooms/list.html`: Danh sách lớp (lọc/tìm kiếm).
- `templates/classrooms/search.html`: Trang/khối tìm lớp theo query/invite code.
- `templates/classrooms/create.html`: Tạo lớp.
- `templates/classrooms/join.html`: Tham gia lớp bằng mã mời.
- `templates/classrooms/detail.html`: Chi tiết lớp (members, announcements, assignments).
- `templates/classrooms/edit.html`: Sửa lớp.
- `templates/classrooms/delete_confirm.html`: Xác nhận xóa lớp.
- `templates/classrooms/leaderboard.html`: Bảng xếp hạng lớp.
- `templates/classrooms/create_announcement.html`: Tạo thông báo.

### 7.4) Assignments

- `templates/assignments/list.html`: Danh sách bài tập theo lớp.
- `templates/assignments/detail.html`: Chi tiết bài tập (mô tả, file, testcase/sample, statistics...).
- `templates/assignments/create.html`: Tạo bài tập.
- `templates/assignments/edit.html`: Sửa bài tập.
- `templates/assignments/delete_confirm.html`: Xác nhận xóa bài tập.
- `templates/assignments/testcase_form.html`: Form thêm/sửa testcase.
- `templates/assignments/statistics.html`: Trang thống kê bài tập.

### 7.5) Submissions

- `templates/submissions/solve_problem.html`: Trang editor để làm bài + run test + submit.
- `templates/submissions/history.html`: Lịch sử nộp bài theo assignment.
- `templates/submissions/detail.html`: Chi tiết một submission (kết quả testcase, output/error...).
- `templates/submissions/list_teacher.html`: Danh sách bài nộp cho giáo viên theo assignment.
- `templates/submissions/grade.html`: Trang chấm tay/feedback cho giáo viên.

### 7.6) Discussions

- `templates/discussions/list.html`: Danh sách thảo luận theo assignment.
- `templates/discussions/detail.html`: Chi tiết topic + replies + vote/mark answer.
- `templates/discussions/create.html`: Tạo topic.
- `templates/discussions/edit.html`: Sửa topic/reply.

### 7.7) Administration (admin nội bộ)

- `templates/administration/base_admin.html`: Layout chung cho trang admin nội bộ.
- `templates/administration/dashboard.html`: Dashboard admin.
- `templates/administration/teacher_approvals.html`: Danh sách đơn đăng ký giáo viên để duyệt.
- `templates/administration/languages.html`: Danh sách ngôn ngữ lập trình.
- `templates/administration/language_form.html`: Form thêm/sửa ngôn ngữ.
- `templates/administration/sandboxes.html`: Danh sách cấu hình sandbox.
- `templates/administration/sandbox_form.html`: Form thêm/sửa sandbox.
- `templates/administration/system_settings.html`: Danh sách system settings.
- `templates/administration/setting_form.html`: Form thêm/sửa system setting.
- `templates/administration/server_metrics.html`: Trang xem metrics hệ thống.
- `templates/administration/activity_logs.html`: Trang xem activity logs.

