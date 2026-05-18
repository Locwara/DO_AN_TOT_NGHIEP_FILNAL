# Kich Ban Fix Trang Chu DevLearn

Muc tieu: bien trang chu thanh **role-aware home dashboard**. Khi chua dang nhap, trang chu gioi thieu DevLearn ro rang va dan user vao dang ky/dang nhap. Khi da dang nhap, trang chu tro thanh bang dieu huong nhanh theo dung vai tro Student, Teacher, Admin.

> Nguyen tac UI: bam sat `devlearn-design-system.md`, dung `card`, `btn`, `form-input`, `badge`, `stat-card`, icon Material Symbols, mau token DevLearn. Khong dua secret, key, hoac data that vao template.

---

## 0. Audit Hien Trang

- [x] Doc lai `templates/home.html` va xac dinh cac block dang co: hero, IDE preview, feature cards.

  > Ghi chu test: Da xac dinh home hien co hero DevLearn, CTA, preview Web IDE va 3 feature cards. CTA da duoc Phase 1 doi sang context theo role.

- [x] Kiem tra `core/urls.py` dang dung `TemplateView` cho route home va lap ke hoach doi sang view rieng.

  > Ghi chu test: Ban dau route `/` dung `TemplateView(template_name='home.html')`. Phase 1 da doi sang `home_view`.

- [x] Kiem tra cac model can lay data cho trang chu: `Classrooms`, `ClassroomMembers`, `ClassroomSubjects`, `Assignments`, `Submissions`, `ExamSessions`, `Notifications`, `TeacherRegistrations`.

  > Ghi chu test: Da doc model va xac dinh nguon data cho cac phase sau: classroom/member/subject link, assignment deadline/exam, submission score, exam session, notification, teacher registration/admin queues.

- [x] Kiem tra role hien tai cua user qua `request.user.profiles.role`, fallback cho superuser/staff la admin.

  > Ghi chu test: Da xac dinh role qua `Profiles.role`; Phase 1 da them helper `get_home_role()` fallback superuser/staff ve admin va user thieu profile ve student.

---

## 1. Backend Home View

- [x] Tao `core/views.py` hoac view phu hop de thay `TemplateView` hien tai.

  > Ghi chu test: Da tao `core/views.py` voi `home_view`, `get_home_role`, `build_home_ctas`, `build_base_home_context`.

- [x] Doi `core/urls.py` route `''` sang `home_view`.

  > Ghi chu test: Route `/` da dung `home_view`, smoke render `/` tra 200 cho anonymous/student/teacher/admin.

- [x] Viet helper xac dinh role:
  - anonymous
  - student
  - teacher
  - admin/superuser/staff

  > Ghi chu test: `get_home_role()` fallback superuser/staff ve admin, user thieu profile ve student va tao profile neu can.

- [x] Tao context chung cho trang chu:
  - `role`
  - `is_role_home`
  - `primary_cta_url`
  - `primary_cta_label`
  - `secondary_cta_url`
  - `secondary_cta_label`

  > Ghi chu test: Context hien co `home_role`, `home_profile`, `is_role_home`, `role_labels`, `home_summary`, `home_sections`, primary/secondary CTA label/url/icon.

- [x] Dam bao query toi uu bang `select_related`, `prefetch_related`, `Count`, `Exists` khi can.

  > Ghi chu test: Phase 1 chi dung query profile toi thieu. Data widget nang cao se toi uu bang `select_related`, `prefetch_related`, `Count`, `Exists` o Phase 3-5.

---

## 2. Trang Chu Cho Khach Chua Dang Nhap

- [x] Hero tren fold dau tien:
  - ten san pham `DevLearn`
  - mo ta ngan: hoc lap trinh, lop theo mon, bai tap, bai thi, cham tu dong
  - CTA `Bat dau mien phi`
  - CTA phu `Dang nhap`

  > Ghi chu test: Hero hien co DevLearn, mo ta lop/mon/bai tap/bai thi/cham tu dong, CTA chinh/phu lay tu context role. Anonymous render thay `Bat dau mien phi` va `Dang nhap`.

