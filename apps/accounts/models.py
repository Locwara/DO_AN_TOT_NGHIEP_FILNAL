from django.db import models
from django.contrib.auth.models import User

class Profiles(models.Model):
    id = models.OneToOneField(User, models.CASCADE, db_column='id', primary_key=True)
    role = models.TextField(blank=True, null=True, default='student')
    avatar_url = models.TextField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True, default='approved')
    last_login = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'profiles'
        indexes = [
            models.Index(fields=['role', 'status'], name='profile_role_status_idx'),
            models.Index(fields=['status', '-created_at'], name='profile_status_created_idx'),
        ]

class TeacherRegistrations(models.Model):
    user = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    institution = models.TextField(blank=True, null=True)
    proof_document_url = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True, default='pending')
    reviewed_by = models.ForeignKey(User, models.SET_NULL, db_column='reviewed_by', related_name='reviewed_registrations', blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'teacher_registrations'
        indexes = [
            models.Index(fields=['status', '-created_at'], name='tr_status_created_idx'),
            models.Index(fields=['reviewed_by', 'status'], name='tr_reviewer_status_idx'),
        ]

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'search_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.query}"
