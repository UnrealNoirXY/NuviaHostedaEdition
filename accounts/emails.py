from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags


def build_privacy_confirmation_url(user):
    base_url = getattr(settings, "BASE_URL", "http://localhost:8000").rstrip("/")
    signer = TimestampSigner(salt="privacy-consent")
    token = signer.sign(str(user.pk))
    return f"{base_url}{reverse('privacy_confirm', args=[token])}"


def send_privacy_confirmation_email(user):
    if not getattr(user, "email", None):
        return False

    confirmation_url = build_privacy_confirmation_url(user)
    context = {
        "user": user,
        "confirmation_url": confirmation_url,
        "site_name": getattr(settings, "SITE_NAME", getattr(settings, "JAZZMIN_SETTINGS", {}).get("site_brand", "")),
    }
    html_body = render_to_string("core/emails/privacy_confirmation.html", context)
    plain_body = strip_tags(html_body)

    send_mail(
        subject="Conferma email e consenso privacy",
        message=plain_body,
        html_message=html_body,
        from_email=getattr(settings, "HR_FROM_EMAIL", None) or getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
        fail_silently=False,
    )
    return True