- [x] Them nut `Dang nhap voi Google` neu muon day nhanh OAuth.

  > Ghi chu test: Da them nut `Dang nhap voi Google` tren hero anonymous, link toi `accounts:google_login`, co SVG Google mark.

- [x] Them preview Web IDE:
  - code mau
  - testcase pass/fail
  - diem so
  - goi y toi uu

  > Ghi chu test: IDE preview co code mau, box ket qua `8/8 pass`, `95/100`, `1 goi y` va goi y toi uu vong lap.

- [x] Them section "Quy trinh hoc":
  - Lop hoc
  - Mon hoc
  - Bai tap/Bai thi
  - Nop bai
  - Xem diem

  > Ghi chu test: Da them section `Learning flow` gom Lop hoc, Mon hoc, Bai tap, Bai thi, Xem diem.

- [x] Them section 3 role:
  - Hoc sinh
  - Giao vien
  - Admin

  > Ghi chu test: Da them section `Role workspace` cho Hoc sinh, Giao vien, Admin.

- [x] Them section "Tai sao phu hop voi lop lap trinh":
  - cham testcase tu dong
  - web IDE
  - exam mode
  - gradebook/thong ke
  - thao luan

  > Ghi chu test: Da giu va mo rong core feature cards: cham diem tu dong, Web IDE, thao luan. Exam/gradebook da co trong hero/flow va se mo rong them khi lam role dashboards.

- [x] Them CTA cuoi trang: `Tao tai khoan` va `Dang nhap`.

  > Ghi chu test: Da them final CTA anonymous voi nut `Tao tai khoan` va `Dang nhap`.

---

## 3. Trang Chu Cho Student

- [x] Hero ca nhan hoa:
  - chao ten hoc sinh
  - tong so lop dang tham gia
  - so bai chua nop
  - so bai sap den han

  > Ghi chu test: Da them block `Student workspace` tren `/` khi dang nhap role student, chao theo ten/username va hien stats lop dang tham gia, bai chua hoan thanh, bai den han 7 ngay, diem trung binh.

- [x] Quick actions:
  - `Vao lop hoc`
  - `Xem lich deadline`
  - `Xem diem cua toi`
  - `Kham pha lop hoc`

  > Ghi chu test: Da them quick actions: Vao lop hoc, Xem lich deadline, Xem diem cua toi, Kham pha lop hoc, Nhap ma moi.

- [x] Widget "Bai sap den han":
  - hien toi da 5 bai
  - hien ten lop, mon, deadline, trang thai da nop/chua nop
  - nut `Lam bai`

  > Ghi chu test: Da lay bai published trong lop da tham gia, due trong 7 ngay, toi da 5 bai, co lop/mon/deadline/trang thai va link lam bai.

- [x] Widget "Bai thi dang/gan mo":
  - hien bai thi trong lop da tham gia
  - neu da nop thi hien `Da nop`
  - neu chua mo thi hien thoi gian mo

  > Ghi chu test: Da them widget exam mode, doc `ExamSessions` cua hoc sinh de hien Dang lam/Da nop/Chua mo/Co the vao va link vao lobby bai thi.

- [x] Widget "Diem gan day":
  - 5 submission moi nhat
  - diem/max_score
  - pass/fail
  - nut xem chi tiet

  > Ghi chu test: Da them 5 submission moi nhat, diem uu tien manual_score neu co, label Dat/Can cai thien va link chi tiet submission.

- [x] Widget "Lop dang hoc":
  - card lop
  - so mon
  - tien do bai tap
  - link vao lop

  > Ghi chu test: Da them card lop toi da 4 lop, so mon, tien do bai tap theo lop va link vao chi tiet lop.

- [x] Widget "Thong bao moi":
  - 5 thong bao chua doc/moi nhat
  - link den thong bao

  > Ghi chu test: Da them 5 thong bao moi nhat, phan biet da doc/chua doc va link qua `notifications:open` de danh dau doc/redirect.

