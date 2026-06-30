from django.urls import path

from .views import HRPortalAppView, BachecaNuviaView, DownloadPayslipView

app_name = "hr_portal"

urlpatterns = [
    path("", HRPortalAppView.as_view(), name="portal"),
    path("bacheca/", BachecaNuviaView.as_view(), name="bacheca"),
    path("payslips/<uuid:payslip_id>/download/", DownloadPayslipView.as_view(), name="download_payslip"),
]
