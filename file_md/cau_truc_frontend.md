# Cau truc frontend DevLearn

Tai lieu nay duoc lap sau khi quet cac template trong `templates/`, cac route trong `core/urls.py` va `apps/*/urls.py`, CSS/JS dung chung trong `static/css/base.css`, `static/js/main.js`.

## 1. Tong quan cong nghe va cau truc thu muc

- Frontend la Django template server-rendered, khong phai SPA.
- Layout chinh nam o `templates/base.html`.
- Header, footer va dropdown CSV dung lai qua:
  - `templates/includes/navbar.html`
  - `templates/includes/footer.html`
  - `templates/includes/csv_dropdown.html`
- Admin co layout rieng ke thua tu base:
  - `templates/administration/base_admin.html`
- Trang IDE code (`templates/submissions/solve_problem.html`) la trang full-screen doc lap, khong ke thua `base.html`.
- Trang in bao cao tre han (`templates/assignments/late_report_print.html`) cung la HTML doc lap de phuc vu in/PDF.
- CSS chung: `static/css/base.css`, them Tailwind CDN va Google Fonts trong layout.
- JS chung: `static/js/main.js`, quan ly loading overlay, inline loading, copy/save bo loc admin.
- Editor code: CodeMirror CDN trong trang IDE.
- Markdown trong IDE: `marked` + `DOMPurify`.

## 2. Design system dung chung

### 2.1 Mau sac

- Mau brand chinh: `#137fec` (`--primary-500`), dung cho nut chinh, link, icon chinh, progress.
- Nen chinh: trang sang `#ffffff`.
- Nen section phu: `--primary-50` `#f0f8ff`.
- Nen code/IDE/footer: `--primary-950` `#020d1f`.
- Trang thai:
  - Thanh cong: `--success-600` `#16a34a`.
  - Canh bao/deadline: `--warning-600` `#ea580c`.
  - Loi/nguy hiem: `--danger-600` `#dc2626`.
  - Accent/quiz/nang cao: violet `#7c3aed`.

### 2.2 Typography

- Font chinh: `Be Vietnam Pro`.
- Font code: `Fira Code`.
- H1/H2/H3 dung trong mau xanh dam, font dam.
- Code inline co nen `primary-50`, border `primary-200`, chu `primary-600`.

### 2.3 Component lap lai

- `.btn`, `.btn-primary`, `.btn-outline`, `.btn-ghost`, `.btn-sm`, `.btn-icon`.
- `.card`, `.course-card`: nen trang, border xanh nhat, shadow nhe.
- `.stat-card`, `.stat-number`, `.stat-label`: the thong ke.
- `.badge`: nhan trang thai/ngon ngu/do kho.
- `.form-input`, `.form-select`, `.form-textarea`, `.form-label`, `.form-error`.
- `.admin-filter-panel`, `.admin-filter-section`, `.admin-filter-status`: bo loc admin.
- `.csv-dropdown`, `.csv-menu`: menu xuat CSV.
- `.global-loading`: overlay loading toan cuc khi click link/form.

## 3. Layout chung `base.html`

### 3.1 Head

- Khai bao HTML `lang="vi"`.
- Meta viewport responsive.
- Title lay tu `{% block title %}`.
- Nap Tailwind CDN voi plugin `forms,container-queries`.
- Nap fonts Be Vietnam Pro, Fira Code, Material Symbols.
- Khai bao `tailwind.config` de dong bo mau/typography/radius.
- Style inline khai bao CSS variables va mot so class nen tang.
- Nap `static/css/base.css`.
- Cac trang con co the chen them qua `{% block extra_head %}`.

### 3.2 Body

- Body co `min-h-screen`, font display, nen trang sang.
- Wrapper chinh: `.layout-container`, co padding-top 60px do header fixed.
- Thu tu hien thi:
  1. Include navbar.
  2. Vung Django messages/toast, nam duoi header, trong container max 1200px.
  3. `<main class="flex-1">` chua `{% block content %}`.
  4. Include footer.
  5. Global loading overlay.
  6. Script auto-hide toast sau 5 giay.
  7. Nap `static/js/main.js`.
  8. `{% block extra_js %}`.

## 4. Header `includes/navbar.html`

Header fixed tren cung, cao toi thieu 60px, nen trang co blur va shadow nhe.

### 4.1 Logo

- Nam ben trai.
- Link ve `home`.
- Icon hinh `</>` trong o xanh.
- Text `DevLearn`, chu `Learn` mau primary.

### 4.2 Khi chua dang nhap

- Nav giua:
  - `Features` -> anchor `#features` tren trang chu.
  - `IDE` -> anchor `#ide`.
  - `Community` -> anchor `#community`.
- Actions ben phai:
  - `Dang ky` -> `accounts:register`.
  - `Dang nhap` -> `accounts:login`.

### 4.3 Khi da dang nhap

- Nav giua thay doi theo role:
  - Teacher: `Dashboard giao vien` -> `accounts:teacher_dashboard`.
  - Admin/superuser: `Dashboard admin` -> `administation:dashboard`.
  - Student/default: `Dashboard hoc sinh` -> `accounts:student_dashboard`.
- Link chung:
  - `Lop hoc` -> `classrooms:classroom_list`.
  - `Lich` -> `assignments:calendar`.
- Link rieng:
  - Teacher co `Tao lop` -> `classrooms:create`.
  - Admin co `Quan tri` -> `administation:dashboard`.
- Actions ben phai:
  - Nut icon thong bao -> `notifications:list`, co badge so unread.
  - Dropdown hover thong bao gan day:
    - Header dropdown co `Xem tat ca`.
    - Moi item link `notifications:open`.
    - Neu chua co thi hien icon `notifications_off`.
  - `Dang xuat` -> `accounts:logout` (an tren mobile nho).
  - Avatar/profile -> `accounts:profile`, hien avatar URL neu co, neu khong hien chu cai dau.

### 4.4 Responsive

- Khi viewport <= 900px, `.nav` bi an, logo text cung bi an, chi con icon logo va action.
- Khi <= 640px, nut header giam padding/font.
- Khi <= 380px, nut outline trong header bi an bot.

## 5. Footer `includes/footer.html`

Footer nam cuoi layout, nen `primary-950`, 4 cot tren desktop, 1 cot tren mobile.

- Cot 1: logo DevLearn va mo ta ngan.
- Cot San pham:
  - `Features` anchor `#features`.
  - `Web IDE` anchor `#ide`.
  - `Lop hoc` -> `classrooms:classroom_list`.
- Cot Hoc tap:
  - `Lich bai tap` -> `assignments:calendar`.
  - `Kham pha lop` -> `classrooms:classroom_list`.
  - `Cong dong` anchor `#community`.
- Cot Tai khoan:
  - Da dang nhap: `Ho so`, `Thong bao`, `Dang xuat`.
  - Chua dang nhap: `Dang nhap`, `Dang ky`, `Quen mat khau`.
- Footer bottom: copyright 2026 va slogan.

## 6. Route map tong quan

### 6.1 Root

- `/` -> `home_view` -> `templates/home.html`.
- `/admin/` -> Django admin.

### 6.2 Accounts

- `/accounts/register/` -> dang ky.
- `/accounts/login/` -> dang nhap.
- `/accounts/google/login/`, `/accounts/google/callback/` -> OAuth Google.
- `/accounts/logout/` -> dang xuat.
- `/accounts/profile/`, `/accounts/profile/<user_id>/` -> profile.
- `/accounts/profile/edit/` -> sua profile.
- `/accounts/dashboard/` -> dashboard hoc sinh.
- `/accounts/teacher-dashboard/` -> dashboard giao vien.
- `/accounts/teacher-register/` -> dang ky giao vien.
- Password reset:
  - `/accounts/password-reset/`
  - `/accounts/password-reset/done/`
  - `/accounts/password-reset-confirm/<uidb64>/<token>/`
  - `/accounts/password-reset-complete/`

### 6.3 Classrooms

- `/classrooms/` -> danh sach lop.
- `/classrooms/search/` -> tim lop.
- `/classrooms/create/` -> tao lop.
- `/classrooms/join/` -> nhap ma moi.
- `/classrooms/<pk>/` -> chi tiet lop.
- `/classrooms/<pk>/gradebook/` -> so diem.
- `/classrooms/<pk>/leaderboard/` -> bang xep hang.
- `/classrooms/<pk>/members/import/` -> import hoc sinh.
- `/classrooms/<pk>/subjects/` -> danh sach mon trong lop.
- `/classrooms/<pk>/subjects/create/` -> tao mon.
- `/classrooms/<pk>/subjects/assign/` -> gan mon co san.
- `/classrooms/<pk>/subjects/<link_pk>/` -> chi tiet mon trong lop.
- `/classrooms/semesters/` va cac route create/edit/delete -> quan ly ky hoc trong admin layout.

### 6.4 Assignments

- `/assignments/calendar/` -> lich deadline.
- `/assignments/classroom/<classroom_pk>/` -> danh sach bai cua lop.
- `/assignments/classroom/<classroom_pk>/create/` -> tao bai.
- `/assignments/<pk>/` -> chi tiet bai.
- `/assignments/<pk>/edit/`, `/clone/`, `/delete/`, `/publish/`, `/release-grades/`.
- `/assignments/<pk>/statistics/` -> thong ke bai.
- `/assignments/<pk>/plagiarism/` -> kiem tra dao van.
- `/assignments/<pk>/file-requirements/` -> cau hinh yeu cau file.
- `/assignments/<pk>/quiz/` va cac route add/import/export/preview/attempts/questions -> quan ly quiz.
- `/assignments/<pk>/testcases/...` -> them/sua/xoa/import testcase.
- Export/report: late report, missing, scores, submissions, quiz attempts, zip files.

### 6.5 Submissions

- `/submissions/solve/<assignment_pk>/` -> IDE lam bai code.
- `/submissions/file/<assignment_pk>/` -> man nộp file.
- `/submissions/exam/<assignment_pk>/` -> phong cho thi.
- `/submissions/exam/<assignment_pk>/ide/` -> IDE/phong lam bai thi.
- `/submissions/exam/<assignment_pk>/monitor/` -> giao vien theo doi phong thi.
- `/submissions/quiz/<assignment_pk>/` -> lobby quiz.
- `/submissions/quiz/attempt/<attempt_pk>/` -> lam quiz.
- `/submissions/quiz/attempt/<attempt_pk>/result/` -> ket qua quiz.
- `/submissions/history/<assignment_pk>/` -> lich su nop bai.
- `/submissions/detail/<pk>/` -> chi tiet bai nop.
- `/submissions/teacher-list/<assignment_pk>/` -> danh sach bai nop cho giao vien.
- `/submissions/grade/<pk>/` -> cham diem.
- AJAX/API noi bo: save draft, run test, submit code, autosave quiz, exam ping/event, comments.

### 6.6 Discussions

- `/discussions/assignment/<assignment_pk>/` -> danh sach thao luan.
- `/discussions/assignment/<assignment_pk>/create/` -> tao cau hoi.
- `/discussions/<pk>/` -> chi tiet chu de.
- `/discussions/<pk>/edit/`, `/delete/`, `/vote/`, `/mark-answer/`, `/pin/`.

### 6.7 Notifications

- `/notifications/` -> danh sach thong bao.
- `/notifications/<pk>/open/` -> danh dau doc va redirect den link thong bao.
- `/notifications/<pk>/read/`, `/notifications/read-all/`.

### 6.8 Administration

- `/administration/` -> dashboard admin.
- Users: `/users/`, create, detail, edit, reset password, export, bulk.
- Teachers/students: `/teachers/`, `/students/`, teacher approvals.
- Classrooms: `/classrooms/`, approve/reject/export/bulk.
- Subjects: `/subjects/`, approve/reject/export/bulk.
- Languages: `/languages/`, create/edit/delete/toggle.
- Sandboxes: `/sandboxes/`, create/edit/delete/test.
- Metrics/logs/exam-events/analytics/sandbox-monitor/settings.

## 7. Trang chu `home.html`

Trang chu dung chung cho 4 bien the theo `home_role`: anonymous, student, teacher, admin.

### 7.1 Phan hero chung

- Container `.home-shell` max 1200px.
- Hero nen `hero-light`, bo goc duoi, layout 2 cot tu viewport rong.
- Cot trai:
  - Eyebrow thay doi theo role.
  - H1 thay doi theo role:
    - Anonymous: hoc lap trinh voi Web IDE va cham diem tu dong.
    - Student: theo doi lop, bai tap, diem so.
    - Teacher: quan ly lop, giao bai, cham nhanh.
    - Admin: kiem soat he thong va hang cho duyet.
  - Doan mo ta.
  - Cum CTA:
    - Primary CTA lay tu context.
    - Secondary CTA neu co.
    - Anonymous them nut Google login.
