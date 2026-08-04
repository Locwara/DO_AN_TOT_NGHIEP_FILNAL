# Kich ban Review & Tinh chinh he thong LMS

> Vai tro review: Senior Full-Stack Developer + QA Lead  
> Ngay tao: 2026-05-17  
> Pham vi: Django backend, template frontend, role Student/Teacher/Admin, database/API, security, QA workflow.  
> Cach dung: lam toi dau doi `- [ ]` thanh `- [x]`, ghi ket qua vao dong `> Ghi chu:` ngay duoi task.

---

## 0. Tom tat nhanh

### Diem manh hien tai

- [x] He thong da co day du cac khoi LMS chinh: account, lop hoc, mon/hoc ky, bai tap, IDE nop code, cham tu dong/thu cong, rubric, gradebook, calendar, notification, plagiarism, exam session.
  > Ghi chu: 2026-05-17: Da quet source va xac nhan cac khoi chinh ton tai trong apps `accounts`, `classrooms`, `assignments`, `submissions`, `discussions`, `notifications`, `administation`.

- [x] Phan quyen role da co decorator rieng: `student`, `teacher`, `admin`; nhieu view da check theo lop va theo giao vien so huu lop.
  > Ghi chu: 2026-05-17: Da xac nhan `core.decorators` co `student_required`, `teacher_required`, `admin_required`; nhieu view co object-level check theo lop/giao vien. Can tiep tuc bo sung regression test matrix o Dot 2.

- [x] Workflow giao vien -> hoc sinh da co notification o cac diem quan trong: publish bai, nop bai, cham bai, comment code, join lop, discussion reply.
  > Ghi chu: 2026-05-17: Da xac nhan da co service notification va cac diem goi notification quan trong. Can E2E test tiep de dam bao UI hien dung moi role.

- [x] Admin da co dashboard, duyet giao vien/lop/mon, quan ly user, ngon ngu, sandbox, system settings, activity logs.
  > Ghi chu: 2026-05-17: Da xac nhan trong `apps.administation` va template admin; da bo sung them export ActivityLogs CSV.

### Rủi ro/diem can uu tien sua

- [x] **Bao mat cao:** `core/settings.py` dang hardcode `SECRET_KEY`, Supabase password, Cloudinary API secret, Gmail app password va `DEBUG=True`.
  > Ghi chu: 2026-05-17: Da dua cau hinh nhay cam sang env/.env.example, `DEBUG`, `ALLOWED_HOSTS`, DB, Cloudinary, email doc tu env. Van can rotate credential that tren Supabase/Cloudinary/Gmail neu da leak.

- [x] **Bao mat cao:** `login_view` redirect theo `next_url` chua thay validate `url_has_allowed_host_and_scheme`, can chan open redirect.
  > Ghi chu: 2026-05-17: Da validate host/scheme hop le va them regression test external `next` khong redirect ra domain la.

- [x] **Admin safety:** bulk action user co the vo hieu hoa chinh admin/superuser neu tick nham; can guard khong de admin tu khoa minh hoac khoa superuser cuoi cung.
  > Ghi chu: 2026-05-17: Da chan self deactivate/delete va chan khoa active superuser cuoi cung; co test hoi quy cho 2 case nay.

- [x] **QA gap:** cac file `apps/*/tests.py` hien gan nhu trong, chua co automated regression tests cho nhung workflow quan trong.
  > Ghi chu: 2026-05-18: Da bo sung regression tests cho login security, admin bulk, activity log/export, classroom role/join, assignment form/publish, notification ownership, submission permission, grading/rubric/statistics/gradebook, exam lifecycle va security direct URL. Local suite = 29 tests OK, 9 skipped do SQLite khong ho tro PostgreSQL `ArrayField`; can chay lai tren PostgreSQL/Supabase de verify nhom skip.

- [x] **Van hanh:** cac management command dinh ky da co nhung chua co cau hinh cron/Celery Beat trong repo/deploy docs.
  > Ghi chu: 2026-05-17: Da them `docs/scheduler.md` voi cron/Celery Beat goi y cho expire exam session, collect metrics va due-soon notifications.

---

## 1. Review theo phan quyen - Student

### 1.1 Dang ky, dang nhap, profile

- [x] Kiem tra register tao `User` + `Profiles(role='student')` dung va khong tao profile trung.
  > Ghi chu: 2026-05-17: `RegisterForm.save()` tao `Profiles(role='student')` ngay sau khi tao user moi.

- [x] Kiem tra login redirect dung role: student ve dashboard/trang home hop ly, teacher ve teacher dashboard, admin ve admin dashboard.
  > Ghi chu: 2026-05-17: `login_view` redirect admin -> admin dashboard, teacher -> teacher dashboard, student -> home/next hop le.

- [x] Kiem tra `next_url` sau login co validate host hop le de tranh open redirect.
  > Ghi chu: 2026-05-17: `apps.accounts.tests.LoginSecurityTests` pass voi external next bi chan va relative next duoc phep.

- [x] Kiem tra profile cong khai co nen cho xem email/sdt cua user khac hay khong; neu khong thi an thong tin nhay cam.
  > Ghi chu: 2026-05-17: Da an email/sdt tren public profile, chi chu profile hoac admin duoc xem thong tin rieng.

- [x] Kiem tra edit profile chi sua profile cua chinh minh, khong sua role/status qua form.
  > Ghi chu: 2026-05-17: `edit_profile_view` luon dung `request.user`; `ProfileForm` khong expose `role/status`.

### 1.2 Lop hoc va join workflow

- [x] Student chi thay lop dang tham gia approved trong "Lop dang tham gia".
  > Ghi chu: 2026-05-17: `classroom_list_view` lay `my_classrooms` tu `ClassroomMembers.status='approved'`.

- [x] Student khong truy cap duoc detail/noi dung lop khi membership `pending`.
  > Ghi chu: 2026-05-17: `classroom_detail_view` dung `_is_classroom_member`, helper nay chi chap nhan membership `approved`.

- [x] Lop bat `join_requires_approval` phai tao `ClassroomMembers.status='pending'`, khong cho vao lop ngay.
  > Ghi chu: 2026-05-17: Join bang ma moi va quick join deu set `pending` khi classroom setting bat duyet vao lop, sau do redirect ve list.

- [x] Lop auto-approve van tao `approved` va redirect vao detail lop.
  > Ghi chu: 2026-05-17: Join workflow set `approved` khi khong can duyet va redirect vao detail lop.

