from django.contrib import admin
from .models import Discussions, DiscussionVotes


@admin.register(Discussions)
class DiscussionsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'get_content_preview', 'assignment', 'user',
        'get_parent_id', 'is_pinned', 'is_answer', 'upvotes', 'created_at',
    )
    list_filter = ('is_pinned', 'is_answer', 'created_at')
    search_fields = ('content', 'user__username', 'assignment__title')
    raw_id_fields = ('assignment', 'user', 'parent')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    fieldsets = (
        ('Thảo luận', {
            'fields': ('assignment', 'user', 'parent', 'content'),
        }),
        ('Trạng thái', {
            'fields': ('is_pinned', 'is_answer', 'upvotes'),
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['pin_discussions', 'unpin_discussions', 'mark_as_answer', 'unmark_as_answer']

    @admin.display(description='Nội dung')
    def get_content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content

    @admin.display(description='Parent')
    def get_parent_id(self, obj):
        return obj.parent_id or '—'

    @admin.action(description='Ghim thảo luận')
    def pin_discussions(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'Đã ghim {updated} thảo luận.')

    @admin.action(description='Bỏ ghim thảo luận')
    def unpin_discussions(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'Đã bỏ ghim {updated} thảo luận.')

    @admin.action(description='Đánh dấu là đáp án')
    def mark_as_answer(self, request, queryset):
        updated = queryset.update(is_answer=True)
        self.message_user(request, f'Đã đánh dấu {updated} thảo luận là đáp án.')

    @admin.action(description='Bỏ đánh dấu đáp án')
    def unmark_as_answer(self, request, queryset):
        updated = queryset.update(is_answer=False)
        self.message_user(request, f'Đã bỏ đánh dấu {updated} thảo luận.')


@admin.register(DiscussionVotes)
class DiscussionVotesAdmin(admin.ModelAdmin):
    list_display = ('id', 'discussion', 'user', 'vote_type', 'get_vote_label', 'created_at')
    list_filter = ('vote_type', 'created_at')
    search_fields = ('user__username', 'discussion__content')
    raw_id_fields = ('discussion', 'user')
    list_per_page = 50
    date_hierarchy = 'created_at'

    @admin.display(description='Loại')
    def get_vote_label(self, obj):
        return '👍 Upvote' if obj.vote_type == 1 else '👎 Downvote'
