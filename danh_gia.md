# 📋 ĐÁNH GIÁ HỆ THỐNG DEVLEARN THEO YÊU CẦU GIÁO VIÊN

> Tài liệu này đánh giá mức độ đáp ứng của hệ thống **DevLearn** so với 8 nhóm yêu cầu chính của giáo viên hướng dẫn.
> Tham chiếu mã nguồn: `services/docker_service.py`, `services/plagiarism_service.py`, `apps/assignments/`, `apps/submissions/`, `apps/classrooms/`, `apps/administation/`.

**Quy ước trạng thái:**
- ✅ **ĐÃ CÓ**: Đã triển khai đầy đủ.
- 🟡 **CÓ MỘT PHẦN**: Có nền tảng nhưng còn thiếu hoặc chưa hoàn chỉnh.
- ❌ **CHƯA CÓ**: Chưa triển khai, cần làm mới.

---

## 1️⃣ Yêu cầu 1 — Thực thi mã & Sandbox

### 1.1. Sinh viên upload file `.c, .cpp, .cs, .py,...` hoặc paste code trực tiếp?
- 🟡 **CÓ MỘT PHẦN**
  - **Đã có**: Paste code trực tiếp vào IDE (Monaco editor) — `templates/submissions/solve_problem.html`, `static/js/editor.js`. Hỗ trợ ngôn ngữ: `python, python3, cpp, c, java, javascript/nodejs` (xem `services/docker_service.py::_get_file_extension`).
  - **Đã có**: Nộp file (`.zip`, `.pdf`, `.docx`, ...) cho dạng `submission_mode='file'` — `apps/submissions/views.py::submit_file_view`.
  - **Thiếu**: KHÔNG hỗ trợ upload trực tiếp file `.c/.cpp/.py` rồi tự nạp vào IDE để chấm. Sinh viên buộc phải copy-paste vào ô code.
  - **Thiếu**: Chưa hỗ trợ `C#` (.cs) — danh sách ngôn ngữ hiện chỉ có Python, C, C++, Java, JS.

### 1.2. Compile + chạy trong Docker container cô lập (mỗi bài một container riêng)?
- ✅ **ĐÃ CÓ**
  - `services/docker_service.py::_execute_with_docker` tạo `tempfile.mkdtemp` + `docker run --rm` cho **mỗi lần chạy** (mount `tmpfs`, `read-only`, user `nobody:65534`).
  - Có **fallback** sang `subprocess` khi Docker không khả dụng (`_execute_with_subprocess`) — phù hợp dev nhưng cần khóa lại trong production.
  - Có quản trị `SandboxConfigs` ở `apps/administation/` để admin cấu hình `docker_image, timeout_seconds, memory_limit_mb, cpu_limit` cho từng ngôn ngữ.

### 1.3. Giới hạn tài nguyên: timeout (VD: 5s), memory limit, không cho phép truy cập mạng?
- ✅ **ĐÃ CÓ**
  - `--network=none` — chặn mạng. ✅
  - `--memory={N}m`, `--memory-swap={N}m` — chặn swap. ✅
  - `--cpus={cpu_limit}` — giới hạn CPU. ✅
  - `--pids-limit=64` — chặn fork-bomb. ✅
  - `--read-only` + `--tmpfs /tmp` — filesystem chỉ đọc. ✅
  - `subprocess.run(timeout=timeout_seconds + 5)` + báo `Time Limit Exceeded`. ✅
  - **Lưu ý**: Trong fallback subprocess không có giới hạn memory thực sự (chỉ có timeout). Cần đảm bảo production luôn dùng Docker.

### 1.4. Trả về: output thực tế, trạng thái (Accepted / WA / TLE / RE / CE)?
- ✅ **ĐÃ CÓ**, đầy đủ trạng thái:
  - `passed` → Accepted (`apps/submissions/tasks.py`).
  - `wrong_answer` → WA.
  - `time_limit_exceeded` → TLE.
  - `runtime_error` → RE.
  - `compilation_error` → CE.
  - Trả về `actual_output, expected_output, execution_time, memory_usage, error_message` — `services/docker_service.py::run_testcase`.
  - **Yếu**: `memory_usage` luôn = 0 (chưa lấy thực từ Docker stats). Cần dùng `docker stats` hoặc `--cgroup` để đo bộ nhớ thực.