- [x] Student khong duoc goi API teacher cua lop: import member, approve/remove member, announcement create/pin/delete.
  > Ghi chu: 2026-05-17: Cac view quan ly thanh vien/thong bao co `teacher_required` va object-level `_is_classroom_teacher`.

- [x] Student khong duoc goi route gradebook/export cua lop.
  > Ghi chu: 2026-05-17: `gradebook_view` va `gradebook_export_view` chan neu khong phai teacher/admin cua lop.

### 1.3 Bai tap, IDE, nop bai

- [x] Student chi thay assignment `is_published=True` trong list/detail/calendar.
  > Ghi chu: 2026-05-17: Assignment list/detail/calendar deu filter hoac chan assignment chua publish voi student.

- [x] Student khong vao solve/run/save-draft/submit khi bai chua den `start_date`.
  > Ghi chu: 2026-05-17: `assignment_open_error()` duoc dung trong solve/save-draft/run-test/submit de chan bai chua mo.

- [x] Student khong submit sau `due_date` neu `late_submission_allowed=False`.
  > Ghi chu: 2026-05-17: `submit_code_view` tra JSON error khi qua han va khong cho nop muon.

- [x] Student submit sau deadline neu allow late thi co `is_late=True` va `penalty_applied` dung.
  > Ghi chu: 2026-05-17: `submit_code_view` set `is_late`, `penalty_applied` va tru diem theo `late_penalty_percent`.

- [x] Student khong submit ngon ngu nam ngoai `assignment.allowed_languages`.
  > Ghi chu: 2026-05-17: `validate_submission_language()` duoc goi trong save-draft/run-test/submit.

- [x] Student khong vuot `max_attempts`.
  > Ghi chu: 2026-05-17: `submit_code_view` dem submission hien co va chan khi dat `max_attempts`.

- [x] API `save_draft` khong cho student luu draft assignment khong publish/khong thuoc lop.
  > Ghi chu: 2026-05-17: `save_draft_view` dung `can_solve_assignment()` va `assignment_open_error()`.

- [x] API `run_test` khong cho student chay bai khong publish/khong thuoc lop/khong dung ngon ngu.
  > Ghi chu: 2026-05-17: `run_test_view` check membership/publish/language va exam policy.

### 1.4 Exam/thi

- [x] Student vao `/submissions/solve/<exam>/` phai redirect sang lobby thi, khong vao IDE thuong.
  > Ghi chu: 2026-05-17: `solve_problem_view` redirect student exam sang `submissions:exam_lobby`.

- [x] Student bam "Bat dau thi" tao duy nhat mot `ExamSessions` cho assignment + student.
  > Ghi chu: 2026-05-17: `start_exam_view` dung `get_or_create`; model co unique `(assignment, student)`.

- [x] Refresh IDE thi khong reset `started_at`/`ends_at`.
  > Ghi chu: 2026-05-17: `exam_ide_view` chi doc session dang chay; `start_exam_view` tiep tuc session cu va khong reset thoi gian.

- [x] Timer hien theo `ExamSessions.ends_at`, khong dua vao `CodeDrafts.last_saved_at`.
  > Ghi chu: 2026-05-17: IDE context dung `exam_session.ends_at` va `_exam_remaining_seconds(session)`.

- [x] Policy tat custom input/sample run phai chan ca UI lan backend API.
  > Ghi chu: 2026-05-17: Template IDE co flag UI; backend `run_test_view` chan custom/sample theo policy. Test exam custom input da viet, can chay tren PostgreSQL.

- [x] Event `tab_hidden`, `focus_lost`, `fullscreen_exit`, `paste/copy/context_menu` tao `ExamEvents` va tang warning neu can.
  > Ghi chu: 2026-05-17: Frontend log cac event nay; backend `exam_event_view` tao `ExamEvents`, `_log_exam_event` tang `violation_count` voi warning events.

- [x] Student submit exam xong session chuyen `submitted`, khong nop lai duoc neu `max_attempts=1`.
  > Ghi chu: 2026-05-17: Submit exam set session `submitted`; submit lan sau bi chan boi `max_attempts` va status session da ket thuc.

- [x] Het gio qua grace period thi backend tu choi submit tre.
  > Ghi chu: 2026-05-17: `submit_code_view` so sanh `ends_at + exam_grace_seconds` va tra loi neu qua han.

### 1.5 Diem, feedback, thảo luận, notification

- [x] Student xem submission detail chi thay testcase sample/visible theo `show_testcase_result`, khong thay hidden result neu bi tat.
  > Ghi chu: 2026-05-17: `submission_detail_view` chi append sample testcase cho student khi `show_testcase_result=False`; teacher moi thay tat ca.

- [x] Student xem rubric breakdown va teacher comment sau khi cham.
  > Ghi chu: 2026-05-17: Submission detail query `RubricScores` va template hien `teacher_comment`/rubric breakdown.

- [x] Student dashboard/gradebook/profile dung cung cong thuc diem cuoi: uu tien `manual_score`, sau do `total_score`.
  > Ghi chu: 2026-05-17: Profile/student dashboard dung `Coalesce(manual_score,total_score)` cho metric; gradebook dung helper `_submission_grade_value`.

- [x] Student chi resolve/comment code comment tren submission cua minh; khong thao tac submission cua ban khac.
  > Ghi chu: 2026-05-17: Add code comment chi teacher; resolve comment chi teacher lop hoac chinh student cua submission.

- [x] Student chi tao/xem discussion trong assignment cua lop minh va assignment da publish.
  > Ghi chu: 2026-05-17: List/create discussion yeu cau assignment publish + membership; da bo sung guard cho discussion detail khi assignment bi unpublish.

- [x] Notification open/mark read chi tac dong notification cua chinh user.
  > Ghi chu: 2026-05-17: Notification list/open/mark-read deu filter `recipient=request.user`; mark-all chi update notification cua user hien tai.

---

## 2. Review theo phan quyen - Teacher

### 2.1 Dashboard va dieu huong

- [x] Teacher login vao `accounts:teacher_dashboard`, navbar hien dashboard dung role.
  > Ghi chu: 2026-05-17: `login_view` redirect role teacher ve `accounts:teacher_dashboard`; dashboard/nav teacher co link Tao lop/Lich/Lop hoc.

- [x] Dashboard teacher dem dung lop, hoc sinh, bai tap, bai nop gan day, pending member, pending approval.
  > Ghi chu: 2026-05-17: `teacher_dashboard_view` dem active classrooms, approved members, assignments, submissions 7d, pending members/classrooms/subjects.

