from django.db import models
from django.contrib.auth.models import User

class ClassroomApprovalStatus(models.TextChoices):
    PENDING = 'pending', 'Chờ duyệt'
    APPROVED = 'approved', 'Đã duyệt'
    REJECTED = 'rejected', 'Từ chối'


class Classrooms(models.Model):
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    invite_code = models.CharField(unique=True, max_length=10)
    teacher = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    max_students = models.IntegerField(default=100)
    status = models.CharField(max_length=16, choices=ClassroomApprovalStatus.choices, default=ClassroomApprovalStatus.PENDING)
    approved_by = models.ForeignKey(User, models.SET_NULL, related_name='approved_classrooms', blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=False)  # Changed default to False - only approved classrooms are active
    settings = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'classrooms'


class SubjectApprovalStatus(models.TextChoices):
    PENDING = 'pending', 'Chờ duyệt'
    APPROVED = 'approved', 'Đã duyệt'
    REJECTED = 'rejected', 'Từ chối'


class Semesters(models.Model):
    """Kỳ học/học kỳ dùng chung toàn hệ thống (VD: HK1 2024-2025)."""
    code = models.CharField(max_length=32, unique=True, help_text='VD: HK1_2024, HK2_2024')
    name = models.CharField(max_length=128, help_text='VD: Học kỳ 1 - 2024-2025')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False, help_text='Đánh dấu kỳ học đang diễn ra')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'semesters'
        ordering = ('-start_date', '-code')

    def __str__(self):
        return self.name or self.code

    def save(self, *args, **kwargs):
        # Chỉ cho phép một kỳ duy nhất là is_current=True
        if self.is_current:
            Semesters.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Subjects(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    languages = models.ManyToManyField('administation.ProgrammingLanguages', related_name='subjects', blank=True)
    status = models.CharField(max_length=16, choices=SubjectApprovalStatus.choices, default=SubjectApprovalStatus.PENDING)
    created_by = models.ForeignKey(User, models.CASCADE, related_name='created_subjects', blank=True, null=True)
    approved_by = models.ForeignKey(User, models.SET_NULL, related_name='approved_subjects', blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subjects'
        ordering = ('status', 'code')

    def __str__(self):
        return f'{self.code} - {self.name}'


class ClassroomSubjects(models.Model):
    classroom = models.ForeignKey(Classrooms, models.CASCADE, related_name='classroom_subject_links')
    subject = models.ForeignKey(Subjects, models.CASCADE, related_name='classroom_links')
    semester = models.ForeignKey(
        Semesters, models.SET_NULL,
        related_name='classroom_subject_links',
        blank=True, null=True,
        help_text='Kỳ học mà lớp này dạy môn này. Có thể để trống nếu chưa phân kỳ.'
    )
    assigned_by = models.ForeignKey(User, models.SET_NULL, related_name='assigned_subject_links', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'classroom_subjects'
        # Một lớp có thể gán cùng một môn cho nhiều kỳ khác nhau (không trùng trong cùng một kỳ).
        unique_together = (('classroom', 'subject', 'semester'),)
        ordering = ('classroom_id', 'subject_id', '-semester_id')

    def __str__(self):
        sem = f' ({self.semester})' if self.semester_id else ''
        return f'{self.classroom} - {self.subject}{sem}'

class ClassroomMembers(models.Model):
    classroom = models.ForeignKey(Classrooms, models.CASCADE, blank=True, null=True)
    student = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    status = models.TextField(blank=True, null=True, default='approved')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'classroom_members'
        unique_together = (('classroom', 'student'),)
        indexes = [
            models.Index(fields=['classroom', 'status'], name='cm_classroom_status_idx'),
            models.Index(fields=['student', 'status'], name='cm_student_status_idx'),
        ]

class Announcements(models.Model):
    classroom = models.ForeignKey(Classrooms, models.CASCADE, blank=True, null=True)
    teacher = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    title = models.TextField()
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'announcements'

class Leaderboard(models.Model):
    classroom = models.ForeignKey(Classrooms, models.CASCADE, blank=True, null=True)
    student = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    total_score = models.FloatField(default=0)
    assignments_completed = models.IntegerField(default=0)
    avg_score = models.FloatField(default=0)
    rank = models.IntegerField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leaderboard'
        unique_together = (('classroom', 'student'),)
