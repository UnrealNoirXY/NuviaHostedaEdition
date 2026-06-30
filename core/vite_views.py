"""Runtime helpers for serving Vite-built assets when nginx is unavailable."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils.http import http_date
from django.views.decorators.http import require_GET


_DIST_ROOT = (Path(settings.BASE_DIR) / "frontend" / "dist").resolve()


@require_GET
def serve_vite_asset(request, asset_path: str):
    """Serve built Vite assets directly from disk as a production fallback."""
    normalized_path = (_DIST_ROOT / Path(asset_path.lstrip("/"))).resolve()

    if not normalized_path.is_file() or _DIST_ROOT not in normalized_path.parents:
        raise Http404("Asset not found")

    content_type, encoding = mimetypes.guess_type(str(normalized_path))
    response = FileResponse(normalized_path.open("rb"), content_type=content_type or "application/octet-stream")

    if encoding:
        response["Content-Encoding"] = encoding

    stat = normalized_path.stat()
    response["Last-Modified"] = http_date(stat.st_mtime)
    response["Cache-Control"] = "public, max-age=31536000, immutable"

    return response
