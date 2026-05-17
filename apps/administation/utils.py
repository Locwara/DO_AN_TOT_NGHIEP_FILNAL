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
