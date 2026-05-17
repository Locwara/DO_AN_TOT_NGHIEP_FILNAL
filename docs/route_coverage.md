# Route coverage note

Tai lieu nay ghi nhanh cac route/entrypoint moi da duoc gan UI, hoac duoc xep la API/command noi bo de van hanh.

## UI-backed routes

- Accounts: register, login, logout, profile, student dashboard, teacher dashboard, teacher registration.
- Classrooms: list/detail/create/edit/delete/join/quick join/leave, gradebook, leaderboard, member import, subject/semester/announcement flows.
- Assignments: list/detail/create/edit/delete/publish, calendar, testcase/rubric/file flows, statistics, plagiarism report, late report.
- Submissions: solve IDE, history/detail, teacher submission list, manual/rubric grading, exam lobby/IDE/monitor/export.
- Discussions: list/detail/create/edit/delete, vote, mark answer, pin.
- Notifications: list, open, mark read, mark all read.
- Administration: dashboards, approvals, users, classroom/subject management, languages, sandbox configs, system settings, logs/export, metrics, exam events, sandbox monitor.

## JSON/internal API routes

- `assignments:calendar_events`: calendar data for assignment calendar UI.
- `submissions:save_draft`: IDE autosave.
- `submissions:run_test`: IDE run sample/custom input.
- `submissions:submit`: IDE final submit.
- `submissions:exam_ping`: exam heartbeat.
- `submissions:exam_event`: exam warning/audit events.
- `submissions:add_comment`: grading code comment AJAX.
- `submissions:resolve_comment`: resolve/unresolve code comment AJAX.
- `discussions:vote`, `discussions:mark_answer`, `discussions:pin`: discussion AJAX actions.
- `classrooms:subject_check_name`: subject duplicate check.

## Management commands

- `send_due_soon_notifications`: scheduler job, documented in `docs/scheduler.md`.
- `expire_exam_sessions`: scheduler job, documented in `docs/scheduler.md`.
- `collect_server_metrics`: scheduler job, documented in `docs/scheduler.md`.
- `detect_sandbox_zombies`: scheduler job, documented in `docs/scheduler.md`.
- `seed_semesters`: setup/seed helper command.

## QA entrypoints

- `docs/qa_smoke.md` contains browser smoke flows for Student, Teacher, Exam, Admin, and Security.
