import statistics
import time

from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse

from profile_cards.models import ProfileCardPublicToken


class Command(BaseCommand):
    help = "Benchmark rapido per endpoint pubblico profile cards"

    def add_arguments(self, parser):
        parser.add_argument("--token", dest="token", help="Token pubblico esistente")
        parser.add_argument("--requests", dest="requests", type=int, default=50)

    def handle(self, *args, **options):
        token_value = options.get("token")
        request_count = options["requests"]
        if request_count <= 0:
            raise CommandError("--requests deve essere > 0")

        if token_value:
            try:
                token = ProfileCardPublicToken.objects.get(token=token_value)
            except ProfileCardPublicToken.DoesNotExist as exc:
                raise CommandError("Token non trovato") from exc
        else:
            token = ProfileCardPublicToken.objects.order_by("-id").first()
            if not token:
                raise CommandError("Nessun token disponibile per benchmark")

        url = reverse("profile_cards:public_profile", kwargs={"token": token.token})
        client = Client()
        timings = []
        for _ in range(request_count):
            start = time.perf_counter()
            response = client.get(url)
            elapsed_ms = (time.perf_counter() - start) * 1000
            if response.status_code not in (200, 403):
                raise CommandError(f"Status inatteso durante benchmark: {response.status_code}")
            timings.append(elapsed_ms)

        self.stdout.write(self.style.SUCCESS(f"Benchmark completato su {request_count} richieste"))
        self.stdout.write(f"avg_ms={statistics.mean(timings):.2f}")
        self.stdout.write(f"p95_ms={statistics.quantiles(timings, n=20)[18]:.2f}")
        self.stdout.write(f"max_ms={max(timings):.2f}")
