import hashlib

from django.core.cache import cache
from django.http import HttpResponseForbidden


def build_ip_hash(ip_address):
    if not ip_address:
        return ""
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()


def check_rate_limit(request, bucket, limit=30, window_seconds=60):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    key = f"profile_cards:ratelimit:{bucket}:{ip}"
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, timeout=window_seconds)
    return True


def security_response():
    response = HttpResponseForbidden("Too many requests")
    response["Retry-After"] = "60"
    return response
