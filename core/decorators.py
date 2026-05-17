import logging
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required as django_login_required
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


def role_required(*roles):
    """Decorator that checks if the user has one of the specified roles.
    Roles: 'student', 'teacher', 'admin'
    """
    def decorator(view_func):
        @wraps(view_func)
        @django_login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            has_access = False
            try:
                profile = request.user.profiles
                has_access = profile.role in roles
                if not has_access:
                    logger.warning('role_required DENIED: user=%s, role=%s, required=%s, view=%s, path=%s',
                                   request.user.username, profile.role, roles, view_func.__name__, request.path)
            except (ObjectDoesNotExist, AttributeError):
                logger.warning('role_required NO PROFILE: user=%s, required=%s, view=%s, path=%s',
                               request.user.username, roles, view_func.__name__, request.path)
            if has_access:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Bạn không có quyền truy cập trang này.')
            return redirect('home')
        return wrapper
    return decorator


def teacher_required(view_func):
    """Shortcut decorator for teacher-only views."""
    return role_required('teacher', 'admin')(view_func)


def admin_required(view_func):
    """Shortcut decorator for admin-only views."""
    return role_required('admin')(view_func)


def student_required(view_func):
    """Shortcut decorator for student-only views."""
    return role_required('student')(view_func)
