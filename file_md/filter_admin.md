# Filter Admin - Ke hoach bo sung bo loc nang cao cho khu vuc quan tri

> Muc tieu: bien cac trang quan ly admin tu "search chung chung" thanh bo loc theo ngu canh that: loc mon theo lop, lop theo mon, user theo vai tro/hoat dong, bai thi theo lop/mon/hoc sinh, sandbox theo ngon ngu dang dung...
>
> Nguyen tac: filter phai ro rang, khong lam roi UI, giu query param khi phan trang/export CSV, va moi filter backend phai validate ID/trang thai truoc khi query.

## 0. Ra soat hien trang

- [x] Lap bang route admin -> view -> template -> filter hien co.
  > Ghi chu:
  >
  > | Route | View | Template | Filter hien co | Can nang cap chinh |
  > | --- | --- | --- | --- | --- |
  > | `/administration/` | `admin_dashboard_view` | `dashboard.html` | Chua co filter, chi tong quan nhanh | Sau nay them preset thoi gian/queue neu can |
  > | `/administration/users/` | `user_management_view` | `user_management.html` | `search`, `role`, `status` | Loc theo lop, mon, profile status, last login, ngay tao |
  > | `/administration/teachers/` | `teacher_management_view` | `user_management.html` | `search`, `status`, block duyet co `approval_status`, `approval_search` | Loc theo lop/mon, don dang ky theo institution/reviewer/date |
  > | `/administration/students/` | `student_management_view` | `user_management.html` | `search`, `status` | Loc theo lop, mon, bai nop, ngay tham gia |
  > | `/administration/teacher-approvals/` | `teacher_approvals_view` | render lai `user_management.html` | `status`, `search` qua helper cu | Route backward-compatible, nen tro ve `/teachers/` |
  > | `/administration/subjects/` | `subject_management_view` | `subject_management.html` | `search`, `status` | Loc theo lop, giao vien, ky, ngon ngu, sandbox, co bai/bai thi |
  > | `/administration/classrooms/` | `classroom_management_view` | `classroom_management.html` | `search`, `status` | Loc theo mon, giao vien, ky, si so, co bai/bai thi |
  > | `/administration/languages/` | `language_list_view` | `languages.html` | `search` | Loc active, co sandbox, dang duoc mon/bai dung |
  > | `/administration/sandboxes/` | `sandbox_list_view` | `sandboxes.html` | `search` | Loc language, active, config status, used by assignments |
  > | `/administration/metrics/` | `server_metrics_view` | `server_metrics.html` | Chua co filter | Loc khoang thoi gian, nguong CPU/memory/queue |
  > | `/administration/settings/` | `system_settings_view` | `system_settings.html` | `search`, `category` | Loc type, critical, missing, updated_by/date |
  > | `/administration/logs/` | `activity_logs_view` | `activity_logs.html` | `user`, `action`, `resource_type`, `resource_id`, `date_from`, `date_to` | Doi resource/action thanh select/preset, loc role/ip |
  > | `/administration/exam-events/` | `exam_events_view` | `exam_events.html` | `search`, `event_type`, `status`, `min_warnings`, `date_from`, `date_to` | Loc assignment, classroom, subject, teacher, student |
  > | `/administration/analytics/` | `analytics_view` | `analytics.html` | Chua co filter | Loc date, lop, mon, giao vien, ngon ngu |
  > | `/administration/sandbox-monitor/` | `sandbox_monitor_view` | `sandbox_monitor.html` | Chua co filter | Loc status, language, assignment, classroom, subject, age |

- [x] Xac dinh cac model chinh va quan he loc cheo:
  `Classrooms`, `Subjects`, `ClassroomSubjects`, `Semesters`, `Assignments`, `Submissions`, `ExamSessions`, `ProgrammingLanguages`, `SandboxConfigs`, `ActivityLogs`, `User`, `Profiles`.
  > Ghi chu:
  >
  > | Nhu cau loc cheo | Quan he/model dung |
  > | --- | --- |
  > | Mon hoc thuoc lop A | `ClassroomSubjects.classroom -> Classrooms`, `ClassroomSubjects.subject -> Subjects` |
  > | Lop nao co mon ABC | `Classrooms -> classroom_subject_links -> Subjects` |
  > | Lop/mon theo ky hoc | `ClassroomSubjects.semester -> Semesters` |
  > | Giao vien day lop/mon | `Classrooms.teacher -> User`, ket hop `ClassroomSubjects` |
  > | Hoc sinh thuoc lop | `ClassroomMembers.classroom/student/status` |
  > | Hoc sinh co hoc mon | `ClassroomMembers` + `ClassroomSubjects` qua classroom |
  > | Mon hoc dung ngon ngu | `Subjects.languages -> ProgrammingLanguages` |
  > | Bai tap/bai thi theo lop/mon | `Assignments.classroom`, `Assignments.classroom_subject`, `Assignments.is_exam` |
  > | Bai nop theo hoc sinh/bai/lop/mon | `Submissions.student`, `Submissions.assignment`, `Assignments.classroom_subject` |
  > | Phien thi/su kien thi | `ExamSessions.assignment/student`, `ExamEvents.session` |
  > | Sandbox co khop ngon ngu | `SandboxConfigs.language` so voi `ProgrammingLanguages.name` va `Assignments.allowed_languages` |
  > | Audit theo doi tuong | `ActivityLogs.user`, `resource_type`, `resource_id`, `created_at` |

