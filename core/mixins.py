from django.contrib.auth.mixins import UserPassesTestMixin
from accounts.models import User

class StaffRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user is a superuser or IT Technician.
    Denies permission rather than redirecting to login.
    """
    def test_func(self):
        return self.request.user.is_authenticated and \
               (self.request.user.is_superuser or \
               (hasattr(self.request.user, 'role') and self.request.user.role == User.IT_TECHNICIAN))
