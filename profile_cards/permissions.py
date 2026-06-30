
def is_superadmin_user(user):
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_superuser or getattr(user, "role", "") == "superadmin")
