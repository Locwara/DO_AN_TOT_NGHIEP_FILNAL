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
