from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from apps.classrooms.models import Classrooms, ClassroomSubjects

class Assignments(models.Model):
    classroom = models.ForeignKey(Classrooms, models.CASCADE, blank=True, null=True)
    classroom_subject = models.ForeignKey(
        ClassroomSubjects, models.SET_NULL,
        related_name='assignments',
        blank=True, null=True,
        help_text='Gắn bài tập vào (lớp + môn + kỳ học). Có thể để trống cho bài tập chưa phân môn.'
    )
    title = models.TextField()
    description = models.TextField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    type = models.TextField(default='auto_grade')
    difficulty = models.TextField(blank=True, null=True)
    allowed_languages = ArrayField(models.TextField(), blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    late_submission_allowed = models.BooleanField(default=False)
    late_penalty_percent = models.FloatField(default=0)
    max_score = models.IntegerField(default=100)
    max_attempts = models.IntegerField(blank=True, null=True)
    show_testcase_result = models.BooleanField(default=True)
    enable_leaderboard = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    # Exam mode fields
    is_exam = models.BooleanField(default=False)
    exam_duration_minutes = models.IntegerField(blank=True, null=True)
    exam_start_time = models.DateTimeField(blank=True, null=True)
    exam_end_time = models.DateTimeField(blank=True, null=True)
    exam_require_fullscreen = models.BooleanField(default=False)
    exam_allow_custom_input = models.BooleanField(default=True)
    exam_allow_sample_run = models.BooleanField(default=True)
    exam_max_run_count = models.IntegerField(blank=True, null=True)
    exam_grace_seconds = models.IntegerField(default=30)
    created_by = models.ForeignKey(User, models.CASCADE, db_column='created_by', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignments'
        indexes = [
            models.Index(
                fields=['classroom', 'is_published', 'due_date'],
                name='asg_cls_pub_due_idx',
            ),
            models.Index(fields=['classroom_subject'], name='asg_cls_subject_idx'),
            models.Index(fields=['classroom_subject', 'is_exam', 'is_published'], name='asg_cs_exam_pub_idx'),
            models.Index(fields=['classroom', 'is_exam', 'is_published'], name='asg_cls_exam_pub_idx'),
            models.Index(fields=['created_by', 'is_published'], name='asg_creator_pub_idx'),
            models.Index(fields=['is_exam', '-created_at'], name='asg_exam_created_idx'),
        ]

class Testcases(models.Model):
    assignment = models.ForeignKey(Assignments, models.CASCADE, blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    input_data = models.TextField(blank=True, null=True)
    expected_output = models.TextField(blank=True, null=True)
    is_hidden = models.BooleanField(default=True)
    is_sample = models.BooleanField(default=False)
    weight = models.FloatField(default=1.0)
    timeout_override = models.IntegerField(blank=True, null=True)
    memory_override = models.IntegerField(blank=True, null=True)
    order_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'testcases'

class AssignmentFiles(models.Model):
    assignment = models.ForeignKey(Assignments, models.CASCADE, blank=True, null=True)
    file_name = models.TextField()
    file_url = models.TextField()
    file_size = models.BigIntegerField(blank=True, null=True)
    mime_type = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assignment_files'

class AssignmentStatistics(models.Model):
    assignment = models.OneToOneField(Assignments, models.CASCADE, blank=True, null=True)
    total_submissions = models.IntegerField(default=0)
    unique_students = models.IntegerField(default=0)
    avg_score = models.FloatField(default=0)
    max_score = models.FloatField(default=0)
    min_score = models.FloatField(default=0)
    pass_rate = models.FloatField(default=0)
    avg_attempts = models.FloatField(default=0)
    most_failed_testcase = models.ForeignKey(Testcases, models.SET_NULL, db_column='most_failed_testcase', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignment_statistics'


class Rubrics(models.Model):
    assignment = models.ForeignKey(
        Assignments,
        models.CASCADE,
        related_name='rubrics',
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    max_points = models.FloatField(default=0)
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rubrics'
        ordering = ('order_index', 'id')

    def __str__(self):
        return f'{self.assignment_id} - {self.name}'


class PlagiarismReports(models.Model):
    assignment = models.ForeignKey(
        Assignments,
        models.CASCADE,
        related_name='plagiarism_reports',
    )
    created_by = models.ForeignKey(User, models.SET_NULL, blank=True, null=True, related_name='plagiarism_reports')
    status = models.CharField(max_length=20, default='pending')
    threshold = models.FloatField(default=0.85)
    language = models.CharField(max_length=40, blank=True, null=True)
    result = models.JSONField(default=list, blank=True)
    submissions_count = models.IntegerField(default=0)
    pairs_count = models.IntegerField(default=0)
    suspicious_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'plagiarism_reports'
        ordering = ('-created_at',)

    def __str__(self):
        return f'Plagiarism report #{self.pk} - {self.assignment_id}'