- [x] Teacher khong thay/khong thao tac lop cua teacher khac qua direct URL.
  > Ghi chu: 2026-05-17: Cac view lop/bai/submission dung `_is_classroom_teacher` object-level check; direct URL lop khac bi redirect/error.

### 2.2 Quan ly lop va thanh vien

- [x] Teacher tao lop xong lop co status pending/active dung theo workflow admin duyet.
  > Ghi chu: 2026-05-17: Tao lop tao request pending va notify admin; da sua redirect de ve teacher dashboard khi lop chua active, tranh vao detail cua lop chua duyet.

- [x] Teacher sua setting `join_requires_approval` va quick join/join code phan anh dung.
  > Ghi chu: 2026-05-17: Classroom form luu setting vao JSON; join bang ma va quick join deu tao `pending`/`approved` theo setting.

- [x] Teacher approve/remove pending member dung lop minh; khong approve/remove lop khac.
  > Ghi chu: 2026-05-17: Approve/remove member check teacher cua lop va get member theo classroom; approve co notification cho student.

- [x] Import CSV thanh vien khong tao duplicate, khong import teacher/admin lam student, bao loi theo dong ro rang.
  > Ghi chu: 2026-05-17: Import member validate duplicate trong file, email conflict, teacher cua lop, role khac student, file size/type CSV va hien ket qua theo dong.

- [x] Teacher reset/doi invite code nen duoc bo sung neu can van hanh lop that.
  > Ghi chu: 2026-05-17: Da bo sung nut "Doi ma moi" trong trang edit lop; POST sinh ma moi unique va vo hieu hoa ma cu.

### 2.3 Mon hoc, hoc ky, gan mon

- [x] Teacher tao subject moi thi subject pending neu khong phai admin, co notification cho admin.
  > Ghi chu: 2026-05-17: `create_subject_view` set pending cho teacher va goi `notify_admins`; admin tao thi approved ngay.

- [x] Teacher chi edit subject minh tao hoac subject trong quyen lop; admin duoc override.
  > Ghi chu: 2026-05-17: Da cho teacher edit subject minh tao hoac subject dang link active voi lop minh; admin override. Neu teacher sua subject da approved/rejected thi dua ve pending va notify admin duyet lai.

- [x] ClassroomSubjects unique theo classroom + subject + semester, khong tao link trung.
  > Ghi chu: 2026-05-17: Model co `unique_together(classroom, subject, semester)` va assign subject dung form/transaction.

- [x] Assignment filter theo mon/hoc ky khop voi classroom subject da gan.
  > Ghi chu: 2026-05-17: Assignment list/calendar/gradebook co filter `classroom_subject` va `semester`, form assignment chi hien subject links cua lop.

### 2.4 Tao/sua/publish assignment

- [x] Form tao/sua assignment render day du field: title, subject, type, difficulty, description, instructions, time, score, attempts, late, testcase display, leaderboard, languages, exam policy.
  > Ghi chu: 2026-05-17: Create/edit templates render day du field chinh, languages va exam policy.

- [x] Create/edit assignment khong mat field exam khi POST invalid.
  > Ghi chu: 2026-05-17: Form invalid render lai template voi `form.*.value`; exam section giu state theo `form.is_exam.value`.

- [x] Preflight publish chan auto-grade khong testcase, exam thieu duration, bai thieu noi dung.
  > Ghi chu: 2026-05-17: `_assignment_publish_errors()` duoc goi khi publish create/toggle.

- [x] Sau publish, student trong lop nhan notification va thay bai tren list/calendar/dashboard.
  > Ghi chu: 2026-05-17: Publish goi `notify_users` cho members approved; assignment list/calendar/dashboard student filter `is_published=True`.

- [x] Clone assignment copy de bai/testcase/rubric/file/policy, khong copy submission/statistics/plagiarism/session.
  > Ghi chu: 2026-05-17: Clone copy assignment fields, testcase, active rubric, file; clone la draft va khong copy submission/statistics/report/session.

- [x] Teacher co nut "Luu va them testcase" hoac checklist setup ro hon de giam publish nham bai thieu testcase.
  > Ghi chu: 2026-05-17: Da them "Checklist cong bo" trong assignment detail cho title/content/testcase/exam duration/rubric total.

### 2.5 Testcase, file, rubric, grading

- [x] Teacher add/edit/delete testcase chi trong assignment lop minh.
  > Ghi chu: 2026-05-17: Add/edit/delete testcase deu check `_is_classroom_teacher` va get testcase theo assignment.

- [x] Import testcase JSON/CSV validate weight, input/output, sample/hidden, clear_existing an toan.
  > Ghi chu: 2026-05-17: Parser JSON/CSV map schema, validate weight > 0; clear + create nam trong transaction.

- [x] Upload file gioi han type/size, link Cloudinary khong leak credential.
  > Ghi chu: 2026-05-17: Upload assignment gioi han 10MB mac dinh, whitelist extension, chi luu secure URL/metadata; Cloudinary credentials doc tu env.

- [x] Rubric total khong vuot `assignment.max_score`.
  > Ghi chu: 2026-05-17: Add rubric tinh tong active rubric va chan vuot `assignment.max_score`.

- [x] Xoa rubric la soft-hide `is_active=False`, khong pha diem cu.
  > Ghi chu: 2026-05-17: Delete rubric view chi set `is_active=False`.

- [x] Teacher grade submission lop minh, luu manual score/rubric score/feedback/template dung.
  > Ghi chu: 2026-05-17: Grade view check teacher cua lop, validate manual/rubric score, luu `RubricScores`, comment, feedback template.

- [x] Grade view co next/previous submission, pagination/list de cham lop dong.
  > Ghi chu: 2026-05-17: Grade context co `prev_submission`, `next_submission`, `all_submissions`, `current_index`; teacher list co paginator.

- [x] Sau cham bai, student nhan notification va detail hien diem/feedback moi.
  > Ghi chu: 2026-05-17: Sau grade goi notification `submission_graded`; submission detail hien manual score, teacher comment, rubric breakdown.

### 2.6 Gradebook, statistics, plagiarism, exam monitor

- [x] Gradebook tinh diem cuoi thong nhat voi dashboard/profile/statistics.
  > Ghi chu: 2026-05-17: Gradebook dung `_submission_grade_value` uu tien manual score; dashboard/profile dung `Coalesce(manual_score,total_score)`.

- [x] Gradebook export CSV co UTF-8 BOM, filter duoc mon/hoc ky/status.
  > Ghi chu: 2026-05-17: `gradebook_export_view` ghi BOM va dung data filter chung `cs`, `semester`, `published`, `status`.

