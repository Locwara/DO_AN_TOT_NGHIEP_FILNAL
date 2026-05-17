from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Profiles, TeacherRegistrations


class ProfilesInline(admin.StackedInline):
    model = Profiles
    can_delete = False
    verbose_name = 'Hồ sơ'
    verbose_name_plural = 'Hồ sơ'
    fields = ('role', 'avatar_url', 'bio', 'phone', 'status')


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfilesInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    date_hierarchy = 'date_joined'
    list_per_page = 30

    @admin.display(description='Vai trò', ordering='profiles__role')
    def get_role(self, obj):
        try:
            return obj.profiles.role or 'student'
        except Profiles.DoesNotExist:
            return '—'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Profiles)
class ProfilesAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'get_email', 'role', 'phone', 'status', 'created_at')
    list_filter = ('role', 'status')
    search_fields = ('id__username', 'id__email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30
    list_editable = ('role', 'status')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Thông tin người dùng', {
            'fields': ('id', 'role', 'status'),
        }),
        ('Chi tiết hồ sơ', {
            'fields': ('avatar_url', 'bio', 'phone'),
        }),
        ('Thời gian', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['make_teacher', 'make_student', 'approve_profiles', 'suspend_profiles']

    @admin.display(description='Username')
    def get_username(self, obj):
        return obj.id.username

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.id.email

    @admin.action(description='Chuyển thành Giáo viên')
    def make_teacher(self, request, queryset):
        updated = queryset.update(role='teacher')
        self.message_user(request, f'Đã chuyển {updated} hồ sơ thành giáo viên.')

    @admin.action(description='Chuyển thành Sinh viên')
    def make_student(self, request, queryset):
        updated = queryset.update(role='student')
        self.message_user(request, f'Đã chuyển {updated} hồ sơ thành sinh viên.')

    @admin.action(description='Phê duyệt hồ sơ')
    def approve_profiles(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'Đã phê duyệt {updated} hồ sơ.')

    @admin.action(description='Tạm khóa hồ sơ')
    def suspend_profiles(self, request, queryset):
        updated = queryset.update(status='suspended')
        self.message_user(request, f'Đã tạm khóa {updated} hồ sơ.')


@admin.register(TeacherRegistrations)
class TeacherRegistrationsAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_email', 'institution', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'institution', 'reason')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'reviewed_by')
    list_per_page = 30
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Thông tin đăng ký', {
            'fields': ('user', 'institution', 'reason', 'proof_document_url'),
        }),
        ('Xét duyệt', {
            'fields': ('status', 'reviewed_by', 'reviewed_at'),
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    actions = ['approve_registrations', 'reject_registrations']

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user.email if obj.user else '—'

    @admin.action(description='Phê duyệt đơn đăng ký')
    def approve_registrations(self, request, queryset):
        pending = queryset.filter(status='pending')
        count = 0
        for reg in pending.select_related('user'):
            reg.status = 'approved'
            reg.reviewed_by = request.user
            reg.reviewed_at = timezone.now()
            reg.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            try:
                profile = Profiles.objects.get(id=reg.user)
                profile.role = 'teacher'
                profile.save(update_fields=['role'])
            except Profiles.DoesNotExist:
                pass
            count += 1
        self.message_user(request, f'Đã phê duyệt {count} đơn đăng ký giáo viên.')

    @admin.action(description='Từ chối đơn đăng ký')
    def reject_registrations(self, request, queryset):
        count = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'Đã từ chối {count} đơn đăng ký.')