- [x] Kiem tra cac filter hien co da giu query params khi phan trang chua.
  > Ghi chu:
  >
  > - `user_management.html`: pagination giu `page`, `search`, `role`, `status`. Block duyet giao vien giu `approval_status`, `approval_search`, `approval_page`, nhung chua giu filter danh sach giao vien khi phan trang block duyet.
  > - `subject_management.html`: pagination giu `page`, `search`, `status`.
  > - `classroom_management.html`: pagination giu `page`, `search`, `status`.
  > - `activity_logs.html`: pagination giu `user`, `action`, `resource_type`, `resource_id`, `date_from`, `date_to`, `page`.
  > - `exam_events.html`: pagination giu `search`, `event_type`, `status`, `min_warnings`, `date_from`, `date_to`, `page`.
  > - `languages.html`, `sandboxes.html`, `system_settings.html`: hien chua dung paginator. Neu them nhieu filter/sap xep thi can helper query string dung chung.
  > - Cac template cu `teacher_management.html`, `teacher_approvals.html`, `subject_approvals.html` con ton tai nhung luong chinh da gop vao `user_management.html` va `subject_management.html`; khi refactor nen tranh sua nham file cu neu khong con render.

- [x] Kiem tra cac CSV export co nhan cung bo filter voi trang hien tai chua.
  > Ghi chu:
  >
  > | CSV | View | Params dang nhan | Muc do khop UI |
  > | --- | --- | --- | --- |
  > | User CSV | `user_export_view` | `role`, `status`, `search`, `type` | Khop filter user hien co |
  > | Classroom CSV | `classroom_export_view` | `status`, `search`, `type` | Khop filter lop hien co |
  > | Subject CSV | `subject_export_view` | `status`, `search`, `type` | Khop filter mon hien co |
  > | Activity Logs CSV | `activity_logs_export_view` | Dung `_filtered_activity_logs_from_request`, nhan GET hien co + `type` | Khop filter log hien co, can canh type bi lap khi request.GET da co `type` |
  > | Exam Events CSV | Chua co route export rieng | Can bo sung neu muon xuat su kien thi |
  > | Languages/Sandboxes/Settings CSV | Chua co CSV rieng | Co the de sau, tuy nhu cau van hanh |

- [x] Chot style filter theo `devlearn-design-system.md`: form gon, label ngan, select/input khong tran, nut xoa loc ro rang.
  > Ghi chu:
  >
  > - Filter co ban dat ngay tren bang: search + 2-4 select quan trong + nut `Tim`.
  > - Filter nang cao dat trong `<details>` voi label ngan, vi du: `Lop`, `Mon`, `Giao vien`, `Ky`, `Ngon ngu`, `Tu ngay`, `Den ngay`.
  > - Nut `Xoa loc` hien khi co query param ngoai `page`.
  > - Cac filter dang active hien thanh badge nho ben duoi form de admin nhin nhanh.
  > - Select/input dung class `form-input`, `form-select`; action dung `btn`, `btn-primary`, `btn-ghost`.
  > - Tren mobile filter xep 1 cot; desktop dung grid/flex wrap, khong de input tran bang.
  > - CSV dropdown phai lay cung query string hien tai, khong viet tay tung param khi filter bat dau nhieu.

## 1. Kien truc filter dung chung

- [x] Tao helper parse GET an toan: `get_int_param`, `get_bool_param`, `get_date_param`, `get_choice_param`.
  > Ghi chu:
  >
  > Da them trong `apps/administation/utils.py`. Hien da dung `get_choice_param` cho status mon/lop va `get_int_param` cho `min_warnings` o trang su kien thi.

- [x] Tao helper build query string de pagination/export giu day du filter.
  > Ghi chu:
  >
  > Da them `build_query_string()` va `admin_filter_context()` trong `apps/administation/utils.py`.
  > Cac context dung chung hien co: `page_query_string`, `approval_page_query_string`, `csv_query_string`.
  > Da noi vao pagination/CSV cua user, subject, classroom, activity logs, exam events.

- [x] Tao helper context option dung chung:
  danh sach giao vien, lop hoc, mon hoc, ky hoc, ngon ngu, trang thai.
  > Ghi chu:
  >
  > Da them `admin_filter_options()` tra ve `filter_options`: teachers, students, admins, classrooms, subjects, semesters, languages, profile_statuses, roles.
  > Chua hien het option ra UI o phase 1; phase sau se dung de them select nang cao.

- [x] Tao partial template filter neu can:
  `templates/administration/partials/_filter_field.html` hoac giu inline neu don gian.
  > Ghi chu:
  >
  > Da tao `templates/administration/partials/filter_status.html` de hien badge filter dang active va nut xoa loc.

- [x] Them nut `Xoa loc` tren tat ca trang co filter.
  > Ghi chu:
  >
  > Partial `filter_status.html` hien nut `Xoa loc` khi co filter active. Da include vao user/teacher/student, subject, classroom, languages, sandboxes, settings, activity logs, exam events.

- [x] Them hien thi "Dang loc theo..." bang badge de admin biet minh dang xem tap du lieu nao.
  > Ghi chu:
  >
  > Da them `active_filter_badges()` va badge `Dang loc` cho cac trang filter chinh. Smoke test xac nhan route co query deu render badge.

- [x] Dam bao filter khong lam mat bulk selected state sau khi submit.
  > Ghi chu:
  >
  > Bulk selection van chi nam trong form POST va khong dua vao GET. Pagination/CSV nay dung `page_query_string`/`csv_query_string`, khong chen checkbox state vao query string. Cac nut bulk van chi tac dong record duoc tick.

## 2. Quan ly nguoi dung / giao vien / hoc sinh

- [x] Them filter `Vai tro`: all, student, teacher, admin, staff, superuser.
  > Ghi chu:
  >
  > Da them vao `user_management.html` va backend `_apply_user_filters()`. `staff` loc `is_staff=True`, `superuser` loc `is_superuser=True`.

