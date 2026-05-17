# Ke hoach bo sung chuc nang tien ich cho LH Programming

> Muc tieu cua file nay la gom lai cac chuc nang nen lam tiep theo de he thong tien dung hon cho giao vien, hoc sinh va admin.
> Lam toi dau tick toi do. Moi phase deu co phan `Check` va `Review` de tranh lam xong ma kho biet da on chua.

---

## Tong quan hien trang

He thong hien da co cac khoi chinh:

- Tai khoan, dang nhap, profile, dang ky giao vien.
- Lop hoc, ma moi, thanh vien, thong bao lop, bang xep hang.
- Mon hoc, hoc ky, gan mon vao lop, duyet mon/lop/giao vien.
- Bai tap, testcase, import testcase JSON/CSV, file dinh kem, cong bo/an bai.
- IDE nop code, autosave, run test, submit, cham tu dong, cham tay.
- Comment theo dong code, lich su nop bai.
- Dashboard hoc sinh, thong ke bai tap, dashboard admin, analytics, sandbox monitor.

Cac khoang trong ban dau da xu ly:

- [x] Notification/inbox luu trong DB.
- [x] Dashboard rieng cho giao vien.
- [x] So diem tong hop theo lop.
- [x] Lich deadline dung nghia.
- [x] Import hoc sinh hang loat vao lop.
- [x] Rubric/feedback mau khi cham bai.
- [x] UI/report kiem tra dao van cho giao vien.
- [x] Sua route admin `teachers/` bi khai bao trung.

---

## Nguyen tac trien khai

- Lam tung phase nho, khong tron nhieu chuc nang lon vao mot lan.
- Sau moi phase phai chay check, mo UI lien quan, review quyen truy cap.
- Uu tien dung pattern hien co: Django app, function-based views, templates Tailwind, `messages`, decorators `teacher_required` / `admin_required`.
- Cac bang moi can co migration ro rang va admin registration neu can quan ly.
- Chuc nang nao co lien quan 3 role thi uu tien notification truoc, vi no ket noi cac workflow lai voi nhau.

---

## Bang uu tien

| Thu tu | Chuc nang | Loi ich chinh | Do kho | Trang thai |
|---|---|---|---|---|
| 0 | Sua route admin bi trung | Giam loi dieu huong admin | Thap | [x] Hoan thanh |
| 1 | Notification Center | Ca 3 role biet viec can xu ly | Trung binh | [x] MVP hoan thanh |
| 2 | Teacher Dashboard | Giao vien co noi lam viec hang ngay | Trung binh | [x] Hoan thanh |
| 3 | Gradebook theo lop | Giao vien quan ly diem nhanh | Cao | [x] Hoan thanh |
| 4 | Calendar Deadline | Hoc sinh/giao vien xem deadline ro | Trung binh | [x] Hoan thanh |
| 5 | Import hoc sinh hang loat | Giao vien/admin setup lop nhanh | Trung binh | [x] Hoan thanh |
| 6 | Rubric va feedback mau | Cham bai nhanh, minh bach | Cao | [x] Hoan thanh |
| 7 | Plagiarism UI | Dung service da co de bat dao van | Trung binh | [x] Hoan thanh |

---

## Phase 0 - Sua route admin bi trung

### Van de

Trong `apps/administation/urls.py` dang co 2 route cung path `teachers/`:

- `teacher_approvals_view`
- `teacher_management_view`

Django se match route dau tien truoc, lam route sau kho truy cap dung cach.

### Kich ban sua

1. Doi route duyet giao vien thanh:
   - `/administration/teacher-approvals/`
   - name giu `teacher_approvals`.
2. Giu route quan ly giao vien:
   - `/administration/teachers/`
   - name `teacher_management`.
3. Quet template de cap nhat link neu co hardcode URL path.
4. Chay check.

### File du kien dung

- `apps/administation/urls.py`
- `templates/administration/base_admin.html`
- `templates/administration/dashboard.html`
- Bat ky template nao dang goi `{% url 'administation:teacher_approvals' %}` thi khong can doi neu name giu nguyen.

### Check

- [x] `python manage.py check`
- [x] Vao `/administration/teacher-approvals/` thay danh sach don GV.
- [x] Vao `/administration/teachers/` thay quan ly GV.
- [x] Click sidebar admin khong bi sai trang.

### Review

- [x] Khong doi ten URL name neu khong can.
- [x] Khong lam vo link dashboard admin.
- [x] Admin-only van duoc bao ve boi `admin_required`.

---

## Phase 1 - Notification Center

### Muc tieu

Them trung tam thong bao de giao vien, hoc sinh va admin khong phai tu di tim viec moi. Day la chuc nang nen lam dau tien vi no tang do tien dung cua toan bo he thong.

### Role duoc loi

- Hoc sinh: biet bai moi, deadline, bai da cham, comment moi.
- Giao vien: biet hoc sinh xin vao lop, bai nop moi, bai can cham.
- Admin: biet don giao vien/lop/mon can duyet, sandbox co zombie task.

### Model goi y

Them app moi `notifications` hoac dat trong app `administation`. Khuyen tao app rieng `apps.notifications` neu muon sach.

Bang `Notifications`:

| Field | Kieu | Ghi chu |
|---|---|---|
| recipient | FK User | Nguoi nhan |
| actor | FK User nullable | Nguoi gay ra su kien |
| notification_type | Char/Text | `assignment_published`, `submission_graded`, ... |
| title | Text | Tieu de ngan |
| message | Text | Noi dung |
| link | Text nullable | Link click vao |
| is_read | Boolean | Mac dinh false |
| read_at | DateTime nullable | Thoi diem doc |
| metadata | JSONField nullable | Du lieu bo sung |
| created_at | DateTime | Tao luc |

### Cac loai thong bao can co

| Type | Nguoi nhan | Trigger |
|---|---|---|
| `assignment_published` | Hoc sinh trong lop | Giao vien cong bo bai |
| `assignment_due_soon` | Hoc sinh chua nop | Job/dash check deadline |
| `submission_submitted` | Giao vien | Hoc sinh nop bai |
| `submission_graded` | Hoc sinh | Cham tu dong/cham tay xong |
| `code_comment_added` | Hoc sinh | GV comment dong code |
| `class_join_requested` | Giao vien | Hoc sinh xin vao lop neu bat duyet |
| `class_join_approved` | Hoc sinh | GV duyet vao lop |
| `teacher_registration_pending` | Admin | User gui don GV |
| `classroom_pending` | Admin | GV tao lop cho duyet |
| `subject_pending` | Admin | GV tao mon cho duyet |
| `sandbox_zombie_detected` | Admin | Co submission pending/running qua lau |

### Service helper

Tao file:

- `apps/notifications/services.py`

Ham goi y:

```python
def notify_user(recipient, title, message, link='', notification_type='', actor=None, metadata=None):
    ...

def notify_users(recipients, title, message, link='', notification_type='', actor=None, metadata=None):
    ...

def mark_all_read(user):
    ...
```

### UI can co

- Badge tren navbar: so thong bao chua doc.
- Dropdown thong bao gan day.
- Trang `/notifications/`: danh sach thong bao, filter `all/unread`.
- Nut "Danh dau da doc".
- Khi click thong bao thi danh dau da doc va redirect sang `link`.

### File du kien dung

- `apps/notifications/models.py`
- `apps/notifications/views.py`
- `apps/notifications/urls.py`
- `apps/notifications/services.py`
- `apps/notifications/admin.py`
- `core/urls.py`
- `core/settings.py`
- `templates/includes/navbar.html`
- `templates/notifications/list.html`
- Cac view trigger:
  - `apps/assignments/views.py`
  - `apps/submissions/views.py`
  - `apps/classrooms/views.py`
  - `apps/administation/views.py`

### Kich ban trien khai

1. Tao app/model/migration.
2. Tao helper service de view khac goi gon.
3. Tao context processor hoac include logic trong navbar de lay unread count.
4. Tao URL/view list, mark read, mark all read.
5. Gan trigger vao cac action quan trong:
   - Publish assignment.
   - Submit code.
   - Grade submission.
   - Add code comment.
   - Join/approve classroom.
   - Admin approval workflow.
6. Them template list va badge navbar.

### Check

- [x] `python manage.py makemigrations notifications`
- [x] `python manage.py migrate`
- [x] `python manage.py check`
- [x] Tao bai moi/cong bo bai -> da gan trigger notification cho hoc sinh trong lop.
- [x] Hoc sinh nop bai -> da gan trigger notification cho giao vien.
- [x] GV cham bai/comment code -> da gan trigger notification cho hoc sinh.
- [x] Admin duyet/tu choi -> da gan trigger notification cho nguoi lien quan.
- [x] Click thong bao redirect dung link.
- [x] Mark read/mark all read hoat dong.

### Review

