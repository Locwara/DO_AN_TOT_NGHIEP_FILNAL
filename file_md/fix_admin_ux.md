# Fix Admin UX - Ke hoach gop chuc nang va tinh chinh luong quan tri

> Muc tieu: lam khu vuc admin gon hon, dung logic van hanh hon, bot trung lap menu, va giup admin xu ly viec quan trong nhanh hon.
>
> Cach lam: trien khai theo phase. Lam xong phase nao thi tick `[x]`, test route/UI/phan quyen phase do roi moi qua phase tiep theo.

## 0. Ra soat hien trang admin

- [x] Kiem tra lai tat ca route trong `apps/administation/urls.py`.
  > Ghi chu:

- [x] Lap bang map route -> template -> current_page -> nhom chuc nang.
  > Ghi chu:

- [x] Kiem tra sidebar `templates/administration/base_admin.html` co muc nao trung y nghia.
  > Ghi chu:

- [x] Kiem tra cac trang admin co dung design system chua: button, table, filter, CSV dropdown, card.
  > Ghi chu:

- [x] Smoke test cac trang admin chinh voi tai khoan admin.
  > Ghi chu:

## 1. Gop nhom menu sidebar

- [x] Doi sidebar thanh cac nhom lon: `Tong quan`, `Nguoi dung`, `Hoc tap`, `Cham code`, `Giam sat`, `Cau hinh`.
  > Ghi chu:

- [x] Gop `Quan ly nguoi dung`, `Quan ly giao vien`, `Duyet giao vien` vao nhom `Nguoi dung`.
  > Ghi chu:

- [x] Gop `Quan ly lop hoc`, `Quan ly mon hoc`, `Ky hoc` vao nhom `Hoc tap`.
  > Ghi chu:

- [x] Gop `Ngon ngu`, `Cau hinh Sandbox`, `Sandbox Monitor` vao nhom `Cham code`.
  > Ghi chu:

- [x] Gop `Server Metrics`, `Su kien thi`, `Nhat ky hoat dong` vao nhom `Giam sat`.
  > Ghi chu:

- [x] Giu `Cai dat he thong` trong nhom `Cau hinh`.
  > Ghi chu:

- [x] Dam bao active state cua menu van dung sau khi gop.
  > Ghi chu:

## 2. Gop trang Nguoi dung

- [x] Tao trang/tabs `Nguoi dung` gom: tat ca, hoc sinh, giao vien, admin, bi khoa.
  > Ghi chu:

- [x] Dua `teacher_management` ve thanh filter/tab trong `user_management`.
  > Ghi chu:

- [x] Dua `teacher_approvals` ve tab `Cho duyet giao vien`.
  > Ghi chu:

- [x] Cho admin duyet/tu choi giao vien ngay trong tab cho duyet.
  > Ghi chu:

- [x] Giu bulk action: kich hoat, vo hieu hoa, xoa, xuat CSV.
  > Ghi chu:

- [x] Them cot can thiet: role, trang thai, so bai nop, so lop day/tham gia, last login.
  > Ghi chu:

- [x] Kiem tra phan quyen: chi admin moi vao duoc cac route nay.
  > Ghi chu:

## 3. Gop trang Mon hoc

- [x] Gop `subject_management` va `subject_approvals` thanh mot trang `Mon hoc`.
  > Ghi chu:

- [x] Tao tabs: Tat ca, Cho duyet, Da duyet, Tu choi, Gan lop/mon/ky.
  > Ghi chu:

- [x] Hien thong tin ngon ngu lap trinh cua mon hoc trong danh sach.
  > Ghi chu:

- [x] Cho duyet/tu choi/bulk approve/bulk reject ngay trong tab.
  > Ghi chu:

- [x] Kiem tra logic mon da duyet moi hien cho hoc sinh.
  > Ghi chu:

- [x] Giu CSV dropdown: danh sach mon, gan lop/mon/ky.
  > Ghi chu:

## 4. Gop trang Lop hoc va Hoc tap

- [x] Tinh chinh `classroom_management` thanh trung tam quan ly lop.
  > Ghi chu:

- [x] Them tabs/filter: Tat ca, Cho duyet, Dang hoat dong, Bi khoa, Day nhieu canh bao.
  > Ghi chu:

- [x] Hien nhanh: giao vien, so hoc sinh, so mon, so bai tap, so bai thi, trang thai duyet.
  > Ghi chu:

- [x] Giu bulk action: duyet, tu choi, kich hoat, vo hieu hoa.
  > Ghi chu:

- [x] Tao lien ket nhanh sang so diem lop va danh sach thanh vien.
  > Ghi chu:

- [x] Giu CSV dropdown: danh sach lop, thanh vien theo lop.
  > Ghi chu:

## 5. Trung tam viec can xu ly

- [x] Tao box/trang `Viec can xu ly` tren admin dashboard.
  > Ghi chu:

- [x] Hien giao vien cho duyet.
  > Ghi chu:

- [x] Hien mon hoc cho duyet.
  > Ghi chu:

- [x] Hien lop hoc cho duyet.
  > Ghi chu:

- [x] Hien bai nop zombie/pending lau.
  > Ghi chu:

- [x] Hien phien thi co nhieu canh bao.
  > Ghi chu:

- [x] Moi item co nut di thang toi trang xu ly.
  > Ghi chu:

## 6. Giam sat he thong

- [x] Gop dieu huong `Server Metrics`, `Sandbox Monitor`, `Su kien thi`, `Activity Logs` vao nhom `Giam sat`.
  > Ghi chu:

- [x] Tao dashboard nho trong `Giam sat`: CPU, memory, zombie tasks, exam warnings, logs moi.
  > Ghi chu:

- [x] Them filter thong minh cho exam events: event type, bai thi, hoc sinh, muc canh bao.
  > Ghi chu:

- [x] Them action nhanh voi zombie task: kill, requeue, xem submission.
  > Ghi chu:

- [x] Giu CSV dropdown trong activity logs va exam monitor.
  > Ghi chu:

## 7. Moi truong cham code

- [x] Gop `Ngon ngu` va `Cau hinh Sandbox` thanh nhom `Moi truong cham code`.
  > Ghi chu:

- [x] Kiem tra moi ngon ngu active co sandbox config tuong ung.
  > Ghi chu:

- [x] Canh bao neu mon hoc dung ngon ngu chua co sandbox.
  > Ghi chu:

- [x] Them cot: enabled, image, timeout, memory, so bai dang dung ngon ngu.
  > Ghi chu:

- [x] Them nut test nhanh sandbox config neu co the.
  > Ghi chu:

## 8. Cai dat va audit

- [x] Giu `Cai dat he thong` rieng nhung them nhom setting theo category.
  > Ghi chu:

- [x] Them canh bao setting quan trong: exam grace, upload max, sandbox timeout, default DB mode.
  > Ghi chu:

- [x] Moi lan admin sua setting phai ghi `ActivityLogs`.
  > Ghi chu:

- [x] Moi lan admin doi role/khoa user/reset password phai ghi log ro metadata.
  > Ghi chu:

- [x] Them filter log theo resource type va resource id.
  > Ghi chu:

## 9. Frontend/UX chung

- [x] Sidebar admin co nhom ro rang, spacing gon, active state de nhin.
  > Ghi chu:

- [x] Tren mobile/tablet admin co nut mo menu thay vi sidebar an mat.
  > Ghi chu:

- [x] Moi trang quan ly co header thong nhat: title, mo ta, primary action, CSV dropdown neu co.
  > Ghi chu:

- [x] Filter form khong bi tran, search input thao tac tot.
  > Ghi chu:

- [x] Bang co empty state, loading state, hover state, bulk select state.
  > Ghi chu:

- [x] Cac nut nguy hiem co confirm ro rang.
  > Ghi chu:

## 10. Test va nghiem thu

- [x] Chay `python manage.py check`.
  > Ghi chu:

- [x] Smoke test tat ca route admin chinh tra ve HTTP 200.
  > Ghi chu:

- [x] Test admin khong bi loi active sidebar sau khi gop menu.
  > Ghi chu:

- [x] Test bulk action user/classroom/subject.
  > Ghi chu:

- [x] Test CSV dropdown tren cac trang admin.
  > Ghi chu:

- [x] Test activity log co ghi khi admin thuc hien hanh dong quan trong.
  > Ghi chu:
