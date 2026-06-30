from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import User

def role_required(allowed_roles=None):
    """
    Decorator to check if a user has one of the allowed roles.
    Redirects to the homepage if the user does not have permission.
    Superusers are always granted access.

    Usage:
        @role_required(allowed_roles=[User.DIRECTOR, User.OWNER])
        def my_view(request):
            ...
    """
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')  # Or your login URL

            user_role = getattr(request.user, 'role', None)

            if request.user.is_superuser or user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Non hai i permessi per accedere a questa pagina.")
                return redirect('home')  # Or your 'unauthorized' page
        return _wrapped_view
    return decorator

# Refactor the old decorator to use the new generic one.
# This maintains backward compatibility if it's used elsewhere.
it_staff_required = role_required(allowed_roles=[User.IT_TECHNICIAN])

def it_support_management_access_required(view_func):
    """
    Decorator to check if a user can manage IT support tickets.
    Access is granted if the user is a superuser, has the 'IT_TECHNICIAN' role,
    or has the 'has_it_support_management_access' flag set to True.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        can_access = (
            request.user.is_superuser or
            request.user.role == User.IT_TECHNICIAN or
            getattr(request.user, 'has_it_support_management_access', False)
        )

        if can_access:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Non hai i permessi per accedere a questa sezione.")
            return redirect('home')
    return _wrapped_view

def inventory_access_required(view_func):
    """
    Decorator to check if a user has access to the inventory.
    Access is granted if the user is a superuser or has the 'has_inventory_access' flag set to True.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        can_access = (
            request.user.is_superuser or
            getattr(request.user, 'has_inventory_access', False)
        )

        if can_access:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Non hai i permessi per accedere a questa sezione.")
            return redirect('home')
    return _wrapped_view

def purchase_order_access_required(view_func):
    """
    Decorator to check if a user can manage purchase orders.
    Access is granted if the user is a superuser, has the 'ADMINISTRATIVE' role,
    or has the 'can_manage_purchase_orders' flag set to True.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        can_access = (
            request.user.is_superuser or
            request.user.role == User.ADMINISTRATIVE or
            getattr(request.user, 'can_manage_purchase_orders', False)
        )

        if can_access:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Non hai i permessi per accedere a questa sezione.")
            return redirect('home')
    return _wrapped_view
