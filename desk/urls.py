from django.urls import path, include
from . import views

app_name = 'desk'

urlpatterns = [
    path('', views.HomeDeskView.as_view(), name='home'),
    path('save-layout/', views.save_layout, name='save_layout'),
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    # Include the new API urls under the /api/ path
    path('api/', include('desk.api_urls', namespace='api')),
]
