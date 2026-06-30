from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Controlli di hardening baseline per profile cards"

    def handle(self, *args, **options):
        checks = {
            "SECURE_CONTENT_TYPE_NOSNIFF": getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False),
            "SESSION_COOKIE_SECURE": getattr(settings, "SESSION_COOKIE_SECURE", False),
            "CSRF_COOKIE_SECURE": getattr(settings, "CSRF_COOKIE_SECURE", False),
        }

        self.stdout.write("Profile Cards Security Audit")
        for name, value in checks.items():
            status = "OK" if value else "WARN"
            self.stdout.write(f"[{status}] {name}={value}")

        self.stdout.write("Suggerimento: monitorare rate-limit e rotazione token pubblici.")