- [x] Khong query unread count qua nang o moi request.
- [x] Link thong bao khong lo thong tin cho user khong co quyen.
- [x] Trigger khong tao duplicate qua nhieu thong bao cho cung mot action.
- [x] Template mobile khong bi vo layout navbar.

### Backlog ban nang cao

- `assignment_due_soon`: can them scheduled job/Celery beat hoac management command chay dinh ky.
- `class_join_requested`: hien workflow join hien tai dang auto-approve, chi can them khi bo sung che do "can duyet".
- `sandbox_zombie_detected`: nen gan sau vao Sandbox Monitor neu muon canh bao tu dong.

---

## Phase 2 - Teacher Dashboard

### Muc tieu

Tao trang lam viec rieng cho giao vien, gom viec can lam trong ngay vao mot noi.

### URL de xuat

- `/accounts/teacher-dashboard/`
- URL name: `accounts:teacher_dashboard`

### Noi dung dashboard

#### Khoi tong quan

- So lop dang day.
- So hoc sinh dang hoc.
- So bai tap da cong bo.
- So bai nop trong 7 ngay.
- So bai dang pending/running/failed.
- So don xin vao lop dang cho.

#### Viec can xu ly

- Bai nop moi can xem/cham.
- Bai project/manual grade can cham tay.
- Bai co testcase fail nhieu.
- Hoc sinh chua nop bai sap den han.
- Lop/mon dang cho admin duyet.

#### Quick actions

- Tao lop.
- Tao bai tap.
- Import testcase.
- Xem so diem.
- Xem late report.

### File du kien dung

- `apps/accounts/views.py`
- `apps/accounts/urls.py`
- `templates/accounts/teacher_dashboard.html`
- `templates/includes/navbar.html`

### Query goi y

- `Classrooms.objects.filter(teacher=request.user, is_active=True)`
- `Assignments.objects.filter(classroom__teacher=request.user)`
- `Submissions.objects.filter(assignment__classroom__teacher=request.user)`
- `ClassroomMembers.objects.filter(classroom__teacher=request.user, status='pending')`

### Kich ban trien khai

1. Tao view `teacher_dashboard_view`.
2. Neu user la teacher thi login redirect ve dashboard giao vien thay vi dashboard hoc sinh.
3. Tao template gom cac card va list viec can lam.
4. Them link navbar "Dashboard" tro dung dashboard theo role.
5. Neu co notification center, hien 5 thong bao moi nhat trong dashboard.

### Check

- [x] `python manage.py check`
- [x] Teacher login vao dung dashboard giao vien.
- [x] Student van vao dashboard hoc sinh.
- [x] Admin van vao dashboard admin.
- [x] Cac card so lieu dung voi DB.
- [x] Link quick action dung URL.

### Review

- [x] View khong bi N+1 query qua nang.
- [x] Chi lay du lieu cua lop do giao vien so huu.
- [x] Khong cho teacher xem data lop cua teacher khac.
- [x] Empty state dep khi giao vien chua co lop/bai.

---

## Phase 3 - Gradebook theo lop

### Muc tieu

Them so diem tong hop theo lop de giao vien xem nhanh diem cua tung hoc sinh tren tat ca bai tap.

### URL de xuat

- `/classrooms/<pk>/gradebook/`
- URL name: `classrooms:gradebook`

### Man hinh chinh

Bang diem:

- Hang: hoc sinh trong lop.
- Cot: bai tap da publish hoac tat ca bai neu teacher.
- O diem: diem cao nhat cua hoc sinh cho bai do.
- Trang thai: chua nop, dang cham, finished, late.
- Tong diem, diem trung binh, so bai da nop, completion rate.

Filter:

- Mon hoc.
- Hoc ky.
- Trang thai nop.
- Chi hien bai da publish.

Export:

- CSV/Excel.
- Cot co dau tieng Viet, BOM UTF-8.

### Du lieu can tinh

Voi moi `(student, assignment)`:

- Lay submission cao diem nhat:
  - `Max(total_score)` voi `status='finished'`
  - neu co manual score thi can quy dinh lay `manual_score` hay `total_score`
- Co nop tre khong.
- So lan nop.
- Lan nop gan nhat.

### File du kien dung

- `apps/classrooms/views.py`
- `apps/classrooms/urls.py`
- `templates/classrooms/gradebook.html`
- Co the them helper `apps/classrooms/services.py` neu logic dai.

### Kich ban trien khai

1. Tao view `gradebook_view` chi teacher/admin/class teacher xem.
2. Lay danh sach assignments theo classroom + filter.
3. Lay danh sach members approved.
4. Query submissions theo classroom mot lan, group bang Python de tranh query trong loop.
5. Tao matrix rows.
6. Render table scroll ngang.
7. Them export CSV route:
   - `/classrooms/<pk>/gradebook/export/`
8. Them link tu classroom detail.

### Check

- [x] `python manage.py check`
- [x] Teacher xem duoc gradebook lop minh.
- [x] Student khong xem duoc gradebook.
- [x] Admin xem duoc neu can.
- [x] Lop co nhieu bai khong vo layout ngang.
- [x] Export CSV mo duoc tieng Viet trong Excel.
- [x] Diem trong bang khop submission detail.

### Review

- [x] Khong query DB trong nested loop student x assignment.
- [x] Xu ly hoc sinh chua nop ro rang.
- [x] Xu ly assignment khong co max_score hoac max_score = 0.
- [x] Tinh diem/avg nhat quan voi dashboard hoc sinh.

---

## Phase 4 - Calendar Deadline

### Muc tieu

Cho hoc sinh va giao vien xem deadline theo lich tuan/thang thay vi chi list ngan.

### URL de xuat

- `/assignments/calendar/`
- URL name: `assignments:calendar`

### Doi tuong

Hoc sinh:

- Chi thay bai publish trong lop da tham gia.
- Mau theo trang thai:
  - chua nop
  - da nop
  - sap het han
  - qua han

Giao vien:

- Thay bai trong lop minh day.
- Co filter lop/mon/hoc ky.

### UI goi y

- View thang.
- View tuan.
- Sidebar filter.
- Click event mo assignment detail.
- Nut "Hom nay".

### File du kien dung

- `apps/assignments/views.py`
- `apps/assignments/urls.py`
- `templates/assignments/calendar.html`
- Co the dung CSS/JS thuan de tranh them dependency lon.

### Kich ban trien khai

1. Tao view calendar tra template.
2. Tao endpoint JSON optional:
   - `/assignments/calendar/events/`
3. Lay assignments theo role.
4. Ghep trang thai submission cua hoc sinh.
5. Render calendar.
6. Link tu dashboard hoc sinh va teacher dashboard.

### Check

- [x] `python manage.py check`
- [x] Student chi thay bai cua minh.
- [x] Teacher chi thay bai lop minh.
- [x] Assignment khong co due_date khong lam loi.
- [x] Click event vao dung detail.
- [x] Mobile khong vo layout.

### Review

- [x] Timezone dung `Asia/Ho_Chi_Minh`.
- [x] Trang thai overdue tinh dung voi `late_submission_allowed`.
- [x] Filter khong lam lo bai chua publish cho student.

---

## Phase 5 - Import hoc sinh hang loat vao lop

### Muc tieu

Giao vien/admin co the them hoc sinh vao lop bang CSV thay vi tung user join bang ma moi.

### URL de xuat

- `/classrooms/<pk>/members/import/`
- URL name: `classrooms:import_members`

### Dinh dang CSV

Cot toi thieu:

```csv
username,email,full_name
student01,student01@example.com,Nguyen Van A
student02,student02@example.com,Tran Thi B
```

Che do import:

- Match user co san theo username/email.
- Neu chua co user:
  - Option A: bo qua va bao loi.
  - Option B: tao account tam voi password random.

Khuyen lam truoc Option A de an toan.

### File du kien dung

- `apps/classrooms/forms.py`
- `apps/classrooms/views.py`
- `apps/classrooms/urls.py`
- `templates/classrooms/import_members.html`

### Kich ban trien khai

1. Tao form upload CSV.
2. Validate file type va size.
3. Parse CSV bang `csv.DictReader`.
4. Match user theo username/email.
5. Tao `ClassroomMembers` status `approved` hoac `pending` tuy classroom setting.
6. Hien preview ket qua:
   - added
   - already member
   - missing user
   - invalid row
7. Them export template CSV mau.

### Check

- [x] `python manage.py check`
- [x] Import user ton tai thanh cong.
- [x] Import user da la member khong tao duplicate.
- [x] Row loi duoc bao ro.
- [x] Student sau khi import thay lop trong danh sach.
- [x] Teacher khac khong import duoc vao lop khong phai cua minh.

### Review

- [x] Dung transaction neu tao nhieu membership.
- [x] Khong tao user moi khi chua co yeu cau ro.
- [x] Xu ly encoding UTF-8 BOM.
- [x] Co thong bao ket qua de giao vien sua file.

---

## Phase 6 - Rubric va feedback mau

### Muc tieu

