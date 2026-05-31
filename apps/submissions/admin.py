from django.contrib import admin
from .models import (
    Submissions, SubmissionDetails, SubmissionFiles, SubmissionFileFeedbacks,
    CodeComments, RubricScores, FeedbackTemplates, CodeDrafts, ExamSessions,
    ExamEvents, QuizAttempts, QuizAnswers, GradeChangeLogs, AIScoringSuggestions,
)


class SubmissionDetailsInline(admin.TabularInline):
    model = SubmissionDetails
    extra = 0
    fields = ('testcase', 'result_status', 'score_earned', 'execution_time', 'memory_usage')
    readonly_fields = ('testcase', 'result_status', 'score_earned', 'execution_time', 'memory_usage')
    can_delete = False
    ordering = ('testcase__order_index',)


class CodeCommentsInline(admin.TabularInline):
    model = CodeComments
    extra = 0
    fields = ('teacher', 'line_number', 'comment_text', 'is_resolved', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('teacher',)


class RubricScoresInline(admin.TabularInline):
    model = RubricScores
    extra = 0
    fields = ('rubric', 'score', 'comment')
    raw_id_fields = ('rubric',)


class SubmissionFilesInline(admin.TabularInline):
    model = SubmissionFiles
    extra = 0
    fields = (
        'file_name', 'extension', 'file_size', 'mime_type',
        'scan_status', 'text_extraction_status', 'storage_provider', 'uploaded_at',
    )
    readonly_fields = ('uploaded_at',)


class SubmissionFileFeedbacksInline(admin.TabularInline):
    model = SubmissionFileFeedbacks
    extra = 0
    fields = ('file_name', 'file_size', 'mime_type', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
    raw_id_fields = ('uploaded_by',)


class QuizAttemptsInline(admin.TabularInline):
    model = QuizAttempts
    extra = 0
    fields = ('assignment', 'student', 'attempt_no', 'status', 'score', 'max_score', 'submitted_at')
    readonly_fields = ('assignment', 'student', 'attempt_no', 'status', 'score', 'max_score', 'submitted_at')
    can_delete = False


class GradeChangeLogsInline(admin.TabularInline):
    model = GradeChangeLogs
    extra = 0
    fields = (
        'created_at', 'changed_by', 'previous_manual_score', 'new_manual_score',
        'previous_status', 'new_status', 'reason',
    )
    readonly_fields = fields
    can_delete = False


class AIScoringSuggestionsInline(admin.TabularInline):
    model = AIScoringSuggestions
    extra = 0
    fields = (
        'target_type', 'status', 'suggested_score', 'max_score',
        'confidence', 'prompt_version', 'accepted_by_teacher', 'created_at',
    )
    readonly_fields = fields
    can_delete = False


@admin.register(Submissions)
class SubmissionsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'assignment', 'student', 'submission_mode_snapshot', 'language', 'status',
        'total_score', 'max_score', 'get_testcase_info',
        'is_late', 'submitted_at',
    )
    list_filter = ('submission_mode_snapshot', 'status', 'language', 'is_late', 'submitted_at')
    search_fields = ('student__username', 'student__email', 'assignment__title')
    raw_id_fields = ('assignment', 'student', 'graded_by')
    readonly_fields = ('submitted_at',)
    list_per_page = 30
    date_hierarchy = 'submitted_at'
    inlines = [
        SubmissionDetailsInline, SubmissionFilesInline, SubmissionFileFeedbacksInline,
        RubricScoresInline, CodeCommentsInline, QuizAttemptsInline, GradeChangeLogsInline,
        AIScoringSuggestionsInline,
    ]
    fieldsets = (
        ('Bài nộp', {
            'fields': ('assignment', 'student', 'submission_mode_snapshot', 'language', 'status'),
        }),
        ('Ghi chú nộp bài', {
            'fields': ('submission_text',),
            'classes': ('collapse',),
        }),
        ('Code', {
            'fields': ('code_content',),
            'classes': ('collapse',),
        }),
        ('Kết quả', {
            'fields': (
                'total_score', 'max_score', 'passed_testcases', 'total_testcases',
                'execution_time', 'memory_usage',
            ),
        }),
        ('Nộp muộn', {
            'fields': ('is_late', 'penalty_applied'),
            'classes': ('collapse',),
        }),
        ('Chấm thủ công', {
            'fields': ('manual_score', 'teacher_comment', 'graded_by', 'graded_at'),
            'classes': ('collapse',),
        }),
        ('Thời gian', {
            'fields': ('submitted_at',),
            'classes': ('collapse',),
        }),
    )
    actions = ['mark_graded', 'mark_pending', 'regrade_submissions']

    @admin.display(description='TC passed')
    def get_testcase_info(self, obj):
        return f'{obj.passed_testcases}/{obj.total_testcases}'

    @admin.action(description='Đánh dấu đã chấm')
    def mark_graded(self, request, queryset):
        updated = queryset.update(status='finished')
        self.message_user(request, f'Đã đánh dấu {updated} bài nộp là đã chấm.')

    @admin.action(description='Đặt lại thành chờ xử lý')
    def mark_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'Đã đặt lại {updated} bài nộp thành chờ xử lý.')

    @admin.action(description='Chấm lại bài nộp (Celery)')
    def regrade_submissions(self, request, queryset):
        from .tasks import grade_submission_task
        count = 0
        for sub in queryset:
            sub.status = 'pending'
            sub.save(update_fields=['status'])
            SubmissionDetails.objects.filter(submission=sub).delete()
            grade_submission_task.delay(sub.pk)
            count += 1
        self.message_user(request, f'Đã gửi {count} bài nộp vào hàng đợi chấm lại.')


