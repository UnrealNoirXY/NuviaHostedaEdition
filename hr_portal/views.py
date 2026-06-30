from pathlib import Path
import re

from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core import signing
from django.core.validators import validate_email
from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, viewsets, status
from rest_framework.renderers import BaseRenderer
from rest_framework.decorators import action, renderer_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from weasyprint import HTML

from core.permissions import Capability, user_can

from .models import (
    HREventLog,
    HRDocument,
    HRNotification,
    HRNotificationDelivery,
    ListeningTicket,
    ListeningTicketMessage,
    NotificationPreference,
    Payslip,
    PayslipBatch,
    PayslipBatchPreview,
    PayslipPreviewJob,
    PayslipEmailRecipient,
    PayslipUnmatched,
)
from .serializers import (
    HREventLogSerializer,
    HRDocumentSerializer,
    HRNotificationSerializer,
    HRNotificationDeliverySerializer,
    ListeningTicketMessageSerializer,
    ListeningTicketSerializer,
    NotificationPreferenceSerializer,
    PayslipBatchSerializer,
    PayslipSerializer,
    PayslipUnmatchedSerializer,
)
import io
import json
import time
import zipfile
import logging
import hashlib

from django.http import FileResponse, HttpResponse, Http404, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .services import (
    build_signed_payslip_url,
    deliver_notification,
    describe_email_error,
    send_payslip_email,
)
from accounts.models import User


class EventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if isinstance(data, (bytes, bytearray)):
            return data
        return str(data).encode(self.charset or "utf-8")


class DownloadPayslipView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        token = request.GET.get("token")
        if token:
            return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, payslip_id):
        user = request.user
        token = request.GET.get("token")

        try:
            payslip = get_object_or_404(Payslip, pk=payslip_id)
        except (ValueError, Http404):
            return HttpResponse("Busta paga non trovata.", status=404)

        token_user_id = None
        if token:
            token_user_id = self._validate_signed_token(token, payslip_id)
            if token_user_id is None:
                return HttpResponse("Link non valido o scaduto.", status=403)

        # Check permissions
        is_owner = payslip.user == user
        is_hr_or_owner = getattr(user, "role", None) in {
            getattr(user, "RISORSE_UMANE", "risorse_umane"),
            getattr(user, "OWNER", "owner"),
            getattr(user, "SUPERADMIN", "superadmin"),
        }

        if not (is_owner or is_hr_or_owner or user.is_superuser):
            if token_user_id and str(payslip.user_id) == str(token_user_id):
                pass
            else:
                return HttpResponse("Non autorizzato.", status=403)

        if not (is_owner or is_hr_or_owner or user.is_superuser or token_user_id):
            return HttpResponse("Non autorizzato.", status=403)

        # Log the download event
        if not payslip.downloaded_at:
            payslip.downloaded_at = timezone.now()
            payslip.save(update_fields=["downloaded_at"])

        HREventLog.record(
            event_type="payslip_download",
            actor=user if user.is_authenticated else None,
            target=payslip,
            metadata={
                "payslip_id": str(payslip.pk),
                "via_signed_link": bool(token_user_id),
                "ip_address": _get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            },
        )

        try:
            return FileResponse(payslip.file.open('rb'), as_attachment=True, filename=payslip.file.name)
        except FileNotFoundError:
            return HttpResponse("File non trovato.", status=404)

    def _validate_signed_token(self, token, payslip_id):
        signer = signing.TimestampSigner(salt="hr.payslip.download")
        try:
            payload = signer.unsign(
                token,
                max_age=getattr(settings, "HR_SIGNED_LINK_MAX_AGE_SECONDS", 60 * 60 * 24 * 2),
            )
        except (signing.BadSignature, signing.SignatureExpired):
            return None
        payload_parts = str(payload).split(":", 1)
        if len(payload_parts) != 2:
            return None
        token_payslip_id, token_user_id = payload_parts
        if str(token_payslip_id) != str(payslip_id):
            return None
        return token_user_id


def _compute_upload_checksum(uploaded_file):
    if not uploaded_file:
        return ""
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    return digest.hexdigest()


def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _has_hr_portal_access(user):
    """Accesso al Portale HR riservato. Fonte di verità: capability HR_PORTAL
    (superuser o ruoli HR/owner/superadmin), la stessa che guida hub e sidebar."""
    return user_can(user, Capability.HR_PORTAL)


class IsHRorSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return _has_hr_portal_access(user)


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


def _is_hr_admin(user):
    return _has_hr_portal_access(user)


class HRDocumentViewSet(viewsets.ModelViewSet):
    queryset = HRDocument.objects.all().select_related("audience_company", "audience_resort").prefetch_related("acknowledged_by")
    serializer_class = HRDocumentSerializer

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsHRorSuperAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_hr_admin(user):
            return self._apply_filters(qs)

        filters = Q(visible_from__lte=timezone.now()) & (
            Q(visible_until__isnull=True) | Q(visible_until__gt=timezone.now())
        )

        if getattr(user, "company_id", None):
            filters &= Q(audience_company__isnull=True) | Q(audience_company_id=user.company_id)
        if getattr(user, "resort_id", None):
            filters &= Q(audience_resort__isnull=True) | Q(audience_resort_id=user.resort_id)
        role = getattr(user, "role", None)
        if role:
            filters &= Q(audience_roles__contains=[role]) | Q(audience_roles=[])

        return self._apply_filters(qs.filter(filters))

    def _apply_filters(self, qs):
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search) | Q(category__icontains=search))

        limit = self.request.query_params.get("limit")
        offset = self.request.query_params.get("offset")
        try:
            limit_val = int(limit) if limit is not None else None
            offset_val = int(offset) if offset is not None else 0
        except (TypeError, ValueError):
            return qs.order_by("-updated_at")

        qs = qs.order_by("-updated_at")
        if limit_val is not None:
            return qs[offset_val : offset_val + limit_val]
        if offset_val:
            return qs[offset_val:]
        return qs

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def acknowledge(self, request, pk=None):
        document = self.get_object()
        user = request.user
        if not (user.is_superuser or document.is_visible_for(user)):
            return Response({"detail": "Documento non disponibile"}, status=403)
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT")
        document.acknowledged_by.add(user)
        HREventLog.record(
            event_type="document_ack",
            actor=user,
            target=document,
            metadata={
                "document_id": str(document.pk),
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )
        return Response({"status": "acknowledged"})


class HRDocumentAckAuditView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, *args, **kwargs):
        limit = request.query_params.get("limit", "100")
        try:
            limit_val = max(1, min(int(limit), 500))
        except ValueError:
            limit_val = 100

        events = (
            HREventLog.objects.filter(event_type="document_ack")
            .select_related("actor")
            .order_by("-created_at")[:limit_val]
        )
        document_ids = [event.metadata.get("document_id") for event in events if event.metadata.get("document_id")]
        documents = HRDocument.objects.filter(id__in=document_ids)
        document_map = {str(doc.id): doc for doc in documents}

        payload = []
        for event in events:
            document_id = event.metadata.get("document_id")
            document = document_map.get(str(document_id)) if document_id else None
            actor = event.actor
            payload.append(
                {
                    "id": str(event.id),
                    "document": {
                        "id": document_id,
                        "title": getattr(document, "title", None),
                    },
                    "actor": {
                        "id": str(actor.id) if actor else None,
                        "username": getattr(actor, "username", None),
                        "display_name": (f"{actor.first_name} {actor.last_name}").strip()
                        if actor and (actor.first_name or actor.last_name)
                        else getattr(actor, "username", None),
                    },
                    "ip_address": event.metadata.get("ip_address"),
                    "user_agent": event.metadata.get("user_agent"),
                    "created_at": event.created_at,
                }
            )

        return Response(payload)


class AssignableUserSearchView(APIView):
    permission_classes = [IsHRorSuperAdmin]

    def get(self, request, *args, **kwargs):
        term = request.query_params.get("q", "").strip()
        User = get_user_model()
        qs = self._scoped_user_queryset(request.user)

        if term:
            qs = qs.filter(
                Q(username__icontains=term)
                | Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(email__icontains=term)
            )

        qs = qs.order_by("username")[:10]

        data = [
            {
                "id": str(u.pk),
                "username": u.username,
                "display_name": (f"{u.first_name} {u.last_name}").strip() or u.username,
                "email": u.email or "",
                "role": u.get_role_display() if hasattr(u, "get_role_display") else "",
            }
            for u in qs
        ]

        return Response(data)

    def _scoped_user_queryset(self, user):
        User = get_user_model()
        qs = User.objects.all()
        if user.is_superuser:
            return qs
        scope_filters = {}
        if getattr(user, "company_id", None):
            scope_filters["company_id"] = user.company_id
        if getattr(user, "resort_id", None):
            scope_filters["resort_id"] = user.resort_id
        return qs.filter(**{k: v for k, v in scope_filters.items() if v})


