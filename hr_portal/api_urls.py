from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AssignableUserSearchView,
    HRDocumentViewSet,
    HRDocumentAckAuditView,
    HREventLogViewSet,
    HRPortalContextView,
    HRNotificationDeliveryViewSet,
    HRNotificationViewSet,
    HRKPIView,
    HRPreviewIncidentAckView,
    HRPreviewIncidentResolveView,
    HRPreviewIncidentActionCompleteView,
    ListeningTicketViewSet,
    NotificationPreferenceViewSet,
    PayslipBatchViewSet,
    PayslipEmailSuggestionView,
    PayslipEmailTestView,
    PayslipUnmatchedViewSet,
    PayslipViewSet,
)

app_name = "hr_portal"

router = DefaultRouter()
router.register(r"documents", HRDocumentViewSet, basename="hr-document")
router.register(r"notifications", HRNotificationViewSet, basename="hr-notification")
router.register(r"notification-preferences", NotificationPreferenceViewSet, basename="hr-notification-preference")
router.register(r"notification-deliveries", HRNotificationDeliveryViewSet, basename="hr-notification-delivery")
router.register(r"payslip-batches", PayslipBatchViewSet, basename="payslip-batch")
router.register(r"payslip-unmatched", PayslipUnmatchedViewSet, basename="payslip-unmatched")
router.register(r"payslips", PayslipViewSet, basename="payslip")
router.register(r"listening-tickets", ListeningTicketViewSet, basename="listening-ticket")
router.register(r"events", HREventLogViewSet, basename="hr-event-log")

urlpatterns = router.urls + [
    path("context/", HRPortalContextView.as_view(), name="hr-context"),
    path("kpi/", HRKPIView.as_view(), name="hr-kpi"),
    path("kpi/incident-ack/", HRPreviewIncidentAckView.as_view(), name="hr-kpi-incident-ack"),
    path("kpi/incident-resolve/", HRPreviewIncidentResolveView.as_view(), name="hr-kpi-incident-resolve"),
    path("kpi/incident-action-complete/", HRPreviewIncidentActionCompleteView.as_view(), name="hr-kpi-incident-action-complete"),
    path("assignable-users/", AssignableUserSearchView.as_view(), name="hr-assignable-users"),
    path("document-acks/", HRDocumentAckAuditView.as_view(), name="hr-document-acks"),
    path("payslip-email-suggestions/", PayslipEmailSuggestionView.as_view(), name="payslip-email-suggestions"),
    path("payslip-email-test/", PayslipEmailTestView.as_view(), name="payslip-email-test"),
]