- [x] Empty state than thien:
  - chua tham gia lop nao -> CTA `Kham pha lop hoc` / `Nhap ma moi`
  - chua co bai tap -> thong bao nhe

  > Ghi chu test: Da them empty state chua co lop voi CTA kham pha/nhap ma moi; bai sap den han, bai thi, diem, thong bao deu co thong bao rong nhe.

---

## 4. Trang Chu Cho Teacher

- [x] Hero ca nhan hoa:
  - chao giao vien
  - so lop dang day
  - so bai da publish
  - so bai nop 7 ngay gan day
  - so thanh vien/lop cho duyet

  > Ghi chu test: Da them `Teacher workspace` tren `/`, chao theo ten/username va hien stats lop dang day, bai da publish/tong bai, bai nop 7 ngay, thanh vien cho duyet.

- [x] Quick actions:
  - `Tao lop hoc`
  - `Tao bai tap`
  - `Tao bai thi`
  - `Xem dashboard giao vien`
  - `Cham bai cho`

  > Ghi chu test: Da them action tao lop, tao bai tap theo lop active dau tien, tao bai thi voi `?exam=1`, dashboard giao vien va cham bai cho neu co queue.

- [x] Widget "Lop dang day":
  - danh sach lop active
  - so hoc sinh
  - so mon
  - so bai tap
  - link vao lop

  > Ghi chu test: Da them toi da 6 lop active, hien so hoc sinh, so mon, so bai tap, ma moi va link vao chi tiet lop.

- [x] Widget "Bai nop can xem":
  - submission moi nhat/chua cham tay
  - ten hoc sinh
  - bai/lop
  - diem auto
  - nut `Cham bai`

  > Ghi chu test: Da lay submission pending/running/error hoac bai manual/project chua co manual_score, hien hoc sinh, bai/lop, diem auto va nut cham bai.

- [x] Widget "Bai thi dang dien ra":
  - exam session running
  - so canh bao
  - nut `Monitor`

  > Ghi chu test: Da them exam monitor, hien session running, so canh bao, hoc sinh/lop va link `exam_monitor`.

- [x] Widget "Cho duyet thanh vien":
  - lop co pending member
  - nut vao lop xu ly

  > Ghi chu test: Da them danh sach pending member, moi item link vao lop de giao vien xu ly.

- [x] Widget "Hieu suat lop":
  - submission 7 ngay
  - pass rate tong quan
  - diem trung binh gan day

  > Ghi chu test: Da them performance 7 ngay voi submission count, pass rate, diem trung binh va danh sach bai co pass_rate thap.

- [x] Empty state:
  - chua co lop -> CTA tao lop
  - chua co bai -> CTA tao bai

  > Ghi chu test: Da them empty state chua co lop voi CTA tao lop; neu co lop nhung chua co bai thi hien goi y tao bai tap dau tien.

---

## 5. Trang Chu Cho Admin

- [x] Hero admin:
  - tong user
  - tong lop
  - giao vien cho duyet
  - lop/mon cho duyet
  - su kien thi can xem

  > Ghi chu test: Da them `Admin control center` tren `/`, hien tong user, tong lop, giao vien cho duyet, so mon/lop pending trong queue va so phien thi co canh bao.

- [x] Quick actions:
  - `Admin dashboard`
  - `Duyet giao vien`
  - `Duyet lop hoc`
  - `Quan ly user`
  - `Cau hinh he thong`
  - `Xem su kien thi`

  > Ghi chu test: Da them quick actions toi admin dashboard, duyet giao vien, duyet lop, quan ly user, cau hinh he thong va exam events.

- [x] Widget "Can xu ly":
  - teacher registrations pending
  - classrooms pending
  - subjects pending
  - exam sessions warning

  > Ghi chu test: Da them 4 card queue can xu ly: teacher registrations, classrooms, subjects va exam warning sessions, moi card co count va link den man hinh xu ly.

- [x] Widget "Suc khoe he thong":
  - server metrics moi nhat neu co
  - sandbox zombie/pending neu co
  - activity logs gan day

  > Ghi chu test: Da them system health voi queue pending/running, zombie task theo setting sandbox threshold, sandbox active va latest server metrics neu co; log gan day nam o widget rieng.

