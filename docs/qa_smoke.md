# QA smoke checklist

Dung file nay de chay smoke test tren moi truong local/staging sau khi deploy migration va seed du lieu co ban.

## Student E2E

- [ ] Dang ky tai khoan hoc sinh moi.
- [ ] Tham gia lop bang invite code auto-approve.
- [ ] Tham gia lop can duyet va thay trang thai pending.
- [ ] Mo assignment da publish va vao IDE lam bai.
- [ ] Luu draft, run testcase mau, submit bai.
- [ ] Xem diem trong submission detail va student dashboard.
- [ ] Nhan notification khi co bai moi, bai duoc cham, comment code.

## Teacher E2E

- [ ] Dang nhap giao vien da duoc duyet.
- [ ] Tao lop, bat/tat yeu cau duyet hoc sinh.
- [ ] Tao/gán mon hoc va hoc ky cho lop.
- [ ] Tao assignment auto-grade co testcase, rubric, file dinh kem.
- [ ] Publish assignment va kiem tra hoc sinh thay bai.
- [ ] Xem submission, cham bang rubric, them comment code.
- [ ] Mo gradebook, statistics, leaderboard va export CSV neu co.

## Exam E2E

- [ ] Giao vien tao exam co duration, window time, fullscreen/custom input policy.
- [ ] Hoc sinh vao lobby, start exam, vao IDE.
- [ ] Gui warning event nhu focus lost/fullscreen exit.
- [ ] Hoc sinh submit bai trong gio.
- [ ] Giao vien mo monitor, export CSV phong thi.
- [ ] Admin xem exam event audit.
- [ ] Chay command `expire_exam_sessions` voi session qua gio tren staging.

## Admin E2E

- [ ] Duyet teacher registration.
- [ ] Duyet classroom pending.
- [ ] Duyet subject pending.
- [ ] Tao/sua/khoa user va reset password.
- [ ] Sua sandbox/language/SystemSettings.
- [ ] Xem server metrics, sandbox monitor, activity logs.
- [ ] Export activity logs va mo file bang UTF-8.

## Security E2E

- [ ] Anonymous vao dashboard/lop/bai/submission bi redirect login.
- [ ] Student direct URL vao admin dashboard bi chan.
- [ ] Student direct URL vao grade view bi chan.
- [ ] Student direct URL vao exam monitor bi chan.
- [ ] Student direct URL vao plagiarism report bi chan.
- [ ] User A khong open/mark-read notification cua user B.
- [ ] Admin bulk action khong khoa duoc chinh minh hoac superuser cuoi cung.