- Cot phai:
  - Mockup IDE dark aspect-video.
  - Thanh topbar voi 3 dot mau.
  - Code demo `grade_submission`.
  - Card ket qua test: `8/8 pass`, `95/100`, `1 goi y`.

### 7.2 Bien the anonymous

- Sau hero co section "Luong hoc tap":
  - 5 card: Lop hoc, Mon hoc, Bai tap, Bai thi, Xem diem.
- Section "Theo vai tro":
  - 3 card: Hoc sinh, Giao vien, Admin.
- Section chung `#features`:
  - Cham diem tu dong.
  - Web IDE tuong tac.
  - Thao luan cong tac.
- CTA cuoi:
  - `Tao tai khoan` -> register.
  - `Dang nhap` -> login.

### 7.3 Bien the student

- Section "Khong gian hoc tap".
- 4 stat-card: so lop dang tham gia, bai chua hoan thanh, bai den han 7 ngay, diem trung binh.
- Quick actions:
  - Vao lop hoc.
  - Xem lich deadline.
  - Xem diem cua toi.
  - Kham pha lop hoc.
  - Nhap ma moi.
- Card "Tiep tuc hoc": co nut tiep tuc neu co draft/bai can lam.
- Heat strip deadline 7 ngay.
- Neu chua co lop: banner bat dau voi nut kham pha/nhap ma moi.
- Cot chinh:
  - Bai sap den han: moi dong co badge, mon, lop, han, nut `Lam bai`.
  - Bai thi dang/gần mo.
  - Lop dang hoc: card lop co progress.
- Cot phu:
  - Diem gan day -> link submission detail.
  - Mini inbox thong bao -> link notification open, form danh dau da doc.
  - Shortcut theo mon -> vao subject detail.
  - Ban nhap -> link assignment detail.

### 7.4 Bien the teacher

- 4 stat-card: lop dang day, bai da cong bo/tong, bai nop 7 ngay, thanh vien cho duyet.
- Quick actions:
  - Tao lop hoc.
  - Tao bai tap.
  - Tao bai thi.
  - Dashboard giao vien.
  - Cham bai cho.
- Neu chua co lop: banner tao lop dau tien.
- Cot chinh:
  - Bai nop can xem -> link `submissions:grade`.
  - Lop dang day -> link chi tiet lop.
  - Hieu suat lop 7 ngay, pass rate, diem TB, assignment yeu.
- Cot phu:
  - Bai thi dang dien ra -> exam monitor.
  - Phien co violation cao -> exam monitor.
  - Cho duyet thanh vien -> classroom detail.
  - Goi y thao tac tiep theo.
  - Teacher checklist.

### 7.5 Bien the admin

- 4 stat-card: total users, total classrooms, pending teachers, exam warnings.
- Quick actions:
  - Admin dashboard.
  - Duyet giao vien.
  - Duyet lop hoc.
  - Quan ly user.
  - Cau hinh he thong.
  - Xem su kien thi.
- Cot chinh:
  - Hang cho duyet: card teacher/classroom/subject pending.
  - Su kien thi can xem.
  - Tang truong: user moi 7 ngay, submissions 7 ngay, lop moi 30 ngay.
- Cot phu:
  - Suc khoe he thong: queue, zombie task, sandbox active, CPU/memory neu co.
  - Admin health checklist.
  - Log gan day.
  - Hang cho moi nhat: teacher registrations, pending classrooms, pending subjects.

## 8. Accounts

### 8.1 Dang nhap `accounts/login.html`

- Layout center, min-height tru header/footer, card max-width md.
- Tren cung la logo icon lon.
- Tieu de "Chao mung tro lai" va subtitle.
- Nut Google login.
- Divider "hoac".
- Form:
  - Username.
  - Password.
  - Checkbox ghi nho dang nhap.
  - Link quen mat khau.
  - Submit `Dang nhap`.
  - Link sang dang ky.
- Neu form loi: alert do voi icon error.
- Lien ket:
  - Google -> `accounts:google_login`, giu `next` neu co.
  - Quen mat khau -> password reset.
  - Dang ky -> register.

### 8.2 Dang ky `accounts/register.html`

- Bo cuc gan giong login.
- Nut Google register.
- Form gom:
  - Ho va ten.
  - Username.
  - Email.
  - Password.
  - Xac nhan password.
- Error box liet ke loi tung field.
- Submit `Tao tai khoan`.
- Link sang dang nhap.

### 8.3 Password reset

- `password_reset.html`: card nhap email, icon lock reset, submit gui link, link quay lai login.
- `password_reset_done.html`: card thanh cong, icon email read, nut quay lai login.
- `password_reset_confirm.html`: neu link hop le hien form password moi/xac nhan; neu invalid hien alert va link gui lai.
- `password_reset_complete.html`: card thanh cong, nut dang nhap ngay.

### 8.4 Profile `accounts/profile.html`

- Container max 960px.
- Header card:
  - Avatar 128px hoac chu cai.
  - Cham xanh online/status.
  - Ho ten, badge role, bio, ngay tham gia.
  - Neu la profile cua minh: nut chinh sua; neu role student co nut dang ky giao vien.
- Details card:
  - Email/phone neu co quyen xem thong tin rieng.
  - Bio.
- Stats:
  - Bai da nop.
  - Diem trung binh.
  - Lop hoc.
- Classes:
  - Card lop dang day/dang hoc, hien icon code, ten lop, mo ta, chevron.

### 8.5 Edit profile `accounts/edit_profile.html`

- Header co arrow back ve profile.
- Form multipart:
  - Card avatar: preview avatar, upload file, URL avatar.
  - Card thong tin ca nhan: ho, ten, email, phone, bio.
  - Actions: Huy, Luu thay doi.

### 8.6 Dashboard hoc sinh `accounts/student_dashboard.html`

- Header voi tieu de, greeting, nut desktop `Lich deadline`, `Vao lop hoc`.
- 4 stats: lop hoc, hoan thanh, diem trung binh, ty le dat.
- Progress bar tien do tong the.
- Grid 2 cot:
  - Cot lon: Bai sap den han; neu co overdue thi them section bai qua han.
  - Cot phu: Thu hang trong lop, link leaderboard; Bai nop gan day, link submission detail.

### 8.7 Dashboard giao vien `accounts/teacher_dashboard.html`

- Header voi nut `Tao lop`, `Lich`, `Lop hoc`.
- 4 stats: lop dang day, bai tap, bai nop 7 ngay, can xu ly.
- Hang tren:
  - Bai can xem -> link grade submission.
  - Cho duyet vao lop -> link classroom detail.