- [x] Them filter `Trang thai tai khoan`: active, inactive.
  > Ghi chu:
  >
  > Da co san va da dua vao helper chung de CSV/pagination/badge cung nhan.

- [x] Them filter `Trang thai profile`: approved, pending, rejected, inactive.
  > Ghi chu:
  >
  > Da them `profile_status` vao bo loc nang cao va queryset `profiles__status`.

- [x] Them filter `Co lop dang day` cho giao vien.
  > Ghi chu:
  >
  > Da them `has_teaching_classes=yes/no`, loc theo quan he reverse `classrooms`.

- [x] Them filter `Dang tham gia lop` cho hoc sinh.
  > Ghi chu:
  >
  > Da them `has_joined_class=yes/no`, loc theo `ClassroomMembers.status='approved'`.

- [x] Them filter theo `classroom_id`: hoc sinh thuoc lop A, giao vien day lop A.
  > Ghi chu:
  >
  > Da them select lop. Neu role la teacher thi loc `classrooms__id`; role student thi loc `classroommembers__classroom_id`; role all thi dung OR ca hai.

- [x] Them filter theo `subject_id`: hoc sinh co hoc mon X, giao vien co lop gan mon X.
  > Ghi chu:
  >
  > Da them select mon. Teacher loc qua `classrooms__classroom_subject_links`; student loc qua `classroommembers__classroom__classroom_subject_links`.

- [x] Them filter theo `last_login`: chua dang nhap, 7 ngay, 30 ngay, 90 ngay.
  > Ghi chu:
  >
  > Da them `last_login=never/7d/30d/90d`. Cac moc ngay la "co dang nhap trong N ngay gan day".

- [x] Them filter theo `date_joined_from` / `date_joined_to`.
  > Ghi chu:
  >
  > Da them input date va loc theo `date_joined__date`.

- [x] Them filter `Co bai nop`: co/khong, va `submission_status`.
  > Ghi chu:
  >
  > Da them `has_submissions=yes/no` va `submission_status` lay option distinct tu `Submissions.status`.

- [x] Cap nhat CSV user/teacher/student de nhan cac filter moi.
  > Ghi chu:
  >
  > `user_export_view` hien dung chung `_user_filter_values()` + `_apply_user_filters()`, nen CSV contacts/audit/full cung nhan role, profile status, class, subject, last_login, date range, submission filter.

- [x] Test route:
  `/administration/users/`, `/administration/teachers/`, `/administration/students/`.
  > Ghi chu:
  >
  > Da smoke test cac URL:
  > `/administration/users/?role=staff&status=active`,
  > `/administration/users/?role=superuser`,
  > `/administration/users/?profile_status=approved&last_login=never`,
  > `/administration/users/?classroom_id=1`,
  > `/administration/users/?subject_id=1`,
  > `/administration/users/?has_submissions=yes&submission_status=finished`,
  > `/administration/teachers/?classroom_id=1&subject_id=1&has_teaching_classes=yes`,
  > `/administration/students/?classroom_id=1&subject_id=1&has_joined_class=yes`.
  > Tat ca tra ve HTTP 200. CSV audit/contacts/full voi filter moi cung tra ve HTTP 200.

## 3. Duyet giao vien trong trang giao vien

- [x] Them filter don dang ky theo `status`: pending, approved, rejected, all.
  > Ghi chu: Da them select `approval_status` va cac chip trang thai trong block duyet giao vien. Link chip giu query hien tai va chi doi trang thai don.

- [x] Them filter don dang ky theo `institution`.
  > Ghi chu: Da them input `approval_institution`, loc bang `institution__icontains`.

- [x] Them filter don dang ky theo ngay gui: from/to.
  > Ghi chu: Da them `approval_created_from` / `approval_created_to`, parse bang `get_date_param()` va loc tren `created_at__date`.

- [x] Them filter don dang ky theo nguoi review.
  > Ghi chu: Da them select `approval_reviewed_by`, options lay tu admin/user da tung review don giao vien.

- [x] Giu filter don dang ky doc lap voi filter danh sach giao vien.
  > Ghi chu: Filter don dung prefix `approval_*`; form giao vien va form don co hidden fields de giu trang thai cua nhau nhung queryset xu ly tach rieng.

- [x] Test pagination cua block don dang ky khong lam mat filter danh sach giao vien.
  > Ghi chu: `approval_page_query_string` giu query cua danh sach giao vien va cac filter don, chi thay `approval_page`.

## 4. Quan ly mon hoc

- [x] Them filter `classroom_id`: mon hoc thuoc lop A.
  > Ghi chu: Da them select lop trong bo loc nang cao, loc qua `classroom_links__classroom_id` va chi tinh link active.

- [x] Them filter `teacher_id`: mon do giao vien A tao hoac dang day trong lop cua giao vien A.
  > Ghi chu: Da loc bang OR `created_by_id` hoac lop dang gan mon co `classroom.teacher_id`.

- [x] Them filter `semester_id`: mon duoc gan trong ky hoc X.
  > Ghi chu: Da loc qua `classroom_links__semester_id`, giu logic mon co the thuoc nhieu lop/ky.

- [x] Them filter `language_id`: mon hoc dung ngon ngu Python/C++/Java...
  > Ghi chu: Da loc qua quan he M2M `Subjects.languages`.

- [x] Them filter `status`: pending, approved, rejected, all.
  > Ghi chu: Filter cu duoc giu lai, cac tab status nay giu them query filter nang cao khi bam doi trang thai.

- [x] Them filter `is_active`: active/inactive/all.
  > Ghi chu: Da them filter hien thi: dang bat / da an / tat ca.