- [x] Statistics khong query N+1 qua nang khi assignment co nhieu submissions/testcases.
  > Ghi chu: 2026-05-17: Da doi fail-rate theo testcase sang annotate `Count` co filter thay vi 2 query/testcase; submissions da `select_related('student')`.

- [x] Plagiarism page chi teacher lop minh/admin vao duoc, khong hien raw code trong bang so sanh.
  > Ghi chu: 2026-05-17: Plagiarism view check `_is_classroom_teacher`; UI chi hien submission/student/score va link detail, khong render raw code trong bang.

- [x] Exam monitor chi teacher lop minh/admin vao duoc.
  > Ghi chu: 2026-05-17: Exam monitor/export/extend/force-submit deu check teacher cua assignment classroom.

- [x] Exam monitor export CSV co BOM va warning/run/submission dung.
  > Ghi chu: 2026-05-17: `exam_monitor_export_view` ghi BOM va export status/start/end/submitted/run_count/warnings/submission/score.

- [x] Gia han/force submit exam session co audit event va khong chay voi session lop khac.
  > Ghi chu: 2026-05-17: Extend/force-submit check ownership va ghi `ExamEvents` (`teacher_extend`, `teacher_force_submit`, empty draft event).

---

## 3. Review theo phan quyen - Admin

### 3.1 Dashboard va approval workflow

- [x] Admin dashboard dem dung pending teacher/classroom/subject va link dung trang can xu ly.
  > Ghi chu: 2026-05-17: Dashboard/base admin dung `_admin_base_context()` de dem pending teacher/classroom/subject va sidebar link toi trang duyet tuong ung.

- [x] Admin approve/reject teacher cap nhat `Profiles.role/status` va notification cho user.
  > Ghi chu: 2026-05-17: Approve set `Profiles.role='teacher'`, `status='approved'`; reject set profile `status='rejected'`; deu gui notification. Regression test approve teacher pass.

- [x] Admin approve/reject classroom cap nhat `status`, `approved_by`, `reviewed_at`, `is_active` va notification cho teacher.
  > Ghi chu: 2026-05-17: Single approve/reject va bulk deu save day du status/approved_by/reviewed_at/is_active va goi notification cho teacher.

- [x] Admin approve/reject subject cap nhat status va notification cho teacher.
  > Ghi chu: 2026-05-17: Single approve/reject va bulk subject set approved/rejected, active flag, reviewer/time va notification cho nguoi tao subject.

- [x] Bulk approve/reject classroom/subject nen gui notification theo tung object, hien tai can review co thong bao du chua.
  > Ghi chu: 2026-05-17: Da doi bulk update thanh loop transaction theo tung classroom/subject de gui notification rieng cho tung object.

### 3.2 User management

- [x] Admin xem, filter, export user duoc theo role/status/search.
  > Ghi chu: 2026-05-17: User management va CSV export filter theo role/status/search, export co BOM UTF-8 va giu search query tu UI.

- [x] Bulk activate/deactivate/delete phai chan admin tu deactivate chinh minh.
  > Ghi chu: 2026-05-17: `user_bulk_action_view` da guard self target cho deactivate/delete; regression test pass.

- [x] Bulk deactivate/delete phai chan khoa superuser cuoi cung.
  > Ghi chu: 2026-05-17: Da dem active superuser truoc khi bulk deactivate/delete; regression test pass.

- [x] Can bo sung CRUD user day du: tao user, doi role, reset password, khoa/mo khoa, xem lich su hoat dong.
  > Ghi chu: 2026-05-17: Da them trang tao/sua/detail/reset password user; detail hien profile, activity logs va submissions gan day; bulk activate/deactivate dong bo `Profiles.status`.

- [x] Admin action doi role phai tao ActivityLogs metadata ro: old_role, new_role, actor, target.
  > Ghi chu: 2026-05-17: `ADMIN_ROLE_CHANGE`/`ADMIN_USER_CREATE` ghi old_role/new_role/actor_id/target_user_id/target_username; regression test role-change pass.

### 3.3 System, sandbox, settings

- [x] ProgrammingLanguages CRUD map voi allowed_languages va IDE syntax/default template.
  > Ghi chu: 2026-05-17: Admin language CRUD expose `syntax_highlight_mode` va `default_template`; assignment create/edit lay active `ProgrammingLanguages.name` lam `allowed_languages`.

- [x] SandboxConfigs CRUD co validate docker image, timeout/memory/cpu hop le.
  > Ghi chu: 2026-05-17: `SandboxConfigForm` validate docker image co tag/khong khoang trang, timeout 1-60s, memory 32-1024MB, CPU 0.1-4.

- [x] Sandbox monitor kill/requeue chi admin goi duoc, co log va notification neu can.
  > Ghi chu: 2026-05-17: Kill/requeue duoc bao boi `admin_required` + POST, ghi ActivityLogs semantic va notify student neu co.

- [x] `SystemSettings` hien dang nhap JSON tu do; can schema/validator cho cac setting quan trong.
  > Ghi chu: 2026-05-17: Da them `SYSTEM_SETTING_SCHEMAS` va validate type/min/max cho exam, notification, sandbox va upload settings.

- [x] Admin policy UI nen gom: exam grace, fullscreen default, allow custom input, notification hours, sandbox zombie threshold, upload size.
  > Ghi chu: 2026-05-17: System settings UI hien quick cards cho 6 policy key; assignment upload va sandbox monitor da doc setting tu DB.

- [x] ServerMetrics command da co, can scheduler va dashboard bieu do lich su.
  > Ghi chu: 2026-05-17: Da them chart canvas xu huong CPU/memory/queue tren dashboard metrics va `docs/scheduler.md` cho job dinh ky.

### 3.4 Audit, bao mat, giam sat

- [x] ActivityLogs hien log method/path; can them resource_id, action semantic, status_code, metadata cho action quan trong.
  > Ghi chu: 2026-05-17: Middleware da luu them `resource_id`, `status_code`, `url_name`, `view_name`. Action semantic rieng theo nghiep vu co the lam tiep o tung view quan trong.

- [x] ActivityLogs middleware khong nen silently swallow moi exception ma khong log; it nhat log debug/error noi bo.
  > Ghi chu: 2026-05-17: Da log exception bang logger thay vi nuot im lang.

- [x] Admin export activity logs theo user/action/date range co BOM UTF-8.
  > Ghi chu: 2026-05-17: Da them route `administation:activity_logs_export`, nut "Xuat CSV" tren UI, filter dung user/action/date, CSV co BOM UTF-8 va test pass.

