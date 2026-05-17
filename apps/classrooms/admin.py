from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from .models import Classrooms, ClassroomMembers, Announcements, Leaderboard, Subjects, ClassroomSubjects, Semesters


class ClassroomMembersInline(admin.TabularInline):
    model = ClassroomMembers
    extra = 0
    raw_id_fields = ('student',)
    fields = ('student', 'status', 'joined_at')
    readonly_fields = ('joined_at',)


class AnnouncementsInline(admin.StackedInline):
    model = Announcements
    extra = 0
    fields = ('title', 'content', 'teacher', 'is_pinned')
    raw_id_fields = ('teacher',)


class ClassroomSubjectsInline(admin.TabularInline):
    model = ClassroomSubjects
    extra = 0
    raw_id_fields = ('subject', 'assigned_by', 'semester')
    fields = ('subject', 'semester', 'assigned_by', 'is_active', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Classrooms)
class ClassroomsAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'invite_code', 'get_member_count', 'max_students', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'invite_code', 'teacher__username', 'description')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('teacher',)
    list_per_page = 25
    date_hierarchy = 'created_at'
    inlines = [ClassroomMembersInline, AnnouncementsInline, ClassroomSubjectsInline]
    fieldsets = (
        ('Thông tin lớp học', {
            'fields': ('name', 'description', 'teacher', 'invite_code'),
        }),
        ('Cài đặt', {
            'fields': ('max_students', 'is_active', 'settings'),
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['activate_classrooms', 'deactivate_classrooms']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _member_count=Count(
                'classroommembers',
                filter=Q(classroommembers__status='approved'),
            ),
        )

    @admin.display(description='Thành viên', ordering='_member_count')
    def get_member_count(self, obj):
        return obj._member_count

    @admin.action(description='Kích hoạt lớp học')
    def activate_classrooms(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Đã kích hoạt {updated} lớp học.')

    @admin.action(description='Tạm đóng lớp học')
    def deactivate_classrooms(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Đã tạm đóng {updated} lớp học.')


@admin.register(ClassroomMembers)
class ClassroomMembersAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'student', 'status', 'joined_at')
    list_filter = ('status', 'joined_at')
    search_fields = ('classroom__name', 'student__username', 'student__email')
    raw_id_fields = ('classroom', 'student')
    list_per_page = 50
    date_hierarchy = 'joined_at'
    actions = ['approve_members', 'remove_members']

    @admin.action(description='Phê duyệt thành viên')
    def approve_members(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f'Đã phê duyệt {updated} thành viên.')

    @admin.action(description='Xóa thành viên')
    def remove_members(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Đã xóa {count} thành viên.')


@admin.register(Announcements)
class AnnouncementsAdmin(admin.ModelAdmin):
    list_display = ('title', 'classroom', 'teacher', 'is_pinned', 'created_at')
    list_filter = ('is_pinned', 'created_at')
    search_fields = ('title', 'content', 'classroom__name', 'teacher__username')
    raw_id_fields = ('classroom', 'teacher')
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['pin_announcements', 'unpin_announcements']

    @admin.action(description='Ghim thông báo')
    def pin_announcements(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'Đã ghim {updated} thông báo.')

    @admin.action(description='Bỏ ghim thông báo')
    def unpin_announcements(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'Đã bỏ ghim {updated} thông báo.')


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'student', 'total_score', 'avg_score', 'rank', 'assignments_completed')
    list_filter = ('classroom',)
    search_fields = ('student__username', 'classroom__name')
    raw_id_fields = ('classroom', 'student')
    list_per_page = 50
    ordering = ('classroom', 'rank')


@admin.register(Subjects)
class SubjectsAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'status', 'created_by', 'approved_by', 'is_active', 'created_at', 'get_classroom_count')
    list_filter = ('status', 'is_active', 'created_at')
    search_fields = ('code', 'name', 'description', 'created_by__username')
    raw_id_fields = ('created_by', 'approved_by')
    filter_horizontal = ('languages',)
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['approve_subjects', 'reject_subjects', 'activate_subjects', 'deactivate_subjects']
    fieldsets = (
        ('Môn học', {
            'fields': ('code', 'name', 'description', 'languages'),
        }),
        ('Trạng thái', {
            'fields': ('status', 'is_active', 'created_by', 'approved_by', 'reviewed_at'),
        }),
    )

    @admin.action(description='Duyệt môn học')
    def approve_subjects(self, request, queryset):
        updated = queryset.update(
            status='approved',
            approved_by=request.user,
            reviewed_at=timezone.now(),
            is_active=True,
        )
        self.message_user(request, f'Đã duyệt {updated} môn học.')

    @admin.action(description='Từ chối môn học')
    def reject_subjects(self, request, queryset):
        updated = queryset.update(
            status='rejected',
            approved_by=request.user,
            reviewed_at=timezone.now(),
            is_active=False,
        )
        self.message_user(request, f'Đã từ chối {updated} môn học.')

    @admin.action(description='Kích hoạt môn học')
    def activate_subjects(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Đã kích hoạt {updated} môn học.')

    @admin.action(description='Vô hiệu hóa môn học')
    def deactivate_subjects(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Đã vô hiệu hóa {updated} môn học.')

    @admin.display(description='Số lớp')
    def get_classroom_count(self, obj):
        return obj.classroom_links.filter(is_active=True).count()


@admin.register(ClassroomSubjects)
class ClassroomSubjectsAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'subject', 'semester', 'assigned_by', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'semester', 'classroom')
    search_fields = ('classroom__name', 'subject__code', 'subject__name', 'assigned_by__username', 'semester__code')
    raw_id_fields = ('classroom', 'subject', 'assigned_by', 'semester')
    list_per_page = 50
    date_hierarchy = 'created_at'


@admin.register(Semesters)
class SemestersAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'start_date', 'end_date', 'is_current', 'is_active', 'get_link_count')
    list_filter = ('is_current', 'is_active')
    search_fields = ('code', 'name')
    list_per_page = 30
    list_editable = ('is_current', 'is_active')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_link_count=Count('classroom_subject_links'))

    @admin.display(description='Liên kết lớp-môn', ordering='_link_count')
    def get_link_count(self, obj):
        return obj._link_count
