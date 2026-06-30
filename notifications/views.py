from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Notification

@login_required
def get_notifications(request):
    notifications_qs = Notification.objects.targeted_to(request.user).exclude(link__startswith='/svago/')
    notifications_qs = notifications_qs.order_by('-is_pinned', '-created_at')

    notifications_data = []
    unread_count = 0

    for notification in notifications_qs:
        if not notification.matches_user(request.user):
            continue

        if not notification.is_read:
            unread_count += 1

        if len(notifications_data) >= 5:
            continue

        notifications_data.append({
            'id': notification.id,
            'message': notification.message,
            'title': notification.display_title,
            'link': notification.link,
            'created_at': notification.created_at.strftime('%d/%m/%Y %H:%M'),
            'icon': notification.icon or 'fa-bell',
            'category': notification.category,
        })

    return JsonResponse({
        'unread_count': unread_count,
        'notifications': notifications_data,
    })

@login_required
def mark_notification_as_read(request, notification_id):
    notification = Notification.objects.filter(id=notification_id).first()
    if not notification or not notification.matches_user(request.user):
        return JsonResponse({'status': 'not_found'}, status=404)

    notification.mark_as_read(save=True)
    return JsonResponse({'status': 'ok'})