- Hang duoi:
  - Bai sap den han -> assignment detail.
  - Bai can ho tro -> statistics.
  - Bai nop gan day -> submission detail.
- Cuoi trang:
  - Lop dang day -> classroom detail.
  - Dang cho admin -> pending classrooms/subjects.

### 8.8 Dang ky giao vien `accounts/teacher_register.html`

- Header back ve profile.
- Neu da co don: card trang thai cho phe duyet, hien to chuc, ly do, status.
- Neu chua co: form gom institution, reason, proof document URL.
- Actions: Huy, Gui don dang ky.

## 9. Classrooms

### 9.1 Danh sach lop `classrooms/list.html`

- Container max 1200px.
- Header:
  - Eyebrow `Classrooms`.
  - Title doi theo role: teacher "Lop hoc cua toi", student "Lop hoc".
  - CTA:
    - Teacher: `Tao lop moi`.
    - Student: `Nhap ma moi`.
- Search bar full width co icon search, input `q`, nut `Tim` hoac nut clear.
- Section 1:
  - Teacher: "Lop toi dang giang day".
  - Student: "Lop dang tham gia".
  - Card lop 3 cot desktop, moi card co thanh mau tren, ten, mo ta, member count, subject count, badge ma moi/da tham gia.
  - Click card -> classroom detail.
- Section 2 chi student:
  - "Kham pha lop hoc".
  - Card lop co teacher avatar, member, subject, nut quick join.
  - Neu pending thi nut disabled "Dang cho duyet".

### 9.2 Tim lop `classrooms/search.html`

- Max 900px, header co arrow back.
- Search input cao 56px tim theo ten lop/ma moi.
- Neu co query: hien so ket qua va list card ket qua.
- Moi item hien icon school, ten, mo ta, member count, giao vien.
- Neu khong co query: empty state huong dan nhap tu khoa.

### 9.3 Tao/Sua lop

- `classrooms/create.html`:
  - Form max 700px, header back ve list.
  - Card thong tin lop: ten lop, mo ta, max students, checkbox yeu cau giao vien duyet khi hoc sinh tham gia.
  - Actions Huy/Tao lop hoc.
- `classrooms/edit.html`:
  - Giong create nhung header hien ma moi.
  - Co danger zone:
    - Doi ma moi.
    - Xoa lop hoc.
  - Actions Huy/Luu thay doi.

### 9.4 Join lop `classrooms/join.html`

- Card center max 448px.
- Icon group_add.
- Input ma moi uppercase, centered, letter spacing.
- Submit `Tham gia`.
- Link quay lai danh sach.

### 9.5 Chi tiet lop `classrooms/detail.html`

- Breadcrumb: Lop hoc -> ten lop.
- Header:
  - H1 ten lop, mo ta.
  - Meta: giao vien, so sinh vien, ma moi.
  - Teacher actions: So diem, Chinh sua, Thong bao.
  - Student actions: Bang xep hang, Roi lop.
- Layout chinh 2 cot: main 2/3, sidebar 1/3.
- Main:
  1. Thong bao:
     - Teacher co link tao moi.
     - Card announcement, co pin, title, content, thoi gian, giao vien.
     - Teacher co nut pin/delete.
  2. Mon hoc:
     - Teacher co link xem tat ca, tao moi, gan mon co san.
     - Card mon: code, name, status badge, description, languages, assignment count, link vao mon.
  3. Bai tap gan day:
     - Teacher co link xem tat ca, tao bai tap.
     - Moi row co icon theo submission mode, title, mode/difficulty/due date, chevron.
- Sidebar:
  - Thanh vien: list 10 thanh vien, avatar, nut remove neu teacher, link import.
  - Cho duyet: chi teacher, card pending members voi nut Duyet/Tu choi.
  - Bang xep hang: nut xem day du.

### 9.6 So diem `classrooms/gradebook.html`

- Max 1400px, breadcrumb den lop -> so diem.
- Header co title, mo ta, dropdown CSV, nut ve lop.
- 4 stat card: hoc sinh, bai tap, co bai nop, diem TB.
- Filter form:
  - Cong bo, mon hoc, hoc ky, trang thai hoc sinh.
  - Nut loc, nut reset.
- Bang diem ngang:
  - Cot sticky trai: hoc sinh.
  - Cot hoan thanh, diem TB.
  - Moi assignment la mot cot, header link assignment detail.
  - Cell co submission link sang grade, mau theo diem/status, icon late.
  - Cell chua nop la dashed card.
- Empty state neu khong co assignment/hoc sinh phu hop.

### 9.7 Mon hoc cua lop `classrooms/subjects.html`

- Breadcrumb: Lop hoc -> ten lop -> Mon hoc.
- Header co CTA tao mon/gán mon.
- Tabs filter ky hoc: Tat ca, Ky hien tai, tung ky, Chua phan ky.
- Group theo semester.
- Moi card mon:
  - Code, name, status approved/pending/rejected.
  - Description.
  - Language badges.
  - Assignment count.
  - Actions: Vao mon, them bai, sua mon neu co quyen, go mon khoi lop.
- Empty state neu chua co mon.

### 9.8 Chi tiet mon `classrooms/subject_detail.html`

- Breadcrumb: Lop hoc -> lop -> Mon hoc -> code.
- Header:
  - Badges code, semester, status.
  - H1 ten mon, description, languages.
  - Actions: danh sach bai, so diem mon, tao bai.
- 4 stats:
  - Bai da cong bo.
  - Bai thi.
  - Teacher: ban nhap; Student: da hoan thanh.
  - Teacher: sinh vien; Student: tien do.
- Filter/search:
  - Tim bai trong mon.
  - Tabs: Tat ca, Bai tap, Bai thi, Nhap (teacher).
- Danh sach assignment row:
  - Icon theo exam/file/quiz/difficulty.
  - Badges bai thi, submission mode, draft, da nop/status.
  - Meta deadline, score, difficulty, so SV nop.
  - Teacher actions: Bai nop, Thong ke.
  - Student action: Vao thi/Nop file/Lam bai/Xem lai.

### 9.9 Form mon va gan mon

- `classrooms/subject_form.html`:
  - Form tao/sua mon, co sidebar danh sach mon da co trong he thong.
  - Fields: code, name, description, languages, semester/status tuy context.
  - JS check trung ten qua `classrooms:subject_check_name`.
  - JS filter danh sach mon da co.
