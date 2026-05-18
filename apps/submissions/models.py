from django.db import models
from django.contrib.auth.models import User
from apps.assignments.models import Assignments, Testcases, Rubrics

class Submissions(models.Model):
    assignment = models.ForeignKey(Assignments, models.CASCADE, blank=True, null=True)
    student = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    code_content = models.TextField()
    language = models.TextField()
    status = models.TextField(default='pending')
    total_score = models.FloatField(default=0)
    max_score = models.FloatField(default=100)
    passed_testcases = models.IntegerField(default=0)
    total_testcases = models.IntegerField(default=0)
    execution_time = models.FloatField(blank=True, null=True)
    memory_usage = models.FloatField(blank=True, null=True)
    is_late = models.BooleanField(default=False)
    penalty_applied = models.FloatField(default=0)
    manual_score = models.FloatField(blank=True, null=True)
    teacher_comment = models.TextField(blank=True, null=True)
    graded_by = models.ForeignKey(User, models.SET_NULL, db_column='graded_by', related_name='graded_submissions', blank=True, null=True)
    graded_at = models.DateTimeField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'submissions'
        indexes = [
            models.Index(
                fields=['assignment', 'student', 'status', '-submitted_at'],
                name='sub_asg_st_status_at_idx',
            ),
            models.Index(fields=['status', '-submitted_at'], name='sub_status_at_idx'),
            models.Index(fields=['language', 'status', '-submitted_at'], name='sub_lang_status_at_idx'),
            models.Index(fields=['student', 'status', '-submitted_at'], name='sub_student_status_at_idx'),
            models.Index(fields=['assignment', 'status', '-submitted_at'], name='sub_asg_status_at_idx'),
        ]

class SubmissionDetails(models.Model):
    submission = models.ForeignKey(Submissions, models.CASCADE, blank=True, null=True)
    testcase = models.ForeignKey(Testcases, models.CASCADE, blank=True, null=True)
    result_status = models.TextField(blank=True, null=True)
    actual_output = models.TextField(blank=True, null=True)
    execution_time = models.FloatField(blank=True, null=True)
    memory_usage = models.FloatField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    log_output = models.TextField(blank=True, null=True)
    score_earned = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'submission_details'

class CodeComments(models.Model):
    submission = models.ForeignKey(Submissions, models.CASCADE, blank=True, null=True)
    teacher = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    line_number = models.IntegerField()
    comment_text = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'code_comments'


class RubricScores(models.Model):
    submission = models.ForeignKey(Submissions, models.CASCADE, related_name='rubric_scores')
    rubric = models.ForeignKey(Rubrics, models.CASCADE, related_name='scores')
    score = models.FloatField(default=0)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rubric_scores'
        unique_together = (('submission', 'rubric'),)
        ordering = ('rubric__order_index', 'rubric_id')


class FeedbackTemplates(models.Model):
    teacher = models.ForeignKey(User, models.CASCADE, related_name='feedback_templates')
    title = models.CharField(max_length=120)
    content = models.TextField()
    category = models.CharField(max_length=60, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feedback_templates'
        ordering = ('category', 'title')

    def __str__(self):
        return self.title


class CodeDrafts(models.Model):
    assignment = models.ForeignKey(Assignments, models.CASCADE, blank=True, null=True)
    student = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    code_content = models.TextField(blank=True, null=True)
    language = models.TextField(blank=True, null=True)
    last_saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'code_drafts'
        unique_together = (('assignment', 'student', 'language'),)


class ExamSessions(models.Model):
    STATUS_NOT_STARTED = 'not_started'
    STATUS_RUNNING = 'running'
    STATUS_SUBMITTED = 'submitted'
    STATUS_AUTO_SUBMITTED = 'auto_submitted'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, 'Chưa bắt đầu'),
        (STATUS_RUNNING, 'Đang làm'),
        (STATUS_SUBMITTED, 'Đã nộp'),
        (STATUS_AUTO_SUBMITTED, 'Tự động nộp'),
        (STATUS_EXPIRED, 'Hết giờ'),
        (STATUS_CANCELLED, 'Đã hủy'),
    ]

    assignment = models.ForeignKey(Assignments, models.CASCADE, related_name='exam_sessions')
    student = models.ForeignKey(User, models.CASCADE, related_name='exam_sessions')
    final_submission = models.ForeignKey(
        Submissions,
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='exam_sessions',
    )
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_NOT_STARTED)
    started_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    current_language = models.TextField(blank=True, null=True)
    latest_draft = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    extra_time_minutes = models.IntegerField(default=0)
    violation_count = models.IntegerField(default=0)
    run_count = models.IntegerField(default=0)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exam_sessions'
        unique_together = (('assignment', 'student'),)
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['assignment', 'status'], name='exam_asg_status_idx'),
            models.Index(fields=['student', 'status'], name='exam_st_status_idx'),
            models.Index(fields=['status', '-updated_at'], name='exam_status_updated_idx'),
            models.Index(fields=['status', 'ends_at'], name='exam_status_ends_idx'),
            models.Index(fields=['violation_count', '-updated_at'], name='exam_warn_updated_idx'),
        ]

    def __str__(self):
        return f'Exam session #{self.pk} - {self.assignment_id}/{self.student_id}'


class ExamEvents(models.Model):
    session = models.ForeignKey(ExamSessions, models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=64)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'exam_events'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['-created_at'], name='exam_event_created_idx'),
        ]

    def __str__(self):
        return f'{self.event_type} - session #{self.session_id}'