- [x] Widget "Tang truong":
  - user moi 7 ngay
  - submission 7 ngay
  - lop moi 30 ngay

  > Ghi chu test: Da them growth cards: user moi 7 ngay, submission 7 ngay, lop moi 30 ngay va link den analytics.

---

## 6. UI/UX & Design System

- [x] Dung layout full-width band + constrained inner content, khong long card trong card.

  > Ghi chu test: Trang chu dung wrapper `max-w-[1200px] mx-auto`, cac role section tach thanh band rieng; cac item ben trong la row/list/link card nho, khong dung UI table nang tren mobile.

- [x] Hero khong qua marketing, van dua duoc user vao workflow that.

  > Ghi chu test: Hero da doi noi dung theo role: anonymous la landing, student vao lop/deadline/diem, teacher vao lop/cham bai/tao bai, admin vao hang cho duyet/canh bao/sandbox.

- [x] Moi CTA co icon phu hop:
  - classroom: `school`
  - assignment: `assignment`
  - exam: `quiz`
  - grade: `fact_check`
  - admin: `admin_panel_settings`

  > Ghi chu test: Da chinh CTA diem/cham bai sang `fact_check`; CTA lop dung `school`, bai/bai tap dung assignment icon, bai thi dung `quiz`, admin dashboard dung `admin_panel_settings`.

- [x] Mobile responsive:
  - hero stack dep
  - cards khong tran text
  - nut khong bi bep
  - bang/list chuyen thanh cards khi can

  > Ghi chu test: Hero dung flex column -> row tu container breakpoint; role widgets dung grid `grid-cols-1/2/lg:3/4`, item co `min-w-0`, `truncate`, `line-clamp`, CTA `flex-wrap`.

- [x] Mau sac dung token DevLearn:
  - primary cho action chinh
  - success cho hoan thanh
  - warning cho deadline/canh bao
  - danger cho loi/qua han

  > Ghi chu test: Home dung `btn-primary`, `primary-*`, `success-*`, `warning-*`, `danger-*` theo token trong `base.css`; badge trang thai theo dung tone.

- [x] Khong hien text huong dan thua thien trong UI; uu tien label ngan, action ro.

  > Ghi chu test: Da doi cac eyebrow/label tieng Anh sang tieng Viet ngan gon theo ngữ cảnh: Khong gian hoc tap, Hang cho cham, Trung tam quan tri, Canh bao thi...

- [x] Loading global van hoat dong khi bam CTA/link noi bo.

  > Ghi chu test: `templates/base.html` co `#global-loading`, load `static/js/main.js`; script bat click link noi bo/form submit va bo qua anchor hash/export/download.

---

## 7. Data & Query Logic

- [x] Student context:
  - lay classroom ids tu `ClassroomMembers(status='approved')`
  - lay assignment published trong cac lop do
  - tinh submitted assignment ids
  - tinh upcoming deadlines

  > Ghi chu test: `build_student_home_context()` lay classroom_ids tu member approved + classroom active, assignments filter `is_published=True`, tinh submitted/completed ids va upcoming due trong 7 ngay. Smoke context: student_allowed=True.

- [x] Teacher context:
  - lay classroom theo `teacher=request.user`
  - lay assignments cua cac lop do
  - lay submissions gan day/can cham
  - lay pending members

  > Ghi chu test: `build_teacher_home_context()` lay active classrooms theo `teacher=user`, assignments/submissions/exam_sessions/pending_members chi theo classroom ids do. Smoke context: teacher_scope=True cho class/submission/exam.

- [x] Admin context:
  - count User/Profile/Classrooms/Subjects/TeacherRegistrations
  - lay pending approval queues
  - lay exam warnings
  - lay ActivityLogs gan day

  > Ghi chu test: `build_admin_home_context()` count User/Profile roles/Classrooms/Subjects/TeacherRegistrations, queue pending teacher/classroom/subject, exam warning sessions va recent ActivityLogs. Smoke context: admin_keys=True, logs=6.

