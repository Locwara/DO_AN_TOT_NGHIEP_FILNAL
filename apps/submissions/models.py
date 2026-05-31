from django.db import models
from django.contrib.auth.models import User
from apps.assignments.models import Assignments, Testcases, Rubrics, QuizQuestions, QuizChoices

class Submissions(models.Model):
    assignment = models.ForeignKey(Assignments, models.CASCADE, blank=True, null=True)
    student = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    code_content = models.TextField(blank=True, default='')
    language = models.TextField(blank=True, default='')
    submission_text = models.TextField(blank=True, null=True)
    submission_mode_snapshot = models.CharField(
        max_length=16,
        choices=Assignments.SUBMISSION_MODE_CHOICES,
        default=Assignments.SUBMISSION_CODE,
    )
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
            models.Index(fields=['submission_mode_snapshot', 'status', '-submitted_at'], name='sub_mode_status_at_idx'),
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


class SubmissionFiles(models.Model):
    SCAN_PENDING = 'pending'
    SCAN_SKIPPED = 'skipped'
    SCAN_CLEAN = 'clean'
    SCAN_FAILED = 'failed'
    SCAN_BLOCKED = 'blocked'
    TEXT_NOT_REQUESTED = 'not_requested'
    TEXT_PENDING = 'pending'
    TEXT_EXTRACTED = 'extracted'
    TEXT_FAILED = 'failed'
    TEXT_UNSUPPORTED = 'unsupported'
    SCAN_STATUS_CHOICES = [
        (SCAN_PENDING, 'Chờ quét'),
        (SCAN_SKIPPED, 'Bỏ qua'),
        (SCAN_CLEAN, 'An toàn'),
        (SCAN_FAILED, 'Quét lỗi'),
        (SCAN_BLOCKED, 'Bị chặn'),
    ]
    TEXT_EXTRACTION_STATUS_CHOICES = [
        (TEXT_NOT_REQUESTED, 'Chưa yêu cầu'),
        (TEXT_PENDING, 'Chờ trích xuất'),
        (TEXT_EXTRACTED, 'Đã trích xuất'),
        (TEXT_FAILED, 'Trích xuất lỗi'),
        (TEXT_UNSUPPORTED, 'Chưa hỗ trợ'),
    ]

    submission = models.ForeignKey(Submissions, models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(User, models.SET_NULL, blank=True, null=True, related_name='uploaded_submission_files')
    file_name = models.TextField()
    file_url = models.TextField()
    file_size = models.BigIntegerField(blank=True, null=True)
    mime_type = models.TextField(blank=True, null=True)
    extension = models.CharField(max_length=16, blank=True, null=True)
    checksum = models.CharField(max_length=128, blank=True, null=True)
    storage_provider = models.CharField(max_length=40, default='cloudinary')
    scan_status = models.CharField(max_length=16, choices=SCAN_STATUS_CHOICES, default=SCAN_PENDING)
    text_extraction_status = models.CharField(
        max_length=24,
        choices=TEXT_EXTRACTION_STATUS_CHOICES,
        default=TEXT_NOT_REQUESTED,
    )
    extracted_text = models.TextField(blank=True, null=True)
    extraction_error = models.TextField(blank=True, null=True)
    extracted_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'submission_files'
        indexes = [
            models.Index(fields=['submission', 'uploaded_at'], name='subfile_submission_at_idx'),
            models.Index(fields=['checksum'], name='subfile_checksum_idx'),
            models.Index(fields=['scan_status', '-uploaded_at'], name='subfile_scan_at_idx'),
            models.Index(fields=['extension', '-uploaded_at'], name='subfile_ext_at_idx'),
            models.Index(fields=['text_extraction_status', '-uploaded_at'], name='subfile_text_at_idx'),
        ]

    def __str__(self):
        return self.file_name


class SubmissionFileFeedbacks(models.Model):
    submission = models.ForeignKey(Submissions, models.CASCADE, related_name='feedback_files')
    uploaded_by = models.ForeignKey(User, models.SET_NULL, blank=True, null=True, related_name='uploaded_feedback_files')
    file_name = models.TextField()
    file_url = models.TextField()
    file_size = models.BigIntegerField(blank=True, null=True)
    mime_type = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'submission_file_feedbacks'
        indexes = [
            models.Index(fields=['submission', '-uploaded_at'], name='subfb_submission_at_idx'),
            models.Index(fields=['uploaded_by', '-uploaded_at'], name='subfb_uploader_at_idx'),
        ]

    def __str__(self):
        return self.file_name

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


class GradeChangeLogs(models.Model):
    submission = models.ForeignKey(Submissions, models.CASCADE, related_name='grade_change_logs')
    changed_by = models.ForeignKey(User, models.SET_NULL, blank=True, null=True, related_name='grade_change_logs')
    previous_manual_score = models.FloatField(blank=True, null=True)
    new_manual_score = models.FloatField(blank=True, null=True)
    previous_total_score = models.FloatField(blank=True, null=True)
    new_total_score = models.FloatField(blank=True, null=True)
    previous_status = models.CharField(max_length=40, blank=True, null=True)
    new_status = models.CharField(max_length=40, blank=True, null=True)
    previous_comment = models.TextField(blank=True, null=True)
    new_comment = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'grade_change_logs'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['submission', '-created_at'], name='gcl_submission_created_idx'),
            models.Index(fields=['changed_by', '-created_at'], name='gcl_user_created_idx'),
            models.Index(fields=['-created_at'], name='gcl_created_idx'),
        ]

    def __str__(self):
        return f'Grade change #{self.pk} - submission #{self.submission_id}'


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