- [x] Them filter `has_assignments`: co/chua co bai tap.
  > Ghi chu: Da annotate `assignment_count` va loc `gt 0` hoac `= 0`.

- [x] Them filter `has_exams`: co/chua co bai thi.
  > Ghi chu: Da annotate `exam_count` tu assignments co `is_exam=True`.

- [x] Them filter `sandbox_status`: ngon ngu da co sandbox / thieu sandbox.
  > Ghi chu: Da loc mon co it nhat mot ngon ngu co sandbox active (`ready`) hoac co ngon ngu thieu sandbox/chua khai bao ngon ngu (`missing`).

- [x] Them filter `created_from` / `created_to`.
  > Ghi chu: Da them input date, parse an toan bang `get_date_param()`.

- [x] Them count phu hop sau filter:
  so lop, so bai tap, so bai thi, so ngon ngu.
  > Ghi chu: Da annotate `classroom_count`, `assignment_count`, `exam_count`, `language_count` va hien trong cot "Dung trong lop".

- [x] Cap nhat CSV `Danh sach mon` va `Gan lop/mon/ky` nhan tat ca filter moi.
  > Ghi chu: CSV dung chung `_subject_filter_values()` + `_apply_subject_filters()`. File gan lop/mon/ky loc tiep theo classroom/teacher/semester de khong xuat lech pham vi.

- [x] Test case quan trong:
  loc mon theo lop A, loc mon theo ngon ngu Python, loc mon thieu sandbox.
  > Ghi chu: Da smoke test cac route filter mon theo lop, giao vien, ky, ngon ngu, status, active, co bai tap, co bai thi, thieu sandbox, khoang ngay tao va 2 CSV. Tat ca HTTP 200.

## 5. Quan ly lop hoc

- [x] Them filter `subject_id`: lop nao co mon ABC.
  > Ghi chu: Da them select mon trong bo loc nang cao, loc qua `classroom_subject_links__subject_id` va chi tinh link active.

- [x] Them filter `teacher_id`: lop cua giao vien A.
  > Ghi chu: Da them select giao vien, loc truc tiep `teacher_id`.

- [x] Them filter `semester_id`: lop co mon trong ky hoc X.
  > Ghi chu: Da loc qua `classroom_subject_links__semester_id`, phu hop voi quan he lop-mon-ky.

- [x] Them filter `status`: pending, approved, rejected, all.
  > Ghi chu: Da tach trang thai duyet rieng voi trang thai active. Tab status giu query filter hien tai va reset `is_active=all`.

- [x] Them filter `is_active`: active/inactive/all.
  > Ghi chu: Da them select hoat dong trong bo loc nang cao va tab nhanh Hoat dong/Vo hieu.

- [x] Them filter `member_count_min` / `member_count_max`.
  > Ghi chu: Da annotate `member_count` voi thanh vien approved va loc theo nguong min/max.

- [x] Them filter `capacity_status`: con cho, day lop, vuot gioi han.
  > Ghi chu: Da so sanh `member_count` voi `max_students` bang `F()`.

- [x] Them filter `has_subjects`: co/chua co mon.
  > Ghi chu: Da annotate `subject_count` va loc co/chua co mon active.

- [x] Them filter `has_assignments`: co/chua co bai tap.
  > Ghi chu: Da annotate `assignment_count` va loc co/chua co bai tap.

- [x] Them filter `has_exams`: co/chua co bai thi.
  > Ghi chu: Da annotate `exam_assignment_count` tu assignments co `is_exam=True`.

- [x] Them filter `has_pending_members`: co hoc sinh cho duyet vao lop.
  > Ghi chu: Da annotate `pending_member_count` va loc co/khong co hoc sinh cho duyet.

- [x] Them filter `created_from` / `created_to`.
  > Ghi chu: Da them input date va parse an toan bang `get_date_param()`.

- [x] Cap nhat CSV `Danh sach lop` va `Thanh vien theo lop` nhan filter moi.
  > Ghi chu: CSV dung chung `_classroom_filter_values()` + `_apply_classroom_filters()`. File danh sach lop them cot bai thi, file thanh vien chi xuat thanh vien thuoc cac lop da loc.

- [x] Test case quan trong:
  loc lop theo mon ABC, loc lop cua giao vien A, loc lop co bai thi.
  > Ghi chu: Da smoke test loc theo mon, giao vien, ky, status + active, si so min/max, suc chua, co mon, co bai tap, co bai thi, co HS cho duyet, khoang ngay tao va 2 CSV. Tat ca HTTP 200.

## 6. Ngon ngu lap trinh

- [x] Them filter `is_active`: active/inactive/all.
  > Ghi chu: Da them select trang thai trong bo loc nang cao cua trang ngon ngu.

- [x] Them filter `has_sandbox`: co sandbox active / thieu sandbox.
  > Ghi chu: Da loc bang danh sach `SandboxConfigs` active theo `language`.

- [x] Them filter `used_by_subject`: co mon hoc dung / chua duoc dung.
  > Ghi chu: Da annotate `subject_count` tu quan he M2M `Subjects.languages` va loc co/chua co mon dung.

- [x] Them filter `used_by_assignment`: co bai tap/bai thi dang cho phep ngon ngu nay.
  > Ghi chu: Da doc `Assignments.allowed_languages`, flatten danh sach ngon ngu dang duoc bai tap/bai thi cho phep va loc theo `ProgrammingLanguages.name`.

- [x] Them filter theo file extension.
  > Ghi chu: Da them select `extension` tu cac `file_extension` dang co trong DB.

- [x] Them sap xep theo so mon dang dung, ten hien thi, ngay tao.
  > Ghi chu: Da them `sort=subject_count|display_name|created_at`; mac dinh sap xep theo ten hien thi.

