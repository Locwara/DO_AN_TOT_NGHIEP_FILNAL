from datetime import date

from django.urls import reverse


def get_system_setting(key, default=None):
    """Read a SystemSettings value with a safe fallback."""
    from .models import SystemSettings

    setting = SystemSettings.objects.filter(setting_key=key).first()
    if not setting:
        return default
    return setting.setting_value


def get_int_setting(key, default=0, minimum=None, maximum=None):
    value = get_system_setting(key, default)
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def get_bool_setting(key, default=False):
    value = get_system_setting(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return bool(value)


def get_int_param(params, name, default=None, minimum=None, maximum=None):
    value = params.get(name)
    if value in (None, ''):
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def get_bool_param(params, name, default=None):
    value = params.get(name)
    if value in (None, ''):
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in ('1', 'true', 'yes', 'on', 'active'):
        return True
    if normalized in ('0', 'false', 'no', 'off', 'inactive'):
        return False
    return default


def get_date_param(params, name, default=None):
    value = params.get(name)
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def get_choice_param(params, name, choices, default=None):
    value = params.get(name)
    if value in (None, ''):
        return default
    return value if value in set(choices) else default


def build_query_string(source, remove=('page',), **overrides):
    params = getattr(source, 'GET', source).copy()
    for key in remove:
        params.pop(key, None)
    for key, value in overrides.items():
        params.pop(key, None)
        if value not in (None, ''):
            params[key] = value
    for key in list(params.keys()):
        values = [value for value in params.getlist(key) if value not in (None, '')]
        if values:
            params.setlist(key, values)
        else:
            params.pop(key, None)
    return params.urlencode()


def csv_query_context(source, remove=('page', 'type')):
    csv_query_string = build_query_string(source, remove=remove)
    return {
        'csv_query_string': csv_query_string,
        'has_active_filters': bool(csv_query_string),
    }


def csv_filename(base, export_type='', filtered=False, timestamp='', extension='csv'):
    parts = [str(base).strip('_-')]
    if export_type:
        parts.append(str(export_type).strip('_-'))
    if filtered:
        parts.append('filtered')
    if timestamp:
        parts.append(str(timestamp).strip('_-'))
    return '_'.join(part for part in parts if part) + f'.{extension}'


def active_filter_badges(source, labels=None, value_labels=None, defaults=None, ignore=None):
    params = getattr(source, 'GET', source)
    labels = labels or {}
    value_labels = value_labels or {}
    defaults = defaults or {}
    ignore = set(ignore or ('page', 'approval_page', 'type'))
    badges = []
    for key in params.keys():
        if key in ignore:
            continue
        values = [value for value in params.getlist(key) if value not in (None, '')]
        if not values:
            continue
        if key in defaults and len(values) == 1 and str(defaults[key]) == str(values[0]):
            continue
        display_values = []
        for value in values:
            display_values.append(value_labels.get(key, {}).get(value, value))
        badges.append({
            'key': key,
            'label': labels.get(key, key.replace('_', ' ').title()),
            'value': ', '.join(display_values),
        })
    return badges


def admin_filter_context(source, clear_url_name, labels=None, value_labels=None, defaults=None, ignore=None):
    active_filters = active_filter_badges(
        source,
        labels=labels,
        value_labels=value_labels,
        defaults=defaults,
        ignore=ignore,
    )
    return {
        'active_filters': active_filters,
        'has_active_filters': bool(active_filters),
        'page_query_string': build_query_string(source, remove=('page',)),
        'approval_page_query_string': build_query_string(source, remove=('approval_page',)),
        'csv_query_string': build_query_string(source, remove=('page', 'type')),
        'clear_filter_url': reverse(clear_url_name),
    }


def admin_filter_options():
    from django.contrib.auth.models import User
    from apps.administation.models import ProgrammingLanguages
    from apps.classrooms.models import Classrooms, Semesters, Subjects
    from apps.submissions.models import Submissions

    user_option_fields = ('id', 'first_name', 'last_name', 'username')
    teachers = User.objects.filter(
        profiles__role='teacher',
    ).only(*user_option_fields).order_by('first_name', 'username')[:200]
    students = User.objects.filter(
        profiles__role='student',
    ).only(*user_option_fields).order_by('first_name', 'username')[:200]
    admins = User.objects.filter(
        profiles__role='admin',
    ).only(*user_option_fields).order_by('first_name', 'username')[:100]
    teacher_registration_reviewers = User.objects.filter(
        reviewed_registrations__isnull=False
    ).only(*user_option_fields).distinct().order_by('first_name', 'username')[:100]
    return {
        'filter_options': {
            'teachers': teachers,
            'students': students,
            'admins': admins,
            'teacher_registration_reviewers': teacher_registration_reviewers,
            'classrooms': Classrooms.objects.only('id', 'name').order_by('name')[:300],
            'subjects': Subjects.objects.only('id', 'code', 'name').order_by('code', 'name')[:300],
            'semesters': Semesters.objects.only('id', 'name', 'start_date', 'is_current').order_by('-is_current', '-start_date', 'name')[:100],
            'languages': ProgrammingLanguages.objects.only('id', 'name', 'display_name').order_by('display_name', 'name')[:100],
            'profile_statuses': ['approved', 'pending', 'rejected', 'inactive'],
            'roles': (
                ('all', 'Tất cả'),
                ('student', 'Học sinh'),
                ('teacher', 'Giáo viên'),
                ('admin', 'Admin'),
                ('staff', 'Staff'),
                ('superuser', 'Superuser'),
            ),
            'submission_statuses': Submissions.objects.values_list('status', flat=True).distinct().order_by('status')[:50],
        }
    }
