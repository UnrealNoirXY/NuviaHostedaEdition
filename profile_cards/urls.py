from django.urls import path

from . import views

app_name = "profile_cards"

urlpatterns = [
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/<int:card_id>/send-email/", views.admin_send_email, name="admin_send_email"),
    path("admin/<int:card_id>/revoke/", views.admin_revoke_tokens, name="admin_revoke_tokens"),
    path("admin/<int:card_id>/generate-token/", views.admin_generate_token, name="admin_generate_token"),
    path("kpi/", views.kpi_dashboard, name="kpi_dashboard"),
    path("public/<str:token>/", views.public_profile, name="public_profile"),
    path("public/<str:token>/vcard/", views.public_vcard, name="public_vcard"),
    path("public/<str:token>/apple-pass/", views.public_apple_pass, name="public_apple_pass"),
    path("public/<str:token>/google-wallet/", views.public_google_wallet, name="public_google_wallet"),
    path("public/<str:token>/track/", views.public_track_event, name="public_track_event"),
    path("public/<str:token>/lead/", views.public_submit_lead, name="public_submit_lead"),
]