- [x] Test: loc ngon ngu active nhung thieu sandbox.
  > Ghi chu: Da smoke test `/administration/languages/?is_active=active&has_sandbox=no` va cac filter/sort lien quan. Tat ca HTTP 200.

## 7. Cau hinh sandbox

- [x] Them filter `language`: Python/C++/Java...
  > Ghi chu: Da them select ngon ngu gom ca `ProgrammingLanguages` va cac sandbox language chua khai bao.

- [x] Them filter `is_active`: active/inactive/all.
  > Ghi chu: Da them select Active/Inactive/Tat ca trong bo loc nang cao.

- [x] Them filter `config_status`: hop le / can kiem tra.
  > Ghi chu: `valid` yeu cau docker image co gia tri, timeout/memory/cpu > 0 va language da khai bao; `needs_review` la cac cau hinh con lai.

- [x] Them filter `language_registered`: co trong `ProgrammingLanguages` / chua co.
  > Ghi chu: Da loc theo `SandboxConfigs.language` co/khong nam trong `ProgrammingLanguages.name`.

- [x] Them filter `used_by_assignments`: dang duoc bai tap dung / chua duoc dung.
  > Ghi chu: Da doc `Assignments.allowed_languages`, dem so bai dang cho phep tung sandbox language va loc co/chua co bai dung.

- [x] Them filter theo nguong timeout/memory/cpu.
  > Ghi chu: Da them `timeout_min/max`, `memory_min/max`, `cpu_min/max`; parse so an toan truoc khi filter.

- [x] Test: loc sandbox active nhung ngon ngu chua khai bao.
  > Ghi chu: Da smoke test `/administration/sandboxes/?is_active=active&language_registered=no` va cac filter sandbox lien quan. Tat ca HTTP 200.

## 8. Cai dat he thong

- [x] Giu filter category hien co, them filter `type`: bool, int, float, str, json.
  > Ghi chu: Da giu select category, them select `type` va loc theo kieu JSON/Python cua `setting_value`; schema missing cung loc theo type du kien.

- [x] Them filter `critical`: setting quan trong / setting thuong.
  > Ghi chu: Da danh dau setting quan trong theo prefix `exam.`, `sandbox.`, `uploads.` va hien badge Quan trong/Thuong.

- [x] Them filter `missing`: setting chua tao nhung schema co dinh nghia.
  > Ghi chu: Da them `missing=yes/no/all`; `missing=yes` chi tap trung vao cac schema key chua co record DB.

- [x] Them filter `updated_by`: admin da sua setting.
  > Ghi chu: Da them select nguoi cap nhat tu cac `SystemSettings.updated_by` dang co.

- [x] Them filter `updated_from` / `updated_to`.
  > Ghi chu: Da them input date va loc theo `updated_at__date`.

- [x] Test: loc setting exam, setting thieu, setting vua sua.
  > Ghi chu: Da smoke test category exam, type bool/int, critical yes/no, missing yes/no, updated_by va updated_from/to. Tat ca HTTP 200.

## 9. Activity Logs

- [x] Nang cap `resource_type` tu input text thanh select goi y cac loai pho bien:
  accounts, classrooms, subjects, assignments, submissions, system_settings, sandbox_configs.
  > Ghi chu: Da doi `resource_type` thanh select, gom cac loai pho bien va cac resource type dang co trong DB.

- [x] Them filter `user_id` bang select/datalist admin/user.
  > Ghi chu: Da them select `user_id` tu cac user co activity log; van giu input text username de tim nhanh.

- [x] Them filter `role`: admin, teacher, student, system.
  > Ghi chu: Da loc admin theo profile admin/staff/superuser, teacher/student theo profile, system theo log khong co user.

- [x] Them filter `action_group`: login, bulk, approve, reject, create, update, delete, export, sandbox.
  > Ghi chu: Da them mapping keyword theo nhom hanh dong va loc bang `action__icontains`; sandbox gom them `resource_type=sandbox_configs`.

- [x] Them filter `ip_address`.
  > Ghi chu: Da them input IP va loc bang `ip_address__icontains`.

- [x] Them filter `date_from` / `date_to` dang co, kiem tra pagination/export giu param.
  > Ghi chu: Da chuyen parse sang `get_date_param()`, pagination va CSV dung `admin_filter_context()` nen giu query string.

- [x] Them preset nhanh: 24h, 7 ngay, 30 ngay.
  > Ghi chu: Da them chip preset `24h`, `7d`, `30d`; filter theo `created_at >= now - preset`.

- [x] Cap nhat CSV activity logs nhan tat ca filter moi.
  > Ghi chu: CSV full/compact dung chung `_filtered_activity_logs_from_request()` nen nhan day du filter moi.

- [x] Test: loc log theo resource_type=subjects va resource_id.
  > Ghi chu: Da smoke test `/administration/logs/?resource_type=subjects&resource_id=1` va CSV tuong ung. Tat ca HTTP 200.

## 10. Su kien thi

- [x] Them filter `assignment_id`: bai thi cu the.
  > Ghi chu: Da them select bai thi tu `Assignments(is_exam=True)` va loc event/session theo `assignment_id`.

- [x] Them filter `classroom_id`: bai thi thuoc lop A.
  > Ghi chu: Da loc qua `assignment__classroom_id`.

- [x] Them filter `subject_id`: bai thi thuoc mon ABC.
  > Ghi chu: Da loc qua `assignment__classroom_subject__subject_id`, dung logic bai thi gan theo lop-mon-ky.

- [x] Them filter `teacher_id`: bai thi cua giao vien A.
  > Ghi chu: Da loc bang OR `assignment.created_by_id` hoac `assignment.classroom.teacher_id`.

