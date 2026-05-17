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