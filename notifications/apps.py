from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self) -> None:  # pragma: no cover - import side effects only
        # Import signals to wire up notification delivery hooks.
        from . import signals  # noqa: F401
