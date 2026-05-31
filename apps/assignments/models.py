from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from apps.classrooms.models import Classrooms, ClassroomSubjects

class Assignments(models.Model):
    SUBMISSION_CODE = 'code'
    SUBMISSION_FILE = 'file'
    SUBMISSION_QUIZ = 'quiz'
    SUBMISSION_MODE_CHOICES = [
        (SUBMISSION_CODE, 'Lập trình'),
        (SUBMISSION_FILE, 'Nộp file'),
        (SUBMISSION_QUIZ, 'Trắc nghiệm'),
    ]

    GRADING_AUTO = 'auto'
    GRADING_MANUAL = 'manual'
    GRADING_MIXED = 'mixed'
    GRADING_MODE_CHOICES = [
        (GRADING_AUTO, 'Tự động'),
        (GRADING_MANUAL, 'Thủ công'),
        (GRADING_MIXED, 'Kết hợp'),
    ]

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
    starter_code = models.TextField(blank=True, null=True, help_text="Mã nguồn hiện sẵn trong IDE khi học sinh mới mở bài.")
    solution_code = models.TextField(blank=True, null=True, help_text="Mã nguồn mẫu của giáo viên dùng để kiểm tra testcase.")
    solution_language = models.TextField(blank=True, null=True, help_text="Ngôn ngữ của mã nguồn mẫu.")
    type = models.TextField(default='auto_grade')
    submission_mode = models.CharField(
        max_length=16,
        choices=SUBMISSION_MODE_CHOICES,
        default=SUBMISSION_CODE,
    )
    grading_mode = models.CharField(
        max_length=16,
        choices=GRADING_MODE_CHOICES,
        default=GRADING_AUTO,
    )
    difficulty = models.TextField(blank=True, null=True)
    allowed_languages = ArrayField(models.TextField(), blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    late_submission_allowed = models.BooleanField(default=False)
    late_penalty_percent = models.FloatField(default=0)
    max_score = models.FloatField(default=100)
    max_attempts = models.IntegerField(blank=True, null=True)

    show_testcase_result = models.BooleanField(default=True)
    enable_leaderboard = models.BooleanField(default=False)
    grades_released_at = models.DateTimeField(blank=True, null=True)
    show_feedback_after_release = models.BooleanField(default=True)
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


class AssignmentFileRequirements(models.Model):
    assignment = models.OneToOneField(
        Assignments,
        models.CASCADE,
        related_name='file_requirements',
    )
    allowed_extensions = ArrayField(
        models.CharField(max_length=16),
        blank=True,
        default=list,
        help_text='VD: .pdf, .docx, .zip, .py',
    )
    allowed_mime_types = ArrayField(
        models.CharField(max_length=128),
        blank=True,
        default=list,
    )
    max_file_size_mb = models.PositiveIntegerField(default=20)
    max_files = models.PositiveIntegerField(default=1)
    require_comment = models.BooleanField(default=False)
    allow_resubmit = models.BooleanField(default=True)
    require_all_files_before_submit = models.BooleanField(default=True)
    scan_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignment_file_requirements'

    def __str__(self):
        return f'File requirements for assignment #{self.assignment_id}'


class QuizSettings(models.Model):
    ORDER_FIXED = 'fixed'
    ORDER_RANDOM = 'random'
    ORDER_CHOICES = [
        (ORDER_FIXED, 'Cố định'),
        (ORDER_RANDOM, 'Ngẫu nhiên'),
    ]

    assignment = models.OneToOneField(
        Assignments,
        models.CASCADE,
        related_name='quiz_settings',
    )
    question_order_mode = models.CharField(max_length=16, choices=ORDER_CHOICES, default=ORDER_FIXED)
    choice_order_mode = models.CharField(max_length=16, choices=ORDER_CHOICES, default=ORDER_FIXED)
    show_score_after_submit = models.BooleanField(default=True)
    show_correct_answers = models.BooleanField(default=False)
    show_explanation = models.BooleanField(default=False)
    time_limit_minutes = models.PositiveIntegerField(blank=True, null=True)
    passing_score = models.FloatField(blank=True, null=True)
    allow_review = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quiz_settings'
        indexes = [
            models.Index(fields=['question_order_mode'], name='quizset_q_order_idx'),
            models.Index(fields=['choice_order_mode'], name='quizset_c_order_idx'),
        ]

    def __str__(self):
        return f'Quiz settings for assignment #{self.assignment_id}'


class QuizQuestions(models.Model):
    TYPE_SINGLE_CHOICE = 'single_choice'
    TYPE_MULTIPLE_CHOICE = 'multiple_choice'
    TYPE_TRUE_FALSE = 'true_false'
    TYPE_SHORT_TEXT = 'short_text'
    QUESTION_TYPE_CHOICES = [
        (TYPE_SINGLE_CHOICE, 'Một đáp án'),
        (TYPE_MULTIPLE_CHOICE, 'Nhiều đáp án'),
        (TYPE_TRUE_FALSE, 'Đúng/Sai'),
        (TYPE_SHORT_TEXT, 'Trả lời ngắn'),
    ]

    assignment = models.ForeignKey(
        Assignments,
        models.CASCADE,
        related_name='quiz_questions',
    )
    question_text = models.TextField()
    question_type = models.CharField(max_length=24, choices=QUESTION_TYPE_CHOICES, default=TYPE_SINGLE_CHOICE)
    points = models.FloatField(default=1)
    order_index = models.IntegerField(default=0)
    explanation = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    media_url = models.TextField(blank=True, null=True)
    tags = ArrayField(models.CharField(max_length=80), blank=True, default=list)
    difficulty = models.TextField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quiz_questions'
        ordering = ('order_index', 'id')
        indexes = [
            models.Index(fields=['assignment', 'is_active', 'order_index'], name='quizq_asg_active_order_idx'),
            models.Index(fields=['assignment', 'question_type'], name='quizq_asg_type_idx'),
            models.Index(fields=['difficulty'], name='quizq_difficulty_idx'),
        ]

    def __str__(self):
        return f'{self.assignment_id} - {self.question_text[:80]}'


class QuizChoices(models.Model):
    question = models.ForeignKey(
        QuizQuestions,
        models.CASCADE,
        related_name='choices',
    )
    choice_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order_index = models.IntegerField(default=0)
    explanation = models.TextField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quiz_choices'
        ordering = ('order_index', 'id')
        indexes = [
            models.Index(fields=['question', 'order_index'], name='quizc_question_order_idx'),
            models.Index(fields=['question', 'is_correct'], name='quizc_question_correct_idx'),
        ]

    def __str__(self):
        return f'{self.question_id} - {self.choice_text[:80]}'


class QuizQuestionImports(models.Model):
    assignment = models.ForeignKey(
        Assignments,
        models.CASCADE,
        related_name='quiz_question_imports',
    )
    file_name = models.TextField(blank=True, null=True)
    imported_by = models.ForeignKey(
        User,
        models.SET_NULL,
        blank=True,
        null=True,
        related_name='quiz_question_imports',
    )
    total_rows = models.PositiveIntegerField(default=0)
    success_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    clear_existing = models.BooleanField(default=False)
    metadata = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quiz_question_imports'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['assignment', '-created_at'], name='quizimp_asg_created_idx'),
            models.Index(fields=['imported_by', '-created_at'], name='quizimp_user_created_idx'),
        ]

    def __str__(self):
        return f'Quiz import #{self.pk} - assignment #{self.assignment_id}'


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