Giup giao vien cham bai nhanh hon va hoc sinh hieu ro diem bi tru o dau.

### Model goi y

`Rubrics`:

| Field | Ghi chu |
|---|---|
| assignment | FK Assignments |
| name | Ten tieu chi |
| description | Mo ta |
| max_points | Diem toi da |
| order_index | Thu tu |

`RubricScores`:

| Field | Ghi chu |
|---|---|
| submission | FK Submissions |
| rubric | FK Rubrics |
| score | Diem |
| comment | Nhan xet theo tieu chi |

`FeedbackTemplates`:

| Field | Ghi chu |
|---|---|
| teacher | FK User |
| title | Ten mau |
| content | Noi dung |
| category | Vi du: logic, style, edge_case |

### UI can co

- Trong assignment create/edit: tao rubric.
- Trong grade submission: form diem theo tung tieu chi.
- Nut chen feedback mau vao comment.
- Trong submission detail cua hoc sinh: hien rubric breakdown.

### File du kien dung

- `apps/assignments/models.py`
- `apps/submissions/models.py`
- `apps/submissions/forms.py`
- `apps/submissions/views.py`
- `templates/submissions/grade.html`
- `templates/submissions/detail.html`
- Migration moi.

### Kich ban trien khai

1. Them model rubric va feedback template.
2. Them admin registration.
3. Them UI quan ly rubric trong assignment detail/edit.
4. Sua grade view de luu diem theo rubric.
5. Tinh final manual score tu rubric neu teacher chon.
6. Hien rubric breakdown cho hoc sinh.
7. Them feedback templates ca nhan cho teacher.

### Check

- [x] `python manage.py makemigrations`
- [x] `python manage.py migrate`
- [x] `python manage.py check`
- [x] Teacher tao rubric cho assignment.
- [x] Teacher cham theo rubric va luu duoc.
- [x] Student xem duoc breakdown.
- [x] Assignment khong co rubric van cham tay nhu cu.

### Review

- [x] Khong pha workflow cham tay hien co.
- [x] Tong diem rubric khong vuot `assignment.max_score`.
- [x] Sua rubric sau khi da cham can co canh bao.
- [x] Feedback template chi teacher so huu moi sua/xoa duoc.

---

## Phase 7 - Plagiarism UI

### Muc tieu

Bien `services/plagiarism_service.py` va task `check_plagiarism_task` thanh chuc nang giao vien dung duoc tren web.

### URL de xuat

- `/assignments/<pk>/plagiarism/`
- URL name: `assignments:plagiarism`
- `/assignments/<pk>/plagiarism/run/`
- URL name: `assignments:run_plagiarism`

### Model goi y

`PlagiarismReports`:

| Field | Ghi chu |
|---|---|
| assignment | FK Assignments |
| created_by | FK User |
| status | pending/running/finished/error |
| threshold | Mac dinh 0.85 |
| result | JSONField |
| created_at | DateTime |
| finished_at | DateTime nullable |

Co the bat dau khong can model, chay sync va render ket qua. Nhung co model se tot hon vi luu lich su report.

### UI can co

- Nut "Kiem tra dao van" trong trang statistics.
- Bang cap bai giong nhau:
  - sinh vien A/B
  - similarity score
  - text/token/structural score
  - link mo 2 submissions
- Filter chi hien suspicious.
- Canh bao neu it hon 2 submission.

### File du kien dung

- `apps/assignments/views.py`
- `apps/assignments/urls.py`
- `templates/assignments/plagiarism.html`
- `apps/submissions/tasks.py`
- `services/plagiarism_service.py`

### Kich ban trien khai

1. Them route va view.
2. Lay latest finished submission moi sinh vien.
3. Goi `check_plagiarism_batch`.
4. Render bang ket qua.
5. Them nut tu `statistics.html`.
6. Neu muon nang cap: luu report vao DB va chay Celery task.

### Check

- [x] `python manage.py check`
- [x] `python manage.py makemigrations --check --dry-run`
- [x] `python manage.py migrate`
- [x] Teacher lop minh moi chay duoc.
- [x] Student khong truy cap duoc.
- [x] Bai co 0/1 submission hien empty state.
- [x] Bai co nhieu submission hien ket qua sap xep giam dan.
- [x] Link submission detail dung quyen.

### Review

- [x] Khong hien code cua hoc sinh cho nguoi khong co quyen.
- [x] Ghi ro diem similarity chi la goi y, khong ket luan gian lan tuyet doi.
- [x] Neu sync cham qua thi chuyen sang Celery + report model.

---

## Checklist review chung sau moi phase

### Code check

- [x] `python manage.py check`
- [x] `python manage.py makemigrations --check --dry-run`
- [x] Neu co migration: `python manage.py migrate`
- [x] Neu co route moi: test URL bang browser hoac Django test client.

### Quyen truy cap

- [x] Anonymous bi redirect login.
- [x] Student khong vao duoc trang teacher/admin.
- [x] Teacher chi xem/sua lop va bai cua minh.
- [x] Admin xem duoc trang quan tri can thiet.

### UI/UX

- [x] Empty state ro rang.
- [x] Button/action co icon phu hop.
- [x] Bang du lieu scroll duoc tren man hinh nho.
- [x] Message success/error ro nghia.
- [x] Khong co text tran khoi button/card.

### Du lieu

- [x] Khong tao duplicate record.
- [x] Xu ly null/blank.
- [x] Query khong N+1 qua nang.
- [x] Export CSV co UTF-8 BOM neu co tieng Viet.

### Review sau khi xong phase

Ghi lai vao muc nay:

```text
Phase:
Ngay:
Da lam:
Da check:
Loi phat hien:
Quyet dinh sua:
Con ton:
```

---

## Nhat ky thuc hien

### Phase 0

- Trang thai: [x] Hoan thanh
- Ngay: 2026-05-17
- Da lam:
  - Doi route duyet giao vien tu `/administration/teachers/` sang `/administration/teacher-approvals/`.
  - Giu route quan ly giao vien la `/administration/teachers/`.
  - Doi label sidebar tu "Quan ly giao vien" thanh "Duyet giao vien" cho route approvals de tranh nham lan.
- Da check:
  - `python manage.py check` thanh cong.
  - `python manage.py makemigrations --check --dry-run` bao `No changes detected` (co warning DNS trong sandbox khi check migration history voi Supabase).
  - Django URL resolver tra dung:
    - `teacher_approvals` -> `/administration/teacher-approvals/` -> `teacher_approvals_view`
    - `teacher_management` -> `/administration/teachers/` -> `teacher_management_view`
  - Django test client voi user `admin` render 2 trang deu status `200`.
- Loi phat hien:
  - Route cu bi trung `teachers/`.
  - Sidebar co 2 muc cung label "Quan ly giao vien".
- Quyet dinh sua:
  - Giu URL name cu de khong can sua link template dang dung `{% url %}`.
  - Chi doi path approvals va label hien thi.
- Con ton:
  - Khong co.
- Check: [x] Da check
- Review: [x] Da review

### Phase 1

- Trang thai: [x] MVP hoan thanh
- Ngay: 2026-05-17
- Da lam:
  - Tao app `apps.notifications`.
  - Tao model `Notifications` voi recipient, actor, type, title, message, link, read state, metadata.
  - Tao service helper `notify_user`, `notify_users`, `notify_admins`.
  - Them context processor lay unread count va 5 thong bao gan day.
  - Them trang `/notifications/`, filter all/unread, open notification, mark read, mark all read.
  - Them badge va dropdown thong bao vao navbar.
  - Gan trigger cho:
    - Cong bo/tap moi trong assignment.
    - Hoc sinh nop bai.
    - Cham tu dong/cham tay xong.
    - Comment dong code.
    - Hoc sinh tham gia lop va GV duyet thanh vien.
    - User gui don giao vien.
    - GV tao lop/mon cho admin duyet.
    - Admin duyet/tu choi giao vien, lop, mon.
  - Tao migration `apps/notifications/migrations/0001_initial.py`.
  - Da migrate bang `python manage.py migrate notifications` tren Supabase.
- Da check:
  - `python manage.py check` thanh cong.
  - `python manage.py makemigrations --check --dry-run` bao `No changes detected` (co warning DNS trong sandbox khi check migration history voi Supabase).
  - Tao notification smoke test bang service, render `/notifications/` status `200`, co hien notification.
  - Test route `/notifications/<pk>/open/` status `302`, redirect dung link va set `is_read=True`.
  - Render lai `/notifications/` voi navbar dropdown status `200`.
  - `python manage.py showmigrations notifications` tren Supabase bao `[X] 0001_initial`.
- Loi phat hien:
  - Sandbox local khong resolve duoc DNS Supabase nen cac test can DB phai chay escalated.