- [x] Them filter `student_id`: hoc sinh cu the.
  > Ghi chu: Da them select hoc sinh va loc theo `ExamSessions.student_id`.

- [x] Giu filter `event_type`, `status`, `min_warnings`, `date_from`, `date_to`.
  > Ghi chu: Da giu cac filter cu, chuyen parse `date_from/date_to` qua `get_date_param()` va dung chung helper cho events/sessions.

- [x] Them filter `has_final_submission`: da nop / chua nop.
  > Ghi chu: Da loc theo `final_submission__isnull`.

- [x] Them filter `session_duration`: qua thoi gian, con dang lam, bi force submit.
  > Ghi chu: `over_time` = running va `ends_at < now`; `running` = running con han/khong co ends_at; `force_submitted` = auto_submitted hoac expired.

- [x] Cap nhat CSV exam events neu co export.
  > Ghi chu: Da them route `/administration/exam-events/export/` voi 2 loai CSV: su kien va phien thi; ca hai dung chung bo filter moi.

- [x] Test: loc su kien thi theo lop + mon + min_warnings.
  > Ghi chu: Da smoke test `/administration/exam-events/?classroom_id=1&subject_id=1&min_warnings=1` va CSV tuong ung. Tat ca HTTP 200.

## 11. Sandbox Monitor

- [x] Them filter `submission_status`: pending, running, error, finished.
  > Ghi chu: Da them select trang thai bai nop cho Sandbox Monitor, mac dinh `all`.

- [x] Them filter `language`.
  > Ghi chu: Da them select ngon ngu tu cac submission language dang co.

- [x] Them filter `assignment_id`.
  > Ghi chu: Da them select bai tap/bai thi va loc theo `assignment_id`.

- [x] Them filter `classroom_id`.
  > Ghi chu: Da loc qua `assignment__classroom_id`.

- [x] Them filter `subject_id`.
  > Ghi chu: Da loc qua `assignment__classroom_subject__subject_id`, dung logic lop-mon-ky.

- [x] Them filter `age_min_minutes`: submission treo hon N phut.
  > Ghi chu: Da loc `submitted_at < now - N phut`; zombie detection van dung nguong he thong `sandbox.zombie_threshold_minutes`.

- [x] Them filter `student_id`.
  > Ghi chu: Da them select hoc sinh va loc theo `student_id`.

- [x] Dam bao action kill/requeue giu lai filter sau khi redirect.
  > Ghi chu: Form Kill/Requeue gui hidden `query_string`; view redirect ve `/administration/sandbox-monitor/?...` dung bo loc cu.

- [x] Test: loc zombie Python trong lop A.
  > Ghi chu: Da smoke test `/administration/sandbox-monitor/?language=python&classroom_id=1` cung cac filter status/assignment/subject/age/student. Tat ca HTTP 200.

## 12. Server Metrics va Analytics

- [x] Server Metrics: them filter khoang thoi gian: 1h, 6h, 24h, 7 ngay.
  > Ghi chu: Da them select `range=1h|6h|24h|7d`, chart/table metrics dung queryset theo range da loc.

- [x] Server Metrics: them filter nguong CPU/memory/queue.
  > Ghi chu: Da them `cpu_min`, `memory_min`, `queue_min` va filter truc tiep tren `ServerMetrics`.

- [x] Analytics: them `date_from` / `date_to`.
  > Ghi chu: Da them filter ngay, mac dinh 30 ngay gan nhat; charts submissions va user growth dung khoang ngay nay.

- [x] Analytics: them filter theo lop, mon, giao vien, ngon ngu.
  > Ghi chu: Da them filter `classroom_id`, `subject_id`, `teacher_id`, `language`; submissions/top lop/chart ngay-gio dung chung queryset da loc.

- [x] Analytics: dam bao chart thay doi theo filter va co empty state.
  > Ghi chu: Chart hourly/daily/top lop dung queryset filter; khi khong co du lieu khop loc se hien empty state va khong khoi tao canvas chart rong.

## 13. UX nang cao cho filter

- [x] Dung layout `Bo loc co ban` + `Bo loc nang cao` bang `<details>` de khong lam trang dai.
  > Ghi chu: Da chuan hoa cac form lon thanh `admin-filter-panel` + `admin-filter-section`: logs, exam events, sandbox monitor, metrics, analytics; cac trang user/mon/lop/ngon ngu/sandbox/settings dung chung details nang cao.

- [x] Moi filter select co label ro rang, khong chi placeholder.
  > Ghi chu: Da bo sung label cho cac filter co ban con thieu: user/mon/lop/search, setting category, exam event basic selects, metrics/analytics/logs.

- [x] Voi danh sach dai, dung datalist hoac select co search don gian khong them dependency neu chua can.
  > Ghi chu: Da them JS nhe trong `static/js/main.js`: select trong filter co tu 12 option tro len se hien o search nho de loc option, khong them dependency.

- [x] Them nut `Luu bo loc` cho admin neu can:
  luu query string vao localStorage theo route.
  > Ghi chu: Partial `filter_status.html` co nut `Luu bo loc`; query string duoc luu trong localStorage theo pathname.

- [x] Them nut `Copy link bo loc` de share cho admin khac.
  > Ghi chu: Da them nut `Copy link loc`, dung Clipboard API va fallback input copy.

- [x] Them badge dem ket qua hien tai: "Dang hien thi X / tong Y".
  > Ghi chu: Partial hien `Dang hien thi start-end / tong` voi trang co paginator; cac trang list khong phan trang dung `filter_result_label`.

- [x] Tren mobile, filter khong bi tran ngang; cac select/input xep 1 cot.
  > Ghi chu: Da them CSS responsive cho `.admin-filter-form`, `.admin-filter-status__actions`, select/button full width tren mobile.