- `classrooms/subject_assign.html`:
  - Header back ve subjects.
  - Form chon mon da duyet va ky hoc.
  - Empty note neu khong co mon da duyet de gan.

### 9.10 Thong bao/import/leaderboard/ky hoc

- `create_announcement.html`: form tao thong bao lop, title/content/is_pinned.
- `import_members.html`: upload CSV hoc sinh, nut tai CSV mau, summary import, danh sach loi/canh bao va huong dan format.
- `leaderboard.html`: bang xep hang hoc sinh trong lop, link back lop, hien diem/rank/tien do.
- `semester_list.html`: admin layout, bang ky hoc, nut tao ky, edit/delete.
- `semester_form.html`: form code, name, start/end date, is_current, is_active.
- `semester_delete_confirm.html`: confirm xoa ky hoc, thong bao gỡ tham chieu khong mat du lieu chinh.

## 10. Assignments

### 10.1 Lich deadline `assignments/calendar.html`

- Max 1400px, breadcrumb Lop hoc -> Lich deadline.
- Header:
  - H1 Lich deadline.
  - Mo ta theo role student/teacher.
  - Nut view mode: Thang, Tuan, Hom nay.
- 4 stats:
  - Deadline trong ky lich.
  - Sap han 48h.
  - Qua han.
  - Student: da nop; Teacher: ban nhap.
- Filter form:
  - Lop.
  - Mon hoc.
  - Hoc ky.
  - Teacher co them cong bo.
- Main calendar:
  - Header co prev/next va title thang/tuan.
  - Grid 7 cot, moi ngay co badge so event.
  - Event card link assignment/action URL, co icon/status, ten bai, lop, gio due, status label, code mon.
- Sidebar:
  - Legend trang thai.
  - Danh sach bai khong co deadline.

### 10.2 Danh sach bai `assignments/list.html`

- Breadcrumb: Lop hoc -> classroom -> Bai tap.
- Header:
  - H1 "Bai tap" hoac ten mon dang filter.
  - Teacher CTA tao bai moi/tao bai cho mon.
- Search/filter:
  - Input q.
  - Select mon/ky.
  - Nut xoa loc.
- Neu dang filter mon: banner mon co link vao subject detail.
- List assignment:
  - Card ngang co icon theo mode/difficulty.
  - Title, draft badge, subject badge, mode badge.
  - Description, difficulty, due date, max score.
  - Chevron.
- Empty state co CTA tao bai neu teacher.

### 10.3 Tao/Sua bai `assignments/create.html`, `edit.html`, `_assignment_form.html`

- Create/edit chi la wrapper voi breadcrumb, H1, include `_assignment_form.html`.
- Form co sticky step tabs 4 buoc:
  1. Thong tin.
  2. Hinh thuc.
  3. Chinh sach.
  4. Hoan tat.
- Phan thong tin:
  - Title.
  - Classroom subject.
  - Hidden legacy type.
  - Submission mode segmented: Lap trinh, Nop file, Trac nghiem.
  - Grading mode: auto/manual/mixed.
  - Difficulty.
  - Partial summary theo mode.
  - Quiz config: random questions/choices, show score/correct/explanation, allow review, time limit, passing score.
  - File requirements: allowed extensions, max size, max files, require comment, allow resubmit, require all files, scan required.
  - Description, instructions.
- Phan chinh sach:
  - Start date, due date.
  - Max score, max attempts.
  - Late submission + penalty.
  - Show testcase result.
  - Enable leaderboard.
  - Exam mode:
    - Exam start/end.
    - Duration, grace submit.
    - Max run count.
    - Fullscreen/custom input/sample run flags.
- Phan hoan tat:
  - Code mode co list ngon ngu duoc phep.
  - File/quiz mode co note.
  - Create: nut Cong bo bai tap, Luu nhap.
  - Edit: Luu thay doi, Huy.
- JS:
  - Toggle late penalty.
  - Toggle exam section.
  - Toggle mode UI and panels.
  - Dong bo legacy type/grading.
  - Scroll tab observer.

### 10.4 Chi tiet bai `assignments/detail.html`

- Breadcrumb: Lop hoc -> classroom -> subject/list -> assignment.
- Header:
  - Title.
  - Badges: nhap/da cong bo, exam, submission mode, subject.
  - Meta: difficulty, due date, score, max attempts.
- Actions:
  - Teacher:
    - An/Cong bo.
    - Chinh sua.
    - Nhan ban.
    - Thong ke.
    - Quiz mode: Quan ly quiz.
    - File mode: Yeu cau file, Tai file nop.
    - Dao van.
    - Exam: Phong thi.
  - Student:
    - Vao phong thi/Nop file/Lam trac nghiem/Lam bai.
- Main content:
  - Mo ta.
  - Huong dan.
  - File mode: yeu cau file (extensions, size, max files, flags).
  - Code mode: testcases, teacher co import/them/sua/xoa, student chi thay sample.
  - Quiz mode: cau hinh trac nghiem, so cau, thu tu, hien ket qua.
  - Tai lieu dinh kem: teacher upload/delete, student open file.
- Sidebar:
  - Teacher checklist cong bo.
  - Cong bo diem.
  - Thong tin bai tap.
  - Student CTA bat dau.
  - Rubric (student view) hoac form quan ly rubric (teacher).
  - Teacher quick stats.
  - Danger zone xoa bai.

### 10.5 Testcase/import/file requirements

- `testcase_form.html`:
  - Form them/sua testcase.
  - Input name, input_data, expected_output, weight, order, timeout, memory.
  - Checkbox sample/hidden.
- `import_testcases.html`:
  - Form import JSON/CSV qua upload hoac paste content.
  - Checkbox clear existing.
  - Sidebar huong dan dinh dang JSON/CSV.
- `file_requirements.html`:
  - Cau hinh file mode cho teacher.
  - Hien allowed extensions, max size, max files, require comment, resubmit, require all, scan.
  - Lien ket ve assignment detail.

### 10.6 Quiz management

- `quiz_manage.html`:
  - Header assignment title.
  - Actions: Preview, Import CSV, Export CSV, Attempts.
  - Stats/cau hinh quiz.
  - Danh sach cau hoi voi type, points, status, tags.
  - Actions sua, an/hien, xoa.
  - Sidebar/form them cau hoi nhanh.
- `quiz_question_form.html`:
  - Sua cau hoi, include `quiz_question_fields.html`.
