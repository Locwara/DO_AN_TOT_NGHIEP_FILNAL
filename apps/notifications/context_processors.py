def notifications_summary(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    try:
        qs = request.user.notifications.all()
        return {
            'unread_notifications_count': qs.filter(is_read=False).count(),
            'recent_notifications': qs[:5],
        }
    except Exception:
        return {
            'unread_notifications_count': 0,
            'recent_notifications': [],
        }