- Quyet dinh sua:
  - Dung app rieng `apps.notifications` de tach logic, khong nhat vao `administation`.
  - Dung URL text link de trigger gon va tranh import reverse tai nhieu noi.
  - De lai `assignment_due_soon`, `class_join_requested`, `sandbox_zombie_detected` cho ban nang cao vi can workflow/job rieng.
- Con ton:
  - Them scheduled reminder cho deadline.
  - Them che do lop "join can duyet" neu muon dung notification request.
  - Them canh bao zombie sandbox tu dong.
- Check: [x] Da check
- Review: [x] Da review

### Phase 2

- Trang thai: [x] Hoan thanh
- Ngay: 2026-05-17
- Da lam:
  - Them route `/accounts/teacher-dashboard/` voi URL name `accounts:teacher_dashboard`.
  - Them view `teacher_dashboard_view` trong `apps/accounts/views.py`.
  - Doi login redirect cua teacher tu danh sach lop sang teacher dashboard.
  - Doi navbar "Dashboard" theo role:
    - teacher -> teacher dashboard
    - admin/superuser -> admin dashboard
    - student -> student dashboard
  - Tao template `templates/accounts/teacher_dashboard.html`.
  - Dashboard gom:
    - Card lop dang day, hoc sinh, bai tap, bai nop 7 ngay, viec can xu ly.
    - Danh sach bai can xem/cham.
    - Hoc sinh cho duyet vao lop.
    - Bai sap den han trong 7 ngay.
    - Bai co pass rate thap can ho tro.
    - Bai nop gan day.
    - Lop dang day va lop/mon dang cho admin duyet.
- Da check:
  - `python manage.py check` thanh cong.
  - `python manage.py makemigrations --check --dry-run` bao `No changes detected` (co warning DNS trong sandbox khi check migration history voi Supabase).
  - Render `/accounts/teacher-dashboard/` bang teacher `locwara`: status `200`, co title "Bang dieu khien giao vien".
  - Student vao `/accounts/teacher-dashboard/` bi redirect ve `/accounts/dashboard/`.
  - Admin vao `/accounts/teacher-dashboard/` bi redirect ve `/administration/`.
  - Navbar cua teacher co link `/accounts/teacher-dashboard/` va khong con link `/accounts/dashboard/`.
- Loi phat hien:
  - Khong co loi runtime trong render voi du lieu Supabase hien tai.
- Quyet dinh sua:
  - Chua tao model moi; tan dung `Classrooms`, `Assignments`, `Submissions`, `ClassroomMembers`, `AssignmentStatistics`.
  - Chi hien pending class/subject duoi dang danh sach thong tin vi cac doi tuong pending co the chua vao duoc detail public.
- Con ton:
  - Nut tao bai nhanh theo tung lop se tien hon sau khi co gradebook/calendar.
- Check: [x] Da check
- Review: [x] Da review

### Phase 3

- Trang thai: [x] Hoan thanh
- Ngay: 2026-05-17
- Da lam:
  - Them helper build du lieu gradebook trong `apps/classrooms/views.py`.
  - Them route `/classrooms/<pk>/gradebook/` voi URL name `classrooms:gradebook`.
  - Them route `/classrooms/<pk>/gradebook/export/` voi URL name `classrooms:gradebook_export`.
  - Tao template `templates/classrooms/gradebook.html`.
  - Them nut "So diem" tren trang chi tiet lop cho giao vien/admin.
  - Bang diem gom hoc sinh, bai tap, diem cao nhat, so lan nop, bai nop tre, ti le hoan thanh va diem trung binh.
  - Bo loc gom cong bo/ban nhap, mon hoc, hoc ky, trang thai nop.
  - Export CSV co BOM UTF-8 de Excel doc tieng Viet on hon.
  - Dong bo cach tinh diem trung binh o profile/dashboard hoc sinh: uu tien `manual_score`, sau do moi den `total_score`.
- Da check:
  - `python manage.py check` thanh cong.
  - `python manage.py makemigrations --check --dry-run` bao `No changes detected`.
  - Teacher cua lop `Python` vao `/classrooms/1/gradebook/`: status `200`, co title "So diem lop hoc", co link export.
  - Export `/classrooms/1/gradebook/export/`: status `200`, `Content-Type: text/csv; charset=utf-8`, co BOM UTF-8.
  - Student `locwara1` vao `/classrooms/1/gradebook/` bi redirect ve `/classrooms/`.
  - Admin `admin` vao `/classrooms/1/gradebook/`: status `200`.
  - Render lai `/accounts/dashboard/` bang student `locwara1`: status `200` sau khi dong bo cach tinh diem.
- Loi phat hien:
  - Khong co migration moi vi phase nay chi them view/template.
  - Khi chay trong sandbox, lenh check migration co the gap DNS Supabase; da chay lai ngoai sandbox va sach.
- Quyet dinh sua:
  - Diem hien thi uu tien `manual_score` neu co, neu khong thi dung `total_score`.
  - Moi cap hoc sinh/bai tap lay submission `finished` diem cao nhat; neu chua finished thi hien submission moi nhat va status.
  - Query submissions mot lan roi group bang Python de tranh query trong nested loop.
- Con ton:
  - Co the them export Excel `.xlsx` that su neu can dinh dang dep hon CSV.
  - Co the them cot tong diem co trong so sau Phase rubric.
- Check: [x] Da check
- Review: [x] Da review

### Phase 4

- Trang thai: [x] Hoan thanh
- Ngay: 2026-05-17
- Da lam:
  - Them route `/assignments/calendar/` voi URL name `assignments:calendar`.
  - Them JSON endpoint `/assignments/calendar/events/` voi URL name `assignments:calendar_events`.
  - Them helper build du lieu lich trong `apps/assignments/views.py`.
  - Tao template `templates/assignments/calendar.html`.
  - Ho tro view thang/tuan, nut Hom nay, lui/toi thang hoac tuan.
  - Filter theo lop, mon hoc, hoc ky; teacher/admin co them filter da cong bo/ban nhap.
  - Student chi query bai `is_published=True` trong lop da tham gia approved.
  - Teacher chi query lop minh day; admin co the xem toan bo lop active.
  - Ghep status submission cho student:
    - `completed`: da nop xong.
    - `submitted`: da gui nhung chua finished.
    - `due_soon`: sap het han trong 48 gio.
    - `overdue_open`: qua han nhung con cho nop muon.
    - `overdue_closed`: qua han va da dong.
  - Them danh sach bai khong co deadline trong sidebar de khong bi loi/bi mat thong tin.
  - Them link "Lich" tren navbar, dashboard hoc sinh va teacher dashboard.
- Da check:
  - `python manage.py check` thanh cong.
  - `python manage.py makemigrations --check --dry-run` bao `No changes detected`.
  - Student `locwara1` vao `/assignments/calendar/`: status `200`, co title "Lich deadline".
  - Student go ep `?published=draft` khong hien filter ban nhap va van chi query bai published.
  - Teacher `locwara` vao `/assignments/calendar/?view=week`: status `200`.
  - JSON `/assignments/calendar/events/`: status `200`, tra `application/json`.
  - Chon thang co bai `print` cua lop `Python`: teacher thay event, JSON tra url `/assignments/3/`.
  - Student trong lop `Python` thay bai `print` vi bai nay da published.
- Loi phat hien:
  - Thang hien tai co the khong co event nen test can chon dung `date` theo deadline co san trong DB.
- Quyet dinh sua:
  - Dung render server-side va CSS thuan de tranh them dependency lich lon.
  - Dung `timezone.localtime` va `settings.TIME_ZONE` hien tai la `Asia/Ho_Chi_Minh`.
  - Overdue cua student tach theo `late_submission_allowed` de hien "Qua han" nhung con nop muon khac voi "Da dong".
- Con ton:
  - Co the them drag/drop doi deadline cho teacher sau nay neu can thao tac nhanh tren lich.
- Check: [x] Da check
- Review: [x] Da review

### Phase 5

- Trang thai: [x] Hoan thanh
- Ngay: 2026-05-17
- Da lam:
  - Them `MemberImportForm` trong `apps/classrooms/forms.py`.
  - Them route `/classrooms/<pk>/members/import/` voi URL name `classrooms:import_members`.
  - Them view `import_members_view` trong `apps/classrooms/views.py`.
  - Them download CSV mau bang `?sample=1`.
  - Tao template `templates/classrooms/import_members.html`.
  - Them link "Import" trong khoi thanh vien cua trang chi tiet lop.
  - Parse CSV bang `csv.DictReader`, ho tro UTF-8 BOM.
  - Match user co san theo username/email, khong tao user moi.
  - Bo qua dong loi: missing user, role khong phai student, user la giao vien cua lop, username/email khop 2 tai khoan khac nhau, duplicate trong file.
  - Tao/cap nhat `ClassroomMembers` trong transaction va gan status `approved`.
  - Gui notification cho hoc sinh duoc them vao lop.