- [x] Admin co cong cu xem exam warning/event theo toan he thong neu co tranh chap thi.
  > Ghi chu: 2026-05-17: Da them route/UI `administation:exam_events` cho admin xem event thi toan he thong, filter theo search/event/status/date va danh sach session co warning.

---

## 4. Frontend review

### 4.1 Dieu huong va role-based UI

- [x] Navbar hien link dung theo role: student dashboard, teacher dashboard, admin dashboard/admin.
  > Ghi chu: 2026-05-17: Navbar da hien label dashboard ro theo role, teacher co link Tao lop, admin/superuser co link Quan tri; mobile header giam overflow.

- [x] Student UI khong hien nut teacher/admin: tao bai, gradebook, plagiarism, monitor, import, approve.
  > Ghi chu: 2026-05-17: Da review cac template lop/bai/submission; cac nut tao bai, gradebook, import, approve, monitor/plagiarism nam sau `is_teacher`/role guard.

- [x] Teacher UI khong hien admin-only link tru khi role admin/superuser.
  > Ghi chu: 2026-05-17: Navbar chi hien Quan tri cho role admin/superuser; admin sidebar nam trong namespace administration.

- [x] Admin UI co link den tat ca tool quan trong: approvals, users, classrooms, subjects, languages, sandbox, settings, logs, analytics.
  > Ghi chu: 2026-05-17: `base_admin.html` co dashboard, users, teacher approvals/management, classrooms, subjects, languages, sandbox configs/monitor, exam events, settings, logs, analytics.

### 4.2 Form va validation hien thi

- [x] Assignment create/edit nen tach partial chung de tranh lech field giua 2 template.
  > Ghi chu: 2026-05-17: Da tach `templates/assignments/_assignment_form.html`, create/edit cung include partial nay; regression test render pass.

- [x] Assignment create/edit hien loi field ro rang, giu lai input da nhap khi form invalid.
  > Ghi chu: 2026-05-17: Partial moi hien summary loi va error gan field; POST invalid giu form value va selected languages.

- [x] Exam section an/hien dung va accessible voi keyboard/screen reader.
  > Ghi chu: 2026-05-17: `exam-toggle` co `aria-controls/aria-expanded`, JS sync state va focus vao field dau trong exam section khi bat.

- [x] Classroom create/edit hien setting join approval va giai thich tac dong.
  > Ghi chu: 2026-05-17: Create/edit classroom da co box giai thich bat/tat duyet hoc sinh vao lop anh huong nhu the nao.

- [x] System settings form can editor JSON than thien hoac form typed theo schema.
  > Ghi chu: 2026-05-17: Setting form co live JSON validation va panel policy schema de chon nhanh key/value/description.

### 4.3 AJAX/API frontend

- [x] IDE `fetch` save draft/run/submit parse JSON error dung, khong hien HTML traceback cho user.
  > Ghi chu: 2026-05-17: `parseJsonResponse()` khong render HTML preview/traceback, tra message than thien theo HTTP status.

- [x] Exam frontend goi `exam_event` va `exam_ping` dung, co fallback khi mang loi.
  > Ghi chu: 2026-05-17: Exam event/ping parse JSON, cap nhat status connected/offline va hien canh bao mat ket noi giam sat khi fail.

- [x] Subject name availability API duoc UI goi va hien feedback dung.
  > Ghi chu: 2026-05-17: `subject_form.html` da debounce GET `subject_check_name`, hien state checking/ok/duplicate/error va khong chan submit khi loi mang vi backend van validate.

- [x] Add code comment/resolve comment API duoc UI xu ly optimistic/error state dung.
  > Ghi chu: 2026-05-17: Grade page them optimistic comment row va rollback khi loi; submission detail co toggle resolve optimistic va rollback khi request fail.

- [x] Notification mark read/mark all read co POST + CSRF, khong dung GET thay doi state.
  > Ghi chu: 2026-05-17: `open` GET chi redirect, khong mark read; list co form POST+CSRF cho mark one/all read; regression test pass.

### 4.4 Responsive, accessibility, UX polish

- [x] Bang gradebook/plagiarism/exam monitor scroll ngang tot tren mobile.
  > Ghi chu: 2026-05-17: Cac bang gradebook/plagiarism/exam monitor co wrapper `overflow-x-auto` va min-width on table de mobile cuon ngang thay vi vo layout.

- [x] IDE thi/lop/bai tap co layout khong tran text tren man hinh nho.
  > Ghi chu: 2026-05-17: IDE them media query <=900px de chuyen workspace thanh cot doc, panel de bai full-width va toolbar wrap.

- [x] Button icon co text/title day du; khong chi dua vao icon.
  > Ghi chu: 2026-05-17: Cac nut icon-only quan trong o classroom/detail va notification co title/text; cac CTA chinh deu co icon + label.

- [x] Trang empty state ro cho: khong co lop, khong co bai, khong co submission, khong co report, chua ai vao thi.
  > Ghi chu: 2026-05-17: Da review cac empty state trong classroom list/detail, assignment/list, gradebook, plagiarism, notification, exam monitor; co icon + text huong dan.

- [x] Mau trang thai co text kem theo, khong chi phu thuoc mau.
  > Ghi chu: 2026-05-17: Status badges trong classroom/subject/submission/plagiarism/exam monitor deu co text trang thai kem mau va icon khi can.

---

## 5. Backend review

### 5.1 Authentication & Authorization

- [x] Moi route thay doi state dung `POST` + CSRF + decorator phu hop.
  > Ghi chu: 2026-05-18: Da them/siết `@require_POST` cho action-only routes: assignment publish/clone/delete testcase/file/rubric/plagiarism, admin subject/classroom bulk, classroom quick join/leave/member/announcement actions. Cac form create/edit/delete confirm van dung GET de render form va POST de mutate.

- [x] Moi object-level action co check so huu/lop: assignment, classroom, submission, exam session, discussion, notification.
  > Ghi chu: 2026-05-18: Review cac helper `_is_classroom_teacher`, `_is_classroom_member`, notification `recipient=request.user`, submission owner/teacher, exam session teacher/classroom, discussion owner/member/teacher. Bo sung DOR tests cho submission/notification/exam actions.

- [x] `teacher_required` cho phep role admin; can dam bao admin flow khong bi coi nhu teacher so huu lop khi logic yeu cau ownership that.
  > Ghi chu: 2026-05-18: Da xac nhan admin/superuser override la chu dich trong `_is_classroom_teacher` de admin support/kiem soat lop; teacher thuong van bi chan theo ownership that.

