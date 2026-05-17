# Kich ban scheduler van hanh

File nay ghi cac job nen chay dinh ky tren production/staging de cac man hinh admin co du lieu moi va khong can thao tac tay.

## Cron don gian

- Moi 1 phut:
  - `python manage.py expire_exam_sessions`
- Moi 5 phut:
  - `python manage.py collect_server_metrics`
  - `python manage.py send_due_soon_notifications`
- Moi 10 phut:
  - `python manage.py detect_sandbox_zombies`

## Celery beat goi y

```python
app.conf.beat_schedule = {
    "expire-exam-sessions-every-minute": {
        "task": "django.core.management.call_command",
        "schedule": 60.0,
        "args": ("expire_exam_sessions",),
    },
    "collect-server-metrics-every-five-minutes": {
        "task": "django.core.management.call_command",
        "schedule": 300.0,
        "args": ("collect_server_metrics",),
    },
    "send-due-soon-notifications-every-five-minutes": {
        "task": "django.core.management.call_command",
        "schedule": 300.0,
        "args": ("send_due_soon_notifications",),
    },
    "detect-sandbox-zombies-every-ten-minutes": {
        "task": "django.core.management.call_command",
        "schedule": 600.0,
        "args": ("detect_sandbox_zombies",),
    },
}
```

## Policy settings lien quan

- `exam.default_grace_seconds`: so giay gia han mac dinh khi het gio thi.
- `exam.require_fullscreen_default`: mac dinh bat fullscreen khi tao bai thi.
- `exam.allow_custom_input_default`: mac dinh cho phep custom input trong bai thi.
- `notifications.due_soon_hours`: so gio truoc deadline de gui nhac han.
- `sandbox.zombie_threshold_minutes`: so phut pending/running de admin monitor coi la zombie.
- `uploads.assignment_max_mb`: dung luong toi da cua file dinh kem bai tap.