- `quiz_question_fields.html`:
  - Fields: question_text, question_type, points, order_index, difficulty, choices_text, correct_answers, explanation, tags, media_url.
- `quiz_import.html`:
  - Upload/paste CSV, preview table, confirm import, clear existing, history import.
- `quiz_preview.html`:
  - Xem truoc cau hoi va dap an theo layout student-like.
- `quiz_attempts.html`:
  - Filter status, bang attempts hoc sinh, link cham/dieu chinh submission.

### 10.7 Statistics, plagiarism, reports

- `statistics.html`:
  - Dashboard thong ke bai: tong submissions, unique students, avg score, pass rate.
  - Bo loc/status va cac bang thong ke theo hoc sinh/testcase/late/missing.
  - Export dropdown va bulk regrade.
- `plagiarism.html`:
  - Header assignment, thong tin report moi nhat.
  - Bang cap bai nop, similarity, text/token/structural score, status dang chu y.
  - Sidebar chay kiem tra voi threshold va lich su report.
- `bulk_regrade_confirm.html`:
  - Confirm cham lai toan bo, canh bao xoa ket qua cu nhung giu comments.
- `late_report_print.html`:
  - Trang in rieng A4, co toolbar quay lai, xuat CSV, in/PDF.

## 11. Submissions

### 11.1 IDE code `submissions/solve_problem.html`

Trang full-screen dark, khong dung `base.html`.

- Head nap Tailwind, base.css, CodeMirror, markdown renderer.
- Topbar:
  - Logo `DevLearn IDE` link ve assignment detail.
  - Nav: Bai tap, Lop hoc, Lich su nop.
  - Exam timer neu exam.
  - Save status.
  - So lan da nop.
  - Profile.
- Main workspace:
  - Left panel 420px:
    - Tabs: De bai, Tai lieu, Testcases.
    - De bai render markdown description/instructions, due date, score, difficulty.
    - Tai lieu link file dinh kem.
    - Testcases sample.
  - Right editor:
    - Toolbar file tab `solution`.
    - Select language.
    - Buttons: Chay thu, Nop bai.
    - CodeMirror editor.
    - Bottom panel tabs: Output, Test Results, Custom Input.
  - Status bar duoi cung: Connected, cursor position, UTF-8, Autosave ON.
- JS:
  - Autosave draft.
  - Run sample testcase.
  - Run custom input.
  - Submit code.
  - Exam timer auto-submit.
  - Exam event tracking: tab hidden/focus/fullscreen/paste/copy/context menu.

### 11.2 Nop file `submissions/submit_file.html`

- Ke thua base.
- Breadcrumb: classroom -> assignment -> Nop file.
- Header co badge Nop file, badge Bai thi neu exam, due date, remaining attempts/time, link history/detail.
- Main:
  - De bai: description/instructions.
  - Form upload:
    - Drop zone keo tha/chon file.
    - Preview selected files.
    - Error box validate extension/size/count.
    - Textarea ghi chu.
    - Nut nop bai, nut xoa file.
    - Mobile sticky submit bar.
  - Neu exam: card phien thi, timer, hidden session_id.
  - Lich su nop file: card submission, status, late, so file, diem, link detail.
- Sidebar:
  - Yeu cau file.
  - Tai lieu de bai.
- JS:
  - Validate file client-side.
  - Draft note localStorage/server clear.
  - Exam timer, ping/event logging.

### 11.3 Quiz lobby `submissions/quiz_lobby.html`

- Breadcrumb: classroom -> assignment -> Quiz.
- Header H1 assignment, link ve de bai.
- Main card:
  - So cau.
  - Open error neu chua mo/het dieu kien.
  - Neu co attempt dang lam: card tiep tuc.
  - Form bat dau luot moi, disabled neu het luot/in progress.
- Sidebar:
  - Da lam, con lai, thoi gian, xem diem, xem lai.
- Section lich su attempts:
  - Bang attempt no, status, started/submitted, score, action tiep tuc/xem ket qua.

### 11.4 Lam quiz `submissions/quiz_take.html`

- Sticky header:
  - Badge quiz/exam quiz.
  - H1 assignment.
  - Autosave status.
  - Timer neu co.
- Form:
  - Main list question cards:
    - So thu tu, type, points, state badge.
    - Question text, media link neu co.
    - Short text textarea hoac choices radio/checkbox.
  - Sidebar sticky:
    - Tien do answered count + progress bar.
    - Grid nav den tung cau.
    - Nut nop quiz.
  - Mobile sticky submit.
- JS:
  - Autosave tung cau qua AJAX.
  - Refresh progress/nav.
  - Confirm submit.
  - Timer auto-submit.
  - Exam event logging neu attempt la exam.

### 11.5 Ket qua quiz `submissions/quiz_result.html`

- Breadcrumb: assignment -> quiz -> result.
- Header: status badge, assignment title, attempt no, submitted time.
- Actions: lich su quiz, ban ghi diem neu co submission.
- Sidebar:
  - Status, duration, score, passing score.
  - Note neu chua cho review hoac an dap an.
- Main:
  - Neu duoc review: list question cards.
  - Moi cau hien answer state, diem, dap an da chon, dap an dung neu duoc phep, explanation neu duoc phep.
  - Neu khong duoc review: empty locked card.

### 11.6 Exam lobby `submissions/exam_lobby.html`

- Card max 4xl.
- Breadcrumb classroom -> assignment -> Phong thi.
- Header exam mode, title, classroom, session status.
- 3 info cards: duration, open time, close time.
- Neu file exam: card yeu cau file.
- Neu quiz exam: card so cau/so luot/xem diem.
- Card quy che phien thi.
- CTA theo status:
  - Running: tiep tuc.
  - Da nop: xem submission/quiz result.
  - Expired/cancelled/closed/not opened: disabled + alert.
  - Chua start: form bat dau thi.

### 11.7 Exam monitor `submissions/exam_monitor.html`

- Breadcrumb classroom -> assignment -> Theo doi phong thi.
- Header co dropdown CSV, nut ve bai thi.
- 5 stats: chua vao, dang lam, da nop, het gio, warning.
- Tabs filter status: all/running/submitted/expired.
- Bang sessions:
  - Student, status, start/end, run/file/answered count, warnings, score neu quiz, final submission/attempt, actions.
  - Actions gom gia han phien, force submit, link submission/quiz result.

### 11.8 History/detail/list teacher/grade

- `history.html`:
  - Lich su submissions cua mot assignment.
  - Card/bang theo lan nop, status, score, submitted time, late, link detail.