- Da check:
  - `python manage.py check` thanh cong.
  - `python manage.py makemigrations --check --dry-run` bao `No changes detected`.
  - Import user ton tai thanh cong, tao dung 1 membership `approved`.
  - Import cung user lap lai trong file khong tao duplicate va hien thong bao duplicate.
  - Dong missing user va role teacher duoc bao loi ro tren bang ket qua.
  - CSV mau tra `Content-Type: text/csv; charset=utf-8` va co BOM UTF-8.
  - Teacher khac vao `/classrooms/<pk>/members/import/` bi redirect ve `/classrooms/`.
  - Student sau khi import dang nhap vao `/classrooms/` thay lop vua duoc them.
- Loi phat hien:
  - Khong co migration moi vi chi them form/view/template.
- Quyet dinh sua:
  - Chon Option A: khong tao account tam, chi bao missing user de giao vien/admin xu ly truoc.
  - Import hop le van tiep tuc ngay ca khi file co mot so dong loi, de giao vien khong phai sua lai toan bo file.
- Con ton:
  - Co the them che do tao account tam/random password neu sau nay admin muon onboarding hang loat tu dau.
- Check: [x] Da check
- Review: [x] Da review

### Phase 6

- Trang thai: [x] Hoan thanh
- Ngay: 2026-05-17
- Da lam:
  - Them model `Rubrics` trong `apps/assignments/models.py`.
  - Them model `RubricScores` va `FeedbackTemplates` trong `apps/submissions/models.py`.
  - Tao migration:
    - `apps/assignments/migrations/0004_rubrics.py`
    - `apps/submissions/migrations/0002_feedbacktemplates_rubricscores.py`
  - Register admin cho rubrics, rubric scores va feedback templates.
  - Them UI quan ly rubric ngay trang chi tiet assignment:
    - Teacher them tieu chi.
    - Teacher an tieu chi, co confirm canh bao diem da cham van duoc luu.
    - Student xem rubric cua assignment neu co.
  - Them route:
    - `/assignments/<pk>/rubrics/add/`
    - `/assignments/<pk>/rubrics/<rubric_pk>/delete/`
  - Sua man chon `submissions:grade`:
    - Hien bang diem rubric.
    - Luu diem va comment theo tung tieu chi.
    - Cho teacher chon dung tong rubric lam diem cuoi.
    - Van cho cham tay bang `manual_score` nhu cu khi khong dung rubric.
    - Tao/xoa feedback mau ca nhan.
    - Nut feedback mau chen nhanh vao nhan xet tong quan.
  - Sua `submissions:detail` de hoc sinh thay rubric breakdown sau khi duoc cham.
- Da check:
  - `python manage.py makemigrations assignments submissions` tao migration moi thanh cong.
  - `python manage.py migrate` tren Supabase thanh cong:
    - `assignments.0004_rubrics`
    - `submissions.0002_feedbacktemplates_rubricscores`
  - `python manage.py check` thanh cong.
  - `python manage.py makemigrations --check --dry-run` bao `No changes detected`.
  - `python manage.py showmigrations assignments submissions` bao migration moi da `[X]`.
  - Smoke test Supabase:
    - Teacher tao 2 rubric cho assignment tam: status `302`, co 2 rubric.
    - Teacher cham submission bang rubric: manual score luu thanh `8.5`, rubric scores luu `5.5` va `3.0`.
    - Teacher tao feedback mau thanh cong va man chon render thay mau.
    - Student vao submission detail: status `200`, thay `Rubric breakdown` va comment rubric.
- Loi phat hien:
  - Khong co loi runtime trong smoke test voi DB Supabase.
- Quyet dinh sua:
  - Rubric max total duoc chan khi them tieu chi de khong vuot `assignment.max_score`.
  - Xoa rubric la an `is_active=False` de khong pha diem rubric da cham.
  - Feedback template la ca nhan theo teacher; route delete chi lay template cua teacher dang dang nhap.
- Con ton:
  - Co the them trang quan ly feedback template rieng neu teacher co nhieu mau.
- Check: [x] Da check
- Review: [x] Da review

### Phase 7

- Trang thai: [x] Hoan thanh
- Da lam:
  - Them model `PlagiarismReports` va admin de luu lich su report.
  - Them migration `apps/assignments/migrations/0005_plagiarismreports.py`.
  - Them route `assignments:plagiarism` va `assignments:run_plagiarism`.
  - Them trang `templates/assignments/plagiarism.html` co bang cap bai, diem similarity/text/token/structural, filter suspicious va empty state.
  - Them nut "Kiem tra dao van" tu trang thong ke va trang chi tiet bai tap.
  - Cap nhat `check_plagiarism_task` de ghi report, bo qua bai nop rong va ho tro nguong tuy chinh.
- Da migrate Supabase: `assignments.0005_plagiarismreports` [X].
- Smoke test:
  - Teacher GET `/assignments/<pk>/plagiarism/`: 200.
  - Teacher POST `/assignments/<pk>/plagiarism/run/`: 302 ve trang report.
  - Report test: `finished`, 2 bai so sanh, 1 cap, 1 cap dang chu y.
  - Student GET trang plagiarism: 302 ve `/`.
  - Bai chi co 1 submission: report `finished`, 1 bai, 0 cap, hien empty state.
- Check: [x] Da check
- Review: [x] Da review

---

## Thu tu da lam thuc te

1. Phase 0: Sua route admin bi trung.
2. Phase 1: Notification Center.
3. Phase 2: Teacher Dashboard.
4. Phase 3: Gradebook theo lop.
5. Phase 4: Calendar Deadline.
6. Phase 5: Import hoc sinh hang loat.
7. Phase 6: Rubric va feedback mau.
8. Phase 7: Plagiarism UI.

Ket luan: Toan bo phase MVP trong file da hoan thanh, da migrate va da smoke test nhung route/quyen chinh.



---

# bo_sung_nang_cao

> Ngay lap audit: 2026-05-17
> Muc tieu: review logic toan he thong sau MVP, xem cac chuc nang co map voi nhau khong, form/flow co hop ly khong, va len kich ban nang cap cho admin, giao vien, hoc sinh. Phan thi/exam duoc dat uu tien cao vi code hien da co mam moc nhung chua du chat luong san pham.

## 1. Ban do model hien co sau khi quet source

### Accounts

- `Profiles`: profile 1-1 voi `User`, co `role`, `avatar_url`, `bio`, `phone`, `status`.
- `TeacherRegistrations`: don dang ky giao vien, co `institution`, `proof_document_url`, `reason`, `status`, `reviewed_by`, `reviewed_at`.

### Classrooms

- `Classrooms`: lop hoc, ma moi, giao vien, gioi han hoc sinh, trang thai duyet, active.
- `Semesters`: hoc ky dung chung, co `code`, `name`, ngay bat dau/ket thuc, `is_current`, `is_active`.
- `Subjects`: mon hoc, ngon ngu lien quan, trang thai duyet, nguoi tao/duyet.
- `ClassroomSubjects`: lien ket lop + mon + hoc ky.
- `ClassroomMembers`: thanh vien lop, hoc sinh, status.
- `Announcements`: thong bao lop.
- `Leaderboard`: bang xep hang theo lop.

### Assignments

- `Assignments`: bai tap/de bai. Da co `classroom`, `classroom_subject`, `title`, `description`, `instructions`, `type`, `difficulty`, `allowed_languages`, `start_date`, `due_date`, nop muon, diem, so lan nop, hien ket qua testcase, leaderboard, publish.
- `Assignments` cung da co field exam: `is_exam`, `exam_duration_minutes`, `exam_start_time`, `exam_end_time`.
- `Testcases`: input/output, sample/hidden, weight, timeout/memory override, order.
- `AssignmentFiles`: file dinh kem.
- `AssignmentStatistics`: thong ke bai tap.
- `Rubrics`: tieu chi cham diem.
- `PlagiarismReports`: report kiem tra dao van/tong dong code.

### Submissions

- `Submissions`: bai nop, code, ngon ngu, status, diem auto/manual, late penalty, nguoi cham.
- `SubmissionDetails`: ket qua tung testcase.
- `CodeComments`: comment theo dong code.
- `RubricScores`: diem theo rubric.
- `FeedbackTemplates`: feedback mau cua giao vien.
- `CodeDrafts`: nhap/luu nhap IDE theo assignment + student + language, chi co `last_saved_at`.

### Discussions

- `Discussions`: cau hoi/tra loi theo assignment, parent reply, pinned, answer, upvotes.
- `DiscussionVotes`: vote 1/-1, unique theo discussion + user.

### Notifications

- `Notifications`: recipient, actor, type, title, message, link, read state, metadata.

### Administation

- `ProgrammingLanguages`: ngon ngu lap trinh, version, file extension, syntax mode, default template.
- `SandboxConfigs`: image docker, timeout, memory, cpu.
- `ServerMetrics`: metric server/sandbox.
- `ActivityLogs`: log POST/PUT/PATCH/DELETE qua middleware.
- `SystemSettings`: key/value cau hinh he thong.

## 2. Danh gia logic tong the

### Diem dang tot

- Role da ro: student, teacher, admin; da co decorator va nhieu check theo lop.
- Workflow lop/mon/hoc ky/bai tap da co map kha tot: lop co mon, mon co ky, bai tap co the gan vao mon trong lop.
- Bai nop, cham tu dong, cham tay, rubric, feedback, notification, gradebook, calendar, plagiarism da noi voi nhau.
- Admin da co cac man hinh duyet giao vien/lop/mon, cau hinh ngon ngu, sandbox, log, analytics.

### Diem chua hop ly/can lam chac

- Form tao/sua bai tap co `AssignmentForm` gom field exam, nhung template `templates/assignments/create.html` va `edit.html` chua render `is_exam`, `exam_duration_minutes`, `exam_start_time`. Giao vien gan nhu khong bat che do thi duoc bang UI.
- `exam_end_time` ton tai trong model nhung form khong xu ly/khong render; logic hien tinh deadline exam bang `exam_start_time + duration`, nen field nay dang thua hoac chua dung dung y.
- `CodeDrafts` chi co `last_saved_at`; trong exam, code dang dung draft de suy ra thoi diem bat dau neu khong co `exam_start_time`. Vi `last_saved_at` tu dong thay doi moi lan autosave, deadline exam co nguy co bi doi sai.
- `save_draft_view` va `run_test_view` can bo sung check quyen/member/published/start_date/allowed_languages. Hien `submit_code_view` check kha tot, nhung API run/draft la mat ngo quan trong.
- `start_date` hien chu yeu de hien thi/lich, chua duoc enforce chat trong `solve_problem_view`, `run_test_view`, `save_draft_view`, `submit_code_view`.
- `AssignmentStatistics` tinh diem tu `total_score`, trong khi gradebook/profile da uu tien `manual_score`. Can dong bo mot cach tinh diem cuoi.
- `type` cua assignment co `auto_grade`, `manual_grade`, `project` nhung flow nop bai van thien ve code IDE/testcase. Can lam ro moi type co hanh vi nao.
- Publishing chua co preflight checklist: bai auto-grade co the publish khi chua co testcase/sample, exam co the publish khi thieu duration/start, ngon ngu khong hop voi mon.
- `show_testcase_result` da co tac dung o submission detail, nhung run sample/custom van cho hoc sinh chay. Voi exam, giao vien co the muon tat custom run hoac gioi han so lan run.
- `Leaderboard` co model rieng nhung can review lai co job cap nhat on dinh sau moi submission/manual grade chua.
- `ActivityLogs` chi log method/path co ban, chua gan resource id/metadata ro cho cac hanh dong quan trong nhu publish, submit exam, force submit, approve/reject.

## 3. Ket luan rieng ve chuc nang thi

### Hien tai da co gi

- Model `Assignments` da co `is_exam`, `exam_duration_minutes`, `exam_start_time`, `exam_end_time`.
- IDE `solve_problem.html` da co timer EXAM, canh bao con 5 phut, auto-submit client-side khi het gio.
- `submit_code_view` co check deadline exam theo `exam_start_time` hoac draft.

### Chua du de goi la chuc nang thi hoan chinh

- Giao vien chua co UI day du de tao/sua bai thi.
- Chua co `ExamSession` rieng theo hoc sinh, nen khong co start/end chinh xac cho tung hoc sinh.
- Chua co audit event: vao thi, roi tab, mat ket noi, autosave, submit, auto-submit, reopen.
- Chua co man lobby/xac nhan truoc khi bat dau thi.
- Chua co man theo doi phong thi cho giao vien.
- Chua co quyen/admin override: mo khoa, gia han gio, force submit, huy session.
- Chua co policy he thong: cho/khong cho custom run, copy/paste, fullscreen, so canh bao toi da.
- Chua co bao cao sau thi: danh sach hoc sinh chua vao thi, dang lam, da nop, auto-submit, qua han, co warning.

Ket luan: phai lam Phase NC-03 den NC-06 ben duoi de co exam dung nghia.

## 4. Kich ban nang cao theo phase

### Phase NC-01 - Hardening quyen va consistency truoc khi them tinh nang lon

Muc tieu: bit cac lo hong API/logic de nhung tinh nang nang cao khong xay tren nen mong manh.

File du kien:

- `apps/submissions/views.py`
- `apps/submissions/utils.py`
- `apps/assignments/forms.py`
- `apps/assignments/views.py`
- `apps/classrooms/views.py`

Viec can lam:

1. Tao helper dung chung:
   - `_can_access_assignment(user, assignment)`
   - `_can_solve_assignment(user, assignment)`
   - `_assignment_is_open_for_student(assignment, now)`
   - `_validate_submission_language(assignment, language)`
2. Ap dung helper vao:
   - `solve_problem_view`
   - `save_draft_view`
   - `run_test_view`
   - `submit_code_view`
   - `submission_history_view`
3. Enforce `start_date`:
   - Student khong vao solve/submit/run/draft truoc `start_date`.
   - Teacher/admin van xem/chay thu de test bai.
4. Enforce `allowed_languages` o `run_test_view`, `save_draft_view`, `submit_code_view`.
5. Dong bo diem cuoi:
   - Tao helper `submission_final_score(submission)` uu tien `manual_score`, sau do `total_score`.
   - Cap nhat `update_assignment_statistics`, gradebook, leaderboard, dashboard hoc sinh/giao vien dung helper nay.
6. Them preflight khi publish:
   - Auto-grade can it nhat 1 testcase.
   - Nen co it nhat 1 sample testcase neu hoc sinh can test.
   - Assignment phai co ngon ngu active.
   - Exam phai co duration hop le.

Check:

- [ ] Student khong goi duoc `/submissions/run-test/<assignment_pk>/` neu khong thuoc lop.
- [ ] Student khong save draft assignment chua publish.
- [ ] Student khong submit ngon ngu nam ngoai `allowed_languages`.
- [ ] Bai chua den `start_date` khong vao solve/submit duoc.
- [ ] Statistics, gradebook, dashboard cho cung mot diem cuoi.

Review:

- [ ] Khong pha teacher/admin preview.
- [ ] Error JSON ro nghia cho API IDE.
- [ ] Khong lap code check quyen lung tung o nhieu view.

### Phase NC-02 - Lam lai UX tao/sua bai tap cho giao vien

Muc tieu: form tao bai tap de hieu, day du, tranh giao vien publish bai thieu cau hinh.

File du kien:

- `apps/assignments/forms.py`
- `templates/assignments/create.html`
- `templates/assignments/edit.html`
- Co the tao partial: `templates/assignments/_assignment_form.html`

Van de hien tai:

- Template create/edit dang copy gan giong nhau, de lech field.
- Field exam co trong form nhung khong co trong UI.
- `type` chua giai thich tac dong.
- Sau khi tao moi them testcase/file/rubric, nhung chua co checklist huong dan trang thai san sang publish.

Kich ban sua:

1. Tach partial form chung cho create/edit.
2. Chia UI thanh nhom:
   - Noi dung de bai.
   - Cau hinh lop/mon/ky.
   - Kieu bai: auto/manual/project/exam.
   - Thoi gian va nop muon.
   - Cham diem va hien thi ket qua.
   - Ngon ngu.
   - Che do thi neu bat exam.
3. Them section "Che do thi":
   - Toggle `is_exam`.
   - `exam_start_time`.
   - `exam_duration_minutes`.
   - `max_attempts` default 1 khi exam.
   - Checkbox de tat custom run khi thi (can field/policy o Phase NC-03).
4. Them validation form:
   - `due_date >= start_date`.
   - `exam_duration_minutes` bat buoc neu `is_exam=True`.
   - `exam_start_time` khong duoc sau `due_date` neu ca hai co gia tri.
   - Neu `late_submission_allowed=False` thi `late_penalty_percent=0`.
   - `max_score > 0`, `max_attempts > 0` neu nhap.
5. Them publish checklist o assignment detail:
   - Da co noi dung de bai.
   - Da co ngon ngu.
   - Da co testcase neu auto-grade.
   - Da co rubric neu manual/project.
   - Exam da co duration/start/session policy.
6. Them nut "Luu nhap", "Luu va them testcase", "Cong bo sau khi hoan tat".

Check:

- [ ] Tao bai auto-grade khong testcase thi canh bao khi publish.
- [ ] Tao bai exam hien day du field thi.
- [ ] Edit bai khong mat field exam.
- [ ] Form mobile khong bi dai/kho doc qua muc.

Review:

- [ ] Giao vien moi vao van hieu can lam gi tiep.
- [ ] Khong can biet database field van cau hinh duoc bai tap.

### Phase NC-03 - Exam core: session that su cho tung hoc sinh

Muc tieu: bien exam tu timer client-side thanh mot workflow thi co server-side state.

Model moi de xuat:

`ExamSessions`

