from django.db import models
from django.contrib.auth.models import User

class ProgrammingLanguages(models.Model):
    name = models.TextField(unique=True)
    display_name = models.TextField()
    version = models.TextField(blank=True, null=True)
    file_extension = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    syntax_highlight_mode = models.TextField(blank=True, null=True)
    default_template = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'programming_languages'

    def __str__(self):
        label = self.display_name or self.name or f'Language #{self.pk}'
        if self.version:
            return f'{label} ({self.version})'
        return label

class SandboxConfigs(models.Model):
    language = models.TextField(unique=True)
    docker_image = models.TextField()
    timeout_seconds = models.IntegerField(default=5)
    memory_limit_mb = models.IntegerField(default=256)
    cpu_limit = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sandbox_configs'

class ServerMetrics(models.Model):
    cpu_usage = models.FloatField(blank=True, null=True)
    memory_usage = models.FloatField(blank=True, null=True)
    active_containers = models.IntegerField(blank=True, null=True)
    queue_length = models.IntegerField(blank=True, null=True)
    avg_execution_time = models.FloatField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'server_metrics'

class ActivityLogs(models.Model):
    user = models.ForeignKey(User, models.SET_NULL, blank=True, null=True)
    action = models.TextField()
    resource_type = models.TextField(blank=True, null=True)
    resource_id = models.IntegerField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'activity_logs'

class SystemSettings(models.Model):
    setting_key = models.TextField(unique=True)
    setting_value = models.JSONField()
    description = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(User, models.SET_NULL, db_column='updated_by', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'