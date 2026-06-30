from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('get/', views.get_notifications, name='get_notifications'),
    path('mark-as-read/<int:notification_id>/', views.mark_notification_as_read, name='mark_as_read'),
]
