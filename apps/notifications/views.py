from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notifications


@login_required
def notification_list_view(request):
    status_filter = request.GET.get('status', 'all')
    notifications = Notifications.objects.filter(recipient=request.user)
    if status_filter == 'unread':
        notifications = notifications.filter(is_read=False)

    return render(request, 'notifications/list.html', {
        'notifications': notifications[:100],
        'status_filter': status_filter,
    })


@login_required
def notification_redirect_view(request, pk):
    notification = get_object_or_404(Notifications, pk=pk, recipient=request.user)
    if notification.link:
        return redirect(notification.link)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_read_view(request, pk):
    notification = get_object_or_404(Notifications, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
    return redirect(request.POST.get('next') or 'notifications:list')


@login_required
@require_POST
def mark_all_read_view(request):
    Notifications.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True, read_at=timezone.now())
    return redirect(request.POST.get('next') or 'notifications:list')
