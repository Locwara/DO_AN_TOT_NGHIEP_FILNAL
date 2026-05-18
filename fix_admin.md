# Fix Admin Bulk Actions & Quan Ly Hang Loat

> Muc tieu: lam cac trang admin co thao tac chon nhieu/bulk action ro rang, linh hoat theo dung nghiep vu tung trang, khong lam admin vo tinh thao tac nguy hiem. Tat ca UI phai bam `devlearn-design-system.md`: dung token primary/success/warning/danger, `btn`, `form-input`, `form-select`, `stat-card`, `course-card`/card border primary, icon Material Symbols va mobile khong tran bang.

---

## 0. Audit Hien Trang

- [ ] Kiem tra lai toan bo route admin trong `apps/administation/urls.py`.

  > Ghi chu test:

- [ ] Lap danh sach trang list/table co kha nang can bulk action: users, teacher approvals, teacher management, classrooms, subjects, languages, sandboxes, system settings, activity logs, exam events, sandbox monitor.

  > Ghi chu test:

- [ ] Xac nhan trang nao da co checkbox/bulk action:
  - `user_management.html`: co checkbox, bulk activate/deactivate/delete.
  - `subject_management.html`: co checkbox, approve/reject/activate/deactivate.
  - `classroom_management.html`: co checkbox, approve/reject/activate/deactivate.

  > Ghi chu test:

- [ ] Xac nhan trang nao chua co bulk action hoac chua du linh hoat:
  - `teacher_approvals.html`: chua co checkbox, chua duyet/tu choi nhieu.
  - `teacher_management.html`: chua co checkbox, chua khoa/mo khoa nhieu giao vien.
  - `languages.html`: chua co checkbox, chua kich hoat/tat/xoa nhieu ngon ngu.
  - `sandboxes.html`: chua co checkbox, chua bat/tat/xoa nhieu sandbox config.
  - `system_settings.html`: chua co checkbox, chua toggle/xoa nhieu setting hop le.
  - `activity_logs.html`: read-only, nen co export selected / delete old logs theo policy neu can.
  - `exam_events.html`: read-only, nen co thao tac review/clear warning cho session neu model cho phep.
  - `sandbox_monitor.html`: co thao tac tung zombie, chua co kill/requeue nhieu.

  > Ghi chu test:

- [ ] Kiem tra cac bulk action hien co co log `ActivityLogs`, thong bao `messages`, va chan thao tac nguy hiem chua.

  > Ghi chu test:

---

## 1. Admin Bulk UX Dung Chung

- [ ] Tao pattern UI thong nhat cho bulk toolbar tren cac trang list:
  - checkbox chon tung dong
  - checkbox `select-all`
  - dem so item dang chon
  - select `action`
  - nut `Ap dung`
  - nut nhanh neu hop ly: `Duyet tat ca dang loc`, `Tu choi tat ca dang loc`, `Export da chon`

  > Ghi chu test:

- [ ] Them JS dung chung cho admin bulk:
  - select all chi tac dong checkbox trong form hien tai
  - cap nhat selected count
  - disable nut ap dung khi chua chon item/action
  - confirm message tuy theo action nguy hiem
  - khong dung duplicate global `const selectAll` gay xung dot khi nhieu table tren cung trang

  > Ghi chu test:

- [ ] Dat helper JS vao file rieng neu phu hop, vi du `static/js/admin_bulk.js`, va include trong `base_admin.html`.

  > Ghi chu test:

- [ ] Chuan hoa ten field checkbox:
  - users: `user_ids`
  - teacher registrations: `registration_ids`
  - teachers: `teacher_ids`
  - classrooms: `classroom_ids`
  - subjects: `subject_ids`
  - languages: `language_ids`
  - sandboxes: `sandbox_ids`
  - settings: `setting_ids`
  - logs: `log_ids`
  - exam sessions/events: `session_ids` / `event_ids`
  - submissions queue: `submission_ids`

  > Ghi chu test:

- [ ] Chuan hoa backend bulk response:
  - action khong hop le -> `messages.error`
  - khong chon item -> `messages.error`
  - thanh cong -> `messages.success` co so luong
  - mot phan bi bo qua -> `messages.warning` co ly do
  - moi action quan trong ghi `ActivityLogs`

  > Ghi chu test:

- [ ] Sau POST, redirect giu lai filter/page neu can bang hidden `next` hoac querystring an toan.

  > Ghi chu test:

---

## 2. Quan Ly Nguoi Dung