---

## 2️⃣ Yêu cầu 2 — Quản lý Test Case

### 2.1. Giảng viên tạo nhiều cặp Input → Expected Output cho mỗi bài?
- ✅ **ĐÃ CÓ**
  - Model `Testcases` (`apps/assignments/models.py`): `input_data, expected_output, weight, order_index, timeout_override, memory_override`.
  - Form & UI: `templates/assignments/testcase_form.html`, `templates/assignments/_assignment_form.html` (Integrated Testcase Manager).
  - **Bonus**: Hỗ trợ **import hàng loạt** từ JSON/CSV — `templates/assignments/import_testcases.html`.

### 2.2. Hỗ trợ test case ẩn (hidden) và test case mẫu (sample)?
- ✅ **ĐÃ CÓ**
  - `Testcases.is_hidden` (default=True) và `Testcases.is_sample` (default=False).
  - Hiển thị testcase mẫu cho học sinh: `apps/submissions/views.py` query `Testcases.filter(is_sample=True)`.
  - Khi `assignment.show_testcase_result=False` → ẩn toàn bộ.

### 2.3. Chấm điểm theo tỉ lệ (VD: 7/10 testcase → 70%)?
- ✅ **ĐÃ CÓ**
  - `apps/submissions/tasks.py::grade_submission_task`:
    ```python
    score_earned = (tc.weight / total_weight) * assignment.max_score
    ```
  - Hỗ trợ **trọng số (`weight`)** cho từng testcase, không chỉ tỉ lệ đếm.
  - Có `late_penalty_percent` áp dụng sau cùng.

---

## 3️⃣ Yêu cầu 3 — Hiển thị kết quả chi tiết

### 3.1. Hiển thị từng test case Pass/Fail?
- ✅ **ĐÃ CÓ**
  - Model `SubmissionDetails` lưu kết quả từng testcase: `result_status, actual_output, execution_time, memory_usage, error_message, score_earned`.
  - UI: `templates/submissions/detail.html`, `templates/submissions/grade.html`.

### 3.2. Test case mẫu hiển thị output thực tế vs expected?
- ✅ **ĐÃ CÓ**
  - `apps/submissions/views.py` (line ~2470): khi `assignment.show_testcase_result` hoặc `tc.is_sample` → hiển thị đầy đủ.

### 3.3. Test case ẩn chỉ hiển thị Pass/Fail?
- 🟡 **CÓ MỘT PHẦN**
  - **Đã có**: Cờ `is_hidden` + `show_testcase_result` để kiểm soát.
  - **Cần kiểm tra kỹ**: Có chỗ render template (`detail.html`) chưa lọc chặt — có khả năng leak `actual_output` của hidden test khi `show_testcase_result=True`. Cần audit lại template để đảm bảo: hidden + không phải teacher → CHỈ hiển thị Pass/Fail, KHÔNG show input/output/error.
  - **Đề xuất**: Thêm helper `should_reveal_testcase(tc, user, assignment)` rõ ràng và dùng nhất quán ở mọi template.

---

## 4️⃣ Yêu cầu 4 — Quản lý phiên thi

### 4.1. Mở/đóng bài thi theo thời gian tự động?
- ✅ **ĐÃ CÓ**
  - `Assignments`: `exam_start_time`, `exam_end_time`, `exam_duration_minutes`, `exam_grace_seconds`.
  - Kiểm tra: `apps/submissions/views.py` (line ~1559, ~1600) — block khi `now < exam_start_time` hoặc `now > exam_end_time`.
  - Có **management command** `expire_exam_sessions.py` chạy định kỳ để tự đóng phiên hết giờ + auto-submit draft.
  - Lịch chạy: `docs/scheduler.md` (cần kiểm tra cron/celery beat đã setup chưa trong production).