## 14. Hieu nang va database

- [x] Kiem tra cac filter can `select_related` / `prefetch_related`.
  > Ghi chu: Cac queryset filter nang da dung `select_related` cho user/assignment/classroom/subject/session; `Subjects` prefetch `languages`; option dropdown chung duoc giam payload bang `.only()`.

- [x] Kiem tra cac annotate count co bi duplicate khi filter nhieu quan he.
  > Ghi chu: Cac count chinh trong user/subject/classroom/classroom-subject/language deu dung `distinct=True`; khong thay count lap do join nhieu quan he.

- [x] Them `distinct()` khi join qua `ClassroomSubjects`, `Assignments`, `Submissions` de tranh lap dong.
  > Ghi chu: Cac filter user, subject, classroom, language, activity logs, exam events/sessions, sandbox monitor deu co `distinct()` sau cac join co nguy co nhan dong.

- [x] Kiem tra index hien co:
  `classroom/status`, `student/status`, `assignment/status`, `event_type/created_at`.
  > Ghi chu: Da co san `cm_classroom_status_idx`, `cm_student_status_idx`, `asg_cls_subject_idx`, `sub_asg_st_status_at_idx`, `exam_asg_status_idx`, `exam_st_status_idx`, `event_type/-created_at`.

- [x] De xuat migration them index neu filter moi cham:
  `Subjects.status`, `Classrooms.status/is_active`, `Assignments.classroom_subject`, `Submissions.language/status`, `ExamSessions.status`.
  > Ghi chu: Da tao va migrate index moi: accounts `0002`, administation `0002`, classrooms `0008`, assignments `0008`, submissions `0005`. Index them cho status/is_active/created_at cua lop-mon, link lop-mon, assignment exam/published, submission language/status, exam session status/ends_at/warnings, activity logs, metrics, settings.

- [x] Test voi data Supabase demo lon: thoi gian response trang < 1s neu co the.
  > Ghi chu: Da smoke test 8 route admin tren Supabase sau migrate, tat ca HTTP 200. Thoi gian do trong Django test client qua DB remote khoang 1.8s-3.1s, chua dat <1s do network/Supabase remote va mot so trang co nhieu dropdown/thong ke; index da apply de giam rui ro cham khi data lon.

## 15. Bao mat va phan quyen

- [x] Tat ca filter admin van qua `@admin_required`.
  > Ghi chu: Da quet 47 route trong `apps/administation/urls.py`, khong co route admin nao thieu decorator. Smoke test student vao `/administration/users/` bi redirect 302 ve `/`.

- [x] Validate moi ID filter: neu khong phai int thi bo qua va hien message nhe.
  > Ghi chu: Da them `_warn_invalid_int_filters()` cho user/teacher/student, mon, lop, settings, logs, exam events, sandbox monitor, analytics. Invalid ID/so am duoc bo qua va hien warning, khong 500.

- [x] Khong cho filter tao raw SQL hoac order_by tuy y tu GET.
  > Ghi chu: Da kiem tra khong co `raw()`, `extra()` hay `order_by()` lay truc tiep tu GET. Cac sort/type dung allowlist qua `get_choice_param()`.

- [x] CSV export phai dung cung queryset da loc, khong export vuot filter admin dang xem.
  > Ghi chu: User/classroom/subject/logs/exam events CSV deu dung chung helper filter voi UI. Da allowlist `type` CSV de type la khong hop le tu quay ve mac dinh an toan.

- [x] Bulk action chi tac dong record dang duoc chon, khong dua vao filter mot cach ngam.
  > Ghi chu: Bulk user/lop/mon chi lay danh sach ID tu POST; da sanitize bang `_selected_int_ids_from_post()`, bo qua ID rac/so am va khong tac dong theo query filter ngam.

## 16. Test va nghiem thu

- [x] Chay `python manage.py check`.
  > Ghi chu: Da chay sau phase 16, ket qua `System check identified no issues`.

- [x] Smoke test tat ca route admin chinh sau khi them filter.
  > Ghi chu: Da smoke test 14 route chinh: dashboard, users, teachers, students, subjects, classrooms, languages, sandboxes, settings, logs, exam-events, sandbox-monitor, metrics, analytics. Tat ca HTTP 200.

- [x] Test filter mon theo lop A.
  > Ghi chu: Da test `/administration/subjects/?classroom_id=25`, HTTP 200.

- [x] Test filter lop theo mon ABC.
  > Ghi chu: Da test `/administration/classrooms/?subject_id=16`, HTTP 200.

- [x] Test filter hoc sinh theo lop va mon.
  > Ghi chu: Da test `/administration/students/?classroom_id=25&subject_id=16`, HTTP 200.

- [x] Test filter giao vien theo lop/mon va don dang ky pending.
  > Ghi chu: Da test `/administration/teachers/?classroom_id=25&subject_id=16&approval_status=pending`, HTTP 200.

- [x] Test filter exam events theo lop + mon + hoc sinh + min_warnings.
  > Ghi chu: Da test `/administration/exam-events/?classroom_id=25&subject_id=17&student_id=4&min_warnings=0`, HTTP 200.

- [x] Test CSV sau filter dung so dong voi UI.
  > Ghi chu: Da doi chieu UI badge va CSV: subjects 2/2, classrooms 1/1, users 2/2, exam_events 27/27.

- [x] Test pagination giu nguyen query string.
  > Ghi chu: Da test `/administration/users/?role=student&classroom_id=25&subject_id=16&page=1`; link pagination giu `role`, `classroom_id`, `subject_id`.

