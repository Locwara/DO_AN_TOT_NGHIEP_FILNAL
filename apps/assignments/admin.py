from django.contrib import admin
from django.db.models import Count
from .models import Assignments, Testcases, AssignmentFiles, AssignmentStatistics, Rubrics, PlagiarismReports


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
        'title', 'classroom', 'type', 'difficulty', 'is_published',
        'max_score', 'due_date', 'get_submission_count', 'created_at',
    )
    list_filter = ('type', 'difficulty', 'is_published', 'is_exam', 'late_submission_allowed', 'enable_leaderboard')
    search_fields = ('title', 'description', 'classroom__name', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('classroom', 'created_by')
    list_per_page = 25
    date_hierarchy = 'created_at'
    list_editable = ('is_published',)
    inlines = [TestcasesInline, RubricsInline, AssignmentFilesInline, AssignmentStatisticsInline]
    fieldsets = (
        ('Thông tin bài tập', {
            'fields': ('title', 'classroom', 'created_by', 'description', 'instructions'),
        }),
        ('Cấu hình', {
            'fields': (
                'type', 'difficulty', 'allowed_languages',
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
            'fields': ('is_published', 'show_testcase_result', 'enable_leaderboard'),
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