### 4.2. Giới hạn số lần nộp (VD: tối đa 5 lần/bài)?
- ✅ **ĐÃ CÓ**
  - `Assignments.max_attempts` (Integer, nullable).
  - Enforcement đầy đủ: code (`submit_code_view` ~line 1069), file (`submit_file_view` ~line 2144), quiz (`view` ~line 1266).
  - Bonus: `exam_max_run_count` cho phép giới hạn số lần "chạy thử" trong phòng thi.

### 4.3. Lưu lịch sử tất cả lần nộp, lấy điểm cao nhất hoặc lần cuối (cấu hình được)?
- 🟡 **CÓ MỘT PHẦN**
  - **Đã có**: Mỗi lần nộp tạo 1 record `Submissions` riêng → lịch sử đầy đủ. UI: `templates/submissions/history.html`.
  - **Đã có**: Gradebook hiện đang dùng `Max(Coalesce('manual_score', 'total_score'))` → mặc định lấy **điểm cao nhất** (`apps/classrooms/views.py::_build_gradebook_data`, `core/views.py` line 146).
  - **THIẾU**: Không có **flag cho giáo viên cấu hình** "lấy điểm cao nhất" hay "lấy lần cuối" hay "trung bình". Hiện cứng = max.
  - **Đề xuất**: Thêm field `Assignments.score_aggregation_mode` với choices `['best', 'latest', 'average', 'first']` và áp dụng trong gradebook + statistics.

---

## 5️⃣ Yêu cầu 5 — Dashboard Giảng viên

### 5.1. Xem toàn bộ kết quả lớp theo thời gian thực?
- 🟡 **CÓ MỘT PHẦN**
  - **Đã có**: `templates/classrooms/gradebook.html` hiển thị toàn bộ học sinh × bài tập.
  - **Đã có**: `templates/submissions/exam_monitor.html` — giám sát phiên thi đang diễn ra (force submit, xem violation).
  - **THIẾU**: KHÔNG có **realtime push** (WebSocket/SSE) — học sinh nộp xong, GV phải refresh trang để thấy.
  - **Đề xuất**: Thêm Django Channels hoặc HTMX SSE cho `gradebook` & `exam_monitor`. Tối thiểu nên auto-refresh `setInterval` 10–30s.

### 5.2. Bảng điểm tổng hợp, xuất Excel/CSV?
- ✅ **ĐÃ CÓ** (CSV).
  - `apps/classrooms/views.py::gradebook_export_view`, `gradebook_missing_export_view`.
  - URL: `classrooms:gradebook_export`.
  - File CSV có BOM UTF-8 → mở Excel tiếng Việt đúng.
  - 🟡 **Thiếu định dạng `.xlsx`** thuần (hiện chỉ CSV). Excel mở CSV vẫn được nhưng sinh viên/GV thường thích `.xlsx` formatted.
  - **Đề xuất**: Thêm export `.xlsx` bằng `openpyxl` (có thể tô màu pass/fail, freeze header).

### 5.3. Biểu đồ phân phối điểm, tỉ lệ pass/fail từng bài?
- 🟡 **CÓ MỘT PHẦN**
  - **Đã có**: `apps/assignments/views.py::statistics_view` (~line 2103) tính `score_distribution`, `pass_rate`, render `templates/assignments/statistics.html`.
  - **Đã có**: `AssignmentStatistics` model lưu `avg_score, max_score, min_score, pass_rate, avg_attempts, most_failed_testcase`.
  - **Thiếu**: Không có **biểu đồ tổng hợp cấp lớp** (so sánh giữa các bài). Mỗi bài 1 trang riêng.
  - **Thiếu**: Chưa có **biểu đồ tỉ lệ pass/fail cho từng testcase** — đặc biệt hữu ích để GV biết testcase nào "khó" nhất.
  - **Đề xuất**: Thêm tab **"Tổng quan lớp"** trong gradebook với chart.js hiển thị: pass rate per assignment, avg score per assignment, hardest testcase per assignment.

---

## 6️⃣ Yêu cầu 6 — Dashboard Sinh viên

### 6.1. Xem điểm, lịch sử nộp bài, tiến độ từng bài tập?
- ✅ **ĐÃ CÓ**
  - `templates/accounts/student_dashboard.html` — điểm trung bình, pass rate, bài cần làm.
  - `templates/submissions/history.html` — lịch sử nộp.
  - `templates/assignments/list.html` — tiến độ từng bài (status, điểm, deadline).
  - `core/views.py` build dashboard với `recent_submissions, due_soon, latest_draft, classrooms[].completion_rate`.

