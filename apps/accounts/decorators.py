from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                profile = request.user.profiles
                if profile.role in allowed_roles:
                    return view_func(request, *args, **kwargs)
            except Exception:
                pass

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            messages.error(request, 'Bạn không có quyền truy cập trang này.')
            return redirect('home')
        return wrapper
    return decorator


def student_required(view_func):
    return role_required(['student'])(view_func)


def teacher_required(view_func):
    return role_required(['teacher'])(view_func)


def admin_required(view_func):
    return role_required(['admin'])(view_func)


def teacher_or_admin_required(view_func):
    return role_required(['teacher', 'admin'])(view_func)
