from django.contrib import admin
from django.db.models import Count
from .models import (
    Assignments, Testcases, AssignmentFiles, AssignmentFileRequirements,
    QuizSettings, QuizQuestions, QuizChoices, QuizQuestionImports, AssignmentStatistics,
    Rubrics, PlagiarismReports,
)


class TestcasesInline(admin.TabularInline):
    model = Testcases
    extra = 0
    fields = ('name', 'is_sample', 'is_hidden', 'weight', 'order_index', 'timeout_override')
    ordering = ('order_index',)


class AssignmentFilesInline(admin.TabularInline):
    model = AssignmentFiles
    extra = 0
    fields = ('file_name', 'file_url', 'file_size', 'mime_type')
    readonly_fields = ('uploaded_at',)


class AssignmentFileRequirementsInline(admin.StackedInline):
    model = AssignmentFileRequirements
    extra = 0
    max_num = 1
    fields = (
        'allowed_extensions', 'allowed_mime_types', 'max_file_size_mb', 'max_files',
        'require_comment', 'allow_resubmit', 'require_all_files_before_submit',
        'scan_required',
    )


class QuizSettingsInline(admin.StackedInline):
    model = QuizSettings
    extra = 0
    max_num = 1
    fields = (
        'question_order_mode', 'choice_order_mode', 'show_score_after_submit',
        'show_correct_answers', 'show_explanation', 'time_limit_minutes',
        'passing_score', 'allow_review',
    )


class QuizQuestionsInline(admin.TabularInline):
    model = QuizQuestions
    extra = 0
    fields = ('question_text', 'question_type', 'points', 'order_index', 'difficulty', 'is_active')
    ordering = ('order_index', 'id')


class AssignmentStatisticsInline(admin.StackedInline):
    model = AssignmentStatistics
    can_delete = False
    readonly_fields = (
        'total_submissions', 'unique_students', 'avg_score',
        'max_score', 'min_score', 'pass_rate', 'avg_attempts', 'updated_at',
    )


class RubricsInline(admin.TabularInline):
    model = Rubrics
    extra = 0
    fields = ('name', 'max_points', 'order_index', 'is_active')
    ordering = ('order_index', 'id')