class QuizAttempts(models.Model):
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED = 'submitted'
    STATUS_AUTO_SUBMITTED = 'auto_submitted'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'Đang làm'),
        (STATUS_SUBMITTED, 'Đã nộp'),
        (STATUS_AUTO_SUBMITTED, 'Tự động nộp'),
        (STATUS_EXPIRED, 'Hết giờ'),
        (STATUS_CANCELLED, 'Đã hủy'),
    ]

    assignment = models.ForeignKey(Assignments, models.CASCADE, related_name='quiz_attempts')
    student = models.ForeignKey(User, models.CASCADE, related_name='quiz_attempts')
    submission = models.ForeignKey(
        Submissions,
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='quiz_attempts',
        help_text="Bản ghi điểm cuối cùng để gradebook/statistics dùng lại.",
    )
    exam_session = models.ForeignKey(
        ExamSessions,
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='quiz_attempts',
    )
    attempt_no = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    started_at = models.DateTimeField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    score = models.FloatField(default=0)
    max_score = models.FloatField(default=0)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    random_seed = models.CharField(max_length=64, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quiz_attempts'
        unique_together = (('assignment', 'student', 'attempt_no'),)
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['assignment', 'student', '-attempt_no'], name='quiza_asg_st_attempt_idx'),
            models.Index(fields=['assignment', 'status', '-updated_at'], name='quiza_asg_status_idx'),
            models.Index(fields=['student', 'status', '-updated_at'], name='quiza_student_status_idx'),
            models.Index(fields=['exam_session'], name='quiza_exam_session_idx'),
            models.Index(fields=['submission'], name='quiza_submission_idx'),
        ]

    def __str__(self):
        return f'Quiz attempt #{self.pk} - {self.assignment_id}/{self.student_id}'


class QuizAnswers(models.Model):
    AI_NOT_REQUESTED = 'not_requested'
    AI_PENDING = 'pending'
    AI_READY = 'ready'
    AI_REVIEWED = 'reviewed'
    AI_IGNORED = 'ignored'
    AI_STATUS_CHOICES = [
        (AI_NOT_REQUESTED, 'Chưa yêu cầu'),
        (AI_PENDING, 'Chờ gợi ý'),
        (AI_READY, 'Có gợi ý'),
        (AI_REVIEWED, 'Đã xem'),
        (AI_IGNORED, 'Bỏ qua'),
    ]

    attempt = models.ForeignKey(QuizAttempts, models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestions, models.CASCADE, related_name='attempt_answers')
    selected_choice_ids = models.JSONField(blank=True, null=True, default=list)
    selected_choices = models.ManyToManyField(QuizChoices, blank=True, related_name='selected_in_answers')
    text_answer = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(blank=True, null=True)
    score_awarded = models.FloatField(default=0)
    ai_suggested_score = models.FloatField(blank=True, null=True)
    ai_suggestion_status = models.CharField(max_length=24, choices=AI_STATUS_CHOICES, default=AI_NOT_REQUESTED)
    ai_suggestion_metadata = models.JSONField(blank=True, null=True, default=dict)
    answered_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quiz_answers'
        unique_together = (('attempt', 'question'),)
        indexes = [
            models.Index(fields=['attempt', 'question'], name='quiza_ans_attempt_q_idx'),
            models.Index(fields=['question', 'is_correct'], name='quiza_ans_q_correct_idx'),
            models.Index(fields=['answered_at'], name='quiza_ans_answered_idx'),
            models.Index(fields=['ai_suggestion_status'], name='quiza_ans_ai_status_idx'),
        ]

    def __str__(self):
        return f'Answer #{self.pk} - attempt {self.attempt_id}'


class AIScoringSuggestions(models.Model):
    TARGET_FILE_SUBMISSION = 'file_submission'
    TARGET_QUIZ_SHORT_TEXT = 'quiz_short_text'
    TARGET_MANUAL_REVIEW = 'manual_review'
    TARGET_CHOICES = [
        (TARGET_FILE_SUBMISSION, 'Bài nộp file'),
        (TARGET_QUIZ_SHORT_TEXT, 'Quiz tự luận ngắn'),
        (TARGET_MANUAL_REVIEW, 'Chấm tay tổng hợp'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_READY = 'ready'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_SUPERSEDED = 'superseded'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Nháp'),
        (STATUS_READY, 'Sẵn sàng'),
        (STATUS_ACCEPTED, 'Đã chấp nhận'),
        (STATUS_REJECTED, 'Đã từ chối'),
        (STATUS_SUPERSEDED, 'Đã thay thế'),
    ]

    submission = models.ForeignKey(Submissions, models.CASCADE, related_name='ai_suggestions')
    quiz_answer = models.ForeignKey(
        QuizAnswers,
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='ai_suggestions',
    )
    target_type = models.CharField(max_length=32, choices=TARGET_CHOICES, default=TARGET_FILE_SUBMISSION)
    suggested_score = models.FloatField(blank=True, null=True)
    max_score = models.FloatField(blank=True, null=True)
    suggestion = models.TextField(blank=True, null=True)
    confidence = models.FloatField(blank=True, null=True)
    prompt_version = models.CharField(max_length=64, blank=True, null=True)
    model_name = models.CharField(max_length=128, blank=True, null=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    accepted_by_teacher = models.ForeignKey(
        User,
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='accepted_ai_scoring_suggestions',
    )
    accepted_at = models.DateTimeField(blank=True, null=True)
    input_snapshot = models.JSONField(blank=True, null=True, default=dict)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_scoring_suggestions'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['submission', 'status', '-created_at'], name='ai_sug_sub_status_idx'),
            models.Index(fields=['target_type', 'status'], name='ai_sug_target_status_idx'),
            models.Index(fields=['accepted_by_teacher', '-accepted_at'], name='ai_sug_accept_teacher_idx'),
        ]

    def __str__(self):
        return f'AI suggestion #{self.pk} - submission #{self.submission_id}'
