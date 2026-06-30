from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.core.cache import cache
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
import csv
import hashlib
import io

from .emailing import send_profile_card_email, send_lead_notification_email
from .models import CardTemplate, ProfileCard, ProfileCardEvent, ProfileCardPublicToken, ProfileCardSettings, ProfileCardLead
from .permissions import is_superadmin_user
from .security import build_ip_hash, check_rate_limit, security_response
from .services import get_kpi_summary
from .tasks import send_profile_card_email_batch_task
from .tokens import issue_public_token
from .utils import generate_qr_code_base64
from .wallet import build_apple_pkpass, build_google_wallet_url


@login_required
@require_http_methods(["GET", "POST"])
def admin_dashboard(request):
    if not is_superadmin_user(request.user):
        return HttpResponseForbidden("Forbidden")

    config = ProfileCardSettings.get_solo()

    action = None
    if request.method == "POST":
        action = request.POST.get("action", "create_card")

        if action == "mark_lead_read":
            lead_id = request.POST.get("lead_id")
            ProfileCardLead.objects.filter(pk=lead_id).update(is_read=True)
            return redirect("profile_cards:admin_dashboard")

        if action == "delete_lead":
            lead_id = request.POST.get("lead_id")
            ProfileCardLead.objects.filter(pk=lead_id).delete()
            return redirect("profile_cards:admin_dashboard")

        if action == "import_cards_csv":
            csv_payload = request.POST.get("csv_payload", "").strip()
            if not csv_payload:
                messages.error(request, "Inserisci un CSV valido.")
                return redirect("profile_cards:admin_dashboard")

            created = 0
            reader = csv.DictReader(io.StringIO(csv_payload))
            for row in reader:
                first_name = (row.get("first_name") or "").strip()
                last_name = (row.get("last_name") or "").strip()
                role = (row.get("role") or "").strip()
                email = (row.get("email") or "").strip()
                if not (first_name and last_name and role and email):
                    continue

                phone = (row.get("phone") or "").strip()
                department = (row.get("department") or "").strip()

                if config.require_phone and not phone:
                    continue
                if config.require_department and not department:
                    continue

                template = CardTemplate.objects.filter(is_active=True, is_default=True).order_by("id").first()
                ProfileCard.objects.create(
                    template=template,
                    applied_template_version=getattr(template, "version", 1),
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    email=email,
                    phone=phone,
                    department=department,
                    status=ProfileCard.STATUS_PUBLISHED,
                )
                created += 1

            messages.success(request, f"Import completato: {created} schede create.")
            return redirect("profile_cards:admin_dashboard")

        if action == "send_email_batch":
            recipients_raw = request.POST.get("recipient_email", "").strip()
            recipients = [mail.strip() for mail in recipients_raw.replace(";", ",").split(",") if mail.strip()]
            if not recipients:
                messages.error(request, "Inserisci almeno un destinatario.")
                return redirect("profile_cards:admin_dashboard")

            card_ids = list(ProfileCard.objects.filter(status=ProfileCard.STATUS_PUBLISHED).values_list("id", flat=True))
            send_profile_card_email_batch_task.delay(card_ids, recipients, request.user.id)

            messages.info(request, "Invio batch avviato in background.")
            return redirect("profile_cards:admin_dashboard")

        if action == "create_template":
            name = request.POST.get("template_name", "").strip()
            if not name:
                messages.error(request, "Nome template obbligatorio.")
                return redirect("profile_cards:admin_dashboard")
            is_default = bool(request.POST.get("is_default_template"))
            if is_default:
                CardTemplate.objects.filter(is_default=True).update(is_default=False)
            CardTemplate.objects.create(
                name=name,
                company_name=request.POST.get("company_name", "").strip(),
                primary_color=request.POST.get("primary_color", "#111111").strip() or "#111111",
                secondary_color=request.POST.get("secondary_color", "#ffffff").strip() or "#ffffff",
                font_family=request.POST.get("font_family", "Inter").strip() or "Inter",
                border_radius=request.POST.get("border_radius", "12px").strip() or "12px",
                button_style=request.POST.get("button_style", "filled").strip() or "filled",
                layout_type=request.POST.get("layout_type", "executive").strip() or "executive",
                background_pattern=request.POST.get("background_pattern", "none").strip() or "none",
                header_image=request.FILES.get("header_image"),
                header_gradient_enabled=bool(request.POST.get("header_gradient_enabled")),
                is_default=is_default,
                is_active=True,
            )
            messages.success(request, "Template creato con successo.")
            return redirect("profile_cards:admin_dashboard")

        if action == "save_settings":
            config.default_token_days = int(request.POST.get("default_token_days", config.default_token_days) or config.default_token_days)
            config.require_phone = bool(request.POST.get("require_phone"))
            config.require_department = bool(request.POST.get("require_department"))
            config.auto_update_wallet_passes = bool(request.POST.get("auto_update_wallet_passes"))
            config.enable_multi_brand_templates = bool(request.POST.get("enable_multi_brand_templates"))
            config.show_apple_wallet = bool(request.POST.get("show_apple_wallet"))
            config.show_google_wallet = bool(request.POST.get("show_google_wallet"))
            config.save()
            messages.success(request, "Impostazioni fase 14 aggiornate.")
            return redirect("profile_cards:admin_dashboard")

        if action == "bump_template_version":
            template_id = request.POST.get("template_id", "").strip()
            template = CardTemplate.objects.filter(pk=template_id, is_active=True).first()
            if template:
                template.version += 1
                template.save(update_fields=["version"])
                if config.auto_update_wallet_passes:
                    ProfileCard.objects.filter(template=template).update(applied_template_version=template.version)
                messages.success(request, "Versione template incrementata.")
            return redirect("profile_cards:admin_dashboard")


        if action in ("create_card", "update_card"):
            phone = request.POST.get("phone", "").strip()
            department = request.POST.get("department", "").strip()

            if config.require_phone and not phone:
                messages.error(request, "Il campo telefono è obbligatorio nelle impostazioni correnti.")
                return redirect("profile_cards:admin_dashboard")
            if config.require_department and not department:
                messages.error(request, "Il campo reparto è obbligatorio nelle impostazioni correnti.")
                return redirect("profile_cards:admin_dashboard")

            template_id = request.POST.get("template_id", "").strip()
            company_name = request.POST.get("company_name", "").strip()
            primary_color = request.POST.get("primary_color", "#111111").strip()
            secondary_color = request.POST.get("secondary_color", "#ffffff").strip()

            template = None
            if action == "update_card":
                card_id = request.POST.get("card_id")
                card_obj = get_object_or_404(ProfileCard, pk=card_id)
                template = card_obj.template

                if template_id and str(getattr(template, 'id', '')) != template_id:
                    template = CardTemplate.objects.filter(pk=template_id, is_active=True).first()

                if template:
                    template.company_name = company_name
                    template.primary_color = primary_color
                    template.secondary_color = secondary_color
                    template.font_family = request.POST.get("font_family", "Inter").strip()
                    template.border_radius = request.POST.get("border_radius", "12px").strip()
                    template.button_style = request.POST.get("button_style", "filled").strip()
                    template.layout_type = request.POST.get("layout_type", "executive").strip()
                    template.background_pattern = request.POST.get("background_pattern", "none").strip()
                    template.header_gradient_enabled = bool(request.POST.get("header_gradient_enabled"))
                    header_img = request.FILES.get("header_image")
                    if header_img:
                        template.header_image = header_img
                    template.save()

            if template is None and template_id:
                template = CardTemplate.objects.filter(pk=template_id, is_active=True).first()

            if template is None:
                template = CardTemplate.objects.filter(is_active=True, is_default=True).order_by("id").first()

            if template is None:
                template = CardTemplate.objects.create(
                    name=f"Template-{timezone.now().timestamp()}",
                    company_name=company_name,
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                    is_active=True
                )

            card_data = {
                "template": template,
                "applied_template_version": getattr(template, "version", 1),
                "first_name": request.POST.get("first_name", "").strip(),
                "last_name": request.POST.get("last_name", "").strip(),
                "role": request.POST.get("role", "").strip(),
                "email": request.POST.get("email", "").strip(),
                "phone": phone,
                "department": department,
                "linkedin_url": request.POST.get("linkedin_url", "").strip(),
                "whatsapp_number": request.POST.get("whatsapp_number", "").strip(),
                "website_url": request.POST.get("website_url", "").strip(),
                "bio": request.POST.get("bio", "").strip(),
                "skills": request.POST.get("skills", "").strip(),
                "cta_text": request.POST.get("cta_text", "").strip(),
                "cta_url": request.POST.get("cta_url", "").strip(),
                "enable_lead_capture": bool(request.POST.get("enable_lead_capture")),
                "show_apple_wallet": bool(request.POST.get("show_apple_wallet")),
                "show_google_wallet": bool(request.POST.get("show_google_wallet")),
                "show_linkedin": bool(request.POST.get("show_linkedin")),
                "show_whatsapp": bool(request.POST.get("show_whatsapp")),
                "show_website": bool(request.POST.get("show_website")),
                "status": ProfileCard.STATUS_PUBLISHED,
            }

            avatar = request.FILES.get("avatar")

            if action == "update_card":
                card_id = request.POST.get("card_id")
                ProfileCard.objects.filter(pk=card_id).update(**card_data)
                if avatar:
                    card = ProfileCard.objects.get(pk=card_id)
                    card.avatar = avatar
                    card.save(update_fields=["avatar"])
                messages.success(request, "Scheda aggiornata correttamente.")
            else:
                card = ProfileCard.objects.create(**card_data)
                if avatar:
                    card.avatar = avatar
                    card.save(update_fields=["avatar"])
                messages.success(request, "Scheda creata correttamente.")

            return redirect("profile_cards:admin_dashboard")

    cards = ProfileCard.objects.select_related("template").order_by("last_name", "first_name")
    templates = CardTemplate.objects.filter(is_active=True).order_by("name")
    leads = ProfileCardLead.objects.select_related("card").order_by("-created_at")
    return render(
        request,
        "profile_cards/admin_dashboard.html",
        {"cards": cards, "templates": templates, "config": config, "leads": leads},
    )