### 6.2. Thông báo deadline sắp tới?
- ✅ **ĐÃ CÓ**
  - **Management command**: `apps/assignments/management/commands/send_due_soon_notifications.py`.
  - Settings `notifications.due_soon_hours` (default 24h) → gửi 1 notification 1 lần/bài (anti-duplicate qua `marker`).
  - UI: `templates/notifications/list.html`, badge ở navbar.
  - **Lưu ý**: Cần đảm bảo command này chạy theo lịch (cron mỗi giờ). Xem `docs/scheduler.md`.
  - **Đề xuất**: Thêm option **email reminder** cho deadline (hiện chỉ in-app).

---

## 7️⃣ Yêu cầu 7 — Phát hiện đạo văn

### 7.1. So sánh code giữa các sinh viên trong cùng lớp?
- ✅ **ĐÃ CÓ**
  - `services/plagiarism_service.py` + `apps/submissions/tasks.py::check_plagiarism_task`.
  - `PlagiarismReports` model lưu kết quả: `result (JSON pairs), submissions_count, pairs_count, suspicious_count, threshold`.
  - UI: `templates/assignments/plagiarism.html`.
  - Logic: Lấy `latest_submissions` per student trong 1 assignment → so sánh **pairwise**.

### 7.2. Dùng thuật toán như MOSS hoặc so sánh AST?
- 🟡 **CÓ MỘT PHẦN** (không phải MOSS thuần, nhưng có heuristic mạnh):
  - **Đã có**: Strip comment (Python + C-style), normalize whitespace, **đổi tên biến Python qua AST** (`_normalize_python_identifiers`), token similarity (SequenceMatcher), structural (bag-of-tokens cosine), text similarity. Score weighted: `0.3*text + 0.4*token + 0.3*structural`.
  - **Yếu so với MOSS**:
    - Chưa dùng **winnowing/k-gram fingerprinting** (thuật toán chuẩn MOSS).
    - AST normalize chỉ rename biến, chưa so sánh **cấu trúc AST node-by-node**.
    - C/C++/Java/JS không được normalize identifier (chỉ strip comment).
  - **Đề xuất**:
    - Tích hợp library `pycode-similar` hoặc `copydetect` để có winnowing thật.
    - Hoặc gọi **MOSS API** thật (`http://moss.stanford.edu/`) cho assignment quan trọng.
    - Tối thiểu: thêm AST-tokenization cho Python (token type thay vì giá trị).

### 7.3. Đánh dấu cảnh báo cho giảng viên?
- ✅ **ĐÃ CÓ**
  - `is_suspicious = similarity_score >= 0.85` (threshold cấu hình được).
  - UI hiển thị danh sách cặp suspicious với màu cảnh báo.
  - **Đề xuất**: Thêm notification khi report hoàn tất + báo số cặp đáng ngờ.

---

## 8️⃣ Yêu cầu 8 — Hỗ trợ chấm bài

### 8.1. Ngoài testcase, GV có thể thêm tiêu chí chấm thủ công (cấu trúc code, comment, ...)?
- ✅ **ĐÃ CÓ ĐẦY ĐỦ**
  - **Rubrics** (`apps/assignments/models.py::Rubrics`): `name, description, max_points, order_index`.
  - **RubricScores** (`apps/submissions/models.py`): điểm GV cho từng rubric per submission, kèm `comment`.
  - Form: `templates/submissions/grade.html` cho GV chấm rubric + đánh giá tổng.
  - **CodeComments**: comment **inline theo dòng code** (`line_number`).
  - **FeedbackTemplates**: GV lưu mẫu feedback tái sử dụng.
  - **AIScoringSuggestions**: AI đề xuất điểm + lý do, GV duyệt/từ chối.
  - **GradeChangeLogs**: log mọi thay đổi điểm để audit.
  - **Grading mode**: `auto / manual / mixed` cho phép kết hợp chấm tự động + chấm tay.

---

## 📊 BẢNG TỔNG KẾT

| # | Yêu cầu | Trạng thái | Mức độ |
|---|---------|------------|--------|
| 1.1 | Upload file / paste code | 🟡 | 60% — paste OK, upload code chưa, thiếu C# |
| 1.2 | Docker sandbox | ✅ | 95% |
| 1.3 | Resource limits + no network | ✅ | 100% |
| 1.4 | Trạng thái Accepted/WA/TLE/RE/CE | ✅ | 90% (memory_usage = 0) |
| 2.1 | Multi testcase | ✅ | 100% |
| 2.2 | Hidden/Sample | ✅ | 100% |
| 2.3 | Tỉ lệ điểm theo testcase | ✅ | 100% (có weight) |
| 3.1 | Pass/Fail từng tc | ✅ | 100% |
| 3.2 | Sample show I/O | ✅ | 100% |
| 3.3 | Hidden ẩn dữ liệu | 🟡 | 70% — cần audit kỹ template |
| 4.1 | Mở/đóng theo giờ | ✅ | 95% |
| 4.2 | Limit số lần nộp | ✅ | 100% |
| 4.3 | Best/Latest configurable | 🟡 | 50% — cứng = best |
| 5.1 | Realtime kết quả lớp | 🟡 | 60% — cần refresh thủ công |
| 5.2 | Export Excel/CSV | 🟡 | 80% — chỉ CSV |
| 5.3 | Chart phân phối điểm | 🟡 | 70% — thiếu so sánh giữa bài |
| 6.1 | Dashboard sinh viên | ✅ | 100% |
| 6.2 | Notify deadline | ✅ | 90% — thiếu email |
| 7.1 | So sánh trong lớp | ✅ | 100% |
| 7.2 | MOSS/AST | 🟡 | 50% — chưa winnowing thật |
| 7.3 | Đánh dấu suspicious | ✅ | 100% |
| 8.1 | Rubric + manual grading | ✅ | 100% |

**Điểm tổng quát**: ~**82%** — Hệ thống đã đáp ứng được phần lớn yêu cầu cốt lõi, các điểm thiếu chủ yếu là **hoàn thiện UX (realtime, xlsx, chart tổng quan)** và **nâng cấp thuật toán (MOSS thật, score aggregation mode)**.

---

## 🚀 ĐỀ XUẤT NÂNG CẤP THEO ƯU TIÊN

### 🔴 Ưu tiên cao (nên làm trước khi báo cáo)
1. **Audit hidden testcase rò rỉ** (Yêu cầu 3.3) — chỉ cần sửa template, ~30 phút.
2. **Thêm `score_aggregation_mode`** (Yêu cầu 4.3) — field + dropdown trong assignment form + đổi 2-3 chỗ ở gradebook. ~2 giờ.
3. **Auto-refresh exam_monitor & gradebook** (Yêu cầu 5.1) — thêm `setInterval` JS gọi endpoint JSON. ~1 giờ.
4. **Export `.xlsx`** (Yêu cầu 5.2) — dùng `openpyxl`, tạo view mới. ~1.5 giờ.

### 🟡 Ưu tiên vừa
5. **Đo memory thực** (Yêu cầu 1.4) — parse `docker stats` hoặc `/sys/fs/cgroup`. ~1 giờ.
6. **Thêm chart tổng quan lớp** (Yêu cầu 5.3) — thêm tab "Tổng quan" trong gradebook. ~3 giờ.
7. **Upload file code rồi paste vào IDE** (Yêu cầu 1.1) — JS đọc `File API` + nạp Monaco. ~1 giờ.
8. **Thêm C#** (Yêu cầu 1.1) — bổ sung config language, mcr.microsoft.com/dotnet/sdk. ~2 giờ.

### 🟢 Ưu tiên thấp (nice-to-have)
9. **Plagiarism: tích hợp `copydetect` (winnowing)** (Yêu cầu 7.2). ~3 giờ.
10. **Email reminder deadline** (Yêu cầu 6.2). ~1 giờ.
11. **Notification khi plagiarism report xong** (Yêu cầu 7.3). ~30 phút.