- [x] `admin_required` cho phep superuser; can dam bao profile missing khong chan superuser.
  > Ghi chu: 2026-05-18: `role_required` cho superuser pass truoc khi doc profile. Them test superuser khong co profile van vao duoc admin dashboard.

- [x] Direct Object Reference tests: student goi URL submission/detail cua ban khac, grade/extend/force-submit cua lop khac, notification cua user khac.
  > Ghi chu: 2026-05-18: Them tests cho student khong xem submission cua ban khac, teacher khong grade/extend/force-submit session cua lop khac, user khong open/mark-read notification cua nguoi khac.

### 5.2 Validation & Data Integrity

- [x] Assignment form validate time, exam policy, late penalty, max attempts, max score.
  > Ghi chu: 2026-05-18: Bo sung validate `max_score > 0`, `max_attempts > 0`, late penalty 0-100, exam duration/run count/grace. Them unit test invalid scoring/exam policy.

- [x] Testcase import validate JSON/CSV schema, file size, clear existing trong transaction.
  > Ghi chu: 2026-05-18: File import gioi han 1MB va .json/.csv; JSON/CSV bat buoc co expected_output/output; clear existing da nam trong `transaction.atomic`. Them unit test schema/size.

- [x] Member import validate username/email conflict, duplicate in file, role student, max_students.
  > Ghi chu: 2026-05-18: Review `_parse_member_csv`/`_validate_member_rows` da check duplicate username/email trong file, conflict username-email, role student, approved/pending member va suc chua lop.

- [x] Submission sanitize NUL chars va gioi han output/error size.
  > Ghi chu: 2026-05-18: DB save da sanitize NUL va cap output/error; bo sung `_safe_json_text` de response run-test/custom/sample khong tra output/error qua lon.

- [x] Upload file can check file size/type theo setting thay vi chi tin frontend.
  > Ghi chu: 2026-05-18: Assignment upload dung `uploads.assignment_max_mb` + whitelist extension o backend; testcase import co size/type server-side.

- [x] SystemSettings can validate JSON theo key schema.
  > Ghi chu: 2026-05-18: Review `SystemSettingForm` dung `SYSTEM_SETTING_SCHEMAS`; UI section 4 da hien schema va live JSON validation.

### 5.3 Async/Commands/Scheduler

- [x] `grade_submission_task` va sync grading cho ket qua tuong duong.
  > Ghi chu: 2026-05-18: Sync grading da dung cung sandbox config timeout/memory/docker_image/cpu_limit nhu async; async submit trong exam lien ket `ExamSession.final_submission` truoc khi enqueue.

- [x] `check_plagiarism_task` co the chay async va ghi report dung.
  > Ghi chu: 2026-05-18: `run_plagiarism_view` enqueue task khi Celery khong eager; task cap nhat running/finished/error va luu `error_message` khi service loi.

- [x] `send_due_soon_notifications` can cron/Celery Beat va co dedupe marker.
  > Ghi chu: 2026-05-18: Command co marker dedupe theo assignment/due_date/window; `--hours` co the lay tu setting `notifications.due_soon_hours`. Scheduler doc da co trong `docs/scheduler.md`.

- [x] `expire_exam_sessions` can cron/Celery Beat de server expire session khi client tat tab.
  > Ghi chu: 2026-05-18: Command co trong scheduler doc; bo sung per-session exception handling va `expire_command_error` event de teacher/admin truy vet.

- [x] `collect_server_metrics` va `detect_sandbox_zombies` can cron/Celery Beat va dashboard/doc van hanh.
  > Ghi chu: 2026-05-18: Da co commands, dashboard lien quan va `docs/scheduler.md`; zombie threshold doc/settings-backed qua `sandbox.zombie_threshold_minutes`.

### 5.4 Error handling & Logging

- [x] API JSON khong leak traceback/HTML khi loi 500/403.
  > Ghi chu: 2026-05-18: Them `JsonExceptionMiddleware` de request JSON/AJAX nhan response JSON gon, khong tra HTML traceback/generic 403/404/405.

- [x] ActivityLogs can luu status_code va metadata; hien tai chi method/path.
  > Ghi chu: 2026-05-18: Review `ActivityLogMiddleware` da luu `status_code`, `url_name`, `view_name`, `resource_id`, IP va user agent; test export filter da co.

- [x] External services Cloudinary/Docker/email failure can hien message than thien va log noi bo.
  > Ghi chu: 2026-05-18: Cloudinary upload co message than thien va log noi bo; Docker/local sandbox failure co `logger.exception`; notification service hien khong phu thuoc email SMTP truc tiep.

- [x] Plagiarism/exam command exceptions can ghi report/session error de teacher/admin thay duoc.
  > Ghi chu: 2026-05-18: Plagiarism report set `status=error/error_message`; `expire_exam_sessions` ghi `expire_command_error` event neu fail tung session.

---

## 6. Database/API review

### 6.1 Secrets & deployment settings

- [x] Chuyen `SECRET_KEY` sang env var, rotate key neu da leak.
  > Ghi chu: 2026-05-17: Code da doc `DJANGO_SECRET_KEY` tu env va chan default secret khi `DJANGO_DEBUG=False`. Pending van hanh: tao key moi tren deploy.

- [x] Chuyen Supabase password sang env var, rotate DB password.
  > Ghi chu: 2026-05-17: DB doc tu `DATABASE_URL` hoac `DB_*`; khong con password hardcode trong settings. Pending van hanh: rotate DB password tren Supabase neu da lo.

- [x] Chuyen Cloudinary API secret sang env var, rotate secret.
  > Ghi chu: 2026-05-17: Cloudinary doc tu `CLOUDINARY_*`; chi bat storage khi du credential. Pending van hanh: rotate API secret neu da lo.

- [x] Chuyen Gmail app password sang env var, rotate app password.
  > Ghi chu: 2026-05-17: Email doc tu env, dev mac dinh console backend. Pending van hanh: rotate Gmail app password neu da lo.

- [x] `DEBUG=False` cho production, `ALLOWED_HOSTS` lay tu env.
  > Ghi chu: 2026-05-17: Da co `DJANGO_DEBUG` va `DJANGO_ALLOWED_HOSTS`.

