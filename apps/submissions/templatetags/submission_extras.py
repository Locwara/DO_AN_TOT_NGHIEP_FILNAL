from django import template
from apps.submissions.utils import can_reveal_testcase_io

register = template.Library()

@register.simple_tag
def reveal_io(testcase, user, assignment):
    """
    Template tag to check if testcase IO can be revealed.
    Usage: {% reveal_io testcase user assignment as can_show %}
    """
    return can_reveal_testcase_io(testcase, user, assignment)


@register.filter
def percentage(value, total):
    """Calculate percentage of value out of total."""
    try:
        if not total or float(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError):
        return 0

EVENT_LABELS = {
    'tab_hidden': 'Đổi tab (Ẩn trang)',
    'tab_visible': 'Quay lại tab bài thi',
    'focus_lost': 'Chuyển sang cửa sổ khác',
    'focus_returned': 'Quay lại cửa sổ bài thi',
    'fullscreen_exit': 'Thoát toàn màn hình',
    'fullscreen_request_failed': 'Lỗi yêu cầu toàn màn hình',
    'paste': 'Dán (Paste) nội dung',
    'paste_prevented': 'Cố tình dán (Paste)',
    'copy': 'Sao chép (Copy) nội dung',
    'context_menu': 'Mở menu chuột phải',
    'run_test': 'Chạy thử code',
    'autosaved': 'Tự động lưu',
    'submitted': 'Nộp bài',
}

@register.filter
def event_label(event_type):
    return EVENT_LABELS.get(event_type, event_type)