@admin.register(GradeChangeLogs)
class GradeChangeLogsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'submission', 'changed_by', 'previous_manual_score',
        'new_manual_score', 'previous_status', 'new_status', 'created_at',
    )
    list_filter = ('previous_status', 'new_status', 'created_at')
    search_fields = (
        'submission__student__username', 'submission__assignment__title',
        'changed_by__username', 'reason',
    )
    raw_id_fields = ('submission', 'changed_by')
    readonly_fields = (
        'submission', 'changed_by', 'previous_manual_score', 'new_manual_score',
        'previous_total_score', 'new_total_score', 'previous_status', 'new_status',
        'previous_comment', 'new_comment', 'reason', 'metadata', 'created_at',
    )
    list_per_page = 50


@admin.register(SubmissionDetails)
class SubmissionDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'testcase', 'result_status', 'score_earned', 'execution_time', 'memory_usage')
    list_filter = ('result_status',)
    search_fields = ('submission__student__username', 'submission__assignment__title')
    raw_id_fields = ('submission', 'testcase')
    readonly_fields = ('created_at',)
    list_per_page = 50


@admin.register(SubmissionFiles)
class SubmissionFilesAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'submission', 'file_name', 'extension', 'file_size',
        'scan_status', 'text_extraction_status', 'storage_provider', 'uploaded_at',
    )
    list_filter = ('scan_status', 'text_extraction_status', 'extension', 'storage_provider', 'uploaded_at')
    search_fields = ('file_name', 'checksum', 'submission__student__username', 'submission__assignment__title')
    raw_id_fields = ('submission', 'uploaded_by')
    readonly_fields = ('uploaded_at', 'extracted_at')
    list_per_page = 50


@admin.register(SubmissionFileFeedbacks)
class SubmissionFileFeedbacksAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'file_name', 'uploaded_by', 'uploaded_at')
    search_fields = ('file_name', 'submission__student__username', 'submission__assignment__title')
    raw_id_fields = ('submission', 'uploaded_by')
    readonly_fields = ('uploaded_at',)
    list_per_page = 50


@admin.register(CodeComments)
class CodeCommentsAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'teacher', 'line_number', 'get_comment_preview', 'is_resolved', 'created_at')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('comment_text', 'teacher__username', 'submission__student__username')
    raw_id_fields = ('submission', 'teacher')
    readonly_fields = ('created_at',)
    list_per_page = 30
    actions = ['resolve_comments', 'unresolve_comments']

    @admin.display(description='Nội dung')
    def get_comment_preview(self, obj):
        return obj.comment_text[:80] + '...' if len(obj.comment_text) > 80 else obj.comment_text

    @admin.action(description='Đánh dấu đã giải quyết')
    def resolve_comments(self, request, queryset):
        updated = queryset.update(is_resolved=True)
        self.message_user(request, f'Đã đánh dấu {updated} bình luận là đã giải quyết.')

    @admin.action(description='Bỏ đánh dấu giải quyết')
    def unresolve_comments(self, request, queryset):
        updated = queryset.update(is_resolved=False)
        self.message_user(request, f'Đã bỏ đánh dấu {updated} bình luận.')