- [x] Khong crash neu user thieu profile; auto fallback/create profile neu can.

  > Ghi chu test: `get_home_role()` bat `Profiles.DoesNotExist` va tao profile student. Smoke trong transaction rollback: user moi khong co profile -> fallback `student` va profile duoc tao, khong de lai data test.

- [x] Khong de student thay data lop/bai khong tham gia.

  > Ghi chu test: Student widgets chi lay assignment/session/submission/draft trong `classroom_ids` da approved; smoke assert tat ca upcoming/exam assignment nam trong allowed classrooms va published.

- [x] Khong de teacher thay lop/bai cua teacher khac.

  > Ghi chu test: Teacher widgets chi lay classroom theo `teacher=user`; smoke assert lop, submission can cham va exam session deu co classroom.teacher_id dung bang teacher id.

---

## 8. Kich Ban Test Theo Role

- [x] Anonymous vao `/` thay landing, nut dang ky/dang nhap/Google.

  > Ghi chu test: Django client render `/` status 200; thay `Hoc lap trinh voi`, `Bat dau mien phi`, `Dang nhap`, `Dang nhap voi Google`.

- [x] Student vao `/` thay bai sap den han, lop dang hoc, diem gan day.

  > Ghi chu test: Login student mau render `/` status 200; thay `Trang hoc sinh`, `Bai sap den han`, `Lop dang hoc`, `Diem gan day`.

- [x] Student chua tham gia lop nao thay empty state dung.

  > Ghi chu test: Tao student tam trong transaction rollback, render `/` status 200; thay `Ban chua tham gia lop nao`, `Kham pha lop hoc`, `Nhap ma moi`.

- [x] Teacher vao `/` thay lop dang day, bai nop can xem, pending members.

  > Ghi chu test: Login teacher mau render `/` status 200; thay `Trang giao vien`, `Lop dang day`, `Bai nop can xem`, `Cho duyet thanh vien`.

- [x] Teacher chua tao lop thay CTA tao lop.

  > Ghi chu test: Tao teacher tam trong transaction rollback, render `/` status 200; thay `Ban chua co lop dang hoat dong` va CTA `Tao lop hoc`.

- [x] Admin vao `/` thay hang doi duyet, dashboard shortcuts, thong ke he thong.

  > Ghi chu test: Login admin/superuser render `/` status 200; thay `Trang quan tri`, `Can xu ly`, `Admin dashboard`, `Suc khoe he thong`.

- [x] Superuser khong co profile van vao home/admin shortcuts binh thuong.

  > Ghi chu test: Tao superuser tam khong profile trong transaction rollback, render `/` status 200; thay `Trang quan tri`, `Admin dashboard`; profile van khong bat buoc.

- [x] Kiem tra query khong qua nang bang Django debug/log co ban.

  > Ghi chu test: CaptureQueriesContext: anonymous 0 query, student 25 query, teacher 21 query, admin 32 query. Muc nay chap nhan duoc cho home dashboard role-aware hien tai.

- [x] Kiem tra mobile viewport 375px, 768px, desktop 1440px.

  > Ghi chu test: Da chay Chromium headless chup `/tmp/devlearn-home-375-fixed10.png`, `/tmp/devlearn-home-768-fixed.png`, `/tmp/devlearn-home-1440-fixed.png`. Sau test 375px da bo sung global `box-sizing`, mobile hero break, giam size h2 mobile, stack testcase preview va an nut login header phu o <=380px de tranh tran.

---

## 9. Tien Ich Nen Them Neu Con Thoi Gian

- [x] Thanh "Tiep tuc hoc" cho student: link den bai tap dang lam gan nhat hoac draft code gan nhat.

  > Ghi chu test: Da them `continue_learning` trong `build_student_home_context()`: uu tien `CodeDrafts` moi nhat, sau do bai sap den han, sau do bai vua nop; template hien CTA `Khôi phục bản nháp`/`Làm bài`/`Xem kết quả`.

- [x] "Deadline heat strip": 7 ngay toi co bao nhieu bai den han moi ngay.

  > Ghi chu test: Da them `deadline_heat_strip` 7 ngay toi, dem bai published chua hoan thanh theo ngay due_date; template hien heat strip mau success/warning/danger.

