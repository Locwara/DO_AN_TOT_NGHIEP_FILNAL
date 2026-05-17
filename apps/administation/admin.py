from django.contrib import admin
from .models import (
    ProgrammingLanguages, SandboxConfigs, ServerMetrics,
    ActivityLogs, SystemSettings,
)


@admin.register(ProgrammingLanguages)
class ProgrammingLanguagesAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'version', 'file_extension', 'syntax_highlight_mode', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')
    ordering = ('display_name',)
    list_per_page = 25
    list_editable = ('is_active',)
    fieldsets = (
        ('Ngôn ngữ', {
            'fields': ('name', 'display_name', 'version', 'file_extension'),
        }),
        ('Cấu hình', {
            'fields': ('is_active', 'syntax_highlight_mode', 'default_template'),
        }),
    )
    actions = ['activate_languages', 'deactivate_languages']

    @admin.action(description='Kích hoạt ngôn ngữ')
    def activate_languages(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Đã kích hoạt {updated} ngôn ngữ.')

    @admin.action(description='Vô hiệu hóa ngôn ngữ')
    def deactivate_languages(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Đã vô hiệu hóa {updated} ngôn ngữ.')


@admin.register(SandboxConfigs)
class SandboxConfigsAdmin(admin.ModelAdmin):
    list_display = ('language', 'docker_image', 'timeout_seconds', 'memory_limit_mb', 'cpu_limit', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('language', 'docker_image')
    ordering = ('language',)
    list_per_page = 25
    list_editable = ('is_active', 'timeout_seconds', 'memory_limit_mb')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Sandbox', {
            'fields': ('language', 'docker_image', 'is_active'),
        }),
        ('Giới hạn tài nguyên', {
            'fields': ('timeout_seconds', 'memory_limit_mb', 'cpu_limit'),
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['activate_sandboxes', 'deactivate_sandboxes']

    @admin.action(description='Kích hoạt sandbox')
    def activate_sandboxes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Đã kích hoạt {updated} cấu hình sandbox.')

    @admin.action(description='Vô hiệu hóa sandbox')
    def deactivate_sandboxes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Đã vô hiệu hóa {updated} cấu hình sandbox.')


@admin.register(ServerMetrics)
class ServerMetricsAdmin(admin.ModelAdmin):
    list_display = ('recorded_at', 'cpu_usage', 'memory_usage', 'active_containers', 'queue_length', 'avg_execution_time')
    ordering = ('-recorded_at',)
    readonly_fields = ('recorded_at', 'cpu_usage', 'memory_usage', 'active_containers', 'queue_length', 'avg_execution_time')
    list_per_page = 50
    date_hierarchy = 'recorded_at'
    actions = ['delete_old_metrics']

    def has_add_permission(self, request):
        return False

    @admin.action(description='Xóa metrics cũ (>7 ngày)')
    def delete_old_metrics(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=7)
        old = queryset.filter(recorded_at__lt=cutoff)
        count = old.count()
        old.delete()
        self.message_user(request, f'Đã xóa {count} bản ghi metrics cũ hơn 7 ngày.')


@admin.register(ActivityLogs)
class ActivityLogsAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'resource_type', 'resource_id', 'ip_address')
    list_filter = ('resource_type', 'created_at')
    search_fields = ('action', 'user__username', 'ip_address', 'resource_type')
    raw_id_fields = ('user',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'user', 'action', 'resource_type', 'resource_id', 'ip_address', 'user_agent', 'metadata')
    list_per_page = 50
    date_hierarchy = 'created_at'
    actions = ['delete_old_logs']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.action(description='Xóa logs cũ (>30 ngày)')
    def delete_old_logs(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=30)
        old = queryset.filter(created_at__lt=cutoff)
        count = old.count()
        old.delete()
        self.message_user(request, f'Đã xóa {count} log cũ hơn 30 ngày.')


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('setting_key', 'get_value_preview', 'description', 'updated_by', 'updated_at')
    search_fields = ('setting_key', 'description')
    raw_id_fields = ('updated_by',)
    list_per_page = 25
    fieldsets = (
        ('Cài đặt', {
            'fields': ('setting_key', 'setting_value', 'description'),
        }),
        ('Cập nhật', {
            'fields': ('updated_by',),
        }),
    )

    @admin.display(description='Giá trị')
    def get_value_preview(self, obj):
        val = str(obj.setting_value)
        return val[:60] + '...' if len(val) > 60 else val

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
