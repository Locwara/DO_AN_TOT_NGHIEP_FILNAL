# Deployment operations checklist

Dung checklist nay cho cac viec khong the xac nhan chi bang source code.

## Credential rotation

- [ ] Tao `DJANGO_SECRET_KEY` moi va cap nhat bien moi truong deploy.
- [ ] Rotate Supabase database password.
- [ ] Cap nhat `DATABASE_URL` hoac `DB_PASSWORD` tren deploy sau khi rotate Supabase.
- [ ] Rotate Cloudinary API secret.
- [ ] Cap nhat `CLOUDINARY_API_SECRET` tren deploy.
- [ ] Rotate Gmail app password neu production dung SMTP Gmail.
- [ ] Cap nhat `EMAIL_HOST_PASSWORD` tren deploy.
- [ ] Restart app/worker/scheduler sau khi cap nhat secrets.
- [ ] Xac nhan app boot voi `DJANGO_DEBUG=False`.

## Supabase/PostgreSQL verification

- [ ] Chay migration tren moi truong Supabase/PostgreSQL:
  `python manage.py migrate`
- [ ] Chay regression suite tren PostgreSQL de cac test `ArrayField` khong bi skip:
  `python manage.py test apps.accounts.tests apps.administation.tests apps.assignments.tests apps.classrooms.tests apps.notifications.tests apps.submissions.tests --keepdb`
- [ ] Xac nhan khong co test skipped do SQLite.

## Browser smoke test

Thuc hien theo `docs/qa_smoke.md` tren staging/Supabase:

- [ ] Student E2E pass.
- [ ] Teacher E2E pass.
- [ ] Exam E2E pass.
- [ ] Admin E2E pass.
- [ ] Security E2E pass.

## Scheduler smoke test

- [ ] Cau hinh cron/Celery Beat theo `docs/scheduler.md`.
- [ ] Xac nhan `send_due_soon_notifications` khong gui trung notification.
- [ ] Xac nhan `expire_exam_sessions` xu ly session qua gio.
- [ ] Xac nhan `collect_server_metrics` tao metric moi.
- [ ] Xac nhan `detect_sandbox_zombies` gui alert cho admin khi co task treo.
