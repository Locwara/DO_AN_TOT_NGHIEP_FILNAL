from django.contrib import admin

from .models import Notifications


@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username', 'recipient__email')
    raw_id_fields = ('recipient', 'actor')
    readonly_fields = ('created_at',)