- [ ] Review `user_bulk_action_view()` hien co:
  - da activate/deactivate/delete soft
  - da chan khoa tai khoan dang login
  - da chan khoa superuser active cuoi cung
  - da sync `Profiles.status`

  > Ghi chu test:

- [ ] Sua UI `user_management.html`:
  - them selected count
  - disable `Ap dung` khi chua chon action/item
  - doi label `Xoa` thanh `Xoa mem / vo hieu hoa` de tranh hieu nham
  - them confirm rieng cho deactivate/delete
  - them nut nhanh `Kich hoat da chon`, `Khoa da chon` neu UX gon hon select

  > Ghi chu test:

- [ ] Bo sung action hop ly neu can:
  - `set_role_student`
  - `set_role_teacher`
  - `set_role_admin` chi cho superuser hoac admin du quyen

  > Ghi chu test:

- [ ] Them rule an toan role:
  - khong cho admin thuong tu cap/quy cap admin neu policy khong cho phep
  - khong ha role superuser qua bulk
  - khong khoa/xoa chinh minh

  > Ghi chu test:

- [ ] Them test cho bulk user:
  - activate nhieu user
  - deactivate nhieu user
  - delete soft nhieu user
  - khong khoa chinh minh
  - khong khoa superuser cuoi cung
  - sync profile status dung

  > Ghi chu test:

---

## 3. Duyet Giao Vien

- [ ] Them route bulk moi, vi du `teacher-approvals/bulk/`.

  > Ghi chu test:

- [ ] Tao `teacher_registration_bulk_action_view()`:
  - `approve`: chi xu ly registration `pending`
  - `reject`: chi xu ly registration `pending`
  - `approve_filtered_pending`: duyet tat ca pending dang theo filter/search neu can
  - `reject_filtered_pending`: tu choi tat ca pending dang theo filter/search neu can

  > Ghi chu test:

- [ ] Khi approve:
  - set `TeacherRegistrations.status='approved'`
  - set `reviewed_by`, `reviewed_at`
  - set profile role `teacher`, status `approved`
  - notify user
  - log admin action

  > Ghi chu test:

- [ ] Khi reject:
  - set `TeacherRegistrations.status='rejected'`
  - set `reviewed_by`, `reviewed_at`
  - profile status `rejected` neu phu hop
  - notify user
  - log admin action

  > Ghi chu test:

- [ ] Sua `teacher_approvals.html`:
  - them checkbox tung dong
  - toolbar duyet/tu choi da chon
  - chi cho chon dong pending hoac disable checkbox dong da reviewed
  - hien selected count
  - confirm khi tu choi nhieu don

  > Ghi chu test:

- [ ] Them test:
  - bulk approve 2 pending
  - bulk reject 2 pending
  - bulk bo qua approved/rejected cu
  - profile role/status cap nhat dung
  - notification/log duoc tao

  > Ghi chu test:

---

## 4. Quan Ly Giao Vien Da Duyet

- [ ] Them route bulk cho `teachers/`, vi du `teachers/bulk/`.

  > Ghi chu test:

- [ ] Tao `teacher_bulk_action_view()` cho tai khoan giao vien:
  - `activate`
  - `deactivate`
  - `reset_profile_status_approved`
  - co the `export_selected`

  > Ghi chu test:

- [ ] Neu deactivate giao vien:
  - set `User.is_active=False`
  - set `Profiles.status='inactive'`
  - can nhac co/khong deactivate lop cua giao vien: mac dinh KHONG tu dong khoa lop, chi can hien canh bao

  > Ghi chu test:

- [ ] Sua `teacher_management.html`:
  - them checkbox
  - them bulk toolbar
  - them cot thao tac: xem chi tiet user, sua user, khoa/mo khoa nhanh
  - them export CSV neu can

  > Ghi chu test:

- [ ] Them test:
  - khoa/mo khoa nhieu giao vien
  - khong anh huong user role khac
  - profile status sync

  > Ghi chu test:

---

## 5. Quan Ly Lop Hoc

- [ ] Review `classroom_bulk_action_view()` hien co:
  - approve/reject pending
  - activate/deactivate
  - notify teacher khi review

  > Ghi chu test:

- [ ] Fix action `approve_all` / `reject_all` tren UI neu hien tai dung querystring `?action=approve_all` nhung backend doc `request.POST.get('action')`.

  > Ghi chu test:

- [ ] Sua `classroom_management.html`:
  - them selected count
  - nut `Duyet da chon`, `Tu choi da chon`
  - nut `Kich hoat`, `Tam an/khoa`
  - chi enable approve/reject cho lop pending, hoac backend bo qua lop khong pending va bao warning

  > Ghi chu test:

- [ ] Them action hop ly:
  - `archive/deactivate`: an lop khoi student discover/list active
  - `activate`: mo lai lop approved
  - khong hard delete lop vi co member/assignment/submission

  > Ghi chu test:

- [ ] Ghi `ActivityLogs` cho bulk approve/reject/activate/deactivate.

  > Ghi chu test:

- [ ] Them test:
  - bulk approve pending class
  - bulk reject pending class
  - deactivate class khong xoa data
  - notification teacher duoc tao

  > Ghi chu test:

---

## 6. Quan Ly Mon Hoc

- [ ] Review `subject_bulk_action_view()` hien co:
  - approve/reject pending
  - activate/deactivate
  - notify creator khi review

  > Ghi chu test:

- [ ] Fix action `approve_all` / `reject_all` tren UI neu hien tai dung querystring thay vi POST `action`.

  > Ghi chu test:

- [ ] Sua `subject_management.html`:
  - selected count
  - action label ro: `Duyet da chon`, `Tu choi da chon`, `Kich hoat`, `Tam an`
  - hien cot active rieng neu can, vi status approve/reject khac voi is_active
  - disable checkbox neu subject dang duoc dung trong lop va action nguy hiem can confirm

  > Ghi chu test:

- [ ] Them rule:
  - deactivate subject khong xoa `ClassroomSubjects`, chi an/chan tao bai moi neu logic can
  - reject pending subject set `is_active=False`
  - approve set `is_active=True`

  > Ghi chu test:

- [ ] Ghi `ActivityLogs` cho bulk subject.

  > Ghi chu test:

- [ ] Them test:
  - bulk approve/reject subject pending
  - activate/deactivate nhieu subject
  - notification creator duoc tao

  > Ghi chu test:

---

## 7. Ngon Ngu Lap Trinh

- [ ] Them route bulk `languages/bulk/`.

  > Ghi chu test:

- [ ] Tao `language_bulk_action_view()`:
  - `activate`
  - `deactivate`
  - `delete` chi cho ngon ngu chua duoc subject/assignment/sandbox phu thuoc, hoac doi thanh soft deactivate

  > Ghi chu test:

- [ ] Sua `languages.html`:
  - checkbox tung language
  - selected count
  - bulk toolbar bat/tat/xoa da chon
  - giu toggle tung dong
  - canh bao neu xoa ngon ngu co lien ket

  > Ghi chu test:

- [ ] Them `ActivityLogs` cho create/edit/delete/toggle/bulk.

  > Ghi chu test:

- [ ] Them test:
  - activate/deactivate nhieu language
  - delete language an toan
  - khong xoa neu co dependency quan trong

  > Ghi chu test:

---

## 8. Cau Hinh Sandbox

- [ ] Them route bulk `sandboxes/bulk/`.

  > Ghi chu test:

- [ ] Tao `sandbox_bulk_action_view()`:
  - `activate`
  - `deactivate`
  - `delete`
  - co the `clone_defaults` neu can tao lai config mac dinh

  > Ghi chu test:

- [ ] Sua `sandboxes.html`:
  - checkbox tung sandbox
  - selected count
  - bulk toolbar bat/tat/xoa
  - them toggle tung dong neu can
  - dung `btn`, `badge`, `danger/success` token thay vi mau lech

  > Ghi chu test:

- [ ] Rule an toan:
  - neu deactivate tat ca sandbox active thi hien warning lon
  - delete config active can confirm
  - khong delete config dang duoc queue dang chay neu co phu thuoc logic

  > Ghi chu test:

- [ ] Them `ActivityLogs` cho sandbox bulk.

  > Ghi chu test:

- [ ] Them test:
  - activate/deactivate/delete selected sandboxes
  - canh bao khong con sandbox active

  > Ghi chu test:

---

## 9. Cai Dat He Thong

- [ ] Them route bulk `settings/bulk/`.

  > Ghi chu test:

- [ ] Tao `system_setting_bulk_action_view()`:
  - `toggle_bool`: chi toggle setting co `setting_value` boolean
  - `delete`: xoa selected, nhung chan/xac nhan setting quan trong
  - `export_selected`: export JSON/CSV selected

  > Ghi chu test:

- [ ] Sua `system_settings.html`:
  - checkbox tung setting
  - selected count
  - bulk toolbar toggle/xoa/export
  - badge phan loai bool/int/json
  - confirm khi xoa nhieu setting

  > Ghi chu test:

- [ ] Rule an toan:
  - khong toggle setting khong phai bool
  - khong xoa setting core neu dang nam trong `SYSTEM_SETTING_SCHEMAS` va duoc danh dau required
  - moi update set `updated_by=request.user`

  > Ghi chu test:

- [ ] Them `ActivityLogs` cho setting bulk.

  > Ghi chu test:

- [ ] Them test:
  - toggle nhieu boolean settings
  - skip non-boolean khi toggle
  - delete selected settings
  - updated_by dung admin

  > Ghi chu test:

---

## 10. Nhat Ky Hoat Dong

- [ ] Quyet dinh policy: activity logs mac dinh read-only, khong nen xoa tuy tien.

  > Ghi chu test:

- [ ] Them thao tac an toan:
  - export CSV theo filter hien co da co
  - export selected neu them checkbox
  - delete old logs > N ngay chi cho superuser hoac co confirm manh

  > Ghi chu test:

- [ ] Neu them delete old logs:
  - route `logs/bulk/` hoac `logs/delete-old/`
  - action `delete_older_than_30d`, `delete_older_than_90d`
  - khong xoa log trong 30 ngay gan nhat
  - ghi log truoc/sau khi xoa voi count

  > Ghi chu test:

- [ ] Sua `activity_logs.html`:
  - neu co checkbox thi selected count + export selected
  - giu table read-only, khong lam admin nham la co the sua log

  > Ghi chu test:

- [ ] Them test:
  - export filter dung
  - delete old logs chi xoa log qua han
  - user khong phai superuser bi chan neu policy yeu cau

  > Ghi chu test:

---

## 11. Su Kien Thi

- [ ] Quyet dinh model review warning:
  - neu chua co field review, them field vao `ExamSessions.metadata` nhu `admin_reviewed_at`, `admin_reviewed_by`, `admin_note`
  - tranh migration neu chua can, metadata du linh hoat

  > Ghi chu test:

- [ ] Them route bulk `exam-events/bulk/`.

  > Ghi chu test:

- [ ] Tao `exam_events_bulk_action_view()`:
  - `mark_sessions_reviewed`: danh dau session da xem
  - `clear_review_flag`: bo danh dau reviewed
  - `export_selected_events`
  - `cancel_running_sessions` neu can va phai confirm manh

  > Ghi chu test:

- [ ] Sua `exam_events.html`:
  - checkbox cho warning sessions
  - checkbox cho events neu can export selected
  - nut `Da xem cac canh bao da chon`
  - hien badge `Da xem/Chua xem`
  - filter `reviewed=0/1`

  > Ghi chu test:

- [ ] Rule an toan:
  - khong xoa event thi, chi mark reviewed/export
  - cancel session chi cho session `running`
  - neu cancel session thi notify student/teacher va log admin action

  > Ghi chu test:

- [ ] Them test:
  - mark reviewed nhieu session
  - filter unreviewed
  - khong xoa event
  - cancel running session neu co lam

  > Ghi chu test:

---

## 12. Sandbox Monitor / Queue

- [ ] Them route bulk queue, vi du `sandbox-monitor/bulk/`.

  > Ghi chu test:

- [ ] Tao `sandbox_monitor_bulk_action_view()`:
  - `requeue_selected`
  - `kill_selected`
  - chi cho submissions status `pending/running`
  - uu tien zombie list, nhung co the chon queue items neu can

  > Ghi chu test:

- [ ] Sua `sandbox_monitor.html`:
  - checkbox trong zombie table
  - selected count
  - bulk `Requeue da chon`, `Kill da chon`
  - confirm manh khi kill nhieu bai nop

  > Ghi chu test:

- [ ] Rule an toan:
  - kill them teacher_comment ro thoi diem/admin
  - requeue xoa details cu va reset score nhu view tung dong hien co
  - notify student cho tung submission
  - log admin action voi danh sach id/count

  > Ghi chu test:

- [ ] Them test:
  - requeue selected zombies
  - kill selected zombies
  - skip submission khong con pending/running

  > Ghi chu test:

---

## 13. Dashboard Admin & Dieu Huong

- [ ] Them quick cards vao dashboard admin cho cac hang cho bulk:
  - teacher registrations pending
  - classroom pending
  - subject pending
  - zombie tasks
  - exam warning unreviewed

  > Ghi chu test:

- [ ] Moi card co CTA vao dung trang voi filter dung, vi du `?status=pending`.

  > Ghi chu test:

