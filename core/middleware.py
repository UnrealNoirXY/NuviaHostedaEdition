from django.utils import timezone

from django.urls import reverse
from django.shortcuts import redirect
from .models import PlatformSettings
from accounts.models import User

class UpdateLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # We update the last_seen field if it's been more than 60 seconds
            # since the last time we did. This is to avoid too many DB writes.
            sixty_seconds_ago = timezone.now() - timezone.timedelta(seconds=60)
            if request.user.last_seen < sixty_seconds_ago:
                request.user.last_seen = timezone.now()
                request.user.save(update_fields=['last_seen'])

        response = self.get_response(request)
        return response

class GamerTagRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the user is accessing the svago area
        if request.path.startswith('/svago/'):
            # Allow access to the setup page itself
            if request.path == reverse('svago:setup_gamertag'):
                return self.get_response(request)

            if request.user.is_authenticated and not request.user.gamertag:
                return redirect('svago:setup_gamertag')

        return self.get_response(request)

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Attempt to load settings, but fail gracefully if DB is not ready
        try:
            settings = PlatformSettings.load()
        except Exception:
            return self.get_response(request)

        # If mode is off, or user is superadmin, do nothing.
        if not settings.maintenance_mode or \
           (request.user.is_authenticated and request.user.role == User.SUPERADMIN):
            return self.get_response(request)

        # Define paths that should always be accessible
        allowed_url_names = ['login', 'logout', 'maintenance_page']
        allowed_paths = [reverse(name) for name in allowed_url_names]

        # Allow access to the maintenance page, login/logout, and the admin panel
        if request.path in allowed_paths or request.path.startswith('/admin/'):
            return self.get_response(request)

        # For all other requests, redirect to the maintenance page
        return redirect(reverse('maintenance_page'))
