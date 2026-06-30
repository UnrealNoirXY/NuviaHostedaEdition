from django.urls import path

from . import api

app_name = 'notifications_api'


urlpatterns = [
    path('feed/', api.NotificationFeedView.as_view(), name='feed'),
    path('summary/', api.NotificationSummaryView.as_view(), name='summary'),
    path('mark-read/<int:notification_id>/', api.MarkNotificationReadView.as_view(), name='mark_read'),
    path('mark-all-read/', api.MarkAllNotificationsReadView.as_view(), name='mark_all'),
    path('subscriptions/', api.PushSubscriptionView.as_view(), name='subscriptions'),
    path('push-test/', api.SendTestPushView.as_view(), name='push_test'),
]