- [ ] Sidebar badge cap nhat dung:
  - pending teachers
  - pending classrooms
  - pending subjects
  - zombie/exam warning neu can

  > Ghi chu test:

---

## 14. Design System & Frontend Cleanup

- [ ] Thay cac mau lech `emerald/rose/amber/slate` trong admin pages bang token dung:
  - success -> `success-*`
  - warning -> `warning-*`
  - danger -> `danger-*`
  - primary -> `primary-*`
  - neutral -> `neutral-*`

  > Ghi chu test:

- [ ] Dung component nhat quan:
  - `btn btn-primary`
  - `btn btn-ghost`
  - `btn btn-sm`
  - `form-input`
  - `form-select`
  - `stat-card`
  - card border `border-primary-200`, bg `bg-white`

  > Ghi chu test:

- [ ] Them state mobile:
  - table co `overflow-x-auto`
  - bulk toolbar wrap duoc
  - checkbox/action khong bi tran
  - selected count van thay duoc

  > Ghi chu test:

- [ ] Sua duplicate pagination block trong `teacher_approvals.html`.

  > Ghi chu test:

- [ ] Doi copy action ro rang:
  - `Vô hiệu hóa` thay vi `Xóa` neu la soft delete
  - `Tạm ẩn` cho deactivate subject/classroom neu khong khoa tai khoan
  - `Khóa tài khoản` cho deactivate user/teacher

  > Ghi chu test:

---

## 15. Backend Safety & Audit Log

- [ ] Moi bulk view phai co `@admin_required` va `@require_POST`.

  > Ghi chu test:

- [ ] Moi bulk view phai validate action nam trong whitelist.

  > Ghi chu test:

- [ ] Moi bulk view phai loc id bang queryset theo dung model, khong tin raw id.

  > Ghi chu test:

- [ ] Moi bulk view phai chan thao tac nguy hiem:
  - khoa chinh minh
  - khoa superuser cuoi cung
  - xoa hard data co lien ket diem/bai nop/lop
  - cancel session thi sai status

  > Ghi chu test:

- [ ] Moi bulk view quan trong dung `transaction.atomic()`.

  > Ghi chu test:

- [ ] Moi bulk view ghi `ActivityLogs` voi:
  - action name ro rang
  - resource_type
  - target ids
  - count
  - skipped ids neu co

  > Ghi chu test:

- [ ] Bulk approve/reject/khoa/mo khoa can notify user lien quan neu hanh dong anh huong truc tiep den ho.

  > Ghi chu test:

---

## 16. Test Plan

- [ ] Chay `python manage.py check`.

  > Ghi chu test:

- [ ] Chay test admin hien co `python manage.py test apps.administation`.

  > Ghi chu test:

- [ ] Them test cho moi bulk route moi:
  - GET bi chan neu route POST-only
  - user khong phai admin bi redirect/forbidden
  - khong chon id -> error
  - action sai -> error
  - action dung -> update dung + message + log

  > Ghi chu test:

- [ ] Smoke render cac trang admin sau khi them checkbox:
  - `/administration/users/`
  - `/administration/teacher-approvals/`
  - `/administration/teachers/`
  - `/administration/classrooms/`
  - `/administration/subjects/`
  - `/administration/languages/`
  - `/administration/sandboxes/`
  - `/administration/settings/`
  - `/administration/logs/`
  - `/administration/exam-events/`
  - `/administration/sandbox-monitor/`

  > Ghi chu test:

- [ ] Smoke bulk thao tac tren data tam trong transaction rollback neu co the.

  > Ghi chu test:

- [ ] Kiem tra mobile/desktop bang screenshot cho cac trang nhieu cot:
  - user management
  - teacher approvals
  - classroom management
  - subject management
  - sandbox monitor

  > Ghi chu test:

---

## 17. Thu Tu Trien Khai De It Rui Ro

- [ ] Phase 1: tao JS/helper UI bulk chung va chuan hoa user/classroom/subject dang co.

  > Ghi chu test:

- [ ] Phase 2: them bulk teacher approvals va teacher management.

  > Ghi chu test:

- [ ] Phase 3: them bulk languages/sandboxes/settings.

  > Ghi chu test:

- [ ] Phase 4: them bulk sandbox monitor va exam warning review.

  > Ghi chu test:

- [ ] Phase 5: activity logs policy/export selected/delete old neu can.

  > Ghi chu test:

- [ ] Phase 6: dashboard badges, design cleanup, mobile screenshots va regression tests.

  > Ghi chu test:

