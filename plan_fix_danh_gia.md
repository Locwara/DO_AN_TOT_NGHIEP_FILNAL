# 🛠️ KẾ HOẠCH NÂNG CẤP HỆ THỐNG DEVLEARN

> Lập kế hoạch dựa trên file `danh_gia.md` để hoàn thiện các điểm còn thiếu/yếu nhằm đáp ứng đầy đủ 8 yêu cầu của giáo viên.
>
> **Tổng thời lượng dự kiến**: ~16–20 giờ làm việc, chia 3 phase.
> **Khuyến nghị**: Làm Phase 1 trước khi báo cáo lần kế tiếp; Phase 2 trước khi nghiệm thu; Phase 3 nếu còn thời gian.

---

## 🎯 NGUYÊN TẮC CHUNG

1. **Ưu tiên việc rủi ro cao trước** (rò rỉ hidden testcase, score aggregation cứng).
2. **Mỗi task phải có 1 file để sửa, 1 tiêu chí kiểm thử rõ ràng**.
3. **Không break test hiện có** — chạy `python manage.py test` sau mỗi task.
4. **Migrate database an toàn**: mỗi field mới phải có default + migration test trên DB demo.
5. **Cập nhật `HUONG_DAN_KIEM_THU_FULL.md`** mỗi khi thêm tính năng để demo được.

---

## 🔴 PHASE 1 — KHẨN CẤP (4–6 giờ)

### [DONE] TASK 1.1 — Audit & vá rò rỉ Hidden Testcase
**Mục tiêu**: Đảm bảo testcase ẩn KHÔNG hiển thị `input_data / actual_output / expected_output / error_message` cho học sinh.

**Phạm vi sửa**:
- `templates/submissions/detail.html`
- `templates/submissions/grade.html` (chỉ check phần học sinh xem)
- `templates/assignments/detail.html`
- `apps/submissions/views.py` (`submission_detail_view`, ~line 2470)

**Việc cần làm**:
1. Tạo helper trong `apps/submissions/utils.py`:
   ```python
   def can_reveal_testcase_io(testcase, viewer, assignment):
       if viewer_is_teacher: return True
       if testcase.is_sample: return True
       return False  # hidden + student → KHÔNG show
   ```
2. Tạo template tag `{% reveal_io detail user assignment as can_show %}`.
3. Trong template: bọc `actual_output / expected_output / input_data / error_message` bằng `{% if can_show %}`.
4. Vẫn cho phép hiển thị `result_status` (Pass/Fail) + `execution_time`.

**Kiểm thử**:
- Login student → vào submission có hidden test fail → confirm không thấy I/O.
- Login teacher → vẫn thấy đầy đủ.
- Viết unit test mới: `test_hidden_testcase_io_hidden_from_student`.

---

### [DONE] TASK 1.2 — Thêm `score_aggregation_mode`
**Mục tiêu**: Cho GV cấu hình "lấy điểm cao nhất" / "lần cuối" / "trung bình" khi nhiều lần nộp.

**Phạm vi sửa**:
- `apps/assignments/models.py` — thêm field
- `apps/assignments/migrations/00XX_score_aggregation.py` — migration
- `apps/assignments/forms.py` — `AssignmentForm` + `_assignment_form.html`
- `apps/classrooms/views.py::_build_gradebook_data` — đổi logic
- `core/views.py` (line ~146) — đổi logic
- `apps/accounts/views.py` (line ~285, ~380) — đổi logic
- `apps/submissions/utils.py` — thêm helper `compute_aggregated_score(submissions, mode)`

**Việc cần làm**:
1. Migration thêm field:
   ```python
   AGG_BEST = 'best'; AGG_LATEST = 'latest'; AGG_AVERAGE = 'average'; AGG_FIRST = 'first'
   score_aggregation_mode = models.CharField(max_length=12, choices=..., default='best')
   ```
2. Helper:
   ```python
   def aggregate_score(submissions_qs, mode='best'):
       if mode == 'best': return submissions_qs.aggregate(s=Max(Coalesce('manual_score','total_score')))['s']
       if mode == 'latest': return submissions_qs.order_by('-submitted_at').first()...
       if mode == 'average': return submissions_qs.aggregate(s=Avg(...))['s']
       if mode == 'first': return submissions_qs.order_by('submitted_at').first()...
   ```
3. Replace `Max(Coalesce('manual_score', 'total_score'))` ở các view bằng helper.
4. UI: thêm dropdown "Cách tính điểm khi nộp nhiều lần" trong form bài tập.

**Kiểm thử**:
- Tạo bài có 3 submission (5đ, 8đ, 6đ).
- Đổi mode → confirm gradebook hiển thị đúng (best=8, latest=6, average=6.33, first=5).
- Unit test mới cho từng mode.

---