class HRNotificationViewSet(viewsets.ModelViewSet):
    queryset = HRNotification.objects.all().select_related("audience_company", "audience_resort", "created_by")
    serializer_class = HRNotificationSerializer

    def _log_status_change(self, notification, previous_status):
        if previous_status == notification.status:
            return
        HREventLog.record(
            event_type="notification_status_changed",
            actor=self.request.user,
            target=notification,
            metadata={"previous": previous_status, "current": notification.status},
        )

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsHRorSuperAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        is_hr = getattr(user, "role", None) == getattr(user, "RISORSE_UMANE", None)
        status_param = self.request.query_params.get("status")
        category_param = self.request.query_params.get("category")
        if user.is_superuser or is_hr:
            if status_param:
                qs = qs.filter(status=status_param)
            if category_param:
                qs = qs.filter(category=category_param)
            return qs
        filters = Q(status=HRNotification.STATUS_PUBLISHED)
        filters &= Q(scheduled_for__isnull=True) | Q(scheduled_for__lte=timezone.now())
        filters &= Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        if getattr(user, "company_id", None):
            filters &= Q(audience_company__isnull=True) | Q(audience_company_id=user.company_id)
        if getattr(user, "resort_id", None):
            filters &= Q(audience_resort__isnull=True) | Q(audience_resort_id=user.resort_id)
        role = getattr(user, "role", None)
        if role:
            filters &= Q(audience_roles__contains=[role]) | Q(audience_roles=[])
        return qs.filter(filters)

    def perform_create(self, serializer):
        notification = serializer.save()
        HREventLog.record(
            event_type="notification_created",
            actor=self.request.user,
            target=notification,
            metadata={"notification_id": str(notification.pk), "status": notification.status},
        )

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        notification = serializer.save()
        HREventLog.record(
            event_type="notification_updated",
            actor=self.request.user,
            target=notification,
            metadata={"notification_id": str(notification.pk)},
        )
        self._log_status_change(notification, previous_status)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def deliver(self, request, pk=None):
        notification = self.get_object()
        result = deliver_notification(notification)
        return Response(
            {
                "delivered": len([d for d in result.deliveries if d.status == HRNotificationDelivery.STATUS_DELIVERED]),
                "errors": result.errors,
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def publish(self, request, pk=None):
        notification = self.get_object()
        previous_status = notification.status
        notification.status = HRNotification.STATUS_PUBLISHED
        notification.save(update_fields=["status", "updated_at"])
        self._log_status_change(notification, previous_status)
        HREventLog.record(
            event_type="notification_published",
            actor=request.user,
            target=notification,
            metadata={"notification_id": str(notification.pk)},
        )
        return Response(self.get_serializer(notification).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def archive(self, request, pk=None):
        notification = self.get_object()
        previous_status = notification.status
        notification.status = HRNotification.STATUS_ARCHIVED
        notification.save(update_fields=["status", "updated_at"])
        self._log_status_change(notification, previous_status)
        HREventLog.record(
            event_type="notification_archived",
            actor=request.user,
            target=notification,
            metadata={"notification_id": str(notification.pk)},
        )
        return Response(self.get_serializer(notification).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def resend_failed(self, request, pk=None):
        notification = self.get_object()
        failed = notification.deliveries.filter(status=HRNotificationDelivery.STATUS_FAILED)
        failed.update(status=HRNotificationDelivery.STATUS_PENDING, error="")
        result = deliver_notification(notification)
        return Response(
            {
                "resent": failed.count(),
                "delivered": len([d for d in result.deliveries if d.status == HRNotificationDelivery.STATUS_DELIVERED]),
                "errors": result.errors,
            }
        )


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user, "role", None) == getattr(user, "RISORSE_UMANE", None):
            return NotificationPreference.objects.all()
        return NotificationPreference.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HRNotificationDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HRNotificationDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = HRNotificationDelivery.objects.select_related("notification", "user")
        if user.is_superuser or getattr(user, "role", None) == getattr(user, "RISORSE_UMANE", None):
            if notification_id := self.request.query_params.get("notification"):
                qs = qs.filter(notification_id=notification_id)
            if status := self.request.query_params.get("status"):
                qs = qs.filter(status=status)
            return qs
        return qs.filter(user=user)


class PayslipBatchViewSet(viewsets.ModelViewSet):
    queryset = PayslipBatch.objects.all().select_related("company", "resort", "uploaded_by")
    serializer_class = PayslipBatchSerializer
    permission_classes = [IsHRorSuperAdmin]
    lookup_field = 'uuid'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_hr_admin(user):
            pass
        else:
            filters = {}
            if getattr(user, "company_id", None):
                filters["company_id"] = user.company_id
            if getattr(user, "resort_id", None):
                filters["resort_id"] = user.resort_id
            qs = qs.filter(**{k: v for k, v in filters.items() if v})
        if status := self.request.query_params.get("status"):
            qs = qs.filter(status=status)
        return qs

    def get_renderers(self):
        if self.action in {"preview_stream_batch", "preview_stream_job"}:
            return [EventStreamRenderer()]
        return super().get_renderers()

    def create(self, request, *args, **kwargs):
        raw_data = request.data.copy()
        if hasattr(raw_data, "lists"):
            data = {key: (values[-1] if len(values) == 1 else values) for key, values in raw_data.lists()}
        else:
            data = dict(raw_data)
        preview_token = data.get("preview_token")
        preview = None
        if preview_token:
            preview = PayslipBatchPreview.objects.filter(id=preview_token, created_by=request.user).first()
            if not preview:
                return Response({"detail": "Preview token non valido o scaduto."}, status=400)
            source_file = request.FILES.get("source_file")
            if preview.source_filename and source_file and preview.source_filename != source_file.name:
                return Response({"detail": "Il file caricato non corrisponde alla preview confermata."}, status=400)
            if source_file and preview.source_checksum:
                if _compute_upload_checksum(source_file) != preview.source_checksum:
                    return Response({"detail": "Il contenuto del file non corrisponde alla preview confermata."}, status=400)
            data["manual_assignments"] = preview.manual_assignments or {}
        manual_assignments = self._parse_manual_assignments(data.get("manual_assignments"))
        if manual_assignments is False:
            return Response({"detail": "Manual assignments non valido.", "error_code": "invalid_manual_assignments"}, status=400)
        if manual_assignments is not None:
            data["manual_assignments"] = manual_assignments
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        if preview:
            preview.delete()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        batch = self.get_object()
        log = batch.process(actor=request.user)
        serializer = self.get_serializer(batch)
        return Response({"batch": serializer.data, "log": log})

    @action(detail=True, methods=["get"], url_path="preview-stream", renderer_classes=[EventStreamRenderer])
    def preview_stream_batch(self, request, pk=None):
        batch = self.get_object()
        serializer = self.get_serializer(batch)

        def event_stream():
            payload = json.dumps(
                {
                    "batch": serializer.data,
                    "status": batch.status,
                }
            )
            yield f"event: preview\ndata: {payload}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(detail=False, methods=["post"], url_path="preview-confirm")
    def preview_confirm(self, request):
        manual_assignments = self._parse_manual_assignments(request.data.get("manual_assignments"))
        if manual_assignments is False:
            return Response({"detail": "Manual assignments non valido.", "error_code": "invalid_manual_assignments"}, status=400)
        source_file = request.FILES.get("source_file")
        preview = PayslipBatchPreview.objects.create(
            created_by=request.user,
            source_filename=source_file.name if source_file else "",
            source_checksum=_compute_upload_checksum(source_file) if source_file else "",
            manual_assignments=manual_assignments or {},
        )
        HREventLog.record(
            event_type="preview_confirmed",
            actor=request.user,
            target=preview,
            metadata={"preview_token": str(preview.pk), "has_manual_assignments": bool((manual_assignments or {}).get("segments"))},
        )
        return Response({"token": str(preview.pk)})

    @action(detail=False, methods=["post"], url_path="preview-start")
    def preview_start(self, request):
        source_file = request.FILES.get("source_file")
        if not source_file:
            return Response({"detail": "Carica un PDF o ZIP per avviare la preview.", "error_code": "missing_source_file"}, status=400)
        filename = source_file.name.lower()
        if not (filename.endswith(".pdf") or filename.endswith(".zip")):
            return Response({"detail": "L'anteprima è disponibile per PDF singoli o ZIP.", "error_code": "unsupported_file_type"}, status=400)

        enable_ocr = str(request.data.get("enable_ocr", "")).lower() in {"true", "1", "yes", "on"}
        ocr_languages = request.data.get("ocr_languages") or "ita+eng"
        auto_match_strategy = request.data.get("auto_match_strategy") or "fiscal_code"
        manifest_hint = request.data.get("manifest_hint") or ""

        preview_job = PayslipPreviewJob.objects.create(
            created_by=request.user,
            source_file=source_file,
            metadata={
                "enable_ocr": enable_ocr,
                "ocr_languages": ocr_languages,
                "auto_match_strategy": auto_match_strategy,
                "manifest_hint": manifest_hint,
            },
        )
        preview_job.start_processing()
        return Response(
            {
                "token": str(preview_job.pk),
                "status": preview_job.status,
                "progress_percent": preview_job.progress_percent,
                "total_items": preview_job.total_items,
                "processed_items": preview_job.processed_items,
                "capabilities": preview_job._default_capabilities(),
            },
            status=201,
        )

    @action(detail=False, methods=["get"], url_path="preview-status/(?P<token>[^/.]+)")
    def preview_status(self, request, token=None):
        preview_job = get_object_or_404(PayslipPreviewJob, pk=token, created_by=request.user)
        payload = {
            "token": str(preview_job.pk),
            "status": preview_job.status,
            "progress_percent": preview_job.progress_percent,
            "total_items": preview_job.total_items,
            "processed_items": preview_job.processed_items,
            "error_message": preview_job.error_message,
            "error_code": "preview_failed" if preview_job.status == PayslipPreviewJob.STATUS_FAILED else "",
            "capabilities": preview_job._default_capabilities(),
        }
        preview_payload = preview_job.build_preview_payload()
        if preview_payload:
            payload["preview"] = preview_payload
        return Response(payload)

    @action(
        detail=False,
        methods=["get"],
        url_path="preview-stream/(?P<token>[^/.]+)",
        renderer_classes=[EventStreamRenderer],
    )
    def preview_stream_job(self, request, token=None):
        preview_job = get_object_or_404(PayslipPreviewJob, pk=token, created_by=request.user)

        def event_stream():
            last_progress = None
            last_status = None
            while True:
                preview_job.refresh_from_db()
                progress = preview_job.progress_percent
                status = preview_job.status
                if progress != last_progress or status != last_status:
                    data = {
                        "token": str(preview_job.pk),
                        "status": status,
                        "progress_percent": progress,
                        "total_items": preview_job.total_items,
                        "processed_items": preview_job.processed_items,
                        "error_message": preview_job.error_message,
                        "error_code": "preview_failed" if status == PayslipPreviewJob.STATUS_FAILED else "",
                        "capabilities": preview_job._default_capabilities(),
                    }
                    preview_payload = preview_job.build_preview_payload()
                    if preview_payload:
                        data["preview"] = preview_payload
                    yield "event: progress\n"
                    yield f"data: {json.dumps(data)}\n\n"
                    last_progress = progress
                    last_status = status
                if status in {PayslipPreviewJob.STATUS_COMPLETED, PayslipPreviewJob.STATUS_FAILED}:
                    break
                time.sleep(1)

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(detail=False, methods=["post"], url_path="preview-fallback")
    def preview_fallback(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Token preview mancante.", "error_code": "missing_preview_token"}, status=400)
        preview_job = get_object_or_404(PayslipPreviewJob, pk=token, created_by=request.user)
        HREventLog.record(
            event_type="preview_fallback_polling",
            actor=request.user,
            target=preview_job,
            metadata={"preview_job_id": str(preview_job.pk), "reason": request.data.get("reason") or "sse_error"},
        )
        return Response({"status": "recorded", "token": str(preview_job.pk)})

    @action(detail=False, methods=["post"])
    def preview(self, request):
        source_file = request.FILES.get("source_file")
        if not source_file:
            return Response({"detail": "Carica un PDF o ZIP per generare l'anteprima.", "error_code": "missing_source_file"}, status=400)

        filename = source_file.name.lower()

        enable_ocr = str(request.data.get("enable_ocr", "")).lower() in {"true", "1", "yes", "on"}
        ocr_languages = request.data.get("ocr_languages") or "ita+eng"
        auto_match_strategy = request.data.get("auto_match_strategy") or "fiscal_code"
        manifest_hint = request.data.get("manifest_hint") or ""
        manual_assignments = self._parse_manual_assignments(request.data.get("manual_assignments"))
        if manual_assignments is False:
            return Response({"detail": "Manual assignments non valido.", "error_code": "invalid_manual_assignments"}, status=400)

        batch = PayslipBatch(
            enable_ocr=enable_ocr,
            ocr_languages=ocr_languages,
            auto_match_strategy=auto_match_strategy,
            manifest_hint=manifest_hint,
            manual_assignments=manual_assignments or {},
            company_id=getattr(request.user, "company_id", None),
            resort_id=getattr(request.user, "resort_id", None),
        )

        try:
            if filename.endswith(".zip"):
                zip_bytes = source_file.read()
                summary, samples, errors = batch.preview_zip_segments(zip_bytes)
                return Response(
                    {
                        "file_name": source_file.name,
                        "preview_type": "zip",
                        "summary": summary,
                        "segments": self._enrich_segments_preview(samples),
                        "errors": errors,
                        "total_segments": len(samples),
                        "capabilities": {
                            "schema_version": "v2",
                            "mode": "sync",
                            "stream_available": False,
                            "polling_available": False,
                            "ocr_enabled": enable_ocr,
                            "ocr_available": False,
                            "rendering_available": False,
                        },
                    }
                )
            if not filename.endswith(".pdf"):
                return Response({"detail": "L'anteprima è disponibile per PDF singoli o ZIP.", "error_code": "unsupported_file_type"}, status=400)

            pdf_bytes = source_file.read()
            segments = batch.preview_pdf_segments(pdf_bytes)
        except Exception as exc:
            logging.exception("Errore durante la preview PDF", exc_info=exc)
            return Response({"detail": f"Impossibile generare la preview: {exc}", "error_code": "preview_generation_failed"}, status=400)

        return Response(
            {
                "file_name": source_file.name,
                "preview_type": "pdf",
                "segments": self._enrich_segments_preview(segments),
                "total_segments": len(segments),
                "capabilities": {
                    "schema_version": "v2",
                    "mode": "sync",
                    "stream_available": False,
                    "polling_available": False,
                    "ocr_enabled": enable_ocr,
                    "ocr_available": False,
                    "rendering_available": False,
                },
            }
        )

    def _enrich_segments_preview(self, segments, scan_pages=None):
        if not isinstance(segments, list):
            return []
        scan_pages = scan_pages if isinstance(scan_pages, list) else []
        page_map = {}
        for page in scan_pages:
            if isinstance(page, dict) and isinstance(page.get("page_index"), int):
                page_map[page["page_index"]] = page

        enriched = []
        for segment in segments:
            if not isinstance(segment, dict):
                enriched.append(segment)
                continue
            if isinstance(segment.get("preview_pages"), list):
                preview_pages = segment.get("preview_pages") or []
            else:
                preview_pages = []
                page_start = segment.get("page_start")
                page_end = segment.get("page_end")
                if isinstance(page_start, int) and isinstance(page_end, int) and page_start <= page_end:
                    for page_idx in range(page_start, page_end + 1):
                        if page_idx in page_map:
                            preview_pages.append(page_map[page_idx])
            payload = {
                **segment,
                "preview_pages": preview_pages,
                "preview_available": bool(preview_pages),
            }
            if not payload["preview_available"] and not payload.get("error") and not payload.get("preview_error_code"):
                payload["preview_error_code"] = "segment_preview_unavailable"
            enriched.append(payload)
        return enriched

    def _parse_manual_assignments(self, raw_value):
        if not raw_value:
            return None
        if isinstance(raw_value, str):
            try:
                raw_value = json.loads(raw_value)
            except json.JSONDecodeError:
                return False
        if not isinstance(raw_value, dict):
            return False
        segments = raw_value.get("segments", {})
        if segments and not isinstance(segments, dict):
            return False
        normalized = {}
        for segment_key, user_id in (segments or {}).items():
            if user_id in (None, ""):
                continue
            if isinstance(user_id, dict):
                normalized_value = {}
                if user_id.get("user_id") or user_id.get("user"):
                    normalized_value["user_id"] = str(user_id.get("user_id") or user_id.get("user"))
                if user_id.get("period_label"):
                    period_label = str(user_id.get("period_label")).strip()
                    if not re.match(r"^20\d{2}[-/](0[1-9]|1[0-2])$", period_label):
                        return False
                    normalized_value["period_label"] = period_label
                if normalized_value:
                    normalized[str(segment_key)] = normalized_value
            else:
                normalized[str(segment_key)] = str(user_id)
        raw_value["segments"] = normalized
        return raw_value

    @action(detail=True, methods=["post"])
    def download_payslips_zip(self, request, *args, **kwargs):
        """
        Generates and returns a ZIP file containing all payslips associated with this batch,
        with each payslip renamed according to the CF_ANNO_MESE.pdf format.
        Accessible only by users with the 'OWNER' role or superusers.
        """
        user = request.user
        if not (getattr(user, "role", None) == getattr(user, "OWNER", "owner") or user.is_superuser):
            return HttpResponse("Non autorizzato.", status=403)

        batch = self.get_object()
        payslips = batch.payslips.all().select_related("user")

        if not payslips.exists():
            return HttpResponse("Nessuna busta paga trovata per questo batch.", status=404)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
            for payslip in payslips:
                if payslip.file and hasattr(payslip.file, 'name') and payslip.file.storage.exists(payslip.file.name):
                    try:
                        # Determine the correct period for the filename
                        _, period_machine, _ = batch._extract_period_from_text(f"{payslip.period_label} 2000")
                        new_filename = batch._build_payslip_name(payslip.user, period_machine)

                        with payslip.file.open('rb') as f:
                            zip_file.writestr(new_filename, f.read())
                    except Exception as e:
                        logging.error(f"Impossibile processare il file della busta paga {payslip.file.name} per il batch {batch.id}: {e}", exc_info=True)
                else:
                    logging.warning(f"File della busta paga per l'utente {payslip.user_id} nel batch {batch.id} non trovato o non valido.")

        zip_buffer.seek(0)
        safe_batch_id = str(batch.id)
        response = HttpResponse(zip_buffer, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="buste_paga_batch_{safe_batch_id}.zip"'

        return response


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayslipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Payslip.objects.select_related("company", "resort", "batch", "user")
        if _is_hr_admin(user):
            return self._apply_filters(qs)

        return self._apply_filters(qs.filter(user=user))

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def download_renamed(self, request, pk=None):
        user = request.user
        if not (getattr(user, "role", None) == getattr(user, "OWNER", "owner") or user.is_superuser):
            return HttpResponse("Non autorizzato.", status=403)

        payslip = self.get_object()

        try:
            created_at = payslip.created_at or timezone.now()
            period_machine = (
                payslip.batch._extract_period_from_text("")[1]
                if payslip.batch
                else created_at.strftime("%Y_%m")
            )
            if payslip.period_label:
                # Re-parse the human label to get a machine version
                _, machine_label, _ = payslip.batch._extract_period_from_text(f"{payslip.period_label} 2000") # Add dummy year
                if machine_label and machine_label.split('_')[0] != created_at.strftime("%Y"): # check if year is dummy
                    period_machine = machine_label

            filename = payslip.batch._build_payslip_name(payslip.user, period_machine)

            response = FileResponse(payslip.file.open('rb'), as_attachment=True, filename=filename)
            return response
        except Exception as e:
            logging.error(f"Errore durante la generazione del nome del file per la busta paga {payslip.pk}: {e}", exc_info=True)
            return HttpResponse("Impossibile generare il file.", status=500)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def mark_downloaded(self, request, pk=None):
        payslip = self.get_object()
        user = request.user

        is_hr = getattr(user, "role", None) == getattr(user, "RISORSE_UMANE", None)
        if not (
            user.is_superuser
            or payslip.user_id == user.id
            or (
                is_hr
                and ((not payslip.company_id) or payslip.company_id == getattr(user, "company_id", None))
                and ((not payslip.resort_id) or payslip.resort_id == getattr(user, "resort_id", None))
            )
        ):
            return Response({"detail": "Non autorizzato"}, status=403)

        if not payslip.downloaded_at:
            payslip.downloaded_at = timezone.now()
            payslip.save(update_fields=["downloaded_at"])

        HREventLog.record(
            event_type="payslip_download",
            actor=user,
            target=payslip,
            metadata={
                "payslip_id": str(payslip.pk),
                "ip_address": _get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            },
        )

        return Response({"status": "downloaded", "downloaded_at": payslip.downloaded_at})

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def regenerate_period(self, request, pk=None):
        payslip = self.get_object()
        period_label = request.data.get("period_label") or self._suggest_period_label(payslip)
        payslip.period_label = period_label
        payslip.save(update_fields=["period_label"])
        return Response(self.get_serializer(payslip).data)

    def _suggest_period_label(self, payslip):
        filename = Path(payslip.file.name).stem
        match = re.search(r"(20\d{2})[-_]?(0[1-9]|1[0-2])", filename)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
        if payslip.created_at:
            return payslip.created_at.strftime("%Y-%m")
        return payslip.period_label or ""

    def _apply_filters(self, qs):
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(period_label__icontains=search) | Q(user__username__icontains=search))

        limit = self.request.query_params.get("limit")
        offset = self.request.query_params.get("offset")
        try:
            limit_val = int(limit) if limit is not None else None
            offset_val = int(offset) if offset is not None else 0
        except (TypeError, ValueError):
            return qs.order_by("-created_at")

        qs = qs.order_by("-created_at")
        if limit_val is not None:
            return qs[offset_val : offset_val + limit_val]
        if offset_val:
            return qs[offset_val:]
        return qs


class PayslipUnmatchedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PayslipUnmatched.objects.select_related("batch", "company", "resort", "resolved_to", "resolved_by")
    serializer_class = PayslipUnmatchedSerializer
    permission_classes = [IsHRorSuperAdmin]

    def _ensure_scope(self, request, unmatched):
        if _is_hr_admin(request.user):
            return None
        if unmatched.company_id and unmatched.company_id != getattr(request.user, "company_id", None):
            return Response({"detail": "Non autorizzato sul batch"}, status=403)
        if unmatched.resort_id and unmatched.resort_id != getattr(request.user, "resort_id", None):
            return Response({"detail": "Non autorizzato sul batch"}, status=403)
        return None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_hr_admin(user):
            if company := self.request.query_params.get("company"):
                qs = qs.filter(company_id=company)
            if resort := self.request.query_params.get("resort"):
                qs = qs.filter(resort_id=resort)
        else:
            filters = {}
            if getattr(user, "company_id", None):
                filters["company_id"] = user.company_id
            if getattr(user, "resort_id", None):
                filters["resort_id"] = user.resort_id
            qs = qs.filter(**{k: v for k, v in filters.items() if v})
        if status := self.request.query_params.get("status"):
            qs = qs.filter(status=status)
        if identifier := self.request.query_params.get("identifier"):
            qs = qs.filter(identifier__icontains=identifier)
        if batch_id := self.request.query_params.get("batch"):
            qs = qs.filter(batch_id=batch_id)
        if period := self.request.query_params.get("period"):
            match = re.match(r"(?P<year>20\d{2})[-_/]?(?P<month>0[1-9]|1[0-2])", period)
            if match:
                qs = qs.filter(created_at__year=match.group("year"), created_at__month=match.group("month"))
        return qs

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        from django.contrib.auth import get_user_model

        unmatched = self.get_object()
        if unmatched.resolved:
            return Response({"detail": "Elemento già risolto"}, status=400)

        scope_response = self._ensure_scope(request, unmatched)
        if scope_response:
            return scope_response

        target_user_identifier = request.data.get("user")
        if not target_user_identifier:
            return Response({"detail": "Campo 'user' obbligatorio"}, status=400)

        User = get_user_model()
        scoped_users = AssignableUserSearchView()._scoped_user_queryset(request.user)
        target_user = None

        try:
            target_user = scoped_users.get(pk=target_user_identifier)
        except (User.DoesNotExist, ValueError):
            target_user = None

        if target_user is None:
            target_user = (
                scoped_users.filter(
                    Q(username__iexact=target_user_identifier)
                    | Q(email__iexact=target_user_identifier)
                    | Q(first_name__iexact=target_user_identifier)
                    | Q(last_name__iexact=target_user_identifier)
                )
                .order_by("username")
                .first()
            )

        if target_user is None:
            return Response({"detail": "Utente non trovato"}, status=404)

        if not request.user.is_superuser:
            if getattr(request.user, "company_id", None) and target_user.company_id not in {
                None,
                request.user.company_id,
            }:
                return Response({"detail": "Non autorizzato sull'utente selezionato"}, status=403)
            if getattr(request.user, "resort_id", None) and target_user.resort_id not in {
                None,
                request.user.resort_id,
            }:
                return Response({"detail": "Non autorizzato sull'utente selezionato"}, status=403)

        if unmatched.company_id and target_user.company_id and unmatched.company_id != target_user.company_id:
            return Response({"detail": "L'utente non appartiene alla stessa company del batch"}, status=400)
        if unmatched.resort_id and target_user.resort_id and unmatched.resort_id != target_user.resort_id:
            return Response({"detail": "L'utente non appartiene alla stessa struttura del batch"}, status=400)

        try:
            payslip = unmatched.mark_resolved(
                user=target_user, resolved_by=request.user, period_label=request.data.get("period_label", "")
            )
        except (SuspiciousFileOperation, FileNotFoundError, OSError, ValueError) as exc:
            return Response({"detail": str(exc) or "Impossibile allegare il file della busta paga"}, status=400)
        if payslip:
            HREventLog.record(
                event_type="payslip_resolved",
                actor=request.user,
                target=payslip,
                metadata={"unmatched_id": str(unmatched.pk), "user_id": str(target_user.pk)},
            )
        payslip_data = PayslipSerializer(payslip, context={"request": request}).data if payslip else None
        unmatched_data = self.get_serializer(unmatched).data
        return Response({"payslip": payslip_data, "unmatched": unmatched_data})

    @action(detail=True, methods=["get"])
    def suggestions(self, request, pk=None):
        from django.contrib.auth import get_user_model

        unmatched = self.get_object()
        scope_response = self._ensure_scope(request, unmatched)
        if scope_response:
            return scope_response

        identifier = (unmatched.identifier or "").strip()
        if not identifier:
            return Response({"results": []})

        User = get_user_model()
        qs = User.objects.all()
        if not request.user.is_superuser:
            if getattr(request.user, "company_id", None):
                qs = qs.filter(company_id=request.user.company_id)
            if getattr(request.user, "resort_id", None):
                qs = qs.filter(resort_id=request.user.resort_id)

        query = identifier.lower()
        tokens = [token for token in query.split() if token]
        candidates = qs.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        ).distinct()[:20]

        scored = []
        for user in candidates:
            score = 0
            if user.username and user.username.lower() == query:
                score = 90
            elif user.email and user.email.lower() == query:
                score = 85
            elif user.username and query in user.username.lower():
                score = 70
            elif user.email and query in user.email.lower():
                score = 70
            if tokens:
                first = (user.first_name or "").lower()
                last = (user.last_name or "").lower()
                if len(tokens) == 2 and tokens[0] == first and tokens[1] == last:
                    score = max(score, 80)
                elif tokens[0] == first or tokens[0] == last:
                    score = max(score, 65)
            if score > 0:
                scored.append(
                    {
                        "id": str(user.pk),
                        "username": user.username,
                        "display_name": (f"{user.first_name} {user.last_name}").strip() or user.username,
                        "email": user.email or "",
                        "score": score,
                    }
                )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return Response({"results": scored[:5]})

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def send_email(self, request, pk=None):
        unmatched = self.get_object()
        scope_response = self._ensure_scope(request, unmatched)
        if scope_response:
            return scope_response

        recipient_email = (request.data.get("recipient_email") or "").strip()
        subject = (request.data.get("subject") or "").strip()
        body = (request.data.get("body") or "").strip()

        if not recipient_email:
            return Response({"detail": "Email destinatario obbligatoria."}, status=400)
        try:
            validate_email(recipient_email)
        except ValidationError:
            return Response({"detail": "Email destinatario non valida."}, status=400)
        if not subject:
            return Response({"detail": "Oggetto email obbligatorio."}, status=400)
        if not body:
            return Response({"detail": "Corpo email obbligatorio."}, status=400)

        file_field = getattr(unmatched, "file", None)
        if not file_field or not getattr(file_field, "name", None):
            return Response({"detail": "File della busta paga non disponibile."}, status=400)
        storage = file_field.storage
        if not storage.exists(file_field.name):
            return Response({"detail": "File della busta paga non trovato."}, status=404)

        try:
            with file_field.open("rb") as fh:
                attachment_bytes = fh.read()
        except (OSError, ValueError) as exc:
            return Response({"detail": f"Impossibile leggere il file della busta paga: {exc}"}, status=400)

        attachment_name = "busta_paga.pdf"

        connection = get_connection(
            host=getattr(settings, "HR_EMAIL_HOST", settings.EMAIL_HOST),
            port=getattr(settings, "HR_EMAIL_PORT", settings.EMAIL_PORT),
            username=getattr(settings, "HR_EMAIL_HOST_USER", settings.EMAIL_HOST_USER),
            password=getattr(settings, "HR_EMAIL_HOST_PASSWORD", settings.EMAIL_HOST_PASSWORD),
            use_tls=getattr(settings, "HR_EMAIL_USE_TLS", settings.EMAIL_USE_TLS),
            use_ssl=getattr(settings, "HR_EMAIL_USE_SSL", settings.EMAIL_USE_SSL),
        )
        from_email = getattr(settings, "HR_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL)

        try:
            success, error_message, attempts = send_payslip_email(
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                attachment_name=attachment_name,
                attachment_bytes=attachment_bytes,
                connection=connection,
                from_email=from_email,
                context={
                    "site_name": settings.JAZZMIN_SETTINGS.get("site_brand", "HR Portal"),
                    "attachment_label": attachment_name,
                },
            )
        except Exception as exc:
            detail = describe_email_error(exc)
            logging.exception("Errore durante l'invio email busta paga", exc_info=exc)
            HREventLog.record(
                event_type="payslip_email_failed",
                actor=request.user,
                target=unmatched,
                metadata={
                    "recipient_email": recipient_email,
                    "attachment_name": attachment_name,
                    "subject": subject,
                    "error": detail,
                    "attempts": 1,
                },
            )
            return Response(
                {
                    "status": "failed",
                    "detail": detail or "Errore tecnico durante l'invio.",
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "body": body,
                    "attachment_name": attachment_name,
                    "attempts": 1,
                },
                status=500,
            )

        if success:
            scope_company = unmatched.company or getattr(request.user, "company", None)
            scope_resort = unmatched.resort or getattr(request.user, "resort", None)
            recipient, _ = PayslipEmailRecipient.objects.get_or_create(
                email=recipient_email.lower(),
                company=scope_company,
                resort=scope_resort,
            )
            recipient.used_count += 1
            recipient.last_used_at = timezone.now()
            recipient.save(update_fields=["used_count", "last_used_at"])

            HREventLog.record(
                event_type="payslip_email_sent",
                actor=request.user,
                target=unmatched,
                metadata={
                    "recipient_email": recipient_email,
                    "attachment_name": attachment_name,
                    "subject": subject,
                    "attempts": attempts,
                },
            )
            return Response(
                {
                    "status": "sent",
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "body": body,
                    "attachment_name": attachment_name,
                    "attempts": attempts,
                }
            )

        failure_detail = error_message or "Servizio email non configurato o non disponibile."
        HREventLog.record(
            event_type="payslip_email_failed",
            actor=request.user,
            target=unmatched,
            metadata={
                "recipient_email": recipient_email,
                "attachment_name": attachment_name,
                "subject": subject,
                "error": failure_detail,
                "attempts": attempts,
            },
        )
        return Response(
            {
                "status": "failed",
                "detail": failure_detail,
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "attachment_name": attachment_name,
                "attempts": attempts,
            },
            status=500,
        )


class PayslipEmailSuggestionView(APIView):
    permission_classes = [IsHRorSuperAdmin]

    def get(self, request):
        query = (request.query_params.get("query") or "").strip()
        qs = PayslipEmailRecipient.objects.all()
        if not request.user.is_superuser:
            filters = {}
            if getattr(request.user, "company_id", None):
                filters["company_id"] = request.user.company_id
            if getattr(request.user, "resort_id", None):
                filters["resort_id"] = request.user.resort_id
            qs = qs.filter(**{k: v for k, v in filters.items() if v})
        if query:
            qs = qs.filter(email__icontains=query)
        suggestions = [
            {"email": rec.email, "last_used_at": rec.last_used_at, "used_count": rec.used_count}
            for rec in qs.order_by("-last_used_at")[:10]
        ]
        return Response({"results": suggestions})


class PayslipEmailTestView(APIView):
    permission_classes = [IsHRorSuperAdmin]

    def post(self, request):
        recipient_email = (request.data.get("recipient_email") or request.user.email or "").strip()
        if not recipient_email:
            return Response({"detail": "Email destinatario obbligatoria per il test SMTP."}, status=400)
        try:
            validate_email(recipient_email)
        except ValidationError:
            return Response({"detail": "Email destinatario non valida."}, status=400)

        connection = get_connection(
            host=getattr(settings, "HR_EMAIL_HOST", settings.EMAIL_HOST),
            port=getattr(settings, "HR_EMAIL_PORT", settings.EMAIL_PORT),
            username=getattr(settings, "HR_EMAIL_HOST_USER", settings.EMAIL_HOST_USER),
            password=getattr(settings, "HR_EMAIL_HOST_PASSWORD", settings.EMAIL_HOST_PASSWORD),
            use_tls=getattr(settings, "HR_EMAIL_USE_TLS", settings.EMAIL_USE_TLS),
            use_ssl=getattr(settings, "HR_EMAIL_USE_SSL", settings.EMAIL_USE_SSL),
        )
        from_email = getattr(settings, "HR_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL)

        try:
            email = EmailMessage(
                subject="Test SMTP HR Portal",
                body="Questo è un test di invio SMTP dal portale HR.",
                from_email=from_email,
                to=[recipient_email],
                connection=connection,
            )
            email.send(fail_silently=False)
        except Exception as exc:
            detail = describe_email_error(exc)
            logging.exception("Errore durante il test SMTP", exc_info=exc)
            return Response(
                {
                    "status": "failed",
                    "detail": detail,
                    "recipient_email": recipient_email,
                },
                status=500,
            )

        return Response({"status": "sent", "recipient_email": recipient_email})


class HREventLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HREventLog.objects.select_related("actor", "company", "resort")
    serializer_class = HREventLogSerializer
    permission_classes = [IsHRorSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        event_type = self.request.query_params.get("event_type")
        if _is_hr_admin(user):
            filtered = qs
        else:
            filters = {}
            if getattr(user, "company_id", None):
                filters["company_id"] = user.company_id
            if getattr(user, "resort_id", None):
                filters["resort_id"] = user.resort_id
            filtered = qs.filter(**{k: v for k, v in filters.items() if v})
        if event_type:
            filtered = filtered.filter(event_type=event_type)
        return filtered

    @action(detail=False, methods=["get"], permission_classes=[IsSuperAdmin])
    def payslip_download_report(self, request):
        events = (
            HREventLog.objects.select_related("actor")
            .filter(event_type="payslip_download")
            .order_by("-created_at")
        )
        rows = []
        for event in events:
            actor = event.actor
            actor_label = (
                getattr(actor, "display_name", None)
                or getattr(actor, "get_full_name", lambda: "")()
                or getattr(actor, "username", None)
                or "Sistema"
            )
            rows.append(
                {
                    "created_at": event.created_at,
                    "actor": actor_label,
                    "actor_email": getattr(actor, "email", "") if actor else "",
                    "ip_address": event.metadata.get("ip_address", ""),
                    "user_agent": event.metadata.get("user_agent", ""),
                    "target_id": event.target_id,
                }
            )

        html = render_to_string(
            "hr_portal/reports/payslip_downloads.html",
            {
                "generated_at": timezone.now(),
                "rows": rows,
            },
        )
        pdf_file = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="payslip_downloads_report.pdf"'
        return response


class ListeningTicketViewSet(viewsets.ModelViewSet):
    queryset = ListeningTicket.objects.select_related("author", "assigned_to", "company", "resort")
    serializer_class = ListeningTicketSerializer

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            return [IsHRorSuperAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_superuser:
            return qs
        filters = {}
        if getattr(user, "company_id", None):
            filters["company_id"] = user.company_id
        if getattr(user, "resort_id", None):
            filters["resort_id"] = user.resort_id
        qs = qs.filter(**{k: v for k, v in filters.items() if v})
        status_param = self.request.query_params.get("status")
        priority_param = self.request.query_params.get("priority")
        due_before = self.request.query_params.get("due_before")
        due_within_hours = self.request.query_params.get("due_within_hours")
        sla_lte = self.request.query_params.get("sla_lte")
        overdue = self.request.query_params.get("overdue")
        assigned_to = self.request.query_params.get("assigned_to")
        if status_param:
            qs = qs.filter(status=status_param)
        if priority_param:
            qs = qs.filter(priority=priority_param)
        if due_before:
            qs = qs.filter(due_at__lte=due_before)
        if due_within_hours:
            try:
                hours = int(due_within_hours)
                limit = timezone.now() + timezone.timedelta(hours=hours)
                qs = qs.filter(due_at__lte=limit)
            except (TypeError, ValueError):
                pass
        if overdue in {"1", "true", "True"}:
            qs = qs.filter(due_at__lte=timezone.now())
        if sla_lte and str(sla_lte).isdigit():
            qs = qs.filter(sla_hours__lte=int(sla_lte))
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)
        return qs

    def perform_create(self, serializer):
        ticket = serializer.save(
            author=self.request.user,
            company=getattr(self.request.user, "company", None),
            resort=getattr(self.request.user, "resort", None),
        )
        HREventLog.record(
            event_type="ticket_created",
            actor=self.request.user,
            target=ticket,
            metadata={"ticket_id": str(ticket.pk)},
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def escalate(self, request, pk=None):
        ticket = self.get_object()
        ticket.priority = "high"
        ticket.status = "in_progress"
        ticket.save(update_fields=["priority", "status", "updated_at"])
        HREventLog.record(
            event_type="ticket_escalated",
            actor=request.user,
            target=ticket,
            metadata={"ticket_id": str(ticket.pk)},
        )
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def add_message(self, request, pk=None):
        ticket = self.get_object()
        user = request.user
        if not (
            user.is_superuser
            or getattr(user, "role", None) == getattr(user, "RISORSE_UMANE", None)
            or ticket.author_id == user.id
            or ticket.assigned_to_id == user.id
        ):
            return Response({"detail": "Non autorizzato"}, status=403)

        serializer = ListeningTicketMessageSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(ticket=ticket, author=user)
        HREventLog.record(
            event_type="ticket_message",
            actor=user,
            target=ticket,
            metadata={"message_id": str(message.pk)},
        )
        return Response(ListeningTicketMessageSerializer(message, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        assignee_id = request.data.get("assigned_to")
        if not assignee_id:
            return Response({"detail": "Campo 'assigned_to' obbligatorio"}, status=400)
        User = ticket._meta.get_field("author").remote_field.model
        try:
            assignee = User.objects.get(pk=assignee_id)
        except User.DoesNotExist:
            return Response({"detail": "Utente non trovato"}, status=404)

        if ticket.company_id and assignee.company_id and ticket.company_id != assignee.company_id:
            return Response({"detail": "L'assegnatario non appartiene alla stessa azienda"}, status=400)
        if ticket.resort_id and assignee.resort_id and ticket.resort_id != assignee.resort_id:
            return Response({"detail": "L'assegnatario non appartiene alla stessa struttura"}, status=400)

        ticket.assigned_to = assignee
        if ticket.status == "new":
            ticket.status = "in_progress"
        ticket.save(update_fields=["assigned_to", "status", "updated_at"])
        HREventLog.record(
            event_type="ticket_assigned",
            actor=request.user,
            target=ticket,
            metadata={"ticket_id": str(ticket.pk), "assigned_to": str(assignee.pk)},
        )
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorSuperAdmin])
    def close(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = "closed"
        ticket.save(update_fields=["status", "closed_at", "updated_at"])
        HREventLog.record(
            event_type="ticket_closed",
            actor=request.user,
            target=ticket,
            metadata={"ticket_id": str(ticket.pk)},
        )
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HRPortalAppView(LoginRequiredMixin, TemplateView):
    template_name = "hr_portal/react_root.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access(request.user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def has_access(self, user):
        return _has_hr_portal_access(user)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BachecaNuviaView(LoginRequiredMixin, TemplateView):
    template_name = "hr_portal/bacheca_root.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access(request.user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def has_access(self, user):
        return bool(user and user.is_authenticated)


class HRPreviewIncidentAckView(APIView):
    permission_classes = [IsHRorSuperAdmin]

    def post(self, request, *args, **kwargs):
        note = (request.data.get("note") or "").strip()
        alert_level = (request.data.get("alert_level") or "warning").strip().lower()
        if alert_level not in {"warning", "critical"}:
            alert_level = "warning"

        user = request.user
        HREventLog.objects.create(
            event_type="preview_incident_ack",
            actor=user if getattr(user, "is_authenticated", False) else None,
            target_model="PayslipPreviewPipeline",
            target_id="global",
            metadata={"note": note[:500], "alert_level": alert_level},
            company=getattr(user, "company", None),
            resort=getattr(user, "resort", None),
        )
        return Response({"detail": "Incidente preview preso in carico."}, status=status.HTTP_201_CREATED)


class HRPreviewIncidentResolveView(APIView):
    permission_classes = [IsHRorSuperAdmin]

    def post(self, request, *args, **kwargs):
        resolution_note = (request.data.get("resolution_note") or "").strip()
        root_cause = (request.data.get("root_cause") or "").strip()
        action_items = request.data.get("action_items") or []
        if isinstance(action_items, str):
            action_items = [item.strip() for item in action_items.splitlines() if item.strip()]
        if not isinstance(action_items, list):
            action_items = []

        normalized_items = []
        for idx, raw_item in enumerate(action_items[:10], start=1):
            label = str(raw_item).strip()[:180]
            if not label:
                continue
            normalized_items.append({
                "id": f"A{idx}",
                "label": label,
            })

        user = request.user
        HREventLog.objects.create(
            event_type="preview_incident_resolved",
            actor=user if getattr(user, "is_authenticated", False) else None,
            target_model="PayslipPreviewPipeline",
            target_id="global",
            metadata={
                "resolution_note": resolution_note[:800],
                "root_cause": root_cause[:400],
                "action_items": normalized_items,
            },
            company=getattr(user, "company", None),
            resort=getattr(user, "resort", None),
        )
        return Response({"detail": "Incidente preview chiuso."}, status=status.HTTP_201_CREATED)


class HRPreviewIncidentActionCompleteView(APIView):
    permission_classes = [IsHRorSuperAdmin]

    def post(self, request, *args, **kwargs):
        action_id = (request.data.get("action_id") or "").strip()
        label = (request.data.get("label") or "").strip()
        if not action_id:
            return Response({"detail": "action_id obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        HREventLog.objects.create(
            event_type="preview_incident_action_completed",
            actor=user if getattr(user, "is_authenticated", False) else None,
            target_model="PayslipPreviewPipeline",
            target_id="global",
            metadata={
                "action_id": action_id[:24],
                "label": label[:180],
            },
            company=getattr(user, "company", None),
            resort=getattr(user, "resort", None),
        )
        return Response({"detail": "Azione correttiva marcata come completata."}, status=status.HTTP_201_CREATED)


class HRPortalContextView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        is_hr_admin = _is_hr_admin(user)
        is_hr = is_hr_admin
        company = self._safe_related(user, "company")
        resort = self._safe_related(user, "resort")
        return Response(
            {
                "user_id": getattr(user, "id", None),
                "username": getattr(user, "username", ""),
                "user_role": getattr(user, "role", None),
                "is_hr": bool(is_hr),
                "is_superuser": bool(user.is_superuser),
                "is_hr_admin": bool(is_hr_admin),
                "company": self._serialize_related(company),
                "resort": self._serialize_related(resort),
                "scopes": {
                    "company_id": getattr(user, "company_id", None),
                    "resort_id": getattr(user, "resort_id", None),
                },
                "permissions": {
                    "can_manage_notifications": bool(is_hr_admin),
                    "can_manage_batches": bool(is_hr_admin),
                    "can_assign_tickets": bool(is_hr_admin),
                    "can_view_audit": bool(is_hr_admin),
                },
            }
        )

    def _safe_related(self, user, attr):
        try:
            return getattr(user, attr)
        except Exception:
            return None

    def _serialize_related(self, obj):
        if not obj:
            return None
        return {"id": getattr(obj, "id", None), "name": getattr(obj, "name", None) or getattr(obj, "title", None)}


class HRKPIView(APIView):
    permission_classes = [IsHRorSuperAdmin]

    def get(self, request, *args, **kwargs):
        user = request.user
        payslip_qs = self._scoped_queryset(Payslip.objects.all(), user)
        total_payslips = payslip_qs.count()
        downloaded_count = payslip_qs.filter(downloaded_at__isnull=False).count()
        download_rate = (downloaded_count / total_payslips * 100) if total_payslips else 0

        event_qs = self._scoped_queryset(HREventLog.objects.all(), user)
        window_days = request.query_params.get("window_days", "30")
        try:
            window_days = max(1, min(int(window_days), 365))
        except (TypeError, ValueError):
            window_days = 30
        window_from = timezone.now() - timezone.timedelta(days=window_days)
        event_qs = event_qs.filter(created_at__gte=window_from)

        def _bounded_float(raw, default, min_value=0.0, max_value=100.0):
            try:
                value = float(raw)
            except (TypeError, ValueError):
                return default
            return max(min_value, min(value, max_value))

        completion_min = _bounded_float(request.query_params.get("completion_min"), 85.0)
        failure_max = _bounded_float(request.query_params.get("failure_max"), 10.0)
        fallback_max = _bounded_float(request.query_params.get("fallback_max"), 30.0)
        try:
            corrective_action_sla_hours = max(1, min(int(request.query_params.get("corrective_sla_hours", 72)), 720))
        except (TypeError, ValueError):
            corrective_action_sla_hours = 72

        email_sent = event_qs.filter(event_type="payslip_email_sent").count()
        email_failed = event_qs.filter(event_type="payslip_email_failed").count()
        email_total = email_sent + email_failed
        email_success_rate = (email_sent / email_total * 100) if email_total else 0

        document_qs = self._scoped_document_queryset(HRDocument.objects.all(), user)
        required_docs = document_qs.filter(requires_acknowledgement=True)
        total_required_docs = required_docs.count()
        acknowledged_docs = required_docs.filter(acknowledged_by__isnull=False).distinct().count()
        ack_rate = (acknowledged_docs / total_required_docs * 100) if total_required_docs else 0

        preview_started = event_qs.filter(event_type="preview_started").count()
        preview_completed = event_qs.filter(event_type="preview_completed").count()
        preview_failed = event_qs.filter(event_type="preview_failed").count()
        preview_confirmed = event_qs.filter(event_type="preview_confirmed").count()
        preview_fallback_polling = event_qs.filter(event_type="preview_fallback_polling").count()
        completion_rate = round((preview_completed / max(preview_started, 1)) * 100, 2)
        failure_rate = round((preview_failed / max(preview_started, 1)) * 100, 2)
        fallback_rate = round((preview_fallback_polling / max(preview_started, 1)) * 100, 2)
        # Phase 3: funnel and latency metrics
        batch_created = event_qs.filter(event_type="payslip_batch_created").count()
        preview_to_confirm_rate = round((preview_confirmed / max(preview_started, 1)) * 100, 2)
        confirm_to_batch_rate = round((batch_created / max(preview_confirmed, 1)) * 100, 2) if preview_confirmed else 0

        preview_confirmed_times = list(
            event_qs.filter(event_type="preview_confirmed").order_by("created_at").values_list("created_at", flat=True)
        )

        preview_started_times = list(
            event_qs.filter(event_type="preview_started").order_by("created_at").values_list("created_at", flat=True)
        )
        preview_completed_times = list(
            event_qs.filter(event_type="preview_completed").order_by("created_at").values_list("created_at", flat=True)
        )
        preview_failed_times = list(
            event_qs.filter(event_type="preview_failed").order_by("created_at").values_list("created_at", flat=True)
        )

        def _pair_durations_minutes(starts, ends):
            samples = []
            end_idx = 0
            for start in starts:
                while end_idx < len(ends) and ends[end_idx] < start:
                    end_idx += 1
                if end_idx >= len(ends):
                    break
                delta = ends[end_idx] - start
                samples.append(round(delta.total_seconds() / 60, 2))
                end_idx += 1
            return samples

        completion_duration_samples = _pair_durations_minutes(preview_started_times, preview_completed_times)
        failure_duration_samples = _pair_durations_minutes(preview_started_times, preview_failed_times)
        avg_preview_completion_minutes = round(sum(completion_duration_samples) / len(completion_duration_samples), 2) if completion_duration_samples else None
        avg_preview_failure_minutes = round(sum(failure_duration_samples) / len(failure_duration_samples), 2) if failure_duration_samples else None
        preview_to_confirm_samples = _pair_durations_minutes(preview_started_times, preview_confirmed_times)
        avg_preview_to_confirm_minutes = (
            round(sum(preview_to_confirm_samples) / len(preview_to_confirm_samples), 2)
            if preview_to_confirm_samples
            else None
        )

        confirmed_events = list(
            event_qs.filter(event_type="preview_confirmed").values_list("metadata", flat=True)
        )
        manual_review_confirmed = sum(
            1 for metadata in confirmed_events if isinstance(metadata, dict) and metadata.get("has_manual_assignments")
        )
        first_pass_resolved = max(preview_confirmed - manual_review_confirmed, 0)
        first_pass_resolution_rate = round((first_pass_resolved / max(preview_confirmed, 1)) * 100, 2) if preview_confirmed else 0

        manual_assignment_errors_current = event_qs.filter(event_type="payslip_resolved").count()
        previous_window_from = window_from - timezone.timedelta(days=window_days)
        previous_window_errors = self._scoped_queryset(HREventLog.objects.all(), user).filter(
            event_type="payslip_resolved",
            created_at__gte=previous_window_from,
            created_at__lt=window_from,
        ).count()
        manual_assignment_error_reduction_rate = (
            round(((previous_window_errors - manual_assignment_errors_current) / max(previous_window_errors, 1)) * 100, 2)
            if previous_window_errors
            else 0
        )
        phase4_kpi_status = {
            "preview_to_confirm_time": "ok" if avg_preview_to_confirm_minutes is None or avg_preview_to_confirm_minutes <= 15 else "warning",
            "first_pass_resolution": "ok" if first_pass_resolution_rate >= 70 else "warning",
            "manual_assignment_error_reduction": (
                "ok"
                if previous_window_errors == 0 or manual_assignment_error_reduction_rate >= 0
                else "warning"
            ),
        }
        phase4_summary = {
            "window_days": window_days,
            "targets": {
                "preview_to_confirm_minutes_max": 15,
                "first_pass_resolution_rate_min": 70,
                "manual_assignment_error_reduction_rate_min": 0,
            },
            "status": phase4_kpi_status,
            "baseline": {
                "manual_assignment_errors_previous": previous_window_errors,
                "manual_assignment_errors_current": manual_assignment_errors_current,
            },
        }

        auto_matched_count = payslip_qs.filter(auto_matched=True).count()
        manual_matched_count = max(total_payslips - auto_matched_count, 0)
        auto_match_share = round((auto_matched_count / max(total_payslips, 1)) * 100, 2) if total_payslips else 0
        manual_match_share = round((manual_matched_count / max(total_payslips, 1)) * 100, 2) if total_payslips else 0

        prev_from = window_from - timezone.timedelta(days=window_days)
        prev_event_qs = self._scoped_queryset(HREventLog.objects.all(), user).filter(
            created_at__gte=prev_from,
            created_at__lt=window_from,
        )
        prev_started = prev_event_qs.filter(event_type="preview_started").count()
        prev_completed = prev_event_qs.filter(event_type="preview_completed").count()
        prev_failed = prev_event_qs.filter(event_type="preview_failed").count()
        prev_fallback = prev_event_qs.filter(event_type="preview_fallback_polling").count()
        prev_completion_rate = round((prev_completed / max(prev_started, 1)) * 100, 2)
        prev_failure_rate = round((prev_failed / max(prev_started, 1)) * 100, 2)
        prev_fallback_rate = round((prev_fallback / max(prev_started, 1)) * 100, 2)

        health_status = "healthy"
        if completion_rate < max(completion_min - 15, 0) or failure_rate > min(failure_max + 10, 100):
            health_status = "critical"
        elif completion_rate < completion_min or failure_rate > failure_max or fallback_rate > fallback_max:
            health_status = "warning"
        recommendations = []
        if completion_rate < completion_min:
            recommendations.append("Verifica worker preview e code Celery")
        if fallback_rate > fallback_max:
            recommendations.append("Controlla proxy/SSE: alto tasso di fallback polling")
        if preview_confirmed < max(preview_started // 2, 1):
            recommendations.append("Bassa conversione preview->conferma: rivedere UX di assegnazione")

        completion_rate_delta = round(completion_rate - prev_completion_rate, 2)
        failure_rate_delta = round(failure_rate - prev_failure_rate, 2)
        fallback_rate_delta = round(fallback_rate - prev_fallback_rate, 2)

        daily_rows = (
            event_qs.filter(event_type__in=[
                "preview_started",
                "preview_completed",
                "preview_failed",
                "preview_fallback_polling",
            ])
            .annotate(day=TruncDate("created_at"))
            .values("day", "event_type")
            .annotate(total=Count("id"))
            .order_by("day")
        )
        daily_map = {}
        for row in daily_rows:
            day_key = row.get("day").isoformat() if row.get("day") else ""
            slot = daily_map.setdefault(day_key, {
                "date": day_key,
                "started": 0,
                "completed": 0,
                "failed": 0,
                "fallback_polling": 0,
            })
            event_type = row.get("event_type")
            total = int(row.get("total") or 0)
            if event_type == "preview_started":
                slot["started"] = total
            elif event_type == "preview_completed":
                slot["completed"] = total
            elif event_type == "preview_failed":
                slot["failed"] = total
            elif event_type == "preview_fallback_polling":
                slot["fallback_polling"] = total
        daily_preview_series = [daily_map[key] for key in sorted(daily_map.keys())]

        top_failure_reasons = []
        failed_events = event_qs.filter(event_type="preview_failed").order_by("-created_at")[:200]
        reason_counter = {}
        for event in failed_events:
            reason = (event.metadata or {}).get("error") or "Errore non classificato"
            reason = str(reason).strip()[:120]
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
        for reason, total in sorted(reason_counter.items(), key=lambda item: item[1], reverse=True)[:5]:
            top_failure_reasons.append({"reason": reason, "count": total})

        alert_level = "none"
        alert_messages = []
        if health_status == "critical":
            alert_level = "critical"
            alert_messages.append("Pipeline preview in stato critico: verifica code worker e stabilità estrazione")
        elif health_status == "warning":
            alert_level = "warning"
            alert_messages.append("Pipeline preview in warning: monitorare failure/fallback nelle prossime ore")
        if failure_rate_delta > 5:
            alert_level = "critical" if alert_level == "critical" else "warning"
            alert_messages.append("Failure rate in aumento rispetto al periodo precedente")
        if fallback_rate_delta > 10:
            alert_level = "critical" if alert_level == "critical" else "warning"
            alert_messages.append("Fallback polling in crescita: possibile degrado canale SSE")

        incident_open = alert_level in {"warning", "critical"}
        latest_incident_ack = event_qs.filter(event_type="preview_incident_ack").select_related("actor").first()
        latest_incident_resolve = event_qs.filter(event_type="preview_incident_resolved").select_related("actor").first()
        incident_acknowledged = bool(incident_open and latest_incident_ack)
        incident_state = {
            "incident_open": incident_open,
            "acknowledged": incident_acknowledged,
            "acknowledged_at": latest_incident_ack.created_at if latest_incident_ack else None,
            "acknowledged_by": (
                latest_incident_ack.actor.get_username()
                if latest_incident_ack and latest_incident_ack.actor
                else None
            ),
            "note": ((latest_incident_ack.metadata or {}).get("note") if latest_incident_ack else "") or "",
            "resolved_at": latest_incident_resolve.created_at if latest_incident_resolve else None,
            "resolved_by": (
                latest_incident_resolve.actor.get_username()
                if latest_incident_resolve and latest_incident_resolve.actor
                else None
            ),
            "resolution_note": ((latest_incident_resolve.metadata or {}).get("resolution_note") if latest_incident_resolve else "") or "",
            "root_cause": ((latest_incident_resolve.metadata or {}).get("root_cause") if latest_incident_resolve else "") or "",
            "action_items": ((latest_incident_resolve.metadata or {}).get("action_items") if latest_incident_resolve else []) or [],
        }
        incident_playbook = self._build_incident_playbook(alert_level)
        incident_journal = []
        incident_events = event_qs.filter(
            event_type__in=["preview_incident_ack", "preview_incident_resolved"]
        ).select_related("actor")[:10]
        for event in incident_events:
            metadata = event.metadata or {}
            incident_journal.append(
                {
                    "event_type": event.event_type,
                    "created_at": event.created_at,
                    "actor": event.actor.get_username() if event.actor else None,
                    "note": metadata.get("note") or metadata.get("resolution_note") or "",
                    "root_cause": metadata.get("root_cause") or "",
                }
            )

        # Step 12 - incident response performance metrics (MTTA/MTTR)
        ack_timestamps = list(
            event_qs.filter(event_type="preview_incident_ack").order_by("created_at").values_list("created_at", flat=True)
        )
        resolve_timestamps = list(
            event_qs.filter(event_type="preview_incident_resolved").order_by("created_at").values_list("created_at", flat=True)
        )
        incident_start_timestamps = list(
            event_qs.filter(event_type="preview_failed").order_by("created_at").values_list("created_at", flat=True)
        )

        def _pair_durations(starts, ends):
            durations = []
            end_idx = 0
            for start_at in starts:
                while end_idx < len(ends) and ends[end_idx] < start_at:
                    end_idx += 1
                if end_idx >= len(ends):
                    break
                durations.append((ends[end_idx] - start_at).total_seconds())
                end_idx += 1
            return durations

        mtta_samples = _pair_durations(incident_start_timestamps, ack_timestamps)
        mttr_samples = _pair_durations(incident_start_timestamps, resolve_timestamps)
        avg_mtta_minutes = round((sum(mtta_samples) / len(mtta_samples)) / 60, 2) if mtta_samples else None
        avg_mttr_minutes = round((sum(mttr_samples) / len(mttr_samples)) / 60, 2) if mttr_samples else None

        incident_response_metrics = {
            "incidents_detected": len(incident_start_timestamps),
            "incidents_acknowledged": len(ack_timestamps),
            "incidents_resolved": len(resolve_timestamps),
            "ack_coverage_rate": round((len(ack_timestamps) / max(len(incident_start_timestamps), 1)) * 100, 2),
            "resolution_rate": round((len(resolve_timestamps) / max(len(incident_start_timestamps), 1)) * 100, 2),
            "avg_mtta_minutes": avg_mtta_minutes,
            "avg_mttr_minutes": avg_mttr_minutes,
            "open_incidents_estimate": max(len(incident_start_timestamps) - len(resolve_timestamps), 0),
        }

        # Phase 3 SLA targets and breach signals
        mtta_target_minutes = 15
        mttr_target_minutes = 30
        incident_response_metrics["targets"] = {
            "mtta_minutes": mtta_target_minutes,
            "mttr_minutes": mttr_target_minutes,
        }
        incident_response_metrics["breaches"] = {
            "mtta": bool(avg_mtta_minutes is not None and avg_mtta_minutes > mtta_target_minutes),
            "mttr": bool(avg_mttr_minutes is not None and avg_mttr_minutes > mttr_target_minutes),
        }

        latest_action_items = (incident_state.get("action_items") or []) if isinstance(incident_state, dict) else []
        action_items_norm = []
        for idx, item in enumerate(latest_action_items, start=1):
            if isinstance(item, dict):
                action_id = str(item.get("id") or f"A{idx}")[:24]
                label = str(item.get("label") or "").strip()[:180]
            else:
                action_id = f"A{idx}"
                label = str(item).strip()[:180]
            if not label:
                continue
            action_items_norm.append({"id": action_id, "label": label})

        completion_events = event_qs.filter(event_type="preview_incident_action_completed").order_by("created_at")
        completion_by_action = {}
        for event in completion_events:
            action_id = str((event.metadata or {}).get("action_id") or "").strip()
            if not action_id:
                continue
            completion_by_action[action_id] = {
                "completed_at": event.created_at,
                "completed_by": event.actor.get_username() if event.actor else None,
            }

        due_base = incident_state.get("resolved_at") or incident_state.get("acknowledged_at") or timezone.now()
        due_at = due_base + timezone.timedelta(hours=corrective_action_sla_hours)
        due_soon_threshold = timezone.now() + timezone.timedelta(hours=24)
        corrective_actions = []
        for item in action_items_norm:
            completion = completion_by_action.get(item["id"])
            completed = bool(completion)
            status = "completed"
            if not completed and due_at < timezone.now():
                status = "overdue"
            elif not completed and due_at <= due_soon_threshold:
                status = "due_soon"
            elif not completed:
                status = "open"
            corrective_actions.append(
                {
                    "id": item["id"],
                    "label": item["label"],
                    "completed": completed,
                    "status": status,
                    "due_at": due_at,
                    "completed_at": completion.get("completed_at") if completion else None,
                    "completed_by": completion.get("completed_by") if completion else None,
                }
            )

        completed_count = sum(1 for item in corrective_actions if item["completed"])
        overdue_count = sum(1 for item in corrective_actions if item["status"] == "overdue")
        due_soon_count = sum(1 for item in corrective_actions if item["status"] == "due_soon")
        corrective_action_metrics = {
            "total": len(corrective_actions),
            "completed": completed_count,
            "open": max(len(corrective_actions) - completed_count, 0),
            "overdue": overdue_count,
            "due_soon": due_soon_count,
            "sla_hours": corrective_action_sla_hours,
            "completion_rate": round((completed_count / max(len(corrective_actions), 1)) * 100, 2) if corrective_actions else 0,
        }

        return Response(
            {
                "payslip_download_rate": {
                    "total": total_payslips,
                    "downloaded": downloaded_count,
                    "rate": round(download_rate, 2),
                },
                "payslip_email_delivery": {
                    "sent": email_sent,
                    "failed": email_failed,
                    "total": email_total,
                    "success_rate": round(email_success_rate, 2),
                },
                "document_ack_rate": {
                    "required": total_required_docs,
                    "acknowledged": acknowledged_docs,
                    "rate": round(ack_rate, 2),
                },
                "payslip_preview_pipeline": {
                    "window_days": window_days,
                    "started": preview_started,
                    "completed": preview_completed,
                    "failed": preview_failed,
                    "confirmed": preview_confirmed,
                    "batch_created": batch_created,
                    "fallback_polling": preview_fallback_polling,
                    "completion_rate": completion_rate,
                    "preview_to_confirm_rate": preview_to_confirm_rate,
                    "confirm_to_batch_rate": confirm_to_batch_rate,
                    "avg_preview_completion_minutes": avg_preview_completion_minutes,
                    "avg_preview_failure_minutes": avg_preview_failure_minutes,
                    "avg_preview_to_confirm_minutes": avg_preview_to_confirm_minutes,
                    "first_pass_resolution_rate": first_pass_resolution_rate,
                    "first_pass_resolved": first_pass_resolved,
                    "manual_review_confirmed": manual_review_confirmed,
                    "manual_assignment_errors_current": manual_assignment_errors_current,
                    "manual_assignment_errors_previous": previous_window_errors,
                    "manual_assignment_error_reduction_rate": manual_assignment_error_reduction_rate,
                    "phase4_summary": phase4_summary,
                    "funnel": {
                        "started": preview_started,
                        "confirmed": preview_confirmed,
                        "batch_created": batch_created,
                        "dropoff_before_confirm": max(preview_started - preview_confirmed, 0),
                        "dropoff_before_batch": max(preview_confirmed - batch_created, 0),
                    },
                    "failure_rate": failure_rate,
                    "fallback_rate": fallback_rate,
                    "health_status": health_status,
                    "recommendations": recommendations,
                    "completion_rate_delta": completion_rate_delta,
                    "failure_rate_delta": failure_rate_delta,
                    "fallback_rate_delta": fallback_rate_delta,
                    "alert_level": alert_level,
                    "alert_messages": alert_messages,
                    "thresholds": {
                        "completion_min": completion_min,
                        "failure_max": failure_max,
                        "fallback_max": fallback_max,
                    },
                    "breaches": {
                        "completion": completion_rate < completion_min,
                        "failure": failure_rate > failure_max,
                        "fallback": fallback_rate > fallback_max,
                    },
                    "incident_open": incident_open,
                    "incident_state": incident_state,
                    "incident_playbook": incident_playbook,
                    "incident_journal": incident_journal,
                    "incident_response_metrics": incident_response_metrics,
                    "corrective_actions": corrective_actions,
                    "corrective_action_metrics": corrective_action_metrics,
                    "daily_preview_series": daily_preview_series,
                    "top_failure_reasons": top_failure_reasons,
                    "matching_mix": {
                        "auto_matched": auto_matched_count,
                        "manual_or_review": manual_matched_count,
                        "auto_match_share": auto_match_share,
                        "manual_match_share": manual_match_share,
                    },
                },
            }
        )

    def _build_incident_playbook(self, alert_level):
        severity = "warning" if alert_level == "warning" else "critical" if alert_level == "critical" else "info"
        return [
            {
                "id": "check_worker_queue",
                "title": "Verifica worker preview / coda task",
                "description": "Controlla che i worker siano online e che la coda preview non sia bloccata.",
                "severity": severity,
                "check": "worker_queue_health",
                "command_hint": "celery -A gestione_manutenzioni inspect active",
            },
            {
                "id": "check_sse_proxy",
                "title": "Verifica canale SSE e reverse proxy",
                "description": "Con fallback elevato, conferma buffering disabilitato e timeout adeguati sul proxy.",
                "severity": severity,
                "check": "sse_proxy",
                "command_hint": "verifica X-Accel-Buffering:no e timeout upstream > 60s",
            },
            {
                "id": "check_rendering_ocr",
                "title": "Verifica dipendenze rendering/OCR",
                "description": "Con errori in aumento, verifica librerie PDF rendering/OCR e storage media accessibile.",
                "severity": severity,
                "check": "ocr_rendering_stack",
                "command_hint": "python -c 'import pypdfium2; print(\"ok\")'",
            },
        ]

    def _scoped_queryset(self, qs, user):
        if user.is_superuser:
            return qs
        filters = {}
        if getattr(user, "company_id", None):
            filters["company_id"] = user.company_id
        if getattr(user, "resort_id", None):
            filters["resort_id"] = user.resort_id
        return qs.filter(**{k: v for k, v in filters.items() if v})

    def _scoped_document_queryset(self, qs, user):
        if user.is_superuser:
            return qs
        filters = Q()
        if getattr(user, "company_id", None):
            filters &= Q(audience_company__isnull=True) | Q(audience_company_id=user.company_id)
        if getattr(user, "resort_id", None):
            filters &= Q(audience_resort__isnull=True) | Q(audience_resort_id=user.resort_id)
        return qs.filter(filters)
