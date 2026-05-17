from django.conf import settings
from django.db import models


class Notifications(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='sent_notifications',
        blank=True,
        null=True,
    )
    notification_type = models.CharField(max_length=80, blank=True)
    title = models.TextField()
    message = models.TextField(blank=True)
    link = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]

    def __str__(self):
        return self.title
