# 📋 TIẾN ĐỘ BỔ SUNG THEO ĐẶC TẢ

> File này theo dõi phần bổ sung dựa trên đặc tả Student / Teacher / Admin / Reporting.
> Đối chiếu: phần backend đã hoàn thiện trong `TIEN_DO_BACKEND.md`.
> Mỗi task hoàn thành đánh dấu ✅.

---

## 🧩 PHÂN TÍCH GAP ĐỐI CHIẾU ĐẶC TẢ

### 1. STUDENT (Sinh viên)
| STT | Yêu cầu | Trạng thái | Ghi chú |
|-----|---------|-----------|---------|
| 1.1 | Học tập lý thuyết (Markdown/PDF) | ✅ | `assignment.instructions` + `AssignmentFiles` → **bổ sung Markdown render (marked.js)** |
| 1.2 | Thực hành bài tập + Sample test | ✅ | `solve_problem_view` + `run_test_view` |
| 1.3 | Kiểm tra (Exam) – khóa IDE khi hết giờ | ✅ | `is_exam`, `exam_duration_minutes`, JS countdown `startExamTimer` + `autoSubmitExam` |
| 1.4 | Nộp bài & chấm điểm | ✅ | `submit_code_view` |
| 1.5 | Quản lý nộp trễ + penalty | ✅ | `is_late`, `penalty_applied` |
| 1.6 | Theo dõi kết quả + comment theo dòng | ✅ | `submission_history`, `submission_detail`, `CodeComments` |

### 2. TEACHER (Giáo viên)
| STT | Yêu cầu | Trạng thái | Ghi chú |
|-----|---------|-----------|---------|
| 2.1 | Quản lý bài học chi tiết (mã HP, mã lớp, nội dung, tài liệu) | ✅ | `Assignments` + `AssignmentFiles` (classroom làm mã lớp) |
| 2.2 | Tạo Testcase đồng loạt (Import JSON/CSV) | ✅ | `import_testcases_view` |
| 2.3 | Chấm bài đồng loạt | ✅ | `bulk_regrade_view` |
| 2.4 | Thống kê bài học | ✅ | `statistics_view` (phổ điểm, top/weak, testcase fail rate, avg time, error dist) |
| 2.5 | Xuất báo cáo nộp trễ (Excel/PDF) | ✅ | `export_late_report_view` xuất CSV (BOM UTF-8 → Excel mở được) → **bổ sung Print view PDF** |

### 3. ADMIN (Quản trị)
| STT | Yêu cầu | Trạng thái | Ghi chú |
|-----|---------|-----------|---------|
| 3.1 | Thống kê toàn hệ thống | ✅ | `dashboard_view` + `analytics_view` |
| 3.2 | Quản lý phê duyệt (giáo viên, ngôn ngữ) | ✅ | `teacher_approvals_view` + languages CRUD |
| **3.3** | **Giám sát hạ tầng Sandbox + Zombie tasks** | ❌ → ✅ | **Thiếu trang giám sát Docker container thực tế + hàng đợi chấm bài + xử lý zombie → cần thêm mới** |

### 4. REPORTING & ANALYTICS
| Đối tượng | Nội dung | Trạng thái |
|-----------|----------|-----------|
| Student | Tiến độ cá nhân, Rank, Pass rate | ✅ `student_dashboard_view` |
| Teacher | Late report, Top/Weak, Testcase analysis | ✅ `statistics_view` + `export_late_report_view` |
| Admin | Lưu lượng submit theo giờ/ngày, Server perf, User growth | ✅ `analytics_view` |

---

## 🔨 DANH SÁCH CẦN LÀM

- [x] **A. Sandbox Monitor (Admin 3.3)** ✅
  - View `sandbox_monitor_view` hiển thị:
    - Trạng thái Docker daemon (available/unavailable)
    - Danh sách Docker containers đang chạy (từ `docker ps`)
    - Hàng đợi chấm bài: `Submissions` status = `pending` / `running`
    - Phát hiện Zombie tasks: submissions `pending`/`running` > 5 phút
  - Actions:
    - Kill zombie task (reset status → `failed`)
    - Regrade zombie task (push lại vào queue)
  - Template `sandbox_monitor.html` (style theo `base_admin.html`)
  - URL `/administration/sandbox-monitor/`
  - Thêm link ở sidebar admin

- [x] **B. Markdown rendering (Student 1.1)** ✅
  - Dùng `marked.js` (CDN) trong `solve_problem.html` và `assignment detail.html`
  - Render `assignment.instructions` và `assignment.description` dạng Markdown
  - Style `prose prose-invert` cho code block, heading, list

- [x] **C. Print/PDF view cho Late Report (Teacher 2.5)** ✅
  - View `late_report_print_view` render HTML đẹp để in / xuất PDF qua trình duyệt
  - Nút "In / Xuất PDF" gọi `window.print()`
  - URL `/assignments/<pk>/late-report/print/`
  - Link từ trang statistics

- [x] **D. Validation** ✅
  - `python manage.py check` – kiểm tra syntax, URL routing
  - Code review các thay đổi

---

## 📊 TỔNG KẾT

| Phần | Trạng thái |
|------|-----------|
| Backend core (0-8) | ✅ Hoàn thành trước đó (`TIEN_DO_BACKEND.md`) |
| A. Sandbox Monitor | ✅ Hoàn thành |
| B. Markdown rendering | ✅ Hoàn thành |
| C. Print/PDF Late Report | ✅ Hoàn thành |
| D. Validation | ✅ Hoàn thành |
