# DevLearn — Dashboard Redesign Spec (v2)

> File này dùng để đưa cho AI agent (Gemini 3.1 Pro) trong project làm theo. Mục tiêu: thiết kế lại `templates/home.html` (và các phần liên quan trong `base.html`, `base.css`) cho 3 role: **student, teacher, admin**. GIỮ NGUYÊN bảng màu Primary xanh dương hiện có, không đổi tech stack (Django Templates + Tailwind CDN + Vanilla JS).

---

## 0. Nguyên tắc thiết kế chung (áp dụng cho cả 3 role)

1. **Không dồn hết mọi thứ lên dashboard.** Dashboard chỉ hiển thị thông tin *cần hành động ngay* hoặc *tổng quan nhanh* (glance-able). Thứ gì chi tiết/đầy đủ thì để ở trang riêng, dashboard chỉ show rút gọn + link "Xem tất cả".
2. **Phân cấp thị giác rõ ràng**: 1 khu vực hero/welcome nhẹ nhàng có gradient màu Primary → không phẳng lì toàn trắng như hiện tại. Card quan trọng nhất (cần hành động) luôn to hơn, đặt góc trên-trái.
3. **Không dùng toàn bộ card giống hệt nhau.** Phân biệt bằng: card có ảnh/icon minh họa lớn (illustration), card dạng số liệu (stat), card dạng list.
4. **Empty state phải có hình minh họa (SVG illustration line-art màu Primary/nhạt)**, không chỉ icon check đơn độc giữa khoảng trắng như hiện tại.
5. **Giữ bo góc & shadow hiện có**: radius `9px` (card), `14–22px` (khối lớn/hero), shadow màu xanh nhạt `rgba(19,127,236,.08–.15)` thay vì xám.
6. **Grid chuẩn**: bố cục 12-cột, khu chính (main) chiếm 8 cột, sidebar phải chiếm 4 cột trên desktop ≥1024px; xuống 1 cột trên mobile/tablet — dùng `@container` queries đã có sẵn plugin.
7. **Ảnh/minh họa**: dùng SVG illustration phong cách flat/line-art tông xanh dương + tím accent (ví dụ: undraw.co style, tự vẽ SVG inline để không phụ thuộc ảnh ngoài) cho: hero banner, empty states, khối "mời bạn bè", khối thi cử.

---

## 1. Bảng màu & token dùng lại (KHÔNG đổi)

```
Primary:   #137fec   (nhạt: #f0f8ff → đậm: #020d1f)
Accent:    #7c3aed
Success:   #16a34a
Warning:   #ea580c
Danger:    #dc2626
Background light: #ffffff | surface: #f8fafc (mới thêm — nền trang thay vì trắng thuần để card nổi lên)
Background dark:  #020d1f

Font sans: "Be Vietnam Pro", Inter, system-ui
Font mono: "Cascadia Code", "Fira Code", "JetBrains Mono"

Radius: sm 5px | DEFAULT/md 9px | lg 14px | xl 22px
Shadow: shadow-card, shadow-btn, shadow-modal (giữ nguyên, tint xanh)
Icon: Material Symbols Outlined
```

**Bổ sung mới (không phá vỡ hệ thống cũ):**
- `--surface`: `#f8fafc` (light) / `#0a1729` (dark) — làm nền `<body>` thay vì trắng tinh, giúp card trắng nổi bật hơn.
- Gradient hero: `linear-gradient(135deg, #137fec 0%, #1e5fd9 45%, #7c3aed 100%)` — dùng cho khối chào mừng trên cùng, chữ trắng.
- `--primary-tint-10`: `rgba(19,127,236,.08)` dùng làm nền cho icon badge tròn trong card thay vì icon trơ trọi.

---

## 2. Layout khung chung

```
[Navbar - giữ nguyên]
[Hero Welcome Band - gradient Primary, bo góc xl, full width] ← MỚI
[Main Grid: 8 cols main | 4 cols sidebar]
[Footer]
```

Hero Welcome Band thay cho dòng chữ "Chào quay trở lại" trơ trọi hiện tại — chứa: lời chào theo giờ trong ngày ("Chào buổi sáng, GV Tuấn!"), 1 dòng mô tả ngắn, 1–2 nút CTA chính (giữ style nút hiện có nhưng đổi nền trắng/outline vì nằm trên nền gradient), và 1 SVG illustration nhỏ bên phải (laptop + code / lớp học) ẩn trên mobile.

---

## 3. Dashboard — Role STUDENT

**Ưu tiên hành động → Ưu tiên xem nhanh → Ít quan trọng nhất xuống dưới/sidebar.**

### Cột chính (8 cols)
1. **Hero band**: "Chào buổi sáng, [Tên]! Bạn có N bài sắp đến hạn." + CTA "Vào lớp" / "Xem lịch".
2. **Card "Sắp đến hạn" (ưu tiên #1, to, nổi bật viền trái màu Warning nếu <24h)**: list rút gọn 3 bài, mỗi dòng gồm badge môn học, tên bài, đếm ngược thời gian (không chỉ ngày tháng — dùng dạng "còn 2 ngày" nổi bật hơn), nút "Làm bài" primary nhỏ bên phải. Nếu trống → illustration "không có deadline nào, thảnh thơi!" nhẹ nhàng.
3. **Card "Lớp đang học"**: dạng carousel/grid ngang 2 card lớp thay vì list dọc, mỗi card có: tên lớp, progress bar tròn (%) thay cho thanh ngang (trực quan & gọn hơn), số bài đã làm/tổng.
4. **Card "Bài thi"**: chỉ hiện nếu có bài thi đang mở hoặc trong 48h tới — icon đồng hồ đếm ngược nổi bật, nếu không có thì **ẩn hẳn khối này** (không hiện "không có gì" chiếm chỗ).

### Sidebar (4 cols)
5. **Điểm gần đây**: dạng mini list 3 dòng, điểm số hiển thị to màu theo ngưỡng (≥80% xanh success, 50–79% cam warning, <50% đỏ danger) thay vì số trơn.
6. **Thông báo mới**: gộp chung 1 card với badge số lượng chưa đọc trên tiêu đề, tối đa 3 dòng, click ra trang notifications.
7. **Hỗ trợ kỹ thuật**: thu nhỏ thành 1 dòng link nhỏ cuối sidebar (icon + text), không cần hẳn 1 card to như hiện tại — đây là chức năng phụ, không đáng chiếm diện tích ngang hàng với điểm số/lớp học.

❌ **Bỏ khỏi dashboard chính** (nếu bản cũ có xu hướng liệt kê hết): không cần thêm biểu đồ thống kê điểm số phức tạp ở trang chủ — để dành cho trang "Dashboard cá nhân" riêng.

---

## 4. Dashboard — Role TEACHER

Giáo viên cần: (1) việc cần làm ngay = chấm bài, duyệt học sinh, giám sát thi gian lận; (2) tổng quan lớp.

### Cột chính (8 cols)
1. **Hero band**: "Chào GV [Tên]! N bài đang chờ chấm." + CTA "Tạo lớp học" / "Dashboard Giáo viên".
2. **Card "Hàng chờ chấm" (to nhất, ưu tiên #1)**: mỗi dòng có avatar/initial học sinh, badge trạng thái code màu theo Success/Warning/Danger (Thành công/Cần review/Lỗi), tên bài + lớp, nút "Chấm bài" nổi bật. Empty state có illustration bút+checkmark "Đã chấm hết, tuyệt vời!".
3. **Card "Lớp đang dạy"**: grid 2 cột card lớp (không phải list dọc), mỗi card: tên lớp, số HS, số bài, mã mời dạng "chip" có nút copy nhanh (icon copy) — tiện dụng hơn text thường.
4. **Card "Hiệu suất lớp 7 ngày"**: đây là khối DUY NHẤT dùng biểu đồ. Thiết kế lại:
   - 3 stat number giữ nguyên nhưng thêm icon nhỏ + mini sparkline (đường xu hướng 7 ngày) phía sau mỗi số để không "trơ" số liệu.
   - Danh sách "bài tập điểm thấp cần chú ý" thu gọn còn 2 dòng, có link "Xem chi tiết thống kê" dẫn sang trang `/assignments/<id>/statistics/` thay vì nhồi hết vào dashboard.

### Sidebar (4 cols)
5. **Bài thi đang chạy**: chỉ hiện khi có session live — có chấm đỏ "LIVE" nhấp nháy nhẹ (CSS), số cảnh báo gian lận hiện badge Danger to dễ thấy. Nếu không có thi nào → ẩn card hoặc thu nhỏ thành 1 dòng trạng thái, không cần cả khối trống.
6. **Thành viên mới chờ duyệt**: list nhỏ, mỗi dòng có 2 nút nhanh Duyệt/Từ chối ngay tại dashboard (giảm thao tác chuyển trang) — đây là cải tiến UX so với bản cũ.
7. **Phím tắt nhanh**: giữ 2 nút to "Lịch học"/"Nhật ký" nhưng đổi từ card vuông nhàm chán sang 2 nút ngang có icon lớn bên trái + label, nền tint Primary nhạt.

❌ Không thêm thống kê nào khác ngoài "Hiệu suất 7 ngày" ở trang chủ — tránh biến dashboard thành trang báo cáo.

---

## 5. Dashboard — Role ADMIN

Hiện tại chỉ là empty state to đùng, lãng phí — vì admin cần thấy **sức khỏe hệ thống** ngay khi vào, không phải click thêm 1 lần nữa.

Thiết kế lại thành dashboard tóm tắt thật sự (nhẹ, không quá tải):

1. **Hero band**: "Trung tâm quản trị" + CTA "Vào Dashboard quản trị đầy đủ" (giữ nút này, nhưng không còn là toàn bộ nội dung trang).
2. **Hàng 4 stat card nhỏ ngang** (chỉ số quan trọng nhất, số to + icon + tint nền theo màu ý nghĩa):
   - Tổng người dùng hoạt động (icon group, Primary)
   - Giáo viên chờ phê duyệt (icon person-check, Warning nếu >0)
   - Lớp học đang hoạt động (icon school, Primary)
   - Cảnh báo hệ thống/lỗi sandbox gần đây (icon warning, Danger nếu >0, xanh success nếu 0)
3. **Card "Giáo viên chờ phê duyệt"**: list rút gọn 3 người kèm nút Duyệt nhanh — đây là việc cần hành động, không nên giấu sau nút "vào dashboard".
4. **Card "Hoạt động gần đây / Logs"**: 3–5 dòng log mới nhất dạng timeline gọn (icon + hành động + thời gian), có link "Xem toàn bộ logs".

Sidebar (nếu giữ layout 2 cột) có thể thêm 1 illustration nhỏ dạng "admin console" tông xanh-tím để đỡ khô khan, đặt cạnh nút CTA chính.

❌ Không nhồi biểu đồ phức tạp (uptime, CPU sandbox...) vào trang chủ admin — để ở trang quản trị chuyên biệt.

---

## 6. Component mới cần thêm vào `base.css` / `includes/`

| Component | Mục đích | Class gợi ý |
|---|---|---|
| `.hero-band` | Khối chào mừng gradient trên cùng mỗi dashboard | dùng chung 1 partial `includes/dashboard_hero.html` với biến `{{ role }}`, `{{ greeting }}`, `{{ cta_list }}` |
| `.stat-chip` | Số liệu nhỏ có icon + tint nền + sparkline optional | thay thế cho 3 khối số trần hiện tại |
| `.progress-ring` | Vòng tròn % tiến độ (thay progress bar ngang cho lớp học) | dùng SVG `stroke-dasharray` |
| `.badge-status` | Badge trạng thái (Success/Warning/Danger) dùng chung mọi nơi (chấm bài, thi, deadline) | đã có phần nào, chuẩn hóa lại 1 chỗ |
| `.empty-illustration` | Wrapper cho SVG minh họa trạng thái trống | dùng lại cho mọi role thay vì icon check đơn |
| `.card-priority` | Card viền trái màu theo mức ưu tiên (deadline gấp, cần chấm gấp) | border-left 4px + tint nền nhẹ |

---

## 7. Việc AI agent cần làm

1. Tạo/refactor `templates/includes/dashboard_hero.html` dùng chung 3 role, truyền context khác nhau.
2. Sửa `templates/home.html`: tổ chức lại theo đúng thứ tự ưu tiên mục 3/4/5 ở trên cho từng role (dùng `{% if user.role == ... %}`).
3. Thêm các class mới ở mục 6 vào `static/css/base.css`, dùng đúng token màu ở mục 1 — **không tạo màu mới ngoài Primary/Accent/Success/Warning/Danger đã có**.
4. Thêm 3–4 SVG illustration inline (line-art, 2 màu Primary + Accent, không dùng ảnh raster) cho: hero band, empty states, admin sidebar.
5. Áp dụng `.progress-ring` cho tiến độ lớp học (student) thay vì thanh ngang.
6. Với các khối có thể rỗng (bài thi, thi live, thông báo), **ẩn hẳn hoặc thu gọn** thay vì luôn chiếm 1 ô full-size như hiện tại.
7. Giữ nguyên toàn bộ route/URL hiện có, không đổi logic backend — chỉ đổi trình bày & bố cục HTML/CSS.
8. Responsive: sidebar 4 cols rơi xuống dưới main content trên màn <1024px, hero band ẩn illustration trên mobile.

Sau khi làm xong, xuất lại: screenshot hoặc diff `home.html` + `base.css` để review trước khi merge.