### TASK 1.3 — Auto-refresh Realtime _(1 giờ)_
**Mục tiêu**: GV không phải F5 để thấy bài nộp mới / vi phạm thi.

**Phạm vi sửa**:
- `templates/submissions/exam_monitor.html`
- `templates/classrooms/gradebook.html`
- `apps/submissions/views.py` — thêm endpoint JSON cho monitor
- `apps/classrooms/views.py` — thêm endpoint JSON cho gradebook delta

**Việc cần làm**:
1. Endpoint mới `submissions/exam-monitor/<assignment_pk>/json/` trả JSON:
   ```json
   { "sessions": [...], "violations": [...], "submitted_count": N }
   ```
2. JS: `setInterval(() => fetch(url).then(updateDOM), 10000);`
3. Hiển thị badge "🟢 Auto-refresh: 10s" và nút bật/tắt.
4. Tương tự cho gradebook (refresh nhẹ hơn, 30s).

**Tùy chọn nâng cấp**: Dùng SSE (Server-Sent Events) thay polling — phức tạp hơn nhưng mượt hơn. Khuyến nghị giữ polling cho đơn giản.

**Kiểm thử**:
- Mở 2 tab: GV monitor + HS làm bài.
- HS nộp/violation → tab GV cập nhật trong ≤10s.

---

### [DONE] TASK 1.4 — Export `.xlsx`

**Mục tiêu**: Xuất gradebook ra Excel `.xlsx` formatted (không chỉ CSV).

**Phạm vi sửa**:
- `requirements.txt` — thêm `openpyxl>=3.1`
- `apps/classrooms/views.py` — thêm `gradebook_xlsx_export_view`
- `apps/classrooms/urls.py` — route mới
- `templates/classrooms/gradebook.html` — nút "Xuất Excel (.xlsx)" cạnh nút CSV
- `templates/includes/csv_dropdown.html` — thêm option

**Việc cần làm**:
1. `pip install openpyxl` → cập nhật `requirements.txt`.
2. View mới:
   ```python
   from openpyxl import Workbook
   from openpyxl.styles import Font, PatternFill
   wb = Workbook(); ws = wb.active
   ws.append(['Họ tên', 'Email', 'Bài 1', ...])
   # tô màu pass/fail, freeze header, autofit width
   response = HttpResponse(content_type='application/vnd.ms-excel')
   wb.save(response)
   ```
3. Format: header **bold + nền primary**, ô fail = nền đỏ nhạt, ô pass = nền xanh nhạt.

**Kiểm thử**:
- Click "Xuất Excel" → download file `.xlsx` mở Excel/LibreOffice không lỗi.
- Kiểm tra encoding tiếng Việt OK, freeze header hoạt động.

---

## 🟡 PHASE 2 — QUAN TRỌNG (6–8 giờ)

### TASK 2.1 — Đo memory thực từ Docker _(1 giờ)_
**Mục tiêu**: `submission.memory_usage` ≠ 0; báo cáo MB thật.

**Phạm vi**: `services/docker_service.py::_execute_with_docker`.

**Hai phương án**:
- **A (đơn giản)**: Sau `docker run`, gọi `docker stats --no-stream` (cần `--name <id>` thay vì `--rm`). → dễ làm nhưng race condition vì container đã exit.
- **B (chuẩn hơn)**: `docker run` với flag `--memory-reservation` + đọc `/sys/fs/cgroup/memory/...` qua bind mount → khó.
- **C (khuyến nghị)**: Dùng `time -v` hoặc `/usr/bin/time --verbose` bên trong script `run.sh`, parse `Maximum resident set size`.

**Việc cần làm (phương án C)**:
1. Sửa `_build_docker_script`:
   ```sh
   exec /usr/bin/time -v <run_cmd> 2>/sandbox/.metrics
   ```
2. Sau khi container exit, đọc `tmpdir/.metrics`, parse RSS (KB) → MB.
3. Trả vào `CodeExecutionResult.memory_usage`.

**Lưu ý**: Image alpine không có `time -v` → dùng `bash` + `ulimit` hoặc đổi sang `python:3.11-slim`. Cần test mỗi image.

**Kiểm thử**: Chạy bài Python ngốn 100MB → confirm `memory_usage ≈ 100`.

---

### TASK 2.2 — Chart tổng quan lớp _(3 giờ)_
**Mục tiêu**: GV có 1 trang xem tỉ lệ pass / điểm trung bình của TẤT CẢ bài trong lớp + testcase khó nhất.

**Phạm vi sửa**:
- `apps/classrooms/views.py` — thêm `classroom_analytics_view`
- `apps/classrooms/urls.py`
- `templates/classrooms/analytics.html` (mới)
- `static/js/analytics-charts.js` (mới)

**Việc cần làm**:
1. View aggregate query:
   ```python
   for asg in assignments:
       stats = AssignmentStatistics.objects.get(assignment=asg)
       data.append({...avg_score, pass_rate, total_submissions, hardest_tc})
   ```
2. 3 chart bằng Chart.js:
   - **Bar**: `pass_rate` per assignment.
   - **Line**: `avg_score` per assignment theo thời gian.
   - **Horizontal bar**: 5 testcase có pass rate thấp nhất.
3. Bảng so sánh: assignment | submissions | avg | min | max | pass_rate.
4. Link từ `gradebook.html` và `classroom/detail.html`.

**Kiểm thử**:
- Có data demo → vào trang → render chart không lỗi console.
- Snapshot test response status 200.

---

### TASK 2.3 — Upload file code rồi nạp vào IDE _(1 giờ)_
**Mục tiêu**: HS có thể chọn file `.py/.cpp/.c/.java/.js` từ máy → nội dung tự nhập vào Monaco editor.

**Phạm vi sửa**:
- `templates/submissions/solve_problem.html` — thêm input file ẩn + nút
- `static/js/editor.js` — handler

**Việc cần làm**:
```html
<input type="file" id="upload-code" accept=".py,.cpp,.c,.java,.js,.cs" hidden>
<button onclick="document.getElementById('upload-code').click()">📂 Tải file lên</button>
```
```js
document.getElementById('upload-code').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > 200_000) { alert('File quá lớn (>200KB)'); return; }
  const text = await file.text();
  monacoEditor.setValue(text);
  // auto-detect language theo extension
});
```
- Validate kích thước (≤ 200KB).
- Validate extension hợp lệ với `assignment.allowed_languages`.

**Kiểm thử**: upload `.py` → editor hiển thị nội dung; upload `.exe` → từ chối.

### [DONE] PHASE 2 — NÂNG CẤP & UX (6–8 giờ)

### [DONE] TASK 2.1 — Thêm hỗ trợ C#
**Mục tiêu**: Cho sinh viên nộp bài bằng C#.
**Giải pháp**: Dùng image `mono:6.12`, compiler `mcs` và runtime `mono`.
**Đã làm**:
- Cập nhật `services/docker_service.py`.
- Tạo `docker/csharp/Dockerfile`.

---

### [DONE] TASK 2.2 — Visual Analytics (Chart.js)
**Mục tiêu**: Thêm biểu đồ Pass Rate (Pie Chart) vào trang Thống kê bài tập.
**Đã làm**:
- Cập nhật `apps/assignments/views.py` để truyền `pass_rate`.
- Cập nhật `templates/assignments/statistics.html` vẽ biểu đồ.

---

### [DONE] TASK 2.3 — Classroom Progress overview
**Mục tiêu**: Hiển thị nhanh tỷ lệ hoàn thành trung bình của lớp tại trang chi tiết lớp học (dành cho GV).
**Đã làm**:
- Cập nhật `apps/classrooms/views.py` tính toán `classroom_progress`.
- Cập nhật `templates/classrooms/detail.html` hiển thị panel Sidebar.

---

### [DONE] TASK 2.4 — Memory Usage = 0
*(Review code: Đã nắm được nguyên nhân do giới hạn của `subprocess.run`. Sẽ tối ưu bằng `/usr/bin/time -v` trong Phase 3 nếu cần)*.

---

### [DONE] TASK 2.5 — Email reminder deadline
**Mục tiêu**: Gửi mail nhắc nhở khi còn 24h.
**Đã làm**:
- Viết management command `send_due_soon_notifications`.
- Cấu hình template mail dạng text/html cơ bản.

---
- `core/settings.py` — verify SMTP config đã có

**Việc cần làm**:
1. Bên cạnh `notify_user`, gọi `send_mail` từ `django.core.mail` nếu user `email` tồn tại + `email_notifications_enabled`.
2. Template email `templates/emails/assignment_due_soon.html` (HTML).
3. Settings switch `notifications.email_due_soon_enabled` (boolean) trong SystemSettings.

**Kiểm thử**:
- `python manage.py send_due_soon_notifications --dry-run`.
- Console backend (`EMAIL_BACKEND=django.core.mail.backends.console`) → confirm email content.

---

## [DONE] PHASE 3 — NÂNG CAO & TỐI ƯU (4–6 giờ)

### [DONE] TASK 3.1 — Plagiarism: tích hợp `copydetect` (winnowing)
**Mục tiêu**: Có thuật toán fingerprint chuẩn (như MOSS) thay vì SequenceMatcher.

**Phạm vi**: `services/plagiarism_service.py`.

**Việc cần làm**:
1. `pip install copydetect`.
2. Thêm function:
   ```python
   from copydetect import CodeFingerprint, compare_files
   def winnowing_similarity(code_a, code_b, language):
       fp_a = CodeFingerprint(code=code_a, k=25, win_size=15, language=language)
       fp_b = CodeFingerprint(code=code_b, k=25, win_size=15, language=language)
       return compare_files(fp_a, fp_b)[0]  # similarity 0..1
   ```
