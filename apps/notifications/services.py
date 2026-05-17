from django.contrib.auth import get_user_model

from .models import Notifications


def notify_user(recipient, title, message='', link='', notification_type='', actor=None, metadata=None):
    if not recipient or not getattr(recipient, 'is_active', True):
        return None

    return Notifications.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type or '',
        title=title,
        message=message or '',
        link=link or '',
        metadata=metadata or None,
    )


def notify_users(recipients, title, message='', link='', notification_type='', actor=None, metadata=None):
    User = get_user_model()
    recipient_ids = []
    for recipient in recipients:
        if isinstance(recipient, User):
            recipient_id = recipient.pk
            is_active = recipient.is_active
        else:
            recipient_id = recipient
            is_active = True
        if recipient_id and is_active:
            recipient_ids.append(recipient_id)

    unique_ids = list(dict.fromkeys(recipient_ids))
    if not unique_ids:
        return []

    notifications = [
        Notifications(
            recipient_id=recipient_id,
            actor=actor,
            notification_type=notification_type or '',
            title=title,
            message=message or '',
            link=link or '',
            metadata=metadata or None,
        )
        for recipient_id in unique_ids
    ]
    return Notifications.objects.bulk_create(notifications)


def notify_admins(title, message='', link='', notification_type='', actor=None, metadata=None):
    User = get_user_model()
    admin_ids = User.objects.filter(
        is_active=True,
        profiles__role='admin',
    ).values_list('id', flat=True)
    superuser_ids = User.objects.filter(
        is_active=True,
        is_superuser=True,
    ).values_list('id', flat=True)
    return notify_users(
        list(admin_ids) + list(superuser_ids),
        title=title,
        message=message,
        link=link,
        notification_type=notification_type,
        actor=actor,
        metadata=metadata,
    )