- [x] Test UI mobile/tablet khong tran form.
  > Ghi chu: Venv chua co Playwright/Selenium nen da nghiem thu tinh bang CSS/template scan: 14 template filter dung grid mobile `grid-cols-1`, CSS co rule `max-width: 640px`, khong con candidate thieu `overflow-x-auto`. Da bo sung wrapper `overflow-x-auto` cho bang languages/sandboxes.

## 17. Thu tu trien khai de it rui ro

- [x] Phase 1: helper parse GET + query string + clear filter + active badges.
  > Ghi chu: Da hoan tat o muc 1: `get_int_param/get_date_param/get_choice_param`, `build_query_string`, `admin_filter_context`, badge active filter, nut xoa loc/copy/luu bo loc.

- [x] Phase 2: filter cho `Mon hoc` va CSV mon hoc.
  > Ghi chu: Da hoan tat muc 4: loc lop/giao vien/ky/ngon ngu/status/active/bai tap/bai thi/sandbox/ngay tao; CSV danh sach mon va gan lop-mon-ky dung cung filter.

- [x] Phase 3: filter cho `Lop hoc` va CSV lop hoc.
  > Ghi chu: Da hoan tat muc 5: loc mon/giao vien/ky/status/active/si so/suc chua/noi dung/HS cho duyet/ngay tao; CSV danh sach lop va thanh vien theo lop dung cung filter.

- [x] Phase 4: filter cho `Nguoi dung`, `Giao vien`, `Hoc sinh`.
  > Ghi chu: Da hoan tat muc 2-3: user/teacher/student ke thua filter, CSV va bulk action; duyet giao vien gop vao trang giao vien va co filter rieng doc lap.

- [x] Phase 5: filter cho `Exam Events` va `Sandbox Monitor`.
  > Ghi chu: Da hoan tat muc 10-11: exam events loc bai thi/lop/mon/giao vien/hoc sinh/event/status/canh bao/phien thi; sandbox monitor loc status/language/assignment/lop/mon/student/age va giu query khi kill/requeue.

- [x] Phase 6: filter cho `Ngon ngu`, `Sandbox Config`, `Settings`, `Logs`.
  > Ghi chu: Da hoan tat muc 6-9: ngon ngu, sandbox config, cai dat he thong, activity logs deu co filter nang cao, badge, xoa loc, CSV logs dung queryset da loc.

- [x] Phase 7: analytics/metrics filter + toi uu query/index neu can.
  > Ghi chu: Da hoan tat muc 12 va 14: metrics/analytics co filter; da them migration index va apply len DB Supabase, dong thoi toi uu dropdown option bang `.only()`.

- [x] Phase 8: QA full route, CSV, pagination, mobile.
  > Ghi chu: Da hoan tat muc 15-16: admin_required, validate GET ID, allowlist CSV type, sanitize bulk ID; smoke 14 route admin, doi chieu CSV/UI, pagination giu query, scan responsive mobile/tablet.

## 18. Nang cap luu bo loc co ten

- [x] Doi nut `Luu bo loc` hien tai thanh flow dat ten truoc khi luu.
  > Ghi chu: Da doi `js-save-filter` sang flow `promptFilterName()`: goi y ten theo tieu de trang + ngay gio, gioi han 80 ky tu, khong cho ten rong.

- [x] Cho moi route admin luu duoc nhieu bo loc trong localStorage.
  > Ghi chu: Da doi key sang `devlearn.admin.savedFilters.<pathname>` va luu danh sach `{id, name, query, createdAt, updatedAt}`; co migrate tu key cu `devlearn.admin.savedFilter.<pathname>`.

- [x] Them dropdown/menu `Bo loc da luu` tren partial `filter_status.html`.
  > Ghi chu: Da them `admin-saved-filters` dropdown, counter so bo loc, empty state va list render bang JS theo route hien tai.

- [x] Them thao tac `Ap dung`, `Doi ten`, `Ghi de`, `Xoa` cho tung bo loc da luu.
  > Ghi chu: Da them action `apply`, `rename`, `overwrite`, `delete`; ghi de va xoa co confirm, doi ten dung prompt, ap dung dieu huong ve `pathname + query`.

- [x] Hien badge/tom tat query trong danh sach bo loc da luu.
  > Ghi chu: Moi item hien ten, badge `Da luu`, so dieu kien, thoi gian cap nhat, query string dang mono va tooltip bang `title`.

- [x] Dam bao localStorage khong luu du lieu nhay cam.
  > Ghi chu: JS chi luu `query` tu `window.location.search`, khong doc/lua form POST, token, cookie, CSRF hay password.

- [x] Dam bao UI mobile/tablet cua dropdown bo loc da luu khong tran ngang.
  > Ghi chu: Da them CSS mobile: dropdown full width, menu nam trong viewport, action xep cot tren man hinh nho.

- [x] Test luu nhieu bo loc tren cung mot trang admin.
  > Ghi chu: Da kiem tra logic JS luu danh sach array toi da 30 item theo route va `node --check static/js/main.js` pass.

- [x] Test bo loc da luu tach rieng theo route.
  > Ghi chu: Storage key gan theo `window.location.pathname`, nen `/administration/users/` va `/administration/subjects/` doc hai danh sach khac nhau.

- [x] Test ap dung, doi ten, ghi de, xoa bo loc.
  > Ghi chu: Da them va syntax-check cac handler `applySavedFilter`, `renameSavedFilter`, `overwriteSavedFilter`, `deleteSavedFilter`; route admin users render du dropdown/action hook.

- [x] Test refresh trang van con danh sach bo loc da luu.
  > Ghi chu: `renderSavedFilters()` doc lai localStorage o `DOMContentLoaded`, nen refresh van render danh sach da luu.
