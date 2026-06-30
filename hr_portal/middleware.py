import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

from .observability import emit_structured_log, metrics


class StructuredLogMiddleware:
    """Logs basic request metadata with duration for observability."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000

        user = getattr(request, "user", None)
        emit_structured_log(
            "http_request",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            user_id=getattr(user, "id", None) if getattr(user, "is_authenticated", False) else None,
            company_id=getattr(user, "company_id", None) if getattr(user, "is_authenticated", False) else None,
            resort_id=getattr(user, "resort_id", None) if getattr(user, "is_authenticated", False) else None,
        )
        metrics.observe(
            "http_request_duration_ms",
            duration_ms,
            method=request.method,
            path=request.path,
            status=str(response.status_code),
        )
        return response