@admin.register(Assignments)
class AssignmentsAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'classroom', 'classroom_subject', 'submission_mode', 'grading_mode',
        'type', 'difficulty', 'is_published', 'max_score', 'due_date',
        'get_submission_count', 'created_at',
    )
    list_filter = (
        'submission_mode', 'grading_mode', 'type', 'difficulty', 'is_published',
        'is_exam', 'late_submission_allowed', 'enable_leaderboard',
        'classroom_subject__subject',
    )
    search_fields = ('title', 'description', 'classroom__name', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('classroom', 'classroom_subject', 'created_by')
    list_per_page = 25
    date_hierarchy = 'created_at'
    list_editable = ('is_published',)
    inlines = [
        TestcasesInline, RubricsInline, AssignmentFilesInline,
        AssignmentFileRequirementsInline, QuizSettingsInline, QuizQuestionsInline,
        AssignmentStatisticsInline,
    ]
    fieldsets = (
        ('Thông tin bài tập', {
            'fields': (
                'title', 'classroom', 'classroom_subject', 'created_by',
                'description', 'instructions',
            ),
        }),
        ('Cấu hình', {
            'fields': (
                'submission_mode', 'grading_mode', 'type', 'difficulty', 'allowed_languages',
                'max_score', 'max_attempts',
            ),
        }),
        ('Thời hạn', {
            'fields': ('start_date', 'due_date', 'late_submission_allowed', 'late_penalty_percent'),
        }),
        ('Cấu hình thi', {
            'fields': (
                'is_exam', 'exam_duration_minutes', 'exam_start_time', 'exam_end_time',
                'exam_require_fullscreen', 'exam_allow_custom_input',
                'exam_allow_sample_run', 'exam_max_run_count', 'exam_grace_seconds',
            ),
            'classes': ('collapse',),
        }),
        ('Tùy chọn hiển thị', {
            'fields': (
                'is_published', 'show_testcase_result', 'enable_leaderboard',
                'grades_released_at', 'show_feedback_after_release',
            ),
            'classes': ('collapse',),
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['publish_assignments', 'unpublish_assignments', 'duplicate_assignments']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_submission_count=Count('submissions'))

    @admin.display(description='Bài nộp', ordering='_submission_count')
    def get_submission_count(self, obj):
        return obj._submission_count

    @admin.action(description='Xuất bản bài tập')
    def publish_assignments(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'Đã xuất bản {updated} bài tập.')

    @admin.action(description='Ẩn bài tập')
    def unpublish_assignments(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'Đã ẩn {updated} bài tập.')

    @admin.action(description='Nhân đôi bài tập')
    def duplicate_assignments(self, request, queryset):
        count = 0
        for assignment in queryset:
            testcases = list(Testcases.objects.filter(assignment=assignment))
            assignment.pk = None
            assignment.title = f'{assignment.title} (Bản sao)'
            assignment.is_published = False
            assignment.grades_released_at = None
            assignment.show_feedback_after_release = True
            assignment.save()
            for tc in testcases:
                tc.pk = None
                tc.assignment = assignment
                tc.save()
            count += 1
        self.message_user(request, f'Đã nhân đôi {count} bài tập (kèm testcases).')


@admin.register(Testcases)
class TestcasesAdmin(admin.ModelAdmin):
    list_display = ('name', 'assignment', 'is_sample', 'is_hidden', 'weight', 'order_index', 'timeout_override')
    list_filter = ('is_sample', 'is_hidden')
    search_fields = ('name', 'assignment__title')
    raw_id_fields = ('assignment',)
    list_per_page = 50
    ordering = ('assignment', 'order_index')
    fieldsets = (
        ('Thông tin', {
            'fields': ('assignment', 'name', 'order_index'),
        }),
        ('Dữ liệu', {
            'fields': ('input_data', 'expected_output'),
        }),
        ('Cấu hình', {
            'fields': ('is_sample', 'is_hidden', 'weight', 'timeout_override', 'memory_override'),
        }),
    )


@admin.register(AssignmentFiles)
class AssignmentFilesAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'assignment', 'file_size', 'mime_type', 'uploaded_at')
    search_fields = ('file_name', 'assignment__title')
    raw_id_fields = ('assignment',)
    list_per_page = 50
    readonly_fields = ('uploaded_at',)


@admin.register(AssignmentFileRequirements)
class AssignmentFileRequirementsAdmin(admin.ModelAdmin):
    list_display = (
        'assignment', 'max_files', 'max_file_size_mb',
        'require_comment', 'allow_resubmit', 'scan_required',
    )
    list_filter = ('require_comment', 'allow_resubmit', 'scan_required')
    search_fields = ('assignment__title',)
    raw_id_fields = ('assignment',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(QuizSettings)
class QuizSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'assignment', 'question_order_mode', 'choice_order_mode',
        'show_score_after_submit', 'show_correct_answers', 'allow_review',
        'time_limit_minutes', 'passing_score',
    )
    list_filter = (
        'question_order_mode', 'choice_order_mode',
        'show_score_after_submit', 'show_correct_answers',
        'show_explanation', 'allow_review',
    )
    search_fields = ('assignment__title',)
    raw_id_fields = ('assignment',)
    readonly_fields = ('created_at', 'updated_at')


class QuizChoicesInline(admin.TabularInline):
    model = QuizChoices
    extra = 0
    fields = ('choice_text', 'is_correct', 'order_index', 'explanation')
    ordering = ('order_index', 'id')


@admin.register(QuizQuestions)
class QuizQuestionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'question_type', 'points', 'order_index', 'difficulty', 'is_active')
    list_filter = ('question_type', 'difficulty', 'is_active')
    search_fields = ('question_text', 'assignment__title', 'tags')
    raw_id_fields = ('assignment',)
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('order_index', 'is_active')
    inlines = [QuizChoicesInline]
    list_per_page = 50


@admin.register(QuizChoices)
class QuizChoicesAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'choice_text', 'is_correct', 'order_index')
    list_filter = ('is_correct',)
    search_fields = ('choice_text', 'question__question_text', 'question__assignment__title')
    raw_id_fields = ('question',)
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_correct', 'order_index')
    list_per_page = 80


@admin.register(QuizQuestionImports)
class QuizQuestionImportsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'assignment', 'file_name', 'imported_by',
        'total_rows', 'success_rows', 'error_rows', 'clear_existing', 'created_at',
    )
    list_filter = ('clear_existing', 'created_at')
    search_fields = ('assignment__title', 'file_name', 'imported_by__username')
    raw_id_fields = ('assignment', 'imported_by')
    readonly_fields = (
        'assignment', 'file_name', 'imported_by', 'total_rows',
        'success_rows', 'error_rows', 'clear_existing', 'metadata', 'created_at',
    )
    list_per_page = 50


@admin.register(AssignmentStatistics)
class AssignmentStatisticsAdmin(admin.ModelAdmin):
    list_display = (
        'assignment', 'total_submissions', 'unique_students',
        'avg_score', 'max_score', 'min_score', 'pass_rate', 'avg_attempts',
    )
    search_fields = ('assignment__title',)
    readonly_fields = (
        'total_submissions', 'unique_students', 'avg_score',
        'max_score', 'min_score', 'pass_rate', 'avg_attempts', 'updated_at',
    )
    list_per_page = 25


@admin.register(Rubrics)
class RubricsAdmin(admin.ModelAdmin):
    list_display = ('name', 'assignment', 'max_points', 'order_index', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description', 'assignment__title')
    raw_id_fields = ('assignment',)
    list_editable = ('order_index', 'is_active')


@admin.register(PlagiarismReports)
class PlagiarismReportsAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'status', 'threshold', 'submissions_count', 'pairs_count', 'suspicious_count', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('assignment__title', 'created_by__username')
    raw_id_fields = ('assignment', 'created_by')
    readonly_fields = ('created_at', 'finished_at')