- `detail.html`:
  - Student/teacher xem bai nop.
  - Header submission, status, score.
  - Code mode: code block, testcase results.
  - File mode: file da nop, feedback files.
  - Quiz mode: answer summary.
  - Feedback/rubric/comments neu co quyen.
- `list_teacher.html`:
  - Giao vien xem tat ca submissions cua assignment.
  - Filter/search/status, export/download zip.
  - Bang student, submission, status, score, late, action grade/detail.
- `grade.html`:
  - Man cham diem.
  - Main panel code/file/quiz answer.
  - Sidebar cham diem: manual score, feedback, rubric scores, AI suggestion neu co, file feedback, save.
  - Code comments theo dong, AJAX add/resolve comment.

## 12. Discussions

### 12.1 List `discussions/list.html`

- Breadcrumb classroom -> assignment -> Thao luan.
- Header co eyebrow, title, description, CTA `Dat cau hoi`.
- Search bar.
- Tabs:
  - Tat ca.
  - Chua tra loi.
  - Cau hoi cua toi.
  - Pho bien.
- Bang topic:
  - Chu de, preview, pin icon.
  - Votes.
  - So tra loi.
  - Trang thai: Da giai/Dang thao luan/Cho tra loi.
  - Nguoi dang + avatar chu cai.
- Pagination.
- Empty state co CTA dat cau hoi.

### 12.2 Create/Edit

- `create.html`:
  - Breadcrumb, title "Dat cau hoi moi".
  - Form title, content, Huy, Dang cau hoi.
- `edit.html`:
  - Dung cho topic hoac reply.
  - Topic co field title, reply chi co content.
  - Huy ve detail tuong ung.

### 12.3 Detail `discussions/detail.html`

- Breadcrumb classroom -> assignment -> discussions -> title.
- Topic card:
  - Vote column up/down.
  - Pin icon neu pinned.
  - Title, body, author, created/updated.
  - Teacher/owner actions: pin, edit, delete.
- Replies:
  - Moi reply card co vote column.
  - Accepted answer co banner xanh.
  - Teacher co button mark answer.
  - Owner/teacher edit/delete.
- Reply form cuoi trang.
- JS goi AJAX vote, mark answer, pin va reload.

## 13. Notifications

### 13.1 List `notifications/list.html`

- Header:
  - Eyebrow Notifications.
  - Title, description.
  - Neu co unread: form mark all read.
- Filter buttons: Tat ca, Chua doc.
- List card:
  - Icon theo notification_type.
  - Title, message, created_at.
  - Unread co nen primary nhe va dot xanh.
  - Click item -> `notifications:open`.
  - Unread co nut `Da doc`.
- Empty state neu khong co thong bao.

### 13.2 Lien ket voi header

- Header dropdown dung recent notifications.
- `notifications:open` danh dau doc roi redirect den `notification.link`, neu khong co link thi ve list.

## 14. Administration

Tat ca trang admin ke thua `administration/base_admin.html`, nen van co navbar/footer global va them admin shell.

### 14.1 Admin shell `administration/base_admin.html`

- Layout flex full height.
- Sidebar desktop `w-72`, an tren mobile.
- Sidebar co cac nhom:
  - Tong quan: Dashboard, Analytics.
  - Nguoi dung: Tai khoan, Hoc sinh, Giao vien, co badge pending teachers.
  - Hoc tap: Lop hoc, Mon hoc, Ky hoc, co badge pending classrooms/subjects.
  - Cham code: Ngon ngu, Cau hinh Sandbox, Sandbox Monitor.
  - Giam sat: Server Metrics, Su kien thi, Nhat ky hoat dong.
  - Cau hinh: Cai dat he thong.
- Mobile:
  - `<details>` "Menu admin" voi grid nut tat.
- Main content:
  - Padding 4/8.
  - Max width 6xl.
  - Trang con render vao `{% block admin_content %}`.

### 14.2 Dashboard `administration/dashboard.html`

- Trung tam tong quan admin.
- Hien stats he thong: users, teachers, students, classrooms, assignments/submissions, pending approvals, sandbox/metrics tuy context.
- Cac card hang cho duyet dan den teacher/classroom/subject management.
- Cac section gan day: submissions/logs/exam events/server health.

### 14.3 User management

- `user_management.html`:
  - Header page title, CTA tao user, CSV dropdown.
  - Tabs role/status: all, students, teachers, admins, inactive.
  - Filter basic: search, role, status.
  - Advanced filters: profile status, classroom, subject, last login, teaching classes, joined class, submissions, submission status, joined date.
  - Include filter status partial: copy link, save filter, saved filters, clear.
  - Teacher approval block neu page teacher: filter approval status/search/institution/reviewer/date, table approve/reject.
  - Bulk action form user_ids.
  - Bang users: checkbox, user info, role, activity, class, status, actions detail/edit.
  - Pagination.
- `user_detail.html`:
  - Header user name, actions edit/reset password.
  - Thong tin user/profile.
  - Bai nop gan day link submission detail.
  - Lich su hoat dong.
- `user_form.html`:
  - Form create/edit: username, email, first/last name, role, password, active.
- `user_reset_password.html`:
  - Form new password/confirm.
- `teacher_management.html` va student route dung bien the cua user management/filter theo role.
- `teacher_approvals.html`: trang rieng/hoac cu, table don dang ky GV va nut approve/reject.

### 14.4 Classroom/subject management

- `classroom_management.html`:
  - Header, CSV dropdown.
  - Tabs approval/active: all, pending, approved, active, inactive.
  - Filter search/status, advanced filter subject, teacher, semester, active, member min/max, capacity, has subjects, has assignments, has exams, pending members.
  - Bulk actions.
  - Bang lop: ten, teacher, member/capacity, subjects/assignments, status, actions approve/reject/link.
- `subject_management.html` / `subject_approvals.html`:
  - Header, CSV dropdown.
  - Tabs all/pending/approved/rejected.
  - Filter search/status, languages, creator, classroom/semester.
  - Bulk action.
  - Bang mon: code/name, languages, creator, used count, status, approve/reject.

### 14.5 Languages va sandboxes

- `languages.html`:
  - Danh sach ngon ngu lap trinh.
  - CTA tao language.
  - Bang name/display/version/active/default config.
  - Actions edit/delete/toggle.
- `language_form.html`:
  - Form create/edit language.
- `sandboxes.html`:
  - Danh sach cau hinh sandbox theo ngon ngu.
  - CTA tao sandbox.
  - Bang image/cmd/timeout/memory/active.
  - Actions edit/delete/test.