@admin.register(RubricScores)
class RubricScoresAdmin(admin.ModelAdmin):
    list_display = ('submission', 'rubric', 'score', 'updated_at')
    search_fields = ('submission__student__username', 'rubric__name', 'comment')
    raw_id_fields = ('submission', 'rubric')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50


@admin.register(FeedbackTemplates)
class FeedbackTemplatesAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'category', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'content', 'teacher__username')
    raw_id_fields = ('teacher',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50


@admin.register(CodeDrafts)
class CodeDraftsAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'student', 'language', 'last_saved_at')
    search_fields = ('student__username', 'assignment__title')
    raw_id_fields = ('assignment', 'student')
    readonly_fields = ('last_saved_at',)
    list_per_page = 50
    actions = ['delete_old_drafts']

    @admin.action(description='Xóa bản nháp cũ (>30 ngày)')
    def delete_old_drafts(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=30)
        old = queryset.filter(last_saved_at__lt=cutoff)
        count = old.count()
        old.delete()
        self.message_user(request, f'Đã xóa {count} bản nháp cũ hơn 30 ngày.')


class ExamEventsInline(admin.TabularInline):
    model = ExamEvents
    extra = 0
    fields = ('event_type', 'metadata', 'created_at')
    readonly_fields = ('event_type', 'metadata', 'created_at')
    can_delete = False


@admin.register(ExamSessions)
class ExamSessionsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'assignment', 'student', 'status', 'started_at',
        'ends_at', 'submitted_at', 'violation_count', 'run_count',
    )
    list_filter = ('status', 'started_at', 'submitted_at')
    search_fields = ('assignment__title', 'student__username', 'student__email')
    raw_id_fields = ('assignment', 'student', 'final_submission')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ExamEventsInline]
    list_per_page = 30


@admin.register(ExamEvents)
class ExamEventsAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'event_type', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('session__student__username', 'session__assignment__title', 'event_type')
    raw_id_fields = ('session',)
    readonly_fields = ('created_at',)
    list_per_page = 50


class QuizAnswersInline(admin.TabularInline):
    model = QuizAnswers
    extra = 0
    fields = (
        'question', 'selected_choice_ids', 'text_answer',
        'is_correct', 'score_awarded', 'ai_suggested_score',
        'ai_suggestion_status', 'answered_at',
    )
    readonly_fields = ('answered_at', 'created_at', 'updated_at')
    raw_id_fields = ('question',)


@admin.register(QuizAttempts)
class QuizAttemptsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'assignment', 'student', 'attempt_no', 'status',
        'score', 'max_score', 'started_at', 'submitted_at',
    )
    list_filter = ('status', 'started_at', 'submitted_at')
    search_fields = ('assignment__title', 'student__username', 'student__email')
    raw_id_fields = ('assignment', 'student', 'submission', 'exam_session')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [QuizAnswersInline]
    list_per_page = 50


@admin.register(QuizAnswers)
class QuizAnswersAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'attempt', 'question', 'is_correct', 'score_awarded',
        'ai_suggested_score', 'ai_suggestion_status', 'answered_at',
    )
    list_filter = ('is_correct', 'ai_suggestion_status', 'answered_at')
    search_fields = (
        'attempt__student__username', 'attempt__assignment__title',
        'question__question_text', 'text_answer',
    )
    raw_id_fields = ('attempt', 'question', 'selected_choices')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 80


@admin.register(AIScoringSuggestions)
class AIScoringSuggestionsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'submission', 'target_type', 'status', 'suggested_score',
        'max_score', 'confidence', 'prompt_version', 'accepted_by_teacher', 'created_at',
    )
    list_filter = ('target_type', 'status', 'prompt_version', 'created_at', 'accepted_at')
    search_fields = (
        'submission__student__username', 'submission__assignment__title',
        'suggestion', 'prompt_version', 'model_name',
    )
    raw_id_fields = ('submission', 'quiz_answer', 'accepted_by_teacher')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