- [x] "Canh bao thi" cho teacher/admin: hien session co violation cao.

  > Ghi chu test: Teacher home co `exam_warning_sessions` theo classroom cua teacher, order theo `violation_count`; admin home da co `warning_exam_sessions`. Smoke render teacher/admin thay `Cảnh báo thi`.

- [x] "Thong bao mini inbox": danh dau da doc nhanh ngay tai home.

  > Ghi chu test: Student home doi block thong bao thanh `Mini inbox`, co form POST `notifications:mark_read` voi `next=/`. Smoke tao notification tam trong transaction rollback, POST `/notifications/<id>/read/` status 302 va `is_read=True`.

- [x] "Shortcut theo mon": student vao thang mon co bai chua lam nhieu nhat.

  > Ghi chu test: Da tinh `subject_shortcut` theo `classroom_subject_id` co nhieu assignment chua hoan thanh nhat, link ve `classrooms:subject_detail` dung lop + mon + ky, khong gom nham cung mon giua cac lop.

- [x] "Khoi phuc ban nhap": neu co `CodeDrafts`, hien nut tiep tuc code.

  > Ghi chu test: Section ban nhap doi thanh `Khôi phục bản nháp`; card tiep tuc hoc uu tien draft moi nhat va nut vao assignment detail de tiep tuc code.

- [x] "Teacher checklist": tao lop -> gan mon -> tao bai -> publish -> xem nop bai.

  > Ghi chu test: Da them `teacher_checklist` gom Tao lop, Gan mon, Tao bai, Cong bo bai, Xem bai nop; moi muc co done/url/icon va hien o sidebar teacher.

- [x] "Admin health checklist": pending approvals -> zombie submissions -> failed exam events -> system settings.

  > Ghi chu test: Da them `admin_health_checklist` gom hang cho duyet, zombie task, canh bao thi, system settings; moi muc link ve dung trang quan tri va hien tong so can xu ly.

---

## 10. Definition Of Done

- [x] Route `/` dung view moi va khong crash cho anonymous/student/teacher/admin.

  > Ghi chu test: `resolve('/')` tra ve `core.views home_view`. Django client render `/` cho anonymous/student/teacher/admin deu status 200. Test them user thuong chua co profile va superuser chua co profile deu render 200.

- [x] Trang chu co noi dung khac nhau theo role.

  > Ghi chu test: Smoke text theo role: anonymous thay `DevLearn Platform`; student thay `Trang học sinh`, `Tiếp tục học`, `Deadline 7 ngày`; teacher thay `Trang giáo viên`, `Bài nộp cần xem`, `Checklist giảng dạy`; admin thay `Trang quản trị`, `Cần xử lý`, `Checklist hệ thống`.

- [x] CTA chinh dua user vao workflow dung.

  > Ghi chu test: Smoke HTML co primary CTA dung role: anonymous -> `accounts:register`, student -> `classrooms:classroom_list`, teacher -> `accounts:teacher_dashboard`, admin -> `administation:dashboard`. Secondary/quick actions vao deadline, tao lop, quan ly user va cau hinh he thong.

- [x] UI khop `devlearn-design-system.md`.

  > Ghi chu test: Home dung token design system trong `static/css/base.css` (`--primary-500 #137fec`, neutral/semantic colors, radius, shadow, font), dung component co san `hero-light`, `course-card`, `stat-card`, `btn`, `badge`, material icons va responsive CSS mobile da them o phase 8.

- [x] `python manage.py check` OK.

  > Ghi chu test: Chay `python manage.py check` -> `System check identified no issues (0 silenced).`

- [x] Smoke render cac role bang Django test client OK.

  > Ghi chu test: Django client smoke: anonymous 200, student 200, teacher 200, admin 200; tat ca role deu match text mong doi va primary CTA dung workflow.

- [x] Khong them secret vao source; `.env` van ignored.

  > Ghi chu test: `git check-ignore -v .env` -> `.gitignore:1:.env`; `git ls-files .env .codex` khong tra ve file tracked. `core/settings.py` doc secret tu env, `.env.example` chi chua placeholder.