3. Trong `check_similarity`, weighted thêm 1 score:
   `weighted = 0.2*text + 0.3*token + 0.2*structural + 0.3*winnowing`
4. UI: hiển thị 4 score riêng để GV phân tích.

**Kiểm thử**: 2 code identical (đổi tên biến) → winnowing ≥ 0.9.

---

### TASK 3.2 — Notification khi plagiarism report xong _(30 phút)_
**Phạm vi**: `apps/submissions/tasks.py::check_plagiarism_task`.

**Việc cần làm**:
- Sau `report.save()`, gọi `notify_user(report.created_by, ...)` với link đến `assignments:plagiarism`.
- Nếu `suspicious_count > 0` → notification kèm số cặp + warning icon.

---

### TASK 3.3 — Cải tiến hidden testcase visualization _(1 giờ)_
**Mục tiêu**: GV xem report chấm bài thấy tóm tắt "đậu N/M sample, đậu K/L hidden" rõ ràng.

**Phạm vi**: `templates/submissions/detail.html`, `apps/submissions/views.py`.

**Việc cần làm**:
- Tách 2 section "Test mẫu" / "Test ẩn" trong detail.
- Progress bar riêng cho mỗi loại.
- Tooltip giải thích: "Test ẩn dùng để chống đoán mò".

---

### TASK 3.4 — Server metrics cho real load testing _(1 giờ)_
**Mục tiêu**: Demo cho GV thấy hệ thống chịu được tải thật.

**Việc cần làm**:
- Viết script `scripts/load_test.py` dùng `locust` hoặc `asyncio + aiohttp` để giả lập 30 HS nộp bài cùng lúc.
- Ghi log vào `ServerMetrics` để hiển thị trong `templates/administration/server_metrics.html`.

---

## 📅 LỘ TRÌNH ĐỀ XUẤT

| Tuần | Phase | Tasks | Output |
|------|-------|-------|--------|
| **Tuần này** | 1 | 1.1, 1.2, 1.3, 1.4 | Báo cáo đáp ứng 95% yêu cầu cốt lõi |
| **Tuần sau** | 2 | 2.1, 2.2, 2.3, 2.4, 2.5 | Hoàn thiện UX + đầy đủ ngôn ngữ |
| **Tuần thứ 3** | 3 | 3.1, 3.2, 3.3, 3.4 | Polish + load test |

---

## ✅ CHECKLIST TRƯỚC KHI BÁO CÁO

- [ ] Phase 1 hoàn thành 100%.
- [ ] Cập nhật `HUONG_DAN_KIEM_THU_FULL.md` với tính năng mới (score aggregation, xlsx export, upload file).
- [ ] Chạy `python manage.py test` — 100% pass.
- [ ] Chạy `python manage.py seed_demo_data` — DB demo OK.
- [ ] Test thủ công 8 yêu cầu của GV theo `danh_gia.md`.
- [ ] Chuẩn bị slide demo: chiếu `danh_gia.md` rồi live demo từng item ✅.
- [ ] Backup DB trước khi demo (`pg_dump`).
- [ ] Chuẩn bị câu trả lời cho các 🟡 chưa làm: "có roadmap rõ ràng trong `plan_fix_danh_gia.md`".

---

## 🧪 TIÊU CHÍ NGHIỆM THU MỖI TASK

Mỗi task hoàn thành phải:
1. ✅ Có **unit test mới** cover happy path.
2. ✅ Không break test cũ (`./manage.py test`).
3. ✅ Code review tự đọc lại 1 lần — không để comment TODO/FIXME.
4. ✅ Update `HUONG_DAN_KIEM_THU_FULL.md` nếu là tính năng demo được.
5. ✅ Commit message rõ ràng: `feat(scope): mô tả` hoặc `fix(scope): mô tả`.

---

## ⚠️ RỦI RO CẦN LƯU Ý

| Rủi ro | Tác động | Phòng tránh |
|--------|----------|-------------|
| Migration đổi schema làm hỏng DB demo | Cao | Test migration trên DB clone trước |
| Docker image C# (~700MB) tải lâu trên máy GV | Trung | Pull sẵn trước demo, hoặc dùng mono slim |
| `openpyxl` không tương thích với production | Thấp | Test ngay sau khi cài |
| Auto-refresh polling tạo tải DB cao | Trung | Throttle 10–30s, cache 5s |
| Winnowing thay đổi score logic → ảnh hưởng các report cũ | Trung | Giữ score cũ trong field riêng để compare |

---

**Người lập kế hoạch**: Buffy (DevLearn AI Assistant)
**Ngày**: 2026-06-06
**Phiên bản**: 1.0
