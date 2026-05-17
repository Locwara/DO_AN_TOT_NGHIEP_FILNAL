from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import logging


logger = logging.getLogger(__name__)


def _wants_json(request):
    accept = request.META.get('HTTP_ACCEPT', '')
    content_type = request.META.get('CONTENT_TYPE', '')
    requested_with = request.META.get('HTTP_X_REQUESTED_WITH', '')
    return (
        'application/json' in accept
        or content_type.startswith('application/json')
        or requested_with == 'XMLHttpRequest'
    )


class JsonExceptionMiddleware(MiddlewareMixin):
    """Return compact JSON errors for API-style requests."""

    GENERIC_MESSAGES = {
        403: 'Bạn không có quyền thực hiện thao tác này.',
        404: 'Không tìm thấy dữ liệu yêu cầu.',
        405: 'Phương thức yêu cầu không được hỗ trợ.',
    }

    def process_exception(self, request, exception):
        if not _wants_json(request):
            return None
        logger.exception('Unhandled JSON request error for %s %s', request.method, request.path)
        return JsonResponse({
            'status': 'error',
            'message': 'Có lỗi hệ thống. Vui lòng thử lại sau.',
        }, status=500)

    def process_response(self, request, response):
        if not _wants_json(request):
            return response
        if response.status_code not in self.GENERIC_MESSAGES:
            return response
        content_type = response.headers.get('Content-Type', '')
        if content_type.startswith('application/json'):
            return response
        return JsonResponse({
            'status': 'error',
            'message': self.GENERIC_MESSAGES[response.status_code],
        }, status=response.status_code)


class ActivityLogMiddleware(MiddlewareMixin):
    """Middleware to log user activity for important actions."""

    LOGGED_METHODS = ('POST', 'PUT', 'PATCH', 'DELETE')

    def process_response(self, request, response):
        if request.method not in self.LOGGED_METHODS:
            return response
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response

        try:
            from apps.administation.models import ActivityLogs
            ActivityLogs.objects.create(
                user=request.user,
                action=f"{request.method} {request.path}",
                resource_type=request.resolver_match.app_name if request.resolver_match else None,
                resource_id=self._get_resource_id(request),
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                metadata={
                    'status_code': response.status_code,
                    'url_name': request.resolver_match.url_name if request.resolver_match else None,
                    'view_name': request.resolver_match.view_name if request.resolver_match else None,
                },
            )
        except Exception:
            logger.exception('Failed to write activity log for %s %s', request.method, request.path)

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _get_resource_id(self, request):
        if not request.resolver_match:
            return None
        for key in ('pk', 'id', 'assignment_pk', 'classroom_pk', 'submission_pk'):
            value = request.resolver_match.kwargs.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None
