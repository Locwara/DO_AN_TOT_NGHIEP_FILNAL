from datetime import datetime

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def datetime_local(value):
    if not value:
        return ''
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%Y-%m-%dT%H:%M')
    return value


@register.filter
def dict_get(value, key):
    if not isinstance(value, dict):
        return None
    return value.get(key)