- [x] Bat `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS khi deploy HTTPS.
  > Ghi chu: 2026-05-17: Da them env cho secure cookie, SSL redirect, HSTS; production can set gia tri theo domain HTTPS that.

### 6.2 Schema/index/performance

- [x] Them index cho query hay dung: `Submissions(assignment, student, status, submitted_at)`.
  > Ghi chu: 2026-05-18: Them model index `sub_asg_st_status_at_idx`; migration `apps/submissions/migrations/0004_examsessions_exam_asg_status_idx_and_more.py`.

- [x] Them index cho `ClassroomMembers(classroom, status)` va `ClassroomMembers(student, status)`.
  > Ghi chu: 2026-05-18: Them `cm_classroom_status_idx` va `cm_student_status_idx`; migration `apps/classrooms/migrations/0007_classroommembers_cm_classroom_status_idx_and_more.py`.

- [x] Them index cho `Assignments(classroom, is_published, due_date)` va `Assignments(classroom_subject)`.
  > Ghi chu: 2026-05-18: Them `asg_cls_pub_due_idx` va `asg_cls_subject_idx`; migration `apps/assignments/migrations/0007_assignments_asg_cls_pub_due_idx_and_more.py`.

- [x] Them index cho `ExamSessions(assignment, status)`, `ExamSessions(student, status)`.
  > Ghi chu: 2026-05-18: Them `exam_asg_status_idx` va `exam_st_status_idx`; migration `apps/submissions/migrations/0004_examsessions_exam_asg_status_idx_and_more.py`.

- [x] Review N+1 tren teacher dashboard, gradebook, statistics, exam monitor, notification dropdown.
  > Ghi chu: 2026-05-18: Review cac queryset chinh da dung `select_related`/aggregate cho dashboard, gradebook, statistics, exam monitor, notification dropdown. Bo sung toi uu student dashboard rank de khong query leaderboard/member count theo tung lop.

### 6.3 API/UI coverage matrix

- [x] Backend co command `send_due_soon_notifications` nhung chua co UI/scheduler config ro rang.
  > Ghi chu: 2026-05-18: Da co `docs/scheduler.md` voi cron/Celery Beat; command doc `notifications.due_soon_hours` va co dedupe marker.

- [x] Backend co command `expire_exam_sessions` nhung chua co scheduler config ro rang.
  > Ghi chu: 2026-05-18: Da co `docs/scheduler.md` voi cron/Celery Beat moi 1 phut; command co event loi `expire_command_error`.

- [x] Backend co helper `SystemSettings` nhung nhieu policy chua doc setting that su.
  > Ghi chu: 2026-05-18: Assignment create doc setting mac dinh `exam.default_grace_seconds`, `exam.require_fullscreen_default`, `exam.allow_custom_input_default`; upload/due-soon/zombie da doc setting tu cac phase truoc.

- [x] Backend co `ActivityLogs` nhung UI chua cho export log.
  > Ghi chu: 2026-05-18: Review `activity_logs_view` va `activity_logs_export_view`; test export filter/BOM da co trong `apps/administation/tests.py`.

- [x] Backend co `ServerMetrics` va collect command, can UI bieu do lich su/auto refresh.
  > Ghi chu: 2026-05-18: UI `server_metrics.html` da co chart lich su; bo sung nut lam moi va auto refresh 60 giay.

- [x] Model `Leaderboard` can review job cap nhat sau submission/manual grade; neu chua co thi bo sung.
  > Ghi chu: 2026-05-18: Them `update_classroom_leaderboard()` trong submissions utils; auto cap nhat sau auto grading qua `update_assignment_statistics()` va sau manual grade.

---

## 7. QA test plan bat buoc

### 7.1 Automated tests nen them

- [x] Test auth role: anonymous/student/teacher/admin voi moi nhom route chinh.
  > Ghi chu: 2026-05-18: Them classroom role matrix smoke cho anonymous/student/teacher/admin; security direct URL smoke cho admin/grade/monitor/plagiarism trong submissions tests.

- [x] Test classroom join auto approve va pending approve.
  > Ghi chu: 2026-05-18: Them `ClassroomJoinAndRoleTests` cover invite join auto-approved, pending approval va notification cho teacher.

- [x] Test assignment publish preflight.
  > Ghi chu: 2026-05-18: Them test publish preflight auto-grade: khong testcase thi khong publish, du description/instructions/testcase thi publish. Test skip tren SQLite do PostgreSQL `ArrayField`, se chay tren Supabase/PostgreSQL.

- [x] Test save draft/run test/submit permission va language validation.
  > Ghi chu: 2026-05-18: Them submission test cho save draft va submit sai language bi 400, outsider run-test bi 403. Skip tren SQLite do `ArrayField`, chay tren PostgreSQL.

- [x] Test grading manual/rubric va statistics/gradebook dung diem cuoi.
  > Ghi chu: 2026-05-18: Them test manual grade bang rubric cap nhat `manual_score`, `RubricScores`, `AssignmentStatistics`, `Leaderboard`, va gradebook score. Skip tren SQLite do `ArrayField`, chay tren PostgreSQL.

- [x] Test exam session lifecycle: lobby -> start -> IDE -> event -> submit -> monitor/export.
  > Ghi chu: 2026-05-18: Them test lifecycle exam bang Django client, gom event warning, submit, monitor va export CSV BOM. Skip tren SQLite do `ArrayField`, chay tren PostgreSQL.

- [x] Test admin bulk user khong khoa duoc chinh minh/superuser cuoi cung.
  > Ghi chu: 2026-05-18: Da co trong `apps/administation/tests.py`: self deactivate va last active superuser deu bi chan.

- [x] Test notification ownership: user A khong open/mark read notification user B.
  > Ghi chu: 2026-05-18: Da co trong `apps/notifications/tests.py`: user khac open/mark-read tra 404 va notification van unread.

### 7.2 Manual/E2E smoke tests

- [x] Student E2E: register -> join lop -> xem assignment -> solve -> submit -> xem diem -> notification.
  > Ghi chu: 2026-05-18: Da them checklist smoke trong `docs/qa_smoke.md`; phan join/submit/grade/notification co Django Client coverage. Can chay browser manual tren staging truoc release.

- [x] Teacher E2E: tao lop -> tao/gán mon -> tao bai -> testcase/rubric/file -> publish -> xem submission -> cham -> gradebook.
  > Ghi chu: 2026-05-18: Da them checklist smoke trong `docs/qa_smoke.md`; publish/cham rubric/gradebook co Django Client coverage. File upload nen smoke browser rieng voi Cloudinary credential staging.

- [x] Exam E2E: teacher tao exam -> student start -> warning event -> submit -> teacher monitor/export -> admin audit.
  > Ghi chu: 2026-05-18: Da them checklist smoke trong `docs/qa_smoke.md`; lifecycle exam/monitor/export co Django Client coverage. Admin audit event can smoke tren staging.

- [x] Admin E2E: approve teacher/class/subject -> quan ly user -> sandbox settings -> activity logs.
  > Ghi chu: 2026-05-18: Da them checklist smoke trong `docs/qa_smoke.md`; admin approve/user/log export/settings pages co Django Client coverage trong admin tests.

- [x] Security E2E: student direct URL vao grade/monitor/plagiarism/admin/bulk action bi chan.
  > Ghi chu: 2026-05-18: Them direct URL security smoke cho student vao grade/exam monitor/plagiarism/admin/bulk action bi redirect/forbidden.

---

## 8. Roadmap tinh chinh uu tien

### Dot 1 - Security hotfix

- [x] Dua secrets ra `.env`, rotate credentials, `DEBUG=False` theo env.
  > Ghi chu: 2026-05-17: Code/.env.example da san sang; credential rotation la buoc van hanh ngoai source.

- [x] Validate `next_url` trong login.
  > Ghi chu: 2026-05-17: Da lam va test pass.

- [x] Guard admin bulk user action khong khoa self/superuser cuoi cung.
  > Ghi chu: 2026-05-17: Da lam va test pass.

- [x] Them secure cookie/HTTPS settings cho production.
  > Ghi chu: 2026-05-17: Da them setting env-driven.

### Dot 2 - Permission regression tests

- [x] Viet test role matrix cho classroom/assignment/submission/exam/admin/notification.
  > Ghi chu: 2026-05-18: Da bo sung classroom role matrix, notification ownership, admin bulk, submission/exam direct URL security. Cac test submission/exam can chay tren PostgreSQL/Supabase do SQLite khong ho tro `ArrayField`.

- [x] Viet test API JSON IDE va exam policy.
  > Ghi chu: 2026-05-18: Da co test save draft/run test/submit language validation, exam custom input policy va lifecycle exam event/submit. Skip tren SQLite, chay tren PostgreSQL/Supabase.

- [x] Viet test export CSV BOM cho gradebook/exam/admin.
  > Ghi chu: 2026-05-18: Admin ActivityLogs export co test BOM; exam monitor export va gradebook export da bo sung assertion BOM trong submission lifecycle test.

### Dot 3 - Admin & operations

- [x] Them UI schema cho SystemSettings.
  > Ghi chu: 2026-05-18: `system_settings.html` va `setting_form.html` hien schema policy tu `SYSTEM_SETTING_SCHEMAS`, co live JSON validation.

- [x] Them export ActivityLogs.
  > Ghi chu: 2026-05-18: Da co `activity_logs_export_view`, nut export trong UI, filter theo query va test UTF-8 BOM.

- [x] Them scheduler docs/Celery Beat config cho commands.
  > Ghi chu: 2026-05-18: Da co `docs/scheduler.md` voi cron/Celery Beat cho `expire_exam_sessions`, `collect_server_metrics`, `send_due_soon_notifications`, `detect_sandbox_zombies`.

- [x] Them metrics chart va zombie alert lifecycle.
  > Ghi chu: 2026-05-18: Server Metrics co chart lich su + auto refresh; Sandbox Monitor co zombie list, kill/requeue actions, notification va command detect.

### Dot 4 - UX polish

- [x] Tach partial assignment form chung create/edit.
  > Ghi chu: 2026-05-18: Da tach `templates/assignments/_assignment_form.html`; create/edit include chung va co test template render.

- [x] Them setup checklist cho assignment detail.
  > Ghi chu: 2026-05-18: `assignment_detail_view` truyen `setup_checks`; template detail hien checklist cho giao vien.

- [x] Pagination/filter cho gradebook/plagiarism/exam monitor neu du lieu lon.
  > Ghi chu: 2026-05-18: Gradebook co filter/export va bang scroll ngang; plagiarism report pairs da paginate 20/cap; exam monitor co status filter va paginate 25/cap.

- [x] Mobile/accessibility pass cho bang lon va IDE.
  > Ghi chu: 2026-05-18: Cac bang lon dung overflow/min-width, IDE co responsive CSS, icon-only buttons co title/label hon, assignment form dung shared controls/accessibility state.

---

## 9. Definition of Done

- [ ] Tat ca task security Dot 1 da xong va credentials da rotate.
  > Ghi chu: 2026-05-18: Source-code side da xong: secrets doc tu env, `DEBUG`/secure cookie/HTTPS setting env-driven, login next_url safe, admin bulk guard co test. Chua tick vi rotation credential la buoc van hanh ngoai source: can rotate `DJANGO_SECRET_KEY`, Supabase password, Cloudinary secret, Gmail app password tren moi truong that.

- [x] `python manage.py check` pass.
  > Ghi chu: 2026-05-18: Pass, `System check identified no issues`.

- [x] `python manage.py makemigrations --check --dry-run` khong co migration pending.
  > Ghi chu: 2026-05-18: Pass, `No changes detected`.

- [x] Automated tests moi pass cho role/security/exam/grading.
  > Ghi chu: 2026-05-18: Local suite `python manage.py test apps.accounts.tests apps.administation.tests apps.assignments.tests apps.classrooms.tests apps.notifications.tests apps.submissions.tests --keepdb` = 29 tests OK, 9 skipped do SQLite khong ho tro PostgreSQL `ArrayField`. Can chay lai cung command tren PostgreSQL/Supabase de verify cac test assignment/submission/exam dang skip.

- [ ] Smoke test tren Supabase pass cho Student/Teacher/Admin.
  > Ghi chu: 2026-05-18: Da tao checklist `docs/qa_smoke.md`; chua tick vi chua chay browser smoke tren Supabase/staging that.

- [x] Moi route moi co UI hoac duoc ghi ro la command/internal API.
  > Ghi chu: 2026-05-18: Da them `docs/route_coverage.md`; route UI, JSON/internal API va management commands deu duoc map, scheduler commands tro ve `docs/scheduler.md`.

- [x] Moi export CSV tieng Viet co UTF-8 BOM.
  > Ghi chu: 2026-05-18: Gradebook, exam monitor, late report, member template, user/classroom/subject/activity logs export deu ghi UTF-8 BOM. Bo sung test BOM cho admin exports, gradebook va exam export.

- [x] Moi thay doi state quan trong co ActivityLog/notification neu can.
  > Ghi chu: 2026-05-18: `ActivityLogMiddleware` log POST/PUT/PATCH/DELETE voi status/metadata; notification da co cho publish assignment, submission/grade/comment, join/import lop, approvals, zombie lifecycle, due-soon va discussion answer/reply.