- `sandbox_form.html`:
  - Form create/edit config sandbox.
- `sandbox_monitor.html`:
  - Monitor hang doi cham code/zombie tasks.
  - Filter status/language/date.
  - Stats queue/running/zombie.
  - Bang submissions dang nghi van.
  - Actions requeue/kill zombie.

### 14.6 Metrics, logs, exam events, analytics

- `server_metrics.html`:
  - Theo doi CPU, memory, disk, docker/queue neu co.
  - Bang/chart-like cards theo metrics moi nhat.
- `activity_logs.html`:
  - Header.
  - Preset 24h/7d/30d.
  - Filter user, user_id, role, date range.
  - Advanced filter action/action_group/resource_type/resource_id/ip.
  - CSV dropdown.
  - Bang logs: user, action, resource, time, IP.
- `exam_events.html`:
  - Filter/search/date/event type/student/assignment.
  - CSV dropdown.
  - Bang su kien thi: session, student, event, metadata, time.
- `analytics.html`:
  - Date range + advanced filters classroom, subject, teacher, language.
  - Stat cards ve submissions/users/classrooms/performance.
  - Bang top/summary theo bo loc.

### 14.7 Settings

- `system_settings.html`:
  - Header CTA them setting.
  - Filter/search/status.
  - Warning/missing required settings.
  - Bang settings key/value/type/active/actions.
  - Toggle/edit/delete.
- `setting_form.html`:
  - Form create/edit setting.

## 15. Dropdown CSV `includes/csv_dropdown.html`

- Component dung trong gradebook, admin pages, exam monitor, reports.
- Dung `<details>`/`summary`.
- Nut mac dinh co icon download.
- Menu canh phai, moi item la link export.
- Co badge neu dang export theo bo loc hien tai.

## 16. Luong lien ket chinh cua website

### 16.1 Anonymous

1. `/` trang chu anonymous.
2. CTA dang ky/dang nhap/Google.
3. Sau login, view redirect theo role:
   - Admin -> admin dashboard.
   - Teacher -> teacher dashboard.
   - Student -> home/dashboard hoc sinh.

### 16.2 Student hoc va nop bai

1. Header/Home/Dashboard -> `classrooms:classroom_list`.
2. Chon lop -> `classrooms:classroom_detail`.
3. Chon mon -> `classrooms:subject_detail` hoac chon bai -> `assignments:detail`.
4. Assignment detail:
   - Code -> `submissions:solve`.
   - File -> `submissions:file_submission`.
   - Quiz -> `submissions:quiz_lobby`.
   - Exam -> `submissions:exam_lobby`.
5. Sau nop:
   - Code/file -> `submissions:detail`.
   - Quiz -> `submissions:quiz_result`.
6. Xem lich su -> `submissions:history`.
7. Xem diem gan day/dashboard -> submission detail.

### 16.3 Teacher tao lop, tao bai, cham bai

1. Header/Teacher dashboard -> `classrooms:create` hoac `classrooms:classroom_list`.
2. Chi tiet lop -> tao/gán mon, tao assignment, import members, gradebook.
3. Tao assignment -> `_assignment_form`, sau do ve assignment detail.
4. Assignment detail:
   - Them testcase/file/rubric.
   - Quiz manage neu quiz.
   - File requirements neu file mode.
   - Publish.
5. Student nop bai -> teacher vao:
   - Dashboard "Bai can xem".
   - Assignment statistics.
   - Teacher submission list.
   - Grade page.
6. Exam:
   - Assignment detail -> exam monitor.
   - Exam monitor -> gia han/force submit/cham submission.

### 16.4 Admin van hanh

1. Header -> Admin dashboard.
2. Sidebar -> users/classrooms/subjects/languages/sandboxes/settings/logs.
3. Hang cho duyet:
   - Teacher registrations -> approve/reject.
   - Classrooms -> approve/reject.
   - Subjects -> approve/reject.
4. Giam sat:
   - Exam events de xem hanh vi thi.
   - Sandbox monitor de xu ly zombie/requeue.
   - Server metrics de xem suc khoe he thong.
5. Bao cao:
   - Analytics/logs/exam events co filter, save filter, CSV export.

## 17. Responsive va hanh vi tuong tac

- Header fixed; body content co padding-top 60px.
- Nav desktop an tren mobile, nhung header action van con.
- Nhieu bang co `overflow-x-auto` va `min-w` de khong vo layout.
- Cac form lon dung grid 1 cot tren mobile, 2/3/4 cot tren desktop.
- Trang IDE co breakpoint <= 900px doi workspace tu ngang sang doc:
  - Instructions panel full width, cao 36vh.
  - Editor min-height 62vh.
  - Bottom panel min-height 220px.
- Submit file va quiz_take co sticky submit bar tren mobile.
- Global loading:
  - Tu dong hien khi click link noi bo/form submit.
  - Bo qua link anchor, download, CSV/PDF/ZIP/export, target blank.
  - Fail-safe tu an sau 12 giay.
- Admin filters:
  - Co copy filter link.
  - Save filter vao localStorage theo pathname.
  - Co saved filter dropdown.

## 18. Danh sach template frontend da quet

- Accounts: login, register, profile, edit_profile, student_dashboard, teacher_dashboard, teacher_register, password reset templates.
- Classrooms: list, search, create, edit, detail, join, gradebook, subjects, subject_detail, subject_form, subject_assign, import_members, create_announcement, leaderboard, semester pages, delete confirm.
- Assignments: calendar, list, detail, create/edit form, testcase, import testcases, file requirements, quiz management, statistics, plagiarism, bulk regrade, late report print.
- Submissions: solve IDE, submit file, quiz lobby/take/result, exam lobby/monitor, history, detail, teacher list, grade.
- Discussions: list, detail, create, edit.
- Notifications: list.
- Administration: base admin, dashboard, user/classroom/subject/language/sandbox/settings/metrics/logs/exam events/analytics pages.
- Includes: navbar, footer, csv dropdown.

## 19. Ghi chu dat ten va typo

- Namespace/app dang dung la `administation` (thieu chu `r` trong "administration") trong URL namespace va app folder. Tai lieu nay giu dung ten route hien co, vi template dang goi `{% url 'administation:...' %}`.
- File `late_report_print.html` khong ke thua layout chung vi phuc vu print/PDF.
- `solve_problem.html` khong ke thua layout chung vi la IDE full-screen.