| Field | Ghi chu |
|---|---|
| assignment | FK `Assignments` |
| student | FK `User` |
| status | `not_started/running/submitted/auto_submitted/expired/cancelled` |
| started_at | Thoi diem hoc sinh bam bat dau |
| ends_at | Deadline rieng cua session |
| submitted_at | Luc nop cuoi |
| last_seen_at | Lan ping gan nhat |
| current_language | Ngon ngu dang dung |
| latest_draft | Text nullable hoac FK den draft neu muon gon |
| ip_address | IP luc bat dau |
| user_agent | Trinh duyet |
| extra_time_minutes | Gia han cua giao vien |
| violation_count | So canh bao |
| metadata | JSON |

`ExamEvents`

| Field | Ghi chu |
|---|---|
| session | FK `ExamSessions` |
| event_type | `started/autosaved/submitted/auto_submitted/tab_hidden/tab_visible/focus_lost/fullscreen_exit/paste/run_test/error/teacher_extend/teacher_force_submit` |
| metadata | JSON |
| created_at | DateTime |

Co the dat model trong app `submissions` de gan gan voi bai nop, hoac tao app `exams` rieng neu muon tach domain. Khuyen nghi: tao app `exams` rieng neu se lam phong thi/monitor lon; neu muon nhanh, dat trong `submissions`.

View/URL de xuat:

- `/assignments/<pk>/exam/` - lobby/xac nhan quy che thi.
- `/assignments/<pk>/exam/start/` - tao/lay session, POST.
- `/assignments/<pk>/exam/ide/` - IDE thi dua tren session.
- `/assignments/<pk>/exam/ping/` - heartbeat.
- `/assignments/<pk>/exam/event/` - ghi event.
- `/assignments/<pk>/exam/submit/` - nop bai exam.
- `/assignments/<pk>/exam/monitor/` - giao vien theo doi.
- `/exam-sessions/<session_pk>/extend/` - giao vien gia han.
- `/exam-sessions/<session_pk>/force-submit/` - giao vien force submit.

Kich ban hoc sinh:

1. Hoc sinh mo bai thi thi vao lobby, thay quy che, thoi gian, ngon ngu, so lan nop, yeu cau fullscreen neu bat.
2. Bam "Bat dau thi" moi tao `ExamSession.started_at`.
3. Server tinh `ends_at = started_at + duration + extra_time`.
4. IDE lay timer tu `ExamSession.ends_at`, khong dung `CodeDrafts.last_saved_at`.
5. Autosave ghi draft va event.
6. Submit thu cong tao `Submissions`, gan session, set session `submitted`.
7. Het gio thi client auto-submit; server cung tu choi submit tre ngoai grace period va co command/job auto-expire.

Kich ban giao vien:

1. Khi tao bai, bat "Che do thi".
2. Xem danh sach phong thi:
   - Chua vao.
   - Dang lam.
   - Da nop.
   - Het gio/chua nop.
   - Co warning.
3. Xem tung session: lan save gan nhat, submission, event timeline.
4. Gia han thoi gian rieng hoc sinh.
5. Force submit bai hien tai neu hoc sinh mat ket noi.
6. Export bao cao thi CSV.

Kich ban admin:

1. Cau hinh policy mac dinh:
   - Co bat fullscreen khong.
   - Co cho custom input khong.
   - Co cho run sample khong.
   - Grace period submit.
   - So warning toi da truoc khi flag.
2. Xem audit exam toan he thong.
3. Override/huy session trong truong hop su co.

Check:

- [ ] Moi hoc sinh chi co mot session running cho mot assignment exam.
- [ ] Refresh trang khong reset thoi gian.
- [ ] Autosave khong lam doi `started_at`/`ends_at`.
- [ ] Server tu choi submit sau `ends_at + grace_period`.
- [ ] Teacher monitor thay realtime gan dung qua heartbeat.
- [ ] Admin co audit cac event quan trong.

Review:

- [ ] Khong dua vao client timer lam nguon su that duy nhat.
- [ ] Khong dung `last_saved_at` lam thoi diem bat dau thi.
- [ ] Co cach xu ly mat mang cong bang cho hoc sinh.

### Phase NC-04 - Exam IDE va chong gian lan muc vua phai

Muc tieu: them cac canh bao hop ly, khong bien app thanh spyware, nhung du giup giao vien co tin hieu.

File du kien:

- `templates/submissions/solve_problem.html` hoac template exam IDE rieng.
- View/event endpoint cua Phase NC-03.
- `apps/administation/models.py` hoac `SystemSettings` cho policy.

Chuc nang:

1. Tao template IDE exam rieng de tranh anh huong IDE bai tap thuong.
2. Tuy chon fullscreen:
   - Yeu cau vao fullscreen khi bat dau.
   - Ghi event khi thoat fullscreen.
3. Ghi event:
   - `visibilitychange`: roi tab/quay lai tab.
   - `blur/focus`: mat/tro lai focus.
   - paste vao editor.
   - change language.
   - run code.
4. Policy theo assignment:
   - Cho phep/khong cho custom input.
   - Cho phep/khong cho xem testcase sample.
   - Gioi han so lan run sample.
   - An history submission den khi het exam.
5. Canh bao hoc sinh:
   - Hien so warning.
   - Giai thich warning la tin hieu de giao vien review, khong tu dong ket luan gian lan.

Check:

- [ ] Roi tab tao event.
- [ ] Paste tao event.
- [ ] Tat custom input dung voi policy.
- [ ] Exam IDE khong lam hong IDE bai tap thuong.

Review:

- [ ] Noi ro ve quyen rieng tu; chi ghi event trong trang thi.
- [ ] Khong chan thao tac can thiet cho hoc sinh khuyet tat neu chua co phuong an thay the.

### Phase NC-05 - Exam grading/report

Muc tieu: giao vien co man cham/xem ket qua thi chuyen nghiep.

Chuc nang:

1. Trang ket qua thi theo assignment:
   - Tong so hoc sinh.
   - Chua vao thi.
   - Dang lam.
   - Da nop.
   - Auto submitted.
   - Qua gio chua nop.
   - Warning count.
2. Bang ket qua:
   - Hoc sinh.
   - Start/end/submitted.
   - Diem cao/diem cuoi.
   - So lan run.
   - So warning.
   - Link submission/session timeline.
3. Export CSV:
   - Co UTF-8 BOM.
   - Include warning summary.
4. Notification:
   - Nhac truoc gio thi.
   - Bao giao vien khi co hoc sinh bi expired/chua nop.

Check:

- [ ] Teacher chi xem exam cua lop minh.
- [ ] Admin xem duoc toan bo khi can.
- [ ] Export doc du tieng Viet.
- [ ] Hoc sinh khong thay warning cua hoc sinh khac.

### Phase NC-06 - Scheduling jobs: deadline reminder, exam auto-expire

Muc tieu: cac viec dinh ky khong phu thuoc user dang mo trang.

Phuong an:

- Neu co Celery beat: tao periodic tasks.
- Neu deploy don gian: tao management command de cron chay moi 1-5 phut.

Tasks/commands:

1. `send_due_soon_notifications`
   - Gui notification deadline trong 24h/2h.
   - Khong gui lap bang metadata/log.
2. `expire_exam_sessions`
   - Session qua `ends_at + grace_period` ma chua submitted thi set `expired`.
   - Neu co draft thi tao auto submission neu policy bat.
3. `collect_server_metrics`
   - Ghi `ServerMetrics` that su thay vi chi co model.
4. `detect_sandbox_zombies`
   - Canh bao admin/giao vien khi submission running qua lau.

Check:

- [ ] Chay command nhieu lan khong tao duplicate notification.
- [ ] Exam expired dung gio tren server.
- [ ] Admin dashboard co metric moi.

### Phase NC-07 - Assignment/question bank va clone bai tap

Muc tieu: giao vien tao bai nhanh hon, tai su dung de/testcase/rubric.

Model de xuat:

- `AssignmentTemplates`: template de bai theo teacher/admin, co title/instructions/type/default languages.
- `TestcaseBankItems`: testcase tai su dung theo mon/ngon ngu/do kho.
- Hoac cach don gian hon: them route clone assignment truoc khi tao model bank.

Chuc nang:

1. Clone assignment:
   - Copy instructions.
   - Copy allowed languages.
   - Copy testcase.
   - Copy rubric.
   - Khong copy submissions/statistics/plagiarism.
2. Luu bai hien tai thanh template.
3. Tao bai tu template.
4. Admin co template global; teacher co template rieng.

Check:

- [ ] Clone khong copy du lieu hoc sinh.
- [ ] Clone testcase giu order/weight/sample/hidden.
- [ ] Template global chi admin quan ly.

### Phase NC-08 - Cai tien workflow lop/thanh vien

Muc tieu: quan ly thanh vien linh hoat hon cho giao vien/admin.

Chuc nang:

1. Them setting lop:
   - Join auto-approve.
   - Join can giao vien duyet.
   - Dong/mo ma moi.
2. Neu can duyet:
   - `ClassroomMembers.status='pending'` khi hoc sinh join.
   - Notification `class_join_requested` cho giao vien.
   - Dashboard teacher hien pending request.
3. Them bulk remove/approve members.
4. Them reset invite code.
5. Them audit log cho import/remove/approve.

Check:

- [ ] Lop auto-approve giu hanh vi cu.
- [ ] Lop can duyet khong cho hoc sinh vao noi dung truoc khi approved.
- [ ] Notification request khong duplicate.

### Phase NC-09 - Discussion/Q&A nang cao

Muc tieu: bien discussion thanh cong cu hoc tap tot hon.

Chuc nang:

1. Gan tag: loi runtime, y tuong, testcase, thong bao, hoi dap.
2. Teacher mark answer da co; them filter unanswered.
3. Notification khi co reply/mark answer.
4. Cho giao vien khoa discussion trong exam.
5. Moderation cho admin/teacher: an/xoa noi dung vi pham.

Check:

- [ ] Hoc sinh chi thao luan trong lop/bai duoc phep.
- [ ] Exam co the tat discussion neu policy yeu cau.
- [ ] Reply tao notification dung nguoi.

### Phase NC-10 - Admin governance va policy he thong

Muc tieu: admin dieu khien he thong thay vi phai sua code.

Dung `SystemSettings` cho:

- `exam.default_grace_seconds`
- `exam.require_fullscreen_default`
- `exam.allow_custom_input_default`
- `assignment.max_file_size_mb`
- `submission.max_code_size_kb`
- `notification.due_soon_hours`
- `sandbox.zombie_threshold_seconds`

Chuc nang:

1. Form setting co validate theo schema, khong nhap JSON tuy y kho dung.
2. Trang policy rieng cho assignment/exam/sandbox.
3. Activity log co metadata ro: object id, action semantic, ket qua.
4. Export audit log theo khoang ngay/user/action.

Check:

- [ ] Setting sai kieu bi bao loi.
- [ ] View dung setting va co fallback default.
- [ ] Admin export log co BOM UTF-8.

### Phase NC-11 - UX/performance polish

Muc tieu: app de dung hon khi du lieu lon.

Viec can lam:

1. Pagination:
   - Submissions teacher list.
   - Gradebook neu lop dong.
   - Activity logs.
   - Notifications.
2. Search/filter:
   - Theo hoc sinh, status, khoang diem, co warning, chua cham.
3. Bulk action:
   - Bulk regrade da co, them bulk publish/unpublish, bulk notify, bulk export.
4. Empty/loading/error state dong bo.
5. Mobile:
   - Gradebook va plagiarism table scroll tot.
   - Assignment form khong qua dai; co sticky save.
6. Accessibility:
   - Label ro cho checkbox/toggle.
   - Button icon co text hoac title.
   - Mau trang thai khong chi phu thuoc mau.

Check:

- [ ] Trang list lon khong load qua cham.
- [ ] Form tao bai tap dung duoc tren laptop nho.
- [ ] Khong co button/icon khong ro nghia.

## 5. Thu tu lam khuyen nghi

1. NC-01: Hardening quyen va consistency.
2. NC-02: UX tao/sua bai tap.
3. NC-03: Exam session core.
4. NC-04: Exam IDE va event warning.
5. NC-05: Exam report/monitor/export.
6. NC-06: Scheduled jobs.
7. NC-08: Workflow join lop can duyet.
8. NC-07: Clone/template bai tap.
9. NC-09: Discussion nang cao.
10. NC-10: Admin policy.
11. NC-11: UX/performance polish.

Ly do: NC-01 va NC-02 sua nen logic/form truoc. Exam can lam sau khi form va quyen chac chan. Scheduled jobs can cho exam auto-expire va reminder. Cac phase sau tang nang su dung hang ngay.

## 6. Dinh nghia done cho ban nang cao

- Moi phase co migration ro neu them model.
- Moi route moi co test quyen: anonymous, student khac lop, student trong lop, teacher dung lop, teacher khac lop, admin.
- Moi API JSON tra loi ro rang va khong leak traceback.
- Moi workflow chinh co notification neu hanh dong tao viec cho role khac.
- Moi export co UTF-8 BOM neu co tieng Viet.
- Sau moi phase chay:
  - `python manage.py check`
  - `python manage.py makemigrations --check --dry-run`
  - `python manage.py migrate` neu co migration
  - Smoke test Django client tren Supabase neu lien quan DB that.

## 7. Nhat ky thuc hien bo_sung_nang_cao

### Dot NC-A - 2026-05-17

Trang thai: [x] Da trien khai core nang cao end-to-end.

Da lam:

- NC-01 hardening:
  - Them helper chung trong `apps/submissions/utils.py` cho quyen solve, ngon ngu hop le, trang thai mo bai, diem cuoi.
  - `save_draft_view`, `run_test_view`, `submit_code_view` da check quyen/lop/published/start/due/language chat hon.
  - `update_assignment_statistics` dung diem cuoi uu tien `manual_score`.
  - Publish co preflight: auto-grade can testcase, exam can duration hop le, bai can noi dung.
- NC-02 UX tao/sua bai:
  - `create.html` va `edit.html` da co section "Che do thi".
  - Giao vien cau hinh duoc duration, gio mo/dong phong, fullscreen, custom input, sample run, max run, grace seconds.
  - Form validate `due_date >= start_date`, exam duration bat buoc, exam time hop le.
- NC-03 exam core:
  - Them model `ExamSessions` va `ExamEvents`.
  - Them migration:
    - `apps/assignments/migrations/0006_assignments_exam_allow_custom_input_and_more.py`
    - `apps/submissions/migrations/0003_examsessions_examevents.py`
  - Them lobby thi, start session, IDE thi, heartbeat, event endpoint.
  - Timer exam dung `ExamSessions.ends_at`, khong con dua vao `CodeDrafts.last_saved_at`.
  - Session khong reset khi refresh.
- NC-04 exam IDE/event:
  - Ghi event tab hidden/visible, focus lost/returned, fullscreen exit, paste/copy/context menu.
  - Policy exam chan custom input/sample run theo cau hinh.
  - Run count duoc luu tren session.
- NC-05 exam monitor/report:
  - Them trang monitor phong thi cho giao vien.
  - Giao vien xem chua vao/dang lam/da nop/het gio/warning.
  - Giao vien gia han session va force submit draft.
  - Them export CSV phong thi co UTF-8 BOM.
- NC-06 scheduled jobs:
  - Them command `send_due_soon_notifications`.
  - Them command `expire_exam_sessions`.
  - Them command `collect_server_metrics`.
  - Them command `detect_sandbox_zombies`.
- NC-07:
  - Them route/action nhan ban assignment.
  - Clone noi dung, ngon ngu, testcase, rubric, file dinh kem; khong clone submission/statistics/plagiarism.
- NC-08:
  - Them setting lop `join_requires_approval` trong form tao/sua lop.
  - Quick join/join code tao member `pending` neu lop can duyet.
  - Gui notification `class_join_requested` cho giao vien.
- NC-09:
  - Discussion reply gui notification cho chu topic.
  - Mark answer gui notification cho nguoi tra loi.
- NC-10:
  - Them helper `apps/administation/utils.py` de doc `SystemSettings` an toan.
- NC-11:
  - Them pagination cho teacher submission list.

Da migrate Supabase:

- `assignments.0006_assignments_exam_allow_custom_input_and_more` [X]
- `submissions.0003_examsessions_examevents` [X]

Da check:

- `python manage.py check`: pass.
- `python manage.py makemigrations --check --dry-run`: `No changes detected`.
- `python manage.py showmigrations assignments submissions`: migration moi da `[X]`.
- Smoke test Supabase bang du lieu tam:
  - Student vao `/submissions/solve/<exam>/` redirect ve lobby thi.
  - Lobby thi render 200.
  - Start exam tao session `running`.
  - IDE thi render timer.
  - Event `tab_hidden` tang warning.
  - Save draft exam OK.
  - Custom input bi chan khi policy tat.
  - Submit exam tao submission va session `submitted`.
  - Teacher monitor render 200.
  - Teacher khac bi chan monitor.
  - Clone assignment tao ban nhap moi, copy testcase/rubric.
  - Lop bat can duyet join tao member `pending`.
  - Export CSV phong thi status 200, co UTF-8 BOM, co username hoc sinh.

Con ton/backlog sau dot NC-A:

- Question bank/template bank dung nghia chua tao model rieng; hien da co clone assignment de giai quyet workflow nhanh truoc.
- Admin policy UI dang co helper doc setting, chua lam form schema rieng cho tung policy.
- Exam monitor hien theo refresh page, chua realtime WebSocket/SSE.
- Scheduled jobs da co command, can cau hinh cron/Celery beat tren moi truong deploy.