@login_required
@require_http_methods(["POST"])
def admin_send_email(request, card_id):
    if not is_superadmin_user(request.user):
        return HttpResponseForbidden("Forbidden")

    card = get_object_or_404(ProfileCard, pk=card_id)
    token = issue_public_token(card)
    public_url = f"{settings.BASE_URL.rstrip('/')}" + f"/cards/public/{token.token}/"
    recipients_raw = request.POST.get("recipient_email", "").strip()
    recipients = [mail.strip() for mail in recipients_raw.replace(";", ",").split(",") if mail.strip()]
    sent_count = 0
    for recipient_email in recipients:
        delivery = send_profile_card_email(
            card=card,
            public_url=public_url,
            recipient_email=recipient_email,
            created_by=request.user,
        )
        if delivery.status == delivery.STATUS_SENT:
            sent_count += 1
    if recipients:
        messages.info(request, f"Invio completato: {sent_count}/{len(recipients)} email inviate.")
    return redirect("profile_cards:admin_dashboard")


@login_required
@require_http_methods(["POST"])
def admin_revoke_tokens(request, card_id):
    if not is_superadmin_user(request.user):
        return HttpResponseForbidden("Forbidden")

    card = get_object_or_404(ProfileCard, pk=card_id)
    ProfileCardPublicToken.objects.filter(card=card, revoked_at__isnull=True).update(revoked_at=timezone.now())
    card.status = ProfileCard.STATUS_REVOKED
    card.save(update_fields=["status", "updated_at"])
    messages.warning(request, "Token pubblici revocati e scheda disattivata.")
    return redirect("profile_cards:admin_dashboard")


@login_required
@require_http_methods(["POST"])
def admin_generate_token(request, card_id):
    if not is_superadmin_user(request.user):
        return HttpResponseForbidden("Forbidden")

    card = get_object_or_404(ProfileCard, pk=card_id)
    ProfileCardPublicToken.objects.filter(card=card, revoked_at__isnull=True).update(revoked_at=timezone.now())
    issue_public_token(card)
    card.status = ProfileCard.STATUS_PUBLISHED
    card.save(update_fields=["status", "updated_at"])
    messages.success(request, "Nuovo token pubblico generato.")
    return redirect("profile_cards:admin_dashboard")


@login_required
@require_GET
def kpi_dashboard(request):
    if not is_superadmin_user(request.user):
        return HttpResponseForbidden("Forbidden")
    data = get_kpi_summary(days=30)
    return render(request, "profile_cards/kpi_dashboard.html", {"kpi": data})


def _load_valid_token(token):
    share_token = get_object_or_404(ProfileCardPublicToken.objects.select_related("card"), token=token)
    if not share_token.is_valid():
        raise Http404("Token non valido")
    return share_token


@require_GET
def public_profile(request, token):
    if not check_rate_limit(request, bucket="public_profile", limit=60, window_seconds=60):
        return security_response()

    share_token = _load_valid_token(token)

    # Tracking logic - must run every time
    ProfileCardPublicToken.objects.filter(pk=share_token.pk).update(open_count=F("open_count") + 1)
    ProfileCardEvent.objects.create(
        card=share_token.card,
        token=share_token,
        event_type=ProfileCardEvent.EVENT_OPEN,
        source="public_profile",
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        ip_hash=build_ip_hash(request.META.get("REMOTE_ADDR", "")),
    )

    public_url = request.build_absolute_uri()

    # Cache only the QR code generation
    cache_key = f"profile_cards:qr:{hashlib.md5(public_url.encode()).hexdigest()}"
    qr_code = cache.get(cache_key)
    if not qr_code:
        qr_code = generate_qr_code_base64(public_url)
        cache.set(cache_key, qr_code, timeout=60 * 60 * 24)

    from .wallet import _has_signing_config
    config = ProfileCardSettings.get_solo()
    wallet_available = _has_signing_config()

    response = render(
        request,
        "profile_cards/public_profile.html",
        {
            "card": share_token.card,
            "token": share_token.token,
            "qr_code": qr_code,
            "wallet_available": wallet_available,
            "show_apple": config.show_apple_wallet,
            "show_google": config.show_google_wallet,
        },
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def public_vcard(request, token):
    if not check_rate_limit(request, bucket="public_vcard", limit=60, window_seconds=60):
        return security_response()

    share_token = _load_valid_token(token)

    ProfileCardPublicToken.objects.filter(pk=share_token.pk).update(vcard_download_count=F("vcard_download_count") + 1)
    ProfileCardEvent.objects.create(
        card=share_token.card,
        token=share_token,
        event_type=ProfileCardEvent.EVENT_VCARD,
        source="public_vcard",
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        ip_hash=build_ip_hash(request.META.get("REMOTE_ADDR", "")),
    )

    card = share_token.card
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{card.first_name} {card.last_name}",
        f"N:{card.last_name};{card.first_name};;;",
        f"TITLE:{card.role}",
        f"EMAIL;TYPE=INTERNET:{card.email}",
    ]
    if card.phone:
        lines.append(f"TEL;TYPE=CELL:{card.phone}")
    if card.linkedin_url:
        lines.append(f"URL;TYPE=LinkedIn:{card.linkedin_url}")
    if card.website_url:
        lines.append(f"URL;TYPE=Website:{card.website_url}")
    lines.append("END:VCARD")
    body = "\n".join(lines) + "\n"

    response = HttpResponse(body, content_type="text/vcard; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{card.first_name}_{card.last_name}.vcf"'
    return response


@require_GET
def public_apple_pass(request, token):
    if not check_rate_limit(request, bucket="public_wallet_apple", limit=60, window_seconds=60):
        return security_response()

    share_token = _load_valid_token(token)
    ProfileCardPublicToken.objects.filter(pk=share_token.pk).update(wallet_add_count=F("wallet_add_count") + 1)
    ProfileCardEvent.objects.create(
        card=share_token.card,
        token=share_token,
        event_type=ProfileCardEvent.EVENT_ADD_WALLET,
        source="wallet_apple",
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        ip_hash=build_ip_hash(request.META.get("REMOTE_ADDR", "")),
    )

    payload = build_apple_pkpass(share_token.card, share_token)
    response = HttpResponse(payload, content_type="application/vnd.apple.pkpass")
    response["Content-Disposition"] = f'attachment; filename="profile_card_{share_token.card.id}.pkpass"'
    return response


@require_GET
def public_google_wallet(request, token):
    if not check_rate_limit(request, bucket="public_wallet_google", limit=60, window_seconds=60):
        return security_response()

    share_token = _load_valid_token(token)
    ProfileCardPublicToken.objects.filter(pk=share_token.pk).update(wallet_add_count=F("wallet_add_count") + 1)
    ProfileCardEvent.objects.create(
        card=share_token.card,
        token=share_token,
        event_type=ProfileCardEvent.EVENT_ADD_WALLET,
        source="wallet_google",
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        ip_hash=build_ip_hash(request.META.get("REMOTE_ADDR", "")),
    )

    google_url = build_google_wallet_url(share_token)
    return redirect(google_url)


@require_http_methods(["POST"])
def public_submit_lead(request, token):
    if not check_rate_limit(request, bucket="public_lead", limit=5, window_seconds=600):
        return security_response()

    share_token = _load_valid_token(token)
    if not share_token.card.enable_lead_capture:
        return HttpResponseForbidden("Lead capture disabled")

    name = request.POST.get("name", "").strip()
    email = request.POST.get("email", "").strip()
    message = request.POST.get("message", "").strip()

    if not (name and email and message):
        return HttpResponse("Dati mancanti", status=400)

    lead = ProfileCardLead.objects.create(
        card=share_token.card,
        name=name,
        email=email,
        message=message
    )

    send_lead_notification_email(lead=lead)

    return HttpResponse("ok")


@require_GET
def public_track_event(request, token):
    if not check_rate_limit(request, bucket="public_event", limit=120, window_seconds=60):
        return security_response()

    event_type = request.GET.get("event", "").strip()
    if event_type not in {
        ProfileCardEvent.EVENT_SHARE,
        ProfileCardEvent.EVENT_ADD_WALLET,
        ProfileCardEvent.EVENT_VCARD,
    }:
        raise Http404("Evento non supportato")

    share_token = _load_valid_token(token)

    updates = {}
    if event_type == ProfileCardEvent.EVENT_SHARE:
        updates["share_count"] = F("share_count") + 1
    elif event_type == ProfileCardEvent.EVENT_ADD_WALLET:
        updates["wallet_add_count"] = F("wallet_add_count") + 1
    elif event_type == ProfileCardEvent.EVENT_VCARD:
        updates["vcard_download_count"] = F("vcard_download_count") + 1
    if updates:
        ProfileCardPublicToken.objects.filter(pk=share_token.pk).update(**updates)

    ProfileCardEvent.objects.create(
        card=share_token.card,
        token=share_token,
        event_type=event_type,
        source="tracking_pixel",
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        ip_hash=build_ip_hash(request.META.get("REMOTE_ADDR", "")),
    )
    return HttpResponse("ok")
