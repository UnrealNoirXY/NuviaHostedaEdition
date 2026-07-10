from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.contrib import messages
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Count, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.db.models import Sum, Avg
from datetime import datetime, timedelta, timezone as dt_timezone
import socket
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views import View
from django.views.decorators.http import require_GET, require_POST
from django.core.cache import cache

import random
import re
import hashlib
from uuid import uuid4

from resort.models import Resort, Room
from tickets.models import Ticket
from it_support.models import IT_Ticket
from assets.models import Asset
from reviews.models import Review, ReviewAnalysis
from accounts.models import User
from clients.models import Company
from documents.models import Document
from purchase_orders.models import Budget, PurchaseOrder, PurchaseCategory
from .forms import (
    UserForm,
    UserCreationForm,
    ResortForm,
    RoomForm,
    ReportFilterForm,
    ProfileAvatarForm,
    TwoFactorAuthForm,
    TwoFactorVerifyForm,
    UserFilterForm,
    UserProfileThemeForm,
    PasswordChangeOTPForm,
    AdminLogFilterForm,
    NuviaMailAccountForm,
    NuviaMailSignatureForm,
    NuviaMailTemplateForm,
    NuviaMailSendQueueForm,
    NuviaMailCompliancePolicyForm,
)
from .utils import themed_render, get_hub_tools
from .feature_flags import get_external_url
from .models import (
    PlatformSettings,
    TrustedDevice,
    InAppGuideAsset,
    AdminLogEntry,
    NuviaMailAccount,
    NuviaMailSignature,
    NuviaMailOnboardingEvent,
    NuviaMailTemplate,
    NuviaMailSendQueue,
    NuviaMailCompliancePolicy,
    NuviaMailFolder,
    NuviaMailThread,
    NuviaMailMessage,
)
from .decorators import role_required
from .nuvia_mail_service import process_send_queue_for_user
from .nuvia_mail_sync_service import sync_read_only_inbox_for_user
from .nuvia_mail_providers import get_provider_adapter
from competitors.models import Competitor, ScrapedData, CompetitorDataAnalysis
from accounts.models import PrivacyPolicyVersion, UserPrivacyConsent
from accounts.emails import send_privacy_confirmation_email

import csv
import json
import qrcode
import io
from django.core.paginator import Paginator
from openpyxl import Workbook
from weasyprint import HTML

# --- Main Views ---

DECOMMISSIONED_MODULES = {
    "menu": {
        "title": "Menu Creation Studio dismesso",
        "message": "Il generatore menu interno è stato scollegato perché ora viene gestito da un'applicazione esterna dedicata.",
        "external_setting": "EXTERNAL_MENU_URL",
    },
    "mail": {
        "title": "Nuvia Mail dismesso",
        "message": "Il client mail interno è stato scollegato. Restano attive solo le email transazionali di sistema.",
        "external_setting": "EXTERNAL_MAIL_URL",
    },
    "tickets": {
        "title": "Ticket interni dismessi",
        "message": "Il ticketing interno è stato scollegato perché la gestione richieste avviene su un sistema esterno.",
        "external_setting": "EXTERNAL_TICKETS_URL",
    },
}


@login_required
def decommissioned_module_view(request, module="tickets"):
    """Show a controlled fallback or redirect for decommissioned modules."""
    config = DECOMMISSIONED_MODULES.get(module, DECOMMISSIONED_MODULES["tickets"])
    external_url = get_external_url(config["external_setting"])
    if external_url:
        return redirect(external_url)
    response = themed_render(
        request,
        "core/decommissioned_module.html",
        {
            "module_title": config["title"],
            "module_message": config["message"],
        },
    )
    response.status_code = 410
    return response

def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _create_admin_log(user, action_type, request, description="", extra=None):
    extra_payload = {"user_agent": request.META.get("HTTP_USER_AGENT", "")}
    if extra:
        extra_payload.update(extra)
    AdminLogEntry.objects.create(
        user=user,
        action_type=action_type,
        ip_address=_get_client_ip(request),
        description=description,
        extra=extra_payload,
    )


def _styled_password_change_form(user, data=None):
    form = SetPasswordForm(user, data=data)
    for fieldname in form.fields:
        form.fields[fieldname].widget.attrs = {'class': 'form-control'}
    return form


def _styled_password_change_otp_form(data=None):
    form = PasswordChangeOTPForm(data=data)
    for fieldname in form.fields:
        form.fields[fieldname].widget.attrs = {'class': 'form-control'}
    return form


def _render_login(request, **context):
    return themed_render(request, 'core/login.html', context)


def landing_page_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return themed_render(request, 'core/landing_page.html')

def privacy_policy_view(request):
    try:
        policy = (
            PrivacyPolicyVersion.objects.filter(is_active=True)
            .order_by("-published_at", "-created_at")
            .first()
        )
    except (OperationalError, ProgrammingError):
        policy = None
    return themed_render(request, "core/privacy_policy.html", {"policy": policy})


def privacy_consent_confirm_view(request, token):
    signer = TimestampSigner(salt="privacy-consent")
    max_age_seconds = getattr(settings, "PRIVACY_CONSENT_TOKEN_MAX_AGE", 60 * 60 * 24 * 7)

    def render_privacy_status(status, policy=None):
        context = {
            "status": status,
            "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "supporto@localhost"),
        }
        if policy is not None:
            context["policy"] = policy
        return themed_render(request, "core/privacy_confirm.html", context)

    try:
        user_id = signer.unsign(token, max_age=max_age_seconds)
    except SignatureExpired:
        return render_privacy_status("expired")
    except BadSignature:
        return render_privacy_status("invalid")

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return render_privacy_status("invalid")

    try:
        policy = (
            PrivacyPolicyVersion.objects.filter(is_active=True)
            .order_by("-published_at", "-created_at")
            .first()
        )
    except (OperationalError, ProgrammingError):
        return render_privacy_status("unavailable")
    if not policy:
        return render_privacy_status("missing_policy")

    if request.method != "POST":
        return themed_render(
            request,
            "core/privacy_accept.html",
            {
                "policy": policy,
                "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "supporto@localhost"),
                "error": None,
            },
        )

    if not request.POST.get("accept_policy"):
        return themed_render(
            request,
            "core/privacy_accept.html",
            {
                "policy": policy,
                "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "supporto@localhost"),
                "error": "Seleziona la checkbox per confermare di aver letto e accettato la policy.",
            },
        )

    now = timezone.now()
    try:
        consent, created = UserPrivacyConsent.objects.get_or_create(
            user=user,
            policy_version=policy,
            defaults={
                "accepted_at": now,
                "payslip_email_opt_in": True,
                "payslip_email_opt_in_at": now,
            },
        )
    except (OperationalError, ProgrammingError):
        return render_privacy_status("unavailable")
    if not created:
        consent.accepted_at = now
        if not consent.payslip_email_opt_in:
            consent.payslip_email_opt_in = True
            consent.payslip_email_opt_in_at = now
        consent.save(
            update_fields=[
                "accepted_at",
                "payslip_email_opt_in",
                "payslip_email_opt_in_at",
                "updated_at",
            ]
        )
    if not consent.email_confirmed_at:
        consent.email_confirmed_at = now
        consent.save(update_fields=["email_confirmed_at", "updated_at"])
    if not getattr(user, "must_change_password", False):
        user.must_change_password = True
        user.save(update_fields=["must_change_password"])

    return render_privacy_status("confirmed", policy=policy)

@login_required
def home(request):
    context = {
        'tools': get_hub_tools(request.user),
    }
    return themed_render(request, 'core/hub.html', context)



def _split_csv_values(value):
    return [entry.strip().lower() for entry in (value or '').split(',') if entry.strip()]


def _evaluate_nuvia_mail_compliance(queue_item, policy):
    recipient = (queue_item.to_email or '').strip().lower()
    recipient_domain = recipient.split('@')[-1] if '@' in recipient else ''
    allowed_domains = set(_split_csv_values(policy.allowed_domains))
    blocked_domains = set(_split_csv_values(policy.blocked_domains))
    blocked_recipients = set(_split_csv_values(policy.blocked_recipients))
    sensitive_keywords = _split_csv_values(policy.sensitive_keywords)
    regex_patterns = [p for p in _split_csv_values(policy.sensitive_regex_patterns) if p]

    body_content = f"{queue_item.subject} {queue_item.body}".lower()

    if recipient in blocked_recipients:
        return NuviaMailSendQueue.STATUS_FAILED, True, f'Destinatario bloccato dalla policy: {recipient}'

    if recipient_domain and recipient_domain in blocked_domains:
        return NuviaMailSendQueue.STATUS_FAILED, True, f'Dominio destinatario bloccato dalla policy: {recipient_domain}'

    if policy.enforce_external_domain_block and allowed_domains and recipient_domain not in allowed_domains:
        return NuviaMailSendQueue.STATUS_FAILED, True, f'Dominio destinatario non consentito: {recipient_domain}'

    keyword_match = any(keyword in body_content for keyword in sensitive_keywords)
    regex_match = False
    for pattern in regex_patterns:
        try:
            if re.search(pattern, queue_item.subject or '', flags=re.IGNORECASE) or re.search(pattern, queue_item.body or '', flags=re.IGNORECASE):
                regex_match = True
                break
        except re.error:
            continue

    if keyword_match or regex_match:
        reason = 'Contenuto potenzialmente sensibile rilevato dalla policy.'
        if policy.flagged_action == NuviaMailCompliancePolicy.ACTION_MARK_FAILED:
            return NuviaMailSendQueue.STATUS_FAILED, True, reason
        return NuviaMailSendQueue.STATUS_PENDING_APPROVAL, True, reason

    return NuviaMailSendQueue.STATUS_QUEUED, False, ''




def _nuvia_oauth_state_key(user_id, provider):
    return f'nuvia-mail:oauth:state:{user_id}:{provider}'


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _mask_secret(secret):
    value = (secret or '').strip()
    if len(value) <= 8:
        return '*' * len(value)
    return f"{value[:4]}...{value[-4:]}"

def _build_nuvia_queue_analytics(user):
    queue_stats = NuviaMailSendQueue.objects.filter(user=user).values('status').annotate(total=Count('id'))
    queue_summary = {item['status']: item['total'] for item in queue_stats}
    return {
        'queued': queue_summary.get(NuviaMailSendQueue.STATUS_QUEUED, 0),
        'sent': queue_summary.get(NuviaMailSendQueue.STATUS_SENT, 0),
        'failed': queue_summary.get(NuviaMailSendQueue.STATUS_FAILED, 0),
        'pending_approval': queue_summary.get(NuviaMailSendQueue.STATUS_PENDING_APPROVAL, 0),
        'flagged': NuviaMailSendQueue.objects.filter(user=user, compliance_flagged=True).count(),
    }

@login_required
def nuvia_mail_landing_view(request):
    mail_account = NuviaMailAccount.objects.filter(user=request.user, is_active=True).order_by('-updated_at').first()

    if request.method == 'POST' or request.GET.get('legacy'):
        return _nuvia_mail_legacy_view(request, mail_account)

    context = {
        'mail_account': mail_account,
        'user': request.user,
    }
    return render(request, 'core/nuvia_mail_workspace.html', context)


def _nuvia_mail_legacy_view(request, mail_account):
    setup_steps = [
        {
            'title': 'Scegli il provider della tua email aziendale',
            'description': 'Seleziona Gmail Workspace, Microsoft 365 o IMAP/SMTP standard per avviare la procedura guidata.',
        },
        {
            'title': 'Inserisci parametri di configurazione',
            'description': 'Compila host IMAP, porta, sicurezza TLS/SSL, host SMTP e credenziali o password app dove richiesto.',
        },
        {
            'title': 'Verifica connessione e sincronizzazione',
            'description': 'Esegui un test di connessione: Nuvia Mail controlla accesso inbox, invio SMTP e cartelle base.',
        },
        {
            'title': 'Attiva firma e preferenze',
            'description': 'Configura firma professionale, orari di notifica, filtri rapidi e modalità mobile.',
        },
    ]

    mail_account = NuviaMailAccount.objects.filter(user=request.user, is_active=True).order_by('-updated_at').first()
    signature = NuviaMailSignature.objects.filter(user=request.user).order_by('-is_default', '-updated_at').first()

    account_form = NuviaMailAccountForm(instance=mail_account)
    signature_form = NuviaMailSignatureForm(instance=signature)
    template_form = NuviaMailTemplateForm()
    queue_form = NuviaMailSendQueueForm()
    policy, _ = NuviaMailCompliancePolicy.objects.get_or_create(user=request.user)
    policy_form = NuviaMailCompliancePolicyForm(instance=policy)
    templates = NuviaMailTemplate.objects.filter(user=request.user, is_active=True).order_by('name')
    queue_items = NuviaMailSendQueue.objects.filter(user=request.user).order_by('-created_at')[:5]

    selected_template_id = request.GET.get('template')
    if selected_template_id:
        selected_template = templates.filter(pk=selected_template_id).first()
        if selected_template:
            queue_form = NuviaMailSendQueueForm(initial={
                'subject': selected_template.subject,
                'body': selected_template.body,
            })

    NuviaMailOnboardingEvent.objects.create(
        user=request.user,
        event_type=NuviaMailOnboardingEvent.EVENT_LANDING_VISIT,
        metadata={'path': request.path},
    )

    analytics = _build_nuvia_queue_analytics(request.user)
    analytics['templates'] = templates.count()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action in {'save_account', 'test_connection'}:
            account_form = NuviaMailAccountForm(request.POST, instance=mail_account)
            if account_form.is_valid():
                account = account_form.save(commit=False)
                account.user = request.user
                if not account.username:
                    account.username = account.email_address

                # Handle password if provided for IMAP
                raw_password = request.POST.get('password_raw')
                if raw_password:
                    account.set_password(raw_password)

                if action == 'test_connection':
                    hosts_to_check = [host for host in [account.imap_host, account.smtp_host] if host]
                    connection_ok = True
                    failing_host = ''
                    for host in hosts_to_check:
                        try:
                            socket.create_connection((host, 443), timeout=4).close()
                        except OSError:
                            connection_ok = False
                            failing_host = host
                            break

                    account.last_test_at = timezone.now()
                    if connection_ok:
                        account.last_test_status = 'ok'
                        account.last_test_message = 'Connessione di rete ai server verificata. Test applicativo completo in Fase 2.'
                        messages.success(request, 'Test preliminare completato: host raggiungibili. Procedi con il salvataggio account.')
                    else:
                        account.last_test_status = 'failed'
                        account.last_test_message = f'Host non raggiungibile: {failing_host}. Verifica parametri IMAP/SMTP con il team IT.'
                        messages.error(request, account.last_test_message)

                    NuviaMailOnboardingEvent.objects.create(
                        user=request.user,
                        event_type=NuviaMailOnboardingEvent.EVENT_CONNECTION_TESTED,
                        metadata={'status': account.last_test_status, 'provider': account.provider},
                    )
                else:
                    messages.success(request, 'Configurazione account Nuvia Mail salvata con successo.')
                    NuviaMailOnboardingEvent.objects.create(
                        user=request.user,
                        event_type=NuviaMailOnboardingEvent.EVENT_ACCOUNT_SAVED,
                        metadata={'provider': account.provider},
                    )

                account.save()
                return redirect('core:nuvia_mail')
            messages.error(request, 'Controlla i campi account evidenziati e riprova.')

        elif action == 'save_signature':
            signature_form = NuviaMailSignatureForm(request.POST, instance=signature)
            if signature_form.is_valid():
                signature_obj = signature_form.save(commit=False)
                signature_obj.user = request.user
                signature_obj.account = mail_account
                signature_obj.save()

                if signature_obj.is_default:
                    NuviaMailSignature.objects.filter(user=request.user).exclude(pk=signature_obj.pk).update(is_default=False)

                NuviaMailOnboardingEvent.objects.create(
                    user=request.user,
                    event_type=NuviaMailOnboardingEvent.EVENT_SIGNATURE_SAVED,
                    metadata={'name': signature_obj.name, 'is_default': signature_obj.is_default},
                )
                messages.success(request, 'Firma email salvata correttamente.')
                return redirect('core:nuvia_mail')
            messages.error(request, 'Controlla i campi firma e riprova.')

        elif action == 'save_template':
            template_form = NuviaMailTemplateForm(request.POST)
            if template_form.is_valid():
                template = template_form.save(commit=False)
                template.user = request.user
                template.save()
                messages.success(request, 'Template email salvato.')
                return redirect('core:nuvia_mail')
            messages.error(request, 'Controlla i campi template e riprova.')

        elif action == 'process_queue_now':
            result = process_send_queue_for_user(request.user, limit=20)
            NuviaMailOnboardingEvent.objects.create(
                user=request.user,
                event_type=NuviaMailOnboardingEvent.EVENT_QUEUE_PROCESSED,
                metadata=result,
            )
            if result['sent']:
                messages.success(request, f"Coda elaborata: {result['sent']} invio/i completati.")
            elif result['failed']:
                messages.error(request, f"Coda elaborata con errori: {result['failed']} invio/i falliti.")
            else:
                messages.info(request, 'Nessuna email pronta da processare in questo momento.')
            return redirect('core:nuvia_mail')

        elif action == 'retry_failed_item':
            item_id = request.POST.get('queue_item_id')
            item = NuviaMailSendQueue.objects.filter(pk=item_id, user=request.user).first()
            if not item:
                messages.error(request, 'Elemento coda non trovato.')
                return redirect('core:nuvia_mail')
            if item.status == NuviaMailSendQueue.STATUS_PENDING_APPROVAL:
                messages.error(request, 'Elemento in attesa approvazione: approva prima dalla API dedicata.')
                return redirect('core:nuvia_mail')
            item.status = NuviaMailSendQueue.STATUS_QUEUED
            item.error_message = ''
            item.save(update_fields=['status', 'error_message'])
            messages.success(request, 'Elemento reinserito in coda per nuovo tentativo.')
            return redirect('core:nuvia_mail')

        elif action == 'save_policy':
            policy_form = NuviaMailCompliancePolicyForm(request.POST, instance=policy)
            if policy_form.is_valid():
                policy_form.save()
                messages.success(request, 'Policy compliance aggiornata.')
                return redirect('core:nuvia_mail')
            messages.error(request, 'Controlla i campi policy e riprova.')

        elif action == 'queue_email':
            queue_form = NuviaMailSendQueueForm(request.POST)
            if queue_form.is_valid():
                queue_item = queue_form.save(commit=False)
                queue_item.user = request.user
                queue_item.account = mail_account
                status, flagged, reason = _evaluate_nuvia_mail_compliance(queue_item, policy)
                queue_item.status = status
                queue_item.compliance_flagged = flagged
                queue_item.compliance_reason = reason
                queue_item.error_message = reason if status == NuviaMailSendQueue.STATUS_FAILED else ''

                queue_item.save()
                NuviaMailOnboardingEvent.objects.create(
                    user=request.user,
                    event_type=NuviaMailOnboardingEvent.EVENT_QUEUE_ITEM_CREATED,
                    metadata={'to': queue_item.to_email, 'scheduled': bool(queue_item.scheduled_for), 'flagged': queue_item.compliance_flagged},
                )

                if queue_item.status == NuviaMailSendQueue.STATUS_FAILED:
                    messages.error(request, f'Invio bloccato dalla policy: {queue_item.compliance_reason}')
                elif queue_item.status == NuviaMailSendQueue.STATUS_PENDING_APPROVAL:
                    messages.warning(request, 'Email in quarantena compliance: richiede approvazione prima dell’invio.')
                elif queue_item.compliance_flagged:
                    messages.warning(request, 'Email in coda con flag compliance: verifica prima dell’invio definitivo.')
                else:
                    messages.success(request, 'Email inserita in coda invio.')
                return redirect('core:nuvia_mail')
            messages.error(request, 'Controlla i campi composizione e riprova.')

    context = {
        'setup_steps': setup_steps,
        'account_form': account_form,
        'signature_form': signature_form,
        'mail_account': mail_account,
        'template_form': template_form,
        'queue_form': queue_form,
        'templates': templates,
        'queue_items': queue_items,
        'policy_form': policy_form,
        'analytics': analytics,
    }
    return themed_render(request, 'core/nuvia_mail_landing.html', context)


@login_required
@require_GET
def nuvia_mail_provider_status_api(request):
    mail_account = NuviaMailAccount.objects.filter(user=request.user, is_active=True).order_by('-updated_at').first()
    active_provider = mail_account.provider if mail_account else NuviaMailAccount.PROVIDER_IMAP

    providers = [
        {'key': NuviaMailAccount.PROVIDER_IMAP, 'label': 'IMAP/SMTP', 'ready': True},
        {'key': NuviaMailAccount.PROVIDER_GOOGLE, 'label': 'Google Workspace', 'ready': False},
        {'key': NuviaMailAccount.PROVIDER_MICROSOFT, 'label': 'Microsoft 365', 'ready': False},
    ]

    return JsonResponse({
        'active_provider': active_provider,
        'providers': providers,
        'phase': 'phase6-foundation',
    })


NUVIA_MAIL_PROVIDER_PRESETS = {
    NuviaMailAccount.PROVIDER_GOOGLE: {
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_ssl': True,
        'use_starttls': True,
        'auth_modes': [NuviaMailAccount.AUTH_OAUTH, NuviaMailAccount.AUTH_APP_PASSWORD],
    },
    NuviaMailAccount.PROVIDER_MICROSOFT: {
        'imap_host': 'outlook.office365.com',
        'imap_port': 993,
        'smtp_host': 'smtp.office365.com',
        'smtp_port': 587,
        'use_ssl': True,
        'use_starttls': True,
        'auth_modes': [NuviaMailAccount.AUTH_OAUTH, NuviaMailAccount.AUTH_APP_PASSWORD],
    },
    NuviaMailAccount.PROVIDER_IMAP: {
        'imap_host': '',
        'imap_port': 993,
        'smtp_host': '',
        'smtp_port': 587,
        'use_ssl': True,
        'use_starttls': True,
        'auth_modes': [NuviaMailAccount.AUTH_PASSWORD, NuviaMailAccount.AUTH_APP_PASSWORD],
    },
}


def _nuvia_mail_test_rate_limit_key(user_id):
    return f'nuvia-mail:test-connection:{user_id}'


@login_required
@require_GET
def nuvia_mail_provider_presets_api(request):
    email = request.GET.get('email', '').lower()
    presets = NUVIA_MAIL_PROVIDER_PRESETS.copy()

    # Simple auto-discovery based on domain
    suggested = None
    if '@' in email:
        domain = email.split('@')[-1]
        if domain in ['gmail.com', 'googlemail.com']:
            suggested = NuviaMailAccount.PROVIDER_GOOGLE
        elif domain in ['outlook.com', 'hotmail.com', 'live.com', 'office365.com']:
            suggested = NuviaMailAccount.PROVIDER_MICROSOFT

    return JsonResponse({
        'presets': presets,
        'suggested_provider': suggested
    })


@login_required
@require_POST
def nuvia_mail_test_connection_api(request):
    rate_key = _nuvia_mail_test_rate_limit_key(request.user.pk)
    if cache.get(rate_key):
        return JsonResponse(
            {'ok': False, 'error': 'Troppi test consecutivi. Attendi qualche secondo e riprova.'},
            status=429,
        )

    cache.set(rate_key, True, timeout=10)

    # We use the existing account if it exists, otherwise a temporary one
    instance = NuviaMailAccount.objects.filter(user=request.user, is_active=True).first()
    form = NuviaMailAccountForm(request.POST, instance=instance)

    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    # We don't save yet, just test
    account = form.save(commit=False)
    account.user = request.user

    # Handle password
    password_raw = request.POST.get('password_raw')
    if password_raw:
        account.set_password(password_raw)
    elif instance and not password_raw:
        # Keep old password if not provided
        account.encrypted_password = instance.encrypted_password

    account.last_test_at = timezone.now()

    try:
        from .nuvia_mail_providers import get_provider_adapter
        adapter = get_provider_adapter(account)
        adapter.test_authentication()
        account.last_test_status = 'ok'
        account.last_test_message = 'Autenticazione IMAP/SMTP completata con successo.'
    except Exception as e:
        account.last_test_status = 'failed'
        account.last_test_message = str(e)

    NuviaMailOnboardingEvent.objects.create(
        user=request.user,
        event_type=NuviaMailOnboardingEvent.EVENT_CONNECTION_TESTED,
        metadata={
            'status': account.last_test_status,
            'provider': account.provider,
            'message': account.last_test_message,
        },
    )

    return JsonResponse(
        {
            'ok': account.last_test_status == 'ok',
            'last_test_status': account.last_test_status,
            'last_test_message': account.last_test_message,
        }
    )


@login_required
@require_POST
def nuvia_mail_save_account_api(request):
    account = NuviaMailAccount.objects.filter(user=request.user, is_active=True).order_by('-updated_at').first()
    form = NuviaMailAccountForm(request.POST, instance=account)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    password_raw = request.POST.get('password_raw')
    account = form.save(commit=False)
    account.user = request.user
    if password_raw:
        account.set_password(password_raw)

    if not account.username:
        account.username = account.email_address
    account.save()

    NuviaMailOnboardingEvent.objects.create(
        user=request.user,
        event_type=NuviaMailOnboardingEvent.EVENT_ACCOUNT_SAVED,
        metadata={'provider': account.provider, 'email': account.email_address},
    )
    return JsonResponse({'ok': True, 'account_id': account.pk, 'email_address': account.email_address})



@login_required
@require_GET
def nuvia_mail_queue_list_api(request):
    items = list(
        NuviaMailSendQueue.objects.filter(user=request.user)
        .order_by('-created_at')[:50]
        .values('id', 'to_email', 'subject', 'status', 'compliance_flagged', 'compliance_reason', 'retry_count', 'created_at')
    )
    return JsonResponse({'items': items})


@login_required
@require_POST
def nuvia_mail_compliance_preview_api(request):
    policy, _ = NuviaMailCompliancePolicy.objects.get_or_create(user=request.user)

    to_email = (request.POST.get('to_email') or '').strip()
    subject = (request.POST.get('subject') or '').strip()
    body = (request.POST.get('body') or '').strip()
    if not to_email:
        return JsonResponse({'ok': False, 'error': 'to_email è obbligatorio.'}, status=400)

    preview_item = NuviaMailSendQueue(
        user=request.user,
        to_email=to_email,
        subject=subject,
        body=body,
    )
    status, flagged, reason = _evaluate_nuvia_mail_compliance(preview_item, policy)
    return JsonResponse(
        {
            'ok': True,
            'status': status,
            'compliance_flagged': flagged,
            'compliance_reason': reason,
        }
    )


@login_required
@require_POST
def nuvia_mail_approve_queue_item_api(request, item_id):
    item = NuviaMailSendQueue.objects.filter(pk=item_id, user=request.user).first()
    if not item:
        return JsonResponse({'ok': False, 'error': 'Elemento coda non trovato.'}, status=404)

    if item.status != NuviaMailSendQueue.STATUS_PENDING_APPROVAL:
        return JsonResponse({'ok': False, 'error': 'Elemento non in stato pending approval.'}, status=400)

    item.status = NuviaMailSendQueue.STATUS_QUEUED
    item.error_message = ''
    item.save(update_fields=['status', 'error_message'])
    NuviaMailOnboardingEvent.objects.create(
        user=request.user,
        event_type=NuviaMailOnboardingEvent.EVENT_QUEUE_ITEM_APPROVED,
        metadata={'approved_item_id': item.id},
    )
    return JsonResponse({'ok': True, 'item_id': item.id, 'status': item.status})


@login_required
@require_POST
def nuvia_mail_reject_queue_item_api(request, item_id):
    item = NuviaMailSendQueue.objects.filter(pk=item_id, user=request.user).first()
    if not item:
        return JsonResponse({'ok': False, 'error': 'Elemento coda non trovato.'}, status=404)

    if item.status != NuviaMailSendQueue.STATUS_PENDING_APPROVAL:
        return JsonResponse({'ok': False, 'error': 'Elemento non in stato pending approval.'}, status=400)

    reason = (request.POST.get('reason') or '').strip() or 'Rifiutato in fase di approvazione.'
    item.status = NuviaMailSendQueue.STATUS_FAILED
    item.error_message = reason[:255]
    item.compliance_reason = reason[:255]
    item.save(update_fields=['status', 'error_message', 'compliance_reason'])
    NuviaMailOnboardingEvent.objects.create(
        user=request.user,
        event_type=NuviaMailOnboardingEvent.EVENT_QUEUE_ITEM_REJECTED,
        metadata={'rejected_item_id': item.id},
    )
    return JsonResponse({'ok': True, 'item_id': item.id, 'status': item.status})


@login_required
@require_GET
def nuvia_mail_queue_analytics_api(request):
    return JsonResponse({'ok': True, 'analytics': _build_nuvia_queue_analytics(request.user)})


@login_required
@require_POST
def nuvia_mail_account_connect_api(request):
    account = NuviaMailAccount.objects.filter(user=request.user, is_active=True).order_by('-updated_at').first()
    if not account:
        return JsonResponse({'ok': False, 'error': 'Configura prima un account attivo.'}, status=400)

    adapter = get_provider_adapter(account)
    state = uuid4().hex
    try:
        authorize_url = adapter.authorize_url(state=state)
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    cache.set(_nuvia_oauth_state_key(request.user.pk, account.provider), state, timeout=600)
    return JsonResponse({'ok': True, 'provider': account.provider, 'state': state, 'authorize_url': authorize_url})



@login_required
@require_POST
def nuvia_mail_oauth_callback_api(request):
    account = NuviaMailAccount.objects.filter(user=request.user, is_active=True).order_by('-updated_at').first()
    if not account:
        return JsonResponse({'ok': False, 'error': 'Configura prima un account attivo.'}, status=400)

    state = (request.POST.get('state') or '').strip()
    code = (request.POST.get('code') or '').strip()
    if not state or not code:
        return JsonResponse({'ok': False, 'error': 'state e code sono obbligatori.'}, status=400)

    cache_key = _nuvia_oauth_state_key(request.user.pk, account.provider)
    expected_state = cache.get(cache_key)
    if not expected_state or state != expected_state:
        return JsonResponse({'ok': False, 'error': 'OAuth state non valido o scaduto.'}, status=400)

    adapter = get_provider_adapter(account)
    try:
        token_result = adapter.exchange_code(code=code)
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    account.set_oauth_tokens(token_result.access_token, token_result.refresh_token)
    account.oauth_access_token_masked = _mask_secret(token_result.access_token)
    account.oauth_refresh_token_masked = _mask_secret(token_result.refresh_token)
    account.oauth_token_expires_at = token_result.expires_at
    account.oauth_connected_at = timezone.now()
    account.save(update_fields=[
        'encrypted_oauth_access_token',
        'encrypted_oauth_refresh_token',
        'oauth_access_token_masked',
        'oauth_refresh_token_masked',
        'oauth_token_expires_at',
        'oauth_connected_at',
        'updated_at',
    ])
    cache.delete(cache_key)

    NuviaMailOnboardingEvent.objects.create(
        user=request.user,
        event_type=NuviaMailOnboardingEvent.EVENT_ACCOUNT_SAVED,
        metadata={'provider': account.provider, 'oauth_connected': True},
    )
    return JsonResponse({'ok': True, 'provider': account.provider, 'oauth_connected_at': account.oauth_connected_at})

@login_required
@require_POST
def nuvia_mail_sync_run_api(request):
    result = sync_read_only_inbox_for_user(request.user)
    return JsonResponse({'ok': True, 'result': result})


@login_required
@require_GET
def nuvia_mail_folders_api(request):
    folders = list(
        NuviaMailFolder.objects.filter(user=request.user)
        .order_by('name')
        .values('id', 'account_id', 'provider_folder_id', 'name', 'is_inbox', 'is_sent', 'updated_at')
    )
    return JsonResponse({'ok': True, 'folders': folders})


@login_required
@require_GET
def nuvia_mail_threads_api(request):
    folder_id = request.GET.get('folder_id')
    limit = max(1, min(_safe_int(request.GET.get('limit'), 100), 200))
    offset = max(0, _safe_int(request.GET.get('offset'), 0))
    queryset = NuviaMailThread.objects.filter(user=request.user)
    if folder_id:
        queryset = queryset.filter(folder_id=folder_id)
    threads = list(
        queryset.order_by('-last_message_at', '-updated_at')[offset:offset + limit]
        .values('id', 'folder_id', 'provider_thread_id', 'subject', 'last_message_at', 'updated_at')
    )
    return JsonResponse({'ok': True, 'threads': threads})


@login_required
@require_GET
def nuvia_mail_thread_detail_api(request, thread_id):
    thread = NuviaMailThread.objects.filter(pk=thread_id, user=request.user).first()
    if not thread:
        return JsonResponse({'ok': False, 'error': 'Thread non trovato.'}, status=404)

    limit = max(1, min(_safe_int(request.GET.get('limit'), 100), 500))
    offset = max(0, _safe_int(request.GET.get('offset'), 0))

    messages = list(
        NuviaMailMessage.objects.filter(thread=thread, user=request.user)
        .order_by('received_at', 'created_at')[offset:offset + limit]
        .values(
            'id',
            'provider_message_id',
            'from_email',
            'to_emails',
            'cc_emails',
            'subject',
            'body_text',
            'body_html',
            'received_at',
        )
    )
    return JsonResponse(
        {
            'ok': True,
            'thread': {
                'id': thread.id,
                'folder_id': thread.folder_id,
                'subject': thread.subject,
                'last_message_at': thread.last_message_at,
            },
            'messages': messages,
        }
    )

@login_required
@require_POST
def nuvia_mail_process_queue_api(request):
    result = process_send_queue_for_user(request.user, limit=20)
    return JsonResponse({'ok': True, 'result': result})

def login_view(request):
    pending_user_id = request.session.get("password_change_user_id")
    otp_hash = request.session.get("password_change_otp_hash")
    otp_user_id = request.session.get("password_change_otp_user_id")
    otp_expiry = request.session.get("password_change_otp_expiry")

    if request.method == 'POST':
        step = request.POST.get('step', 'login')

        if step == "change_password":
            user = User.objects.filter(pk=pending_user_id).first()
            if not user:
                messages.error(request, "Sessione scaduta. Effettua nuovamente il login.")
                request.session.pop("password_change_user_id", None)
                return _render_login(request, step="login")

            password_form = _styled_password_change_form(user, data=request.POST)
            if password_form.is_valid():
                password_form.save()

                otp_code = str(random.randint(100000, 999999))
                otp_hash_value = hashlib.sha256(otp_code.encode()).hexdigest()
                request.session['password_change_otp_hash'] = otp_hash_value
                request.session['password_change_otp_user_id'] = user.id
                request.session['password_change_otp_expiry'] = (
                    datetime.now(dt_timezone.utc) + timedelta(minutes=10)
                ).isoformat()

                context = {
                    'user': user,
                    'code': otp_code,
                    'site_name': getattr(
                        settings,
                        "SITE_NAME",
                        settings.JAZZMIN_SETTINGS.get("site_brand", ""),
                    ),
                }
                html_message = render_to_string('core/emails/password_change_otp.html', context)
                plain_message = strip_tags(html_message)
                send_mail(
                    subject=(
                        "Codice OTP per conferma cambio password - "
                        f"{getattr(settings, 'SITE_NAME', settings.JAZZMIN_SETTINGS.get('site_brand', ''))}"
                    ),
                    message=plain_message,
                    html_message=html_message,
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.info(request, "Ti abbiamo inviato un codice OTP via email.")
                otp_form = _styled_password_change_otp_form()
                return _render_login(
                    request,
                    step="otp",
                    otp_form=otp_form,
                )
            return _render_login(
                request,
                step="change_password",
                password_form=password_form,
            )

        if step == "otp":
            if not otp_hash or not otp_user_id or not otp_expiry:
                messages.error(request, "Sessione OTP non valida. Effettua nuovamente il login.")
                request.session.pop("password_change_user_id", None)
                return _render_login(request, step="login")

            try:
                expiry_time = datetime.fromisoformat(otp_expiry)
            except ValueError:
                expiry_time = datetime.now(dt_timezone.utc)

            if datetime.now(dt_timezone.utc) > expiry_time:
                messages.error(request, "Il codice OTP è scaduto. Effettua nuovamente il login.")
                for key in [
                    'password_change_otp_hash',
                    'password_change_otp_user_id',
                    'password_change_otp_expiry',
                ]:
                    request.session.pop(key, None)
                request.session.pop("password_change_user_id", None)
                return _render_login(request, step="login")

            otp_form = _styled_password_change_otp_form(data=request.POST)
            if otp_form.is_valid():
                entered_code_hash = hashlib.sha256(
                    otp_form.cleaned_data['code'].encode()
                ).hexdigest()
                if entered_code_hash == otp_hash and otp_user_id == pending_user_id:
                    user = User.objects.filter(pk=otp_user_id).first()
                    if not user:
                        messages.error(request, "Utente non trovato. Effettua nuovamente il login.")
                        return _render_login(request, step="login")

                    user.must_change_password = False
                    user.save(update_fields=["must_change_password"])
                    for key in [
                        'password_change_otp_hash',
                        'password_change_otp_user_id',
                        'password_change_otp_expiry',
                        'password_change_user_id',
                    ]:
                        request.session.pop(key, None)
                    login(request, user)
                    _create_admin_log(
                        user,
                        AdminLogEntry.PASSWORD_CHANGE,
                        request,
                        description="Cambio password confermato tramite OTP.",
                    )
                    _create_admin_log(
                        user,
                        AdminLogEntry.ACCESS,
                        request,
                        description="Accesso completato dopo cambio password obbligatorio.",
                    )
                    messages.success(request, "Password aggiornata e confermata con successo.")
                    response = redirect('home')
                    if request.session.pop("remember_device_after_password_change", False):
                        token = TrustedDevice.generate_token()
                        TrustedDevice.objects.create(user=user, token=token)
                        response.set_signed_cookie(
                            'trusted_device',
                            token,
                            salt='trusted-device-salt',
                            max_age=timedelta(days=30).total_seconds(),
                            httponly=True, # Prevent JS access
                            secure=not settings.DEBUG # Use secure cookies in production
                        )
                    return response
                messages.error(request, "Codice OTP non valido.")
            return _render_login(
                request,
                step="otp",
                otp_form=otp_form,
            )

        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                active_policy = (
                    PrivacyPolicyVersion.objects.filter(is_active=True)
                    .order_by("-published_at", "-created_at")
                    .first()
                )
            except (OperationalError, ProgrammingError):
                messages.error(request, "Servizio temporaneamente non disponibile. Riprova più tardi.")
                return _render_login(request, error='Servizio non disponibile.', step="login")
            if not active_policy:
                messages.error(request, "Policy privacy non disponibile. Contatta l'assistenza.")
                return _render_login(request, error='Policy non disponibile.', step="login")

            consent = (
                UserPrivacyConsent.objects.filter(user=user, policy_version=active_policy)
                .order_by("-accepted_at")
                .first()
            )
            if not consent or not consent.email_confirmed_at:
                messages.error(
                    request,
                    "Devi confermare la tua email e accettare la privacy prima di accedere.",
                )
                return _render_login(
                    request,
                    error='Conferma privacy richiesta.',
                    privacy_resend_username=username,
                    step="login",
                )

            if user.is_2fa_enabled:
                # Check for a trusted device cookie
                trusted_token = request.get_signed_cookie('trusted_device', default=None, salt='trusted-device-salt')
                if trusted_token:
                    try:
                        trusted_device = TrustedDevice.objects.get(user=user, token=trusted_token)
                        # Check if the token is still valid (within 30 days)
                        if (timezone.now() - trusted_device.created_at) < timedelta(days=30):
                            if getattr(user, "must_change_password", False):
                                request.session['password_change_user_id'] = user.id
                                messages.warning(
                                    request,
                                    "Per motivi di sicurezza devi cambiare la password al primo accesso.",
                                )
                                password_form = _styled_password_change_form(user)
                                return _render_login(
                                    request,
                                    step="change_password",
                                    password_form=password_form,
                                )
                            login(request, user)
                            _create_admin_log(
                                user,
                                AdminLogEntry.ACCESS,
                                request,
                                description="Accesso effettuato tramite dispositivo fidato.",
                            )
                            return redirect('home')
                        else:
                            # Token has expired, delete it and proceed with 2FA
                            trusted_device.delete()
                    except TrustedDevice.DoesNotExist:
                        # Token is invalid, just proceed with 2FA
                        pass

                # User has 2FA enabled, start the verification process
                code = str(random.randint(100000, 999999))

                # Store hash of the code and user_id in session
                request.session['2fa_code_hash'] = hashlib.sha256(code.encode()).hexdigest()
                request.session['2fa_user_id'] = user.id
                request.session['2fa_expiry'] = (datetime.now(dt_timezone.utc) + timedelta(minutes=5)).isoformat()
                request.session['force_password_change'] = bool(getattr(user, "must_change_password", False))

                # Send code to user's email
                try:
                    context = {
                        'user': user,
                        'code': code,
                        'site_name': getattr(
                            settings,
                            "SITE_NAME",
                            settings.JAZZMIN_SETTINGS.get("site_brand", ""),
                        ),
                    }
                    html_message = render_to_string('core/2fa_code_email.html', context)
                    plain_message = strip_tags(html_message)

                    send_mail(
                        subject=(
                            "Il tuo codice di verifica per l'accesso - "
                            f"{getattr(settings, 'SITE_NAME', settings.JAZZMIN_SETTINGS.get('site_brand', ''))}"
                        ),
                        message=plain_message,
                        html_message=html_message,
                        from_email=None, # Uses DEFAULT_FROM_EMAIL from settings
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    messages.info(request, 'Ti abbiamo inviato un codice di verifica via email.')
                except Exception:
                    # If email sending fails, show an error and don't proceed.
                    messages.error(request, 'Impossibile inviare il codice di verifica. Riprova più tardi o contatta l\'assistenza.')
                    return _render_login(request, error='Errore nell\'invio dell\'email.', step="login")

                return redirect('verify_2fa')

            if getattr(user, "must_change_password", False):
                request.session['password_change_user_id'] = user.id
                messages.warning(request, "Per motivi di sicurezza devi cambiare la password al primo accesso.")
                password_form = _styled_password_change_form(user)
                return _render_login(
                    request,
                    step="change_password",
                    password_form=password_form,
                )

            # User does not have 2FA and does not need password change, log them in directly
            login(request, user)
            _create_admin_log(
                user,
                AdminLogEntry.ACCESS,
                request,
                description="Accesso effettuato con credenziali.",
            )
            return redirect('home')
        return _render_login(request, error='Credenziali non valide', step="login")

    if pending_user_id:
        user = User.objects.filter(pk=pending_user_id).first()
        if user and otp_hash and otp_user_id == pending_user_id and otp_expiry:
            return _render_login(
                request,
                step="otp",
                otp_form=_styled_password_change_otp_form(),
            )
        if user:
            return _render_login(
                request,
                step="change_password",
                password_form=_styled_password_change_form(user),
            )
        request.session.pop("password_change_user_id", None)

    return _render_login(request, step="login")


def resend_privacy_confirmation_view(request):
    if request.method != "POST":
        return redirect('login')

    username = request.POST.get("username")
    if not username:
        messages.error(request, "Inserisci l'username per reinviare la conferma privacy.")
        return redirect('login')

    user = User.objects.filter(username=username).first()
    if not user:
        messages.error(request, "Username non trovato.")
        return redirect('login')

    if send_privacy_confirmation_email(user):
        messages.success(request, "Email di conferma privacy reinviata.")
    else:
        messages.error(request, "Impossibile reinviare la conferma privacy. Riprova più tardi.")
    return redirect('login')


@login_required
def force_password_change_view(request):
    if not getattr(request.user, "must_change_password", False):
        return redirect('home')

    user = request.user
    password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, user)

            otp_code = str(random.randint(100000, 999999))
            otp_hash = hashlib.sha256(otp_code.encode()).hexdigest()
            request.session['password_change_otp_hash'] = otp_hash
            request.session['password_change_otp_user_id'] = user.id
            request.session['password_change_otp_expiry'] = (
                datetime.now(dt_timezone.utc) + timedelta(minutes=10)
            ).isoformat()

            context = {
                'user': user,
                'code': otp_code,
                'site_name': getattr(
                    settings,
                    "SITE_NAME",
                    settings.JAZZMIN_SETTINGS.get("site_brand", ""),
                ),
            }
            html_message = render_to_string('core/emails/password_change_otp.html', context)
            plain_message = strip_tags(html_message)
            send_mail(
                subject=(
                    "Codice OTP per conferma cambio password - "
                    f"{getattr(settings, 'SITE_NAME', settings.JAZZMIN_SETTINGS.get('site_brand', ''))}"
                ),
                message=plain_message,
                html_message=html_message,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.info(request, "Ti abbiamo inviato un codice OTP via email.")
            return redirect('password_change_otp')
        messages.error(request, 'Correggi gli errori nel form per cambiare la password.')

    for fieldname in password_form.fields:
        password_form.fields[fieldname].widget.attrs = {'class': 'form-control'}

    return themed_render(
        request,
        'core/force_password_change.html',
        {
            'password_form': password_form,
        },
    )


@login_required
def password_change_otp_view(request):
    if not getattr(request.user, "must_change_password", False):
        return redirect('home')

    otp_hash = request.session.get('password_change_otp_hash')
    otp_user_id = request.session.get('password_change_otp_user_id')
    otp_expiry = request.session.get('password_change_otp_expiry')
    if not otp_hash or not otp_user_id or not otp_expiry:
        return redirect('force_password_change')

    try:
        expiry_time = datetime.fromisoformat(otp_expiry)
    except ValueError:
        expiry_time = datetime.now(dt_timezone.utc)

    if datetime.now(dt_timezone.utc) > expiry_time:
        messages.error(request, "Il codice OTP è scaduto. Richiedi un nuovo codice.")
        return redirect('force_password_change')

    form = PasswordChangeOTPForm()
    if request.method == 'POST':
        form = PasswordChangeOTPForm(request.POST)
        if form.is_valid():
            entered_code_hash = hashlib.sha256(form.cleaned_data['code'].encode()).hexdigest()
            if entered_code_hash == otp_hash and request.user.id == otp_user_id:
                request.user.must_change_password = False
                request.user.save(update_fields=["must_change_password"])
                _create_admin_log(
                    request.user,
                    AdminLogEntry.PASSWORD_CHANGE,
                    request,
                    description="Cambio password confermato tramite OTP.",
                )
                for key in [
                    'password_change_otp_hash',
                    'password_change_otp_user_id',
                    'password_change_otp_expiry',
                ]:
                    request.session.pop(key, None)
                messages.success(request, "Password aggiornata e confermata con successo.")
                return redirect('home')
            messages.error(request, "Codice OTP non valido.")

    return themed_render(
        request,
        'core/password_change_otp.html',
        {
            'form': form,
        },
    )

def logout_view(request):
    logout(request)
    return redirect('login')

def verify_2fa_view(request):
    # Check for an active lockout first
    lockout_time_iso = request.session.get('2fa_lockout_until')
    if lockout_time_iso:
        lockout_time = datetime.fromisoformat(lockout_time_iso)
        if datetime.now(dt_timezone.utc) < lockout_time:
            remaining = lockout_time - datetime.now(dt_timezone.utc)
            messages.error(request, f"Hai superato il numero di tentativi. Riprova tra {remaining.seconds // 60} minuti.")
            return redirect('login')
        else:
            # Lockout has expired, clear it
            del request.session['2fa_lockout_until']
            if '2fa_attempts' in request.session:
                del request.session['2fa_attempts']

    # Check if the session contains the necessary 2FA data
    if '2fa_user_id' not in request.session:
        messages.error(request, "Sessione di verifica non valida o scaduta. Per favore, effettua nuovamente il login.")
        return redirect('login')

    # Check for code expiry
    expiry_time = datetime.fromisoformat(request.session['2fa_expiry'])
    if datetime.now(dt_timezone.utc) > expiry_time:
        # Clean up session and redirect to login
        del request.session['2fa_user_id']
        del request.session['2fa_code_hash']
        del request.session['2fa_expiry']
        if '2fa_attempts' in request.session:
            del request.session['2fa_attempts']
        messages.error(request, "Il codice di verifica è scaduto. Per favore, effettua nuovamente il login.")
        return redirect('login')

    if request.method == 'POST':
        form = TwoFactorVerifyForm(request.POST)
        if form.is_valid():
            entered_code = form.cleaned_data['code']
            remember_device = form.cleaned_data.get('remember_device', False)
            user_id = request.session['2fa_user_id']

            # Hash the entered code to compare with the stored hash
            entered_code_hash = hashlib.sha256(entered_code.encode()).hexdigest()

            if entered_code_hash == request.session.get('2fa_code_hash'):
                # Code is correct, log the user in
                try:
                    user = User.objects.get(id=user_id)
                    force_password_change = request.session.get('force_password_change')
                    if force_password_change is None:
                        force_password_change = bool(getattr(user, "must_change_password", False))

                    # Clean up session
                    for key in [
                        '2fa_user_id',
                        '2fa_code_hash',
                        '2fa_expiry',
                        '2fa_attempts',
                        '2fa_lockout_until',
                        'force_password_change',
                    ]:
                        if key in request.session:
                            del request.session[key]

                    if force_password_change:
                        if remember_device:
                            request.session['remember_device_after_password_change'] = True
                        request.session['password_change_user_id'] = user.id
                        messages.warning(
                            request,
                            "Per motivi di sicurezza devi cambiare la password al primo accesso.",
                        )
                        return redirect('login')

                    login(request, user)
                    _create_admin_log(
                        user,
                        AdminLogEntry.ACCESS,
                        request,
                        description="Accesso confermato tramite 2FA.",
                    )
                    response = redirect('home')

                    if remember_device:
                        token = TrustedDevice.generate_token()
                        TrustedDevice.objects.create(user=user, token=token)
                        # Set a signed cookie that expires in 30 days
                        response.set_signed_cookie(
                            'trusted_device',
                            token,
                            salt='trusted-device-salt',
                            max_age=timedelta(days=30).total_seconds(),
                            httponly=True, # Prevent JS access
                            secure=not settings.DEBUG # Use secure cookies in production
                        )

                    return response
                except User.DoesNotExist:
                    messages.error(request, "Utente non trovato.")
                    return redirect('login')
            else:
                # Incorrect code, handle brute-force attempts
                attempts = request.session.get('2fa_attempts', 0) + 1
                request.session['2fa_attempts'] = attempts

                if attempts >= 5:
                    lockout_duration = timedelta(minutes=15)
                    request.session['2fa_lockout_until'] = (datetime.now(dt_timezone.utc) + lockout_duration).isoformat()
                    # Invalidate the current 2FA attempt
                    del request.session['2fa_code_hash']
                    messages.error(request, f"Hai superato il numero di tentativi. Per sicurezza, l'accesso è stato bloccato per {lockout_duration.seconds // 60} minuti.")
                    return redirect('login')
                else:
                    remaining_attempts = 5 - attempts
                    messages.error(request, f"Il codice inserito non è corretto. Ti rimangono {remaining_attempts} tentativi.")

    else:
        form = TwoFactorVerifyForm()

    return themed_render(request, 'core/verify_2fa.html', {'form': form})

# --- Dashboard Views ---

@login_required
@role_required([User.SUPERADMIN])
def dashboard_superadmin(request):

    companies = Company.objects.all()
    selected_company_id = request.GET.get('company_id')

    resort_queryset = Resort.objects.all()
    user_queryset = User.objects.all()
    ticket_queryset = Ticket.objects.all()

    if selected_company_id:
        resort_queryset = resort_queryset.filter(company_id=selected_company_id)
        user_queryset = user_queryset.filter(company_id=selected_company_id)
        ticket_queryset = ticket_queryset.filter(resort__company_id=selected_company_id)

    # Group tickets by company and then by resort
    from collections import defaultdict
    tickets_by_company = defaultdict(lambda: defaultdict(list))

    # Filter tickets if a company is selected
    ticket_queryset = Ticket.objects.all()
    if selected_company_id:
        ticket_queryset = ticket_queryset.filter(resort__company_id=selected_company_id)

    for ticket in ticket_queryset.select_related('resort', 'resort__company').order_by('resort__company__name', 'resort__name'):
        company_name = "Altro (Nessuna Società)"
        resort_name = "Altro (Nessun Resort)"
        if ticket.resort and ticket.resort.company:
            company_name = ticket.resort.company.name
            resort_name = ticket.resort.name
        elif ticket.resort:
            resort_name = ticket.resort.name

        tickets_by_company[company_name][resort_name].append(ticket)

    context = {
        'resort_count': resort_queryset.count(),
        'users_count': user_queryset.count(),
        'tickets_open': ticket_queryset.filter(status='open').count(),
        'companies': companies,
        'selected_company_id': selected_company_id,
        'tickets_by_company': dict(tickets_by_company),
    }
    return themed_render(request, 'core/dashboard_superadmin.html', context)

@login_required
@role_required([User.RECEPTIONIST, User.DIRECTOR, User.SUPERADMIN, User.RISORSE_UMANE])
def ticket_dashboard(request):

    if request.user.is_superuser:
        base_queryset = Ticket.objects.all()
    elif request.user.role == User.RISORSE_UMANE:
        if not request.user.company:
            messages.error(request, "Non sei associato a nessuna società.")
            return themed_render(request, 'core/ticket_dashboard.html', {'tickets': []})
        base_queryset = Ticket.objects.filter(resort__company=request.user.company)
    else:
        # A receptionist or director should only see tickets for their specific resort.
        if not request.user.resort:
            messages.error(request, "Non sei associato a nessun resort.")
            return themed_render(request, 'core/ticket_dashboard.html', {'tickets': []})
        base_queryset = Ticket.objects.filter(resort=request.user.resort)

    base_queryset = base_queryset.select_related('assigned_to', 'resort')
    status_filter = request.GET.get('status', '')
    if status_filter:
        base_queryset = base_queryset.filter(status=status_filter)
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        base_queryset = base_queryset.filter(priority=priority_filter)
    tickets = base_queryset.order_by('-created_at')

    counts = {
        'open': base_queryset.filter(status='open').count(),
        'in_progress': base_queryset.filter(status='in_progress').count(),
        'resolved': base_queryset.filter(status='resolved').count(),
        'closed': base_queryset.filter(status='closed').count(),
        'total': base_queryset.count()
    }
    context = {
        'tickets': tickets, 'counts': counts,
        'status_choices': Ticket.STATUS_CHOICES, 'priority_choices': Ticket.PRIORITY_CHOICES,
        'current_status': status_filter, 'current_priority': priority_filter,
    }
    return themed_render(request, 'core/ticket_dashboard.html', context)

@login_required
@role_required([User.HOUSEKEEPING, User.SUPERADMIN])
def dashboard_housekeeping(request):

    if request.user.is_superuser:
        base_queryset = Ticket.objects.all()
    else:
        # A housekeeper should only see tickets for their specific resort.
        base_queryset = Ticket.objects.filter(resort=request.user.resort)

    base_queryset = base_queryset.select_related('assigned_to', 'resort')
    tickets = base_queryset.order_by('-created_at')

    return themed_render(request, 'core/ticket_dashboard.html', {'tickets': tickets})

@login_required
@role_required([User.MAINTAINER, User.SUPERADMIN])
def dashboard_maintainer(request):

    if request.user.is_superuser:
        base_queryset = Ticket.objects.all()
    else:
        # Scope tickets to the user's company
        base_queryset = Ticket.objects.filter(assigned_to=request.user, resort__company=request.user.company)

    base_queryset = base_queryset.select_related('resort')
    status_filter = request.GET.get('status', '')
    if status_filter:
        base_queryset = base_queryset.filter(status=status_filter)
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        base_queryset = base_queryset.filter(priority=priority_filter)
    tickets = base_queryset.order_by('priority', '-created_at')

    counts = {
        'open': base_queryset.filter(status='open').count(),
        'in_progress': base_queryset.filter(status='in_progress').count(),
        'total': base_queryset.count()
    }
    context = {
        'tickets': tickets, 'counts': counts,
        'status_choices': Ticket.STATUS_CHOICES, 'priority_choices': Ticket.PRIORITY_CHOICES,
        'current_status': status_filter, 'current_priority': priority_filter,
    }
    return themed_render(request, 'core/dashboard_maintainer.html', context)

@login_required
@role_required([User.OWNER])
def dashboard_owner(request):

    if not request.user.company:
        messages.error(request, "Non sei associato a nessuna società.")
        return themed_render(request, 'core/ticket_dashboard.html', {'tickets': []})

    base_queryset = Ticket.objects.filter(resort__company=request.user.company)
    base_queryset = base_queryset.select_related('assigned_to', 'resort')

    status_filter = request.GET.get('status', '')
    if status_filter:
        base_queryset = base_queryset.filter(status=status_filter)
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        base_queryset = base_queryset.filter(priority=priority_filter)

    tickets = base_queryset.order_by('-created_at')

    counts = {
        'open': base_queryset.filter(status='open').count(),
        'in_progress': base_queryset.filter(status='in_progress').count(),
        'resolved': base_queryset.filter(status='resolved').count(),
        'closed': base_queryset.filter(status='closed').count(),
        'total': base_queryset.count()
    }

    context = {
        'tickets': tickets, 'counts': counts,
        'status_choices': Ticket.STATUS_CHOICES, 'priority_choices': Ticket.PRIORITY_CHOICES,
        'current_status': status_filter, 'current_priority': priority_filter,
        'is_owner_view': True,
    }
    return themed_render(request, 'core/ticket_dashboard.html', context)


@login_required
@role_required([User.HEAD_MAINTAINER, User.SUPERADMIN])
def dashboard_head_maintainer(request):
    user = request.user
    company = user.company

    # === 1. Team Performance ===
    maintainers_in_company = User.objects.none()
    if company:
        maintainers_in_company = User.objects.filter(
            company=company,
            role__in=[User.MAINTAINER, User.HEAD_MAINTAINER]
        )

    maintainer_stats = maintainers_in_company.annotate(
        open_tickets=Count('assigned_tickets', filter=Q(assigned_tickets__status='open')),
        in_progress_tickets=Count('assigned_tickets', filter=Q(assigned_tickets__status='in_progress')),
        closed_tickets_month=Count('assigned_tickets', filter=Q(
            assigned_tickets__status='closed',
            assigned_tickets__updated_at__month=timezone.now().month
        ))
    ).order_by('-open_tickets')

    # === 2. Maintenance Costs KPI ===
    maintenance_budget = 0
    maintenance_spent = 0
    if company:
        try:
            maintenance_category = PurchaseCategory.objects.get(name__iexact="Manutenzione")
            now = timezone.now()

            budget_query = Budget.objects.filter(
                resort__company=company,
                category=maintenance_category,
                year=now.year,
                month=now.month
            )
            total_budget_agg = budget_query.aggregate(total=Sum('amount'))
            maintenance_budget = total_budget_agg['total'] or 0

            spent_query = PurchaseOrder.objects.filter(
                resort__company=company,
                category=maintenance_category,
                status='completed',
                updated_at__year=now.year,
                updated_at__month=now.month
            )
            maintenance_spent = sum(order.total_amount for order in spent_query)

        except PurchaseCategory.DoesNotExist:
            pass # If the category doesn't exist, these will just stay 0

    # === 3. Review Insights ===
    maintenance_keywords = ['manutenzione', 'guasto', 'rotto', 'rotta', 'problema', 'rumore']
    q_objects = Q()
    for keyword in maintenance_keywords:
        q_objects |= Q(text__icontains=keyword)

    recent_negative_reviews = []
    if company:
        recent_negative_reviews = Review.objects.filter(
            resort__company=company,
            analysis__sentiment_label='negative',
            review_date__gte=timezone.now() - timezone.timedelta(days=90)
        ).filter(q_objects).select_related('resort')[:5]

    context = {
        'page_title': "Dashboard Capomanutentore",
        'maintainer_stats': maintainer_stats,
        'maintenance_budget': maintenance_budget,
        'maintenance_spent': maintenance_spent,
        'recent_negative_reviews': recent_negative_reviews,
    }
    return themed_render(request, 'core/dashboard_head_maintainer.html', context)


@login_required
def maintenance_tool_redirect_view(request):
    """Serve il nuovo frontend React per la manutenzione."""

    user = request.user
    if not (user.is_superuser or user.has_maintenance_access or user.role in [
        User.MAINTAINER,
        User.HEAD_MAINTAINER,
        User.OWNER,
        User.MAINTENANCE_MANAGER,
    ]):
        messages.error(request, "Non hai accesso allo strumento manutenzione.")
        return redirect('home')

    context = {
        'vite_entry': 'src/maintenance_entry.jsx',
    }

    # Force chromeless mode for maintainers on mobile
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(x in user_agent for x in ['iphone', 'android', 'mobile'])

    if is_mobile and not request.GET.get('chromeless'):
        return redirect(f"{request.path}?chromeless=true")

    return themed_render(request, 'tickets/maintenance_app.html', context)

# --- Management Views ---

@login_required
@role_required([User.OWNER, User.SUPERADMIN])
def management_dashboard(request):
    settings = PlatformSettings.load()

    if request.method == 'POST':
        # Check for a specific name in post to identify the form submission
        if 'maintenance_toggle' in request.POST:
            if request.user.role != User.SUPERADMIN:
                messages.error(request, "Non hai i permessi per modificare questa impostazione.")
                return redirect('core:management_dashboard')

            # The value from a checkbox is 'on' if checked, otherwise it's not in the POST data
            new_status = request.POST.get('maintenance_mode_checkbox') == 'on'

            if settings.maintenance_mode != new_status:
                settings.maintenance_mode = new_status
                settings.save()
                if new_status:
                    messages.success(request, "Modalità manutenzione ATTIVATA.")
                else:
                    messages.success(request, "Modalità manutenzione DISATTIVATA.")

            return redirect('core:management_dashboard')
        # Add other POST handling here if needed for other forms on the page

    context = {
        'maintenance_mode_active': settings.maintenance_mode
    }
    return themed_render(request, 'core/management_dashboard.html', context)

@login_required
def room_management_landing_view(request):
    user = request.user
    if user.role == User.SUPERADMIN:
        return redirect('core:select_company')
    elif user.role == User.OWNER:
        return redirect('core:select_resort_owner')
    elif user.role == User.DIRECTOR:
        if user.resort:
            return redirect('core:resort_room_list', resort_id=user.resort.id)
        else:
            messages.warning(request, "Non sei associato a nessuna struttura.")
            return redirect('home')
    else:
        messages.error(request, "Non hai i permessi per accedere a questa sezione.")
        return redirect('home')

@login_required
@role_required([User.SUPERADMIN])
def select_company_view(request):
    companies = Company.objects.all().order_by('name')
    return themed_render(request, 'core/select_company.html', {
        'title': 'Gestione Camere: Seleziona Società',
        'companies': companies
    })

@login_required
@role_required([User.OWNER, User.SUPERADMIN])
def select_resort_view(request, company_id=None):
    user = request.user
    if user.role == User.SUPERADMIN:
        if not company_id:
            messages.error(request, "ID Società non specificato.")
            return redirect('core:select_company')
        company = get_object_or_404(Company, pk=company_id)
        resorts = Resort.objects.filter(company=company).order_by('name')
        title = f"Gestione Camere: Seleziona Struttura per {company.name}"
    elif user.role == User.OWNER:
        if user.company:
            resorts = Resort.objects.filter(company=user.company).order_by('name')
            title = "Gestione Camere: Seleziona Struttura"
        else:
            resorts = Resort.objects.none()
            messages.warning(request, "Non sei associato a nessuna società.")
            title = "Nessuna Struttura Trovata"
    else:
        return redirect('home')
    return themed_render(request, 'core/select_resort.html', {'title': title, 'resorts': resorts})

@login_required
@role_required([User.SUPERADMIN, User.OWNER, User.DIRECTOR])
def resort_room_list_view(request, resort_id=None):
    user = request.user
    resort = get_object_or_404(Resort, pk=resort_id)
    can_access = False
    if user.role == User.SUPERADMIN:
        can_access = True
    elif user.role == User.OWNER and user.company and resort.company == user.company:
        can_access = True
    elif user.role == User.DIRECTOR and user.resort and resort.id == user.resort.id:
        can_access = True
    if not can_access:
        messages.error(request, "Non hai il permesso di visualizzare le camere di questa struttura.")
        return redirect('home')
    rooms = Room.objects.filter(resort=resort).order_by('name')
    context = {
        'title': f'Camere per {resort.name}',
        'resort': resort,
        'rooms': rooms,
        'ROLES': {'SUPERADMIN': User.SUPERADMIN}
    }
    return themed_render(request, 'core/room_card_list.html', context)

@login_required
@role_required([User.SUPERADMIN])
def room_bulk_create_form_view(request, resort_id):
    resort = get_object_or_404(Resort, pk=resort_id)
    return themed_render(request, 'core/room_bulk_form.html', {
        'title': f'Crea Camere Multiple per {resort.name}',
        'resort': resort,
    })

@login_required
@role_required([User.SUPERADMIN])
def room_bulk_create_api_view(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Metodo non valido.'}, status=405)
    try:
        data = json.loads(request.body)
        resort_id = data.get('resort_id')
        rooms_data = data.get('rooms', [])
        if not resort_id or not rooms_data:
            return JsonResponse({'status': 'error', 'message': 'Dati mancanti.'}, status=400)
        resort = get_object_or_404(Resort, pk=resort_id)
        with transaction.atomic():
            created_rooms = []
            for room_data in rooms_data:
                name = room_data.get('name')
                if not name: continue
                if Room.objects.filter(resort=resort, name=name).exists():
                    raise Exception(f"Una camera con nome '{name}' esiste già in questo resort.")
                room = Room.objects.create(
                    resort=resort,
                    name=name,
                    description=room_data.get('description', '')
                )
                created_rooms.append({'id': room.id, 'name': room.name})
        return JsonResponse({'status': 'success', 'message': f'{len(created_rooms)} camere create con successo.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class GuideAssetApiView(View):
    http_method_names = ['get', 'post', 'delete']

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'detail': 'Autenticazione richiesta.'}, status=401)
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _can_manage(user):
        role = getattr(user, 'role', None)
        return user.is_superuser or role == User.SUPERADMIN

    def get(self, request, *args, **kwargs):
        guide_key = request.GET.get('guide_key')
        if not guide_key:
            return JsonResponse({'detail': 'Parametro guide_key mancante.'}, status=400)

        queryset = InAppGuideAsset.objects.active().filter(guide_key=guide_key)
        step_key = request.GET.get('step_key')
        if step_key:
            queryset = queryset.filter(step_key=step_key)

        assets = [asset.as_payload() for asset in queryset]
        return JsonResponse({'status': 'ok', 'results': assets})

    def post(self, request, *args, **kwargs):
        if not self._can_manage(request.user):
            return JsonResponse({'detail': 'Non sei autorizzato a modificare i tutorial.'}, status=403)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'detail': 'Formato JSON non valido.'}, status=400)

        required = ['guide_key', 'step_key', 'title', 'resource_type', 'url']
        missing = [field for field in required if not payload.get(field)]
        if missing:
            return JsonResponse({
                'detail': f"Campi mancanti: {', '.join(missing)}."
            }, status=400)

        resource_type = payload.get('resource_type')
        valid_types = {choice[0] for choice in InAppGuideAsset.TYPE_CHOICES}
        if resource_type not in valid_types:
            return JsonResponse({'detail': 'Tipo di risorsa non supportato.'}, status=400)

        try:
            position = int(payload.get('position') or 0)
        except (TypeError, ValueError):
            position = 0

        asset = InAppGuideAsset.objects.create(
            guide_key=payload['guide_key'],
            step_key=payload['step_key'],
            title=payload['title'],
            description=payload.get('description', ''),
            resource_type=resource_type,
            url=payload['url'],
            thumbnail_url=payload.get('thumbnail', ''),
            position=position,
            created_by=request.user,
        )

        return JsonResponse({'status': 'ok', 'data': asset.as_payload()}, status=201)

    def delete(self, request, *args, **kwargs):
        if not self._can_manage(request.user):
            return JsonResponse({'detail': 'Non sei autorizzato a modificare i tutorial.'}, status=403)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            payload = {}

        asset_id = payload.get('id') or request.GET.get('id')
        if not asset_id:
            return JsonResponse({'detail': 'Parametro id mancante.'}, status=400)

        try:
            asset = InAppGuideAsset.objects.get(pk=asset_id)
        except (TypeError, ValueError, InAppGuideAsset.DoesNotExist):
            return JsonResponse({'detail': 'Risorsa non trovata.'}, status=404)

        asset.delete()
        return JsonResponse({'status': 'ok'})

@login_required
@role_required([User.SUPERADMIN])
def room_update_view(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('core:resort_room_list', resort_id=room.resort.id)
    else:
        form = RoomForm(instance=room, user=request.user)
    return themed_render(request, 'core/room_form.html', {'form': form, 'title': f'Modifica Camera: {room.name}'})

@login_required
@role_required([User.SUPERADMIN])
def room_delete_view(request, pk):
    room = get_object_or_404(Room, pk=pk)
    resort_id = room.resort.id
    if request.method == 'POST':
        room.delete()
        return redirect('core:resort_room_list', resort_id=resort_id)
    return themed_render(request, 'core/room_confirm_delete.html', {'object_to_delete': room, 'object_name': 'Camera'})

@login_required
@role_required([User.SUPERADMIN])
def room_qr_code_view(request, room_id):
    ticket_create_url = request.build_absolute_uri(f"{reverse('ticket_create')}?room_id={room_id}")
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(ticket_create_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, "PNG")
    buffer.seek(0)
    return HttpResponse(buffer, content_type="image/png")

@login_required
@role_required([User.OWNER, User.SUPERADMIN])
def resort_list_view(request):

    if request.user.is_superuser:
        resorts = Resort.objects.all().select_related('company').order_by('company__name', 'name')
    else:
        resorts = Resort.objects.filter(company=request.user.company).order_by('name')

    return themed_render(request, 'core/resort_list.html', {'resorts': resorts})

@login_required
@role_required([User.OWNER, User.SUPERADMIN])
def resort_create_view(request):

    if request.method == 'POST':
        form = ResortForm(request.POST, user=request.user)
        if form.is_valid():
            resort = form.save(commit=False)
            if request.user.role == User.OWNER:
                resort.company = request.user.company
            resort.save()
            messages.success(request, "Resort creato con successo.")
            return redirect('core:resort_list')
    else:
        form = ResortForm(user=request.user)
    return themed_render(request, 'core/resort_form.html', {'form': form, 'title': 'Crea Resort'})

@login_required
@role_required([User.SUPERADMIN])
def resort_update_view(request, pk):
    resort = get_object_or_404(Resort, pk=pk)

    if request.method == 'POST':
        form = ResortForm(request.POST, instance=resort, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Resort aggiornato con successo.")
            return redirect('core:resort_list')
    else:
        form = ResortForm(instance=resort, user=request.user)
    return themed_render(request, 'core/resort_form.html', {'form': form, 'title': f'Modifica Resort: {resort.name}'})

@login_required
@role_required([User.SUPERADMIN])
def resort_delete_view(request, pk):
    resort = get_object_or_404(Resort, pk=pk)

    if request.method == 'POST':
        resort.delete()
        messages.success(request, "Resort eliminato con successo.")
        return redirect('core:resort_list')
    return themed_render(request, 'core/resort_confirm_delete.html', {'object_to_delete': resort, 'object_name': 'Resort'})


@login_required
@role_required([User.OWNER, User.SUPERADMIN, User.DIRECTOR, User.HEAD_MAINTAINER])
def user_list_view(request):
    user = request.user
    users = User.objects.all()

    # Apply base scoping
    if user.is_superuser:
        users = users
    elif user.role in [User.OWNER, User.RISORSE_UMANE, User.HEAD_MAINTAINER]:
        users = users.filter(company=user.company)
    elif user.role == User.DIRECTOR:
        users = users.filter(resort=user.resort)
    else:
        # Should not be reached due to decorator, but as a fallback
        users = User.objects.none()

    if user.role == User.HEAD_MAINTAINER:
        users = users.filter(role__in=[User.MAINTAINER, User.HEAD_MAINTAINER])

    users = users.select_related('company', 'resort').order_by('company__name', 'username')

    filter_form = UserFilterForm(request.GET, user=request.user)
    if filter_form.is_valid():
        name = filter_form.cleaned_data.get('name')
        if name:
            users = users.filter(
                Q(username__icontains=name) |
                Q(first_name__icontains=name) |
                Q(last_name__icontains=name)
            )

        resort = filter_form.cleaned_data.get('resort')
        if resort:
            users = users.filter(resort=resort)

        role = filter_form.cleaned_data.get('role')
        if role:
            users = users.filter(role=role)

    context = {
        'users': users,
        'filter_form': filter_form
    }
    if request.htmx:
        return render(request, 'partials/_user_table.html', context)

    return themed_render(request, 'core/user_list.html', context)

@login_required
@role_required([User.OWNER, User.SUPERADMIN, User.HEAD_MAINTAINER])
def user_create_view(request):

    if request.method == 'POST':
        form = UserCreationForm(request.POST, user=request.user) # Pass user to form
        if form.is_valid():
            new_user = form.save(commit=False)
            # If the creator is an owner, assign the new user to their company
            if request.user.role == User.OWNER:
                new_user.company = request.user.company

            # Set permissions based on role
            if new_user.role == User.CORPORATE:
                new_user.has_maintenance_access = True
                new_user.has_reviews_access = True
            elif new_user.role in [User.ECONOMO, User.CAPO_ECONOMO]:
                new_user.can_manage_purchase_orders = True
                new_user.has_inventory_access = True
                new_user.has_it_support_management_access = True

            new_user.save()
            messages.success(request, "Utente creato con successo.")
            return redirect('core:user_list')
    else:
        form = UserCreationForm(user=request.user) # Pass user to form

    return themed_render(request, 'core/user_form.html', {'form': form, 'title': 'Crea Utente'})

@login_required
def user_update_view(request, pk):
    user_to_edit = get_object_or_404(User, pk=pk)

    # An owner can only edit users in their own company, and cannot edit superusers
    can_edit = request.user.is_superuser or \
               (request.user.role == User.OWNER and user_to_edit.company == request.user.company and not user_to_edit.is_superuser) or \
               (request.user.role == User.HEAD_MAINTAINER and user_to_edit.company == request.user.company and user_to_edit.role == User.MAINTAINER)

    if not can_edit:
        messages.error(request, "Non hai il permesso di modificare questo utente.")
        return redirect('core:user_list')

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_to_edit, user=request.user) # Pass user to form
        if form.is_valid():
            user = form.save(commit=False)

            # Handle password change
            password = form.cleaned_data.get("new_password")
            if password:
                user.set_password(password)

            # Set permissions based on role
            if user.role == User.CORPORATE:
                user.has_maintenance_access = True
                user.has_reviews_access = True
            elif user.role in [User.ECONOMO, User.CAPO_ECONOMO]:
                user.can_manage_purchase_orders = True
                user.has_inventory_access = True
                user.has_it_support_management_access = True

            # NOTE: We are intentionally not resetting the flags to false in an else block.
            # This is to allow for more flexible permission combinations in the future,
            # where a user might have a different role but still need access to a specific tool.
            # Permissions should be explicitly revoked by an admin via the form if needed.

            user.save()
            messages.success(request, "Utente aggiornato con successo.")
            return redirect('core:user_list')
    else:
        form = UserForm(instance=user_to_edit, user=request.user) # Pass user to form

    return themed_render(request, 'core/user_form.html', {'form': form, 'title': f'Modifica Utente: {user_to_edit.username}'})

@login_required
def user_delete_view(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)

    # An owner can only delete users in their own company, and cannot delete superusers
    can_delete = request.user.is_superuser or \
                 (request.user.role == User.OWNER and user_to_delete.company == request.user.company and not user_to_delete.is_superuser) or \
                 (request.user.role == User.HEAD_MAINTAINER and user_to_delete.company == request.user.company and user_to_delete.role == User.MAINTAINER)

    if not can_delete:
        messages.error(request, "Non hai il permesso di eliminare questo utente.")
        return redirect('core:user_list')

    if request.method == 'POST':
        user_to_delete.delete()
        messages.success(request, "Utente eliminato con successo.")
        return redirect('core:user_list')

    return themed_render(request, 'core/user_confirm_delete.html', {'user_to_delete': user_to_delete})


# --- Other Views ---

@login_required
@role_required([User.SUPERADMIN])
def reporting_view(request):
    form = ReportFilterForm(request.GET)
    tickets = Ticket.objects.all()
    if form.is_valid():
        if form.cleaned_data['start_date']:
            tickets = tickets.filter(created_at__gte=form.cleaned_data['start_date'])
        if form.cleaned_data['end_date']:
            tickets = tickets.filter(created_at__lte=form.cleaned_data['end_date'])
        if form.cleaned_data['resort']:
            tickets = tickets.filter(resort=form.cleaned_data['resort'])
        if form.cleaned_data['user']:
            tickets = tickets.filter(
                Q(created_by=form.cleaned_data['user']) | Q(assigned_to=form.cleaned_data['user'])
            )
    status_data = tickets.values('status').annotate(count=Count('status')).order_by('status')
    status_map = dict(Ticket.STATUS_CHOICES)
    status_labels = [status_map.get(item['status'], item['status']) for item in status_data]
    status_counts = [item['count'] for item in status_data]
    daily_tickets = (
        tickets
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    daily_labels = [item['day'].strftime('%Y-%m-%d') for item in daily_tickets]
    daily_counts = [item['count'] for item in daily_tickets]
    context = {
        'form': form,
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'daily_labels': json.dumps(daily_labels),
        'daily_counts': json.dumps(daily_counts),
    }
    return themed_render(request, 'core/reporting.html', context)

@login_required
@role_required([User.SUPERADMIN])
def export_tickets_csv(request):
    form = ReportFilterForm(request.GET)
    tickets = Ticket.objects.all().select_related('resort', 'room', 'created_by', 'assigned_to')
    if form.is_valid():
        if form.cleaned_data['start_date']:
            tickets = tickets.filter(created_at__gte=form.cleaned_data['start_date'])
        if form.cleaned_data['end_date']:
            tickets = tickets.filter(created_at__lte=form.cleaned_data['end_date'])
        if form.cleaned_data['resort']:
            tickets = tickets.filter(resort=form.cleaned_data['resort'])
        if form.cleaned_data['user']:
            tickets = tickets.filter(
                Q(created_by=form.cleaned_data['user']) | Q(assigned_to=form.cleaned_data['user'])
            )
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report_ticket.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Titolo', 'Resort', 'Camera', 'Stato', 'Priorità', 'Creato Da', 'Assegnato A', 'Data Creazione'])
    for ticket in tickets:
        writer.writerow([
            ticket.id, ticket.title, ticket.resort.name,
            ticket.room.name if ticket.room else 'N/A',
            ticket.get_status_display(), ticket.get_priority_display(),
            ticket.created_by.username,
            ticket.assigned_to.username if ticket.assigned_to else 'N/A',
            ticket.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


def _get_admin_log_queryset(form):
    logs = AdminLogEntry.objects.select_related("user")
    if form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        if start_date:
            start_dt = timezone.make_aware(
                datetime.combine(start_date, datetime.min.time()),
                timezone.get_current_timezone(),
            )
            logs = logs.filter(timestamp__gte=start_dt)
        if end_date:
            end_dt = timezone.make_aware(
                datetime.combine(end_date, datetime.max.time()),
                timezone.get_current_timezone(),
            )
            logs = logs.filter(timestamp__lte=end_dt)
        action_type = form.cleaned_data.get("action_type")
        if action_type:
            logs = logs.filter(action_type=action_type)
        user = form.cleaned_data.get("user")
        if user:
            logs = logs.filter(user=user)
        ip_address = form.cleaned_data.get("ip_address")
        if ip_address:
            logs = logs.filter(ip_address__icontains=ip_address)
    return logs


@login_required
@role_required([User.SUPERADMIN])
def admin_logs_view(request):
    form = AdminLogFilterForm(request.GET)
    logs = _get_admin_log_queryset(form)
    paginator = Paginator(logs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    export_query = request.GET.copy()
    export_query.pop("page", None)
    context = {
        "form": form,
        "page_obj": page_obj,
        "export_query": export_query.urlencode(),
    }
    return themed_render(request, "core/admin_logs.html", context)


@login_required
@role_required([User.SUPERADMIN])
def export_admin_logs_csv(request):
    form = AdminLogFilterForm(request.GET)
    logs = _get_admin_log_queryset(form)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="admin_logs.csv"'
    writer = csv.writer(response)
    writer.writerow(["Timestamp", "Funzione", "Utente", "IP", "Descrizione", "User-Agent", "Extra"])
    for log in logs:
        user_label = log.user.get_full_name() if log.user else "Sistema"
        writer.writerow(
            [
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                log.get_action_type_display(),
                user_label,
                log.ip_address or "",
                log.description,
                log.extra.get("user_agent", ""),
                json.dumps(log.extra, ensure_ascii=False),
            ]
        )
    return response


@login_required
@role_required([User.SUPERADMIN])
def export_admin_logs_excel(request):
    form = AdminLogFilterForm(request.GET)
    logs = _get_admin_log_queryset(form)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Log amministratore"
    worksheet.append(["Timestamp", "Funzione", "Utente", "IP", "Descrizione", "User-Agent", "Extra"])
    for log in logs:
        user_label = log.user.get_full_name() if log.user else "Sistema"
        worksheet.append(
            [
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                log.get_action_type_display(),
                user_label,
                log.ip_address or "",
                log.description,
                log.extra.get("user_agent", ""),
                json.dumps(log.extra, ensure_ascii=False),
            ]
        )
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="admin_logs.xlsx"'
    workbook.save(response)
    return response


@login_required
@role_required([User.SUPERADMIN])
def export_admin_logs_pdf(request):
    form = AdminLogFilterForm(request.GET)
    logs = _get_admin_log_queryset(form)
    rows = []
    for log in logs:
        rows.append(
            {
                "timestamp": log.timestamp,
                "action": log.get_action_type_display(),
                "user": log.user.get_full_name() if log.user else "Sistema",
                "ip_address": log.ip_address or "",
                "description": log.description or "",
                "user_agent": log.extra.get("user_agent", ""),
                "extra": log.extra,
            }
        )
    html = render_to_string(
        "core/reports/admin_logs_pdf.html",
        {
            "generated_at": timezone.now(),
            "rows": rows,
        },
    )
    pdf_file = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="admin_logs_report.pdf"'
    return response

@login_required
def search_results_view(request):
    query = request.GET.get('q', '')
    if query:
        tickets = Ticket.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).distinct()
    else:
        tickets = Ticket.objects.none()
    return themed_render(request, 'core/search_results.html', {'tickets': tickets, 'query': query})

from communications.models import Announcement

@login_required
def profile_view(request):
    if getattr(request.user, "must_change_password", False):
        return redirect('force_password_change')
    from hr_portal.models import Payslip
    # This view handles the user profile page, which includes multiple forms.
    user = request.user
    user_documents = Document.objects.filter(user=user)
    announcements = user.announcements.all()
    payslips = Payslip.objects.filter(user=user).order_by('-created_at')
    try:
        active_policy = (
            PrivacyPolicyVersion.objects.filter(is_active=True)
            .order_by("-published_at", "-created_at")
            .first()
        )
    except (OperationalError, ProgrammingError):
        active_policy = None
    consent = None
    if active_policy:
        consent = (
            UserPrivacyConsent.objects.filter(user=user, policy_version=active_policy)
            .order_by("-accepted_at")
            .first()
        )
    email_verified = bool(consent and consent.email_confirmed_at)
    privacy_accepted = bool(consent)
    must_change_password = bool(getattr(user, "must_change_password", False))

    # Initialize forms
    password_form = PasswordChangeForm(user)
    avatar_form = ProfileAvatarForm(instance=user)
    two_factor_form = TwoFactorAuthForm(initial={'enable_2fa': user.is_2fa_enabled})
    theme_form = UserProfileThemeForm(instance=user)

    if request.method == 'POST':
        # Determine which form was submitted and process it
        if 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                if getattr(user, "must_change_password", False):
                    user.must_change_password = False
                    user.save(update_fields=["must_change_password"])
                update_session_auth_hash(request, user)
                messages.success(request, 'La tua password è stata cambiata con successo!')
                return redirect('profile')
            else:
                messages.error(request, 'Correggi gli errori nel form per cambiare la password.')

        elif 'change_avatar' in request.POST:
            avatar_form = ProfileAvatarForm(request.POST, request.FILES, instance=user)
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, 'La tua immagine del profilo è stata aggiornata!')
                return redirect('profile')
            else:
                messages.error(request, 'Correggi gli errori nel form per cambiare l\'immagine.')

        elif 'change_theme' in request.POST:
            theme_form = UserProfileThemeForm(request.POST, request.FILES, instance=user)
            if theme_form.is_valid():
                theme_form.save()
                messages.success(request, 'Le tue preferenze grafiche sono state aggiornate!')
                return redirect('profile')
            else:
                messages.error(request, 'Correggi gli errori nel form per aggiornare le preferenze.')

        elif 'toggle_2fa' in request.POST:
            two_factor_form = TwoFactorAuthForm(request.POST)
            if two_factor_form.is_valid():
                enable_2fa = two_factor_form.cleaned_data['enable_2fa']
                user.is_2fa_enabled = enable_2fa
                user.save(update_fields=['is_2fa_enabled'])
                if enable_2fa:
                    messages.success(request, 'Autenticazione a due fattori ABILITATA.')
                else:
                    messages.success(request, 'Autenticazione a due fattori DISABILITATA.')
                return redirect('profile')
            # No else needed, if invalid it will just re-render with errors

    # This part is now outside the GET-only block, so it runs for GET and failed POSTs
    for fieldname in password_form.fields:
        password_form.fields[fieldname].widget.attrs = {'class': 'form-control'}

    context = {
        'password_form': password_form,
        'avatar_form': avatar_form,
        'two_factor_form': two_factor_form,
        'theme_form': theme_form,
        'user_documents': user_documents,
        'announcements': announcements,
        'payslips': payslips,
        'email_verified': email_verified,
        'privacy_accepted': privacy_accepted,
        'must_change_password': must_change_password,
    }
    return themed_render(request, 'core/profile.html', context)

# --- Demo Views for Landing Page ---

@login_required
def demo_tickets_view(request):
    """A chrome-less view of the tickets list for the landing page demo."""
    # Use the demo resort created by the seeder
    demo_resort = Resort.objects.filter(name__icontains='(Demo)').first()
    if not demo_resort:
        return HttpResponse("Dati demo non trovati. Eseguire il comando 'seed_demo_data'.", status=500)

    tickets = Ticket.objects.filter(resort=demo_resort).select_related('resort', 'assigned_to').order_by('-created_at')[:5]
    return render(request, 'core/demos/demo_tickets.html', {'tickets': tickets})

@login_required
def demo_reviews_view(request):
    """A chrome-less view of the reviews list for the landing page demo."""
    demo_resort = Resort.objects.filter(name__icontains='(Demo)').first()
    if not demo_resort:
        return HttpResponse("Dati demo non trovati.", status=500)

    reviews = Review.objects.filter(resort=demo_resort).select_related('source').order_by('-review_date')[:5]
    return render(request, 'core/demos/demo_reviews.html', {'reviews': reviews})

@login_required
def demo_dashboard_view(request):
    """A chrome-less view of the director's dashboard for the landing page demo."""
    demo_resort = Resort.objects.filter(name__icontains='(Demo)').first()
    if not demo_resort:
        return HttpResponse("Dati demo non trovati.", status=500)

    kpis = {
        'maintenance_tickets_open': Ticket.objects.filter(resort=demo_resort, status='open').count(),
        'avg_sentiment': Review.objects.filter(resort=demo_resort).aggregate(avg=Avg('analysis__sentiment_score'))['avg'] or 0,
        'avg_rating': Review.objects.filter(resort=demo_resort).aggregate(avg=Avg('rating'))['avg'] or 0,
    }
    return render(request, 'core/demos/demo_dashboard.html', {'kpis': kpis})


@login_required
@role_required([User.OWNER, User.DIRECTOR, User.SUPERADMIN, User.CAPO_ECONOMO, User.ECONOMO, User.HEAD_MAINTAINER])
def director_cockpit_view(request):

    # Date filtering
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30) # Default to last 30 days

    if 'start_date' in request.GET and request.GET['start_date']:
        try:
            start_date = datetime.strptime(request.GET['start_date'], '%Y-%m-%d')
        except (ValueError, TypeError):
            pass # Keep default
    if 'end_date' in request.GET and request.GET['end_date']:
        try:
            end_date = datetime.strptime(request.GET['end_date'], '%Y-%m-%d')
        except (ValueError, TypeError):
            pass # Keep default

    # --- KPI Calculations ---
    base_ticket_qs = Ticket.objects.all()
    base_it_ticket_qs = IT_Ticket.objects.all()
    base_asset_qs = Asset.objects.all()
    base_review_qs = Review.objects.all()
    base_budget_qs = Budget.objects.all()
    base_po_qs = PurchaseOrder.objects.all()

    # Filter querysets based on user role
    if not request.user.is_superuser:
        if request.user.role in [User.OWNER, User.CAPO_ECONOMO, User.HEAD_MAINTAINER]:
            if request.user.company:
                company = request.user.company
                base_ticket_qs = base_ticket_qs.filter(resort__company=company)
                base_it_ticket_qs = base_it_ticket_qs.filter(asset__resort__company=company)
                base_asset_qs = base_asset_qs.filter(resort__company=company)
                base_review_qs = base_review_qs.filter(resort__company=company)
                base_budget_qs = base_budget_qs.filter(resort__company=company)
                base_po_qs = base_po_qs.filter(resort__company=company)
            else:
                # Users in these roles without a company see nothing
                base_ticket_qs, base_it_ticket_qs, base_asset_qs, base_review_qs, base_budget_qs, base_po_qs = (qs.none() for qs in [base_ticket_qs, base_it_ticket_qs, base_asset_qs, base_review_qs, base_budget_qs, base_po_qs])
        elif request.user.role in [User.DIRECTOR, User.ECONOMO]:
            if request.user.resort:
                resort = request.user.resort
                base_ticket_qs = base_ticket_qs.filter(resort=resort)
                base_it_ticket_qs = base_it_ticket_qs.filter(asset__resort=resort)
                base_asset_qs = base_asset_qs.filter(resort=resort)
                base_review_qs = base_review_qs.filter(resort=resort)
                base_budget_qs = base_budget_qs.filter(resort=resort)
                base_po_qs = base_po_qs.filter(resort=resort)
            else:
                # Users in these roles without a resort see nothing
                base_ticket_qs, base_it_ticket_qs, base_asset_qs, base_review_qs, base_budget_qs, base_po_qs = (qs.none() for qs in [base_ticket_qs, base_it_ticket_qs, base_asset_qs, base_review_qs, base_budget_qs, base_po_qs])

    # Filter by date range
    tickets_in_range = base_ticket_qs.filter(created_at__range=(start_date, end_date))
    it_tickets_in_range = base_it_ticket_qs.filter(created_at__range=(start_date, end_date))
    reviews_in_range = base_review_qs.filter(review_date__range=(start_date, end_date))

    # --- Budget Calculation ---
    today = timezone.now().date()
    budget_for_month = base_budget_qs.filter(year=today.year, month=today.month)
    pos_for_month = base_po_qs.filter(status='completed', created_at__year=today.year, created_at__month=today.month)

    total_budget = budget_for_month.aggregate(total=Sum('amount'))['total'] or 0
    total_spent = sum(order.total_amount for order in pos_for_month)

    # Calculate KPIs
    kpis = {
        'maintenance_tickets_open': tickets_in_range.filter(status='open').count(),
        'it_tickets_open': it_tickets_in_range.filter(status='open').count(),
        'total_asset_cost': base_asset_qs.aggregate(total=Sum('purchase_cost'))['total'] or 0,
        'total_intervention_cost': it_tickets_in_range.aggregate(total=Sum('intervention_cost'))['total'] or 0,
        'avg_sentiment': ReviewAnalysis.objects.filter(review__in=reviews_in_range).aggregate(avg=Avg('sentiment_score'))['avg'] or 0,
        'budget_total': total_budget,
        'budget_spent': total_spent,
    }

    # Data for charts (example: tickets created over time)
    maintenance_trend = tickets_in_range.annotate(day=TruncDay('created_at')).values('day').annotate(count=Count('id')).order_by('day')
    it_trend = it_tickets_in_range.annotate(day=TruncDay('created_at')).values('day').annotate(count=Count('id')).order_by('day')

    all_days = sorted(list(set([d['day'].strftime('%Y-%m-%d') for d in maintenance_trend] + [d['day'].strftime('%Y-%m-%d') for d in it_trend])))

    maintenance_map = {item['day'].strftime('%Y-%m-%d'): item['count'] for item in maintenance_trend}
    it_map = {item['day'].strftime('%Y-%m-%d'): item['count'] for item in it_trend}

    maintenance_data = [maintenance_map.get(day, 0) for day in all_days]
    it_data = [it_map.get(day, 0) for day in all_days]

    # --- Competitor Analysis Data ---
    user_resorts = Resort.objects.none()
    if request.user.is_superuser:
        user_resorts = Resort.objects.all()
    elif request.user.role == User.OWNER and request.user.company:
        user_resorts = Resort.objects.filter(company=request.user.company)
    elif request.user.role == User.DIRECTOR and request.user.resort:
        user_resorts = Resort.objects.filter(pk=request.user.resort.pk)

    selected_resort_for_comp = None
    if user_resorts.count() == 1:
        selected_resort_for_comp = user_resorts.first()

    selected_resort_id = request.GET.get('competitor_resort_id')
    if selected_resort_id:
        try:
            selected_resort_for_comp = user_resorts.get(pk=selected_resort_id)
        except Resort.DoesNotExist:
            pass

    available_competitors = Competitor.objects.none()
    if selected_resort_for_comp:
        available_competitors = Competitor.objects.filter(resort_associations__resort=selected_resort_for_comp)

    selected_competitor_id = request.GET.get('competitor_id')
    selected_competitor_data = None
    if selected_competitor_id:
        try:
            competitor = available_competitors.get(pk=selected_competitor_id)
            latest_data = ScrapedData.objects.filter(scraping_link__competitor=competitor).order_by('-publication_date')[:10]
            selected_competitor_data = {'name': competitor.name, 'data': latest_data}
        except Competitor.DoesNotExist:
            pass

    rating_trend_data = {}
    sentiment_breakdown_data = {}

    if selected_resort_for_comp:
        resort_reviews_chart_qs = base_review_qs.filter(resort=selected_resort_for_comp, review_date__range=(start_date, end_date))
        resort_rating_trend = resort_reviews_chart_qs.annotate(month=TruncMonth('review_date')).values('month').annotate(avg_rating=Avg('rating')).order_by('month')
        resort_sentiment_counts = ReviewAnalysis.objects.filter(review__in=resort_reviews_chart_qs).values('sentiment_label').annotate(count=Count('id'))
        rating_trend_data['my_resort'] = {item['month'].strftime('%Y-%m'): float(item['avg_rating']) for item in resort_rating_trend if item['month'] and item['avg_rating'] is not None}
        sentiment_breakdown_data['my_resort'] = {item['sentiment_label']: item['count'] for item in resort_sentiment_counts}

        if selected_competitor_data:
            competitor_scraped_data = ScrapedData.objects.filter(scraping_link__competitor_id=selected_competitor_id, publication_date__range=(start_date, end_date))
            comp_rating_trend = competitor_scraped_data.annotate(month=TruncMonth('publication_date')).values('month').annotate(avg_rating=Avg('rating')).order_by('month')
            comp_sentiment_counts = CompetitorDataAnalysis.objects.filter(scraped_data__in=competitor_scraped_data).values('sentiment_label').annotate(count=Count('id'))
            rating_trend_data['competitor'] = {item['month'].strftime('%Y-%m'): float(item['avg_rating']) for item in comp_rating_trend if item['month'] and item['avg_rating'] is not None}
            sentiment_breakdown_data['competitor'] = {item['sentiment_label']: item['count'] for item in comp_sentiment_counts}

    context = {
        'kpis': kpis,
        'chart_labels': all_days,
        'maintenance_data': maintenance_data,
        'it_data': it_data,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'page_title': "Cruscotto Direzione",

        # Competitor analysis context
        'competitor_user_resorts': user_resorts,
        'competitor_selected_resort': selected_resort_for_comp,
        'competitor_available': available_competitors,
        'competitor_selected_data': selected_competitor_data,
        'selected_competitor_id': selected_competitor_id,

        # Chart data
        'rating_trend_data': json.dumps(rating_trend_data),
        'sentiment_breakdown_data': json.dumps(sentiment_breakdown_data),
    }
    return themed_render(request, 'core/director_cockpit.html', context)


def maintenance_page_view(request):
    """
    Renders the maintenance page.
    This page should be accessible even when maintenance mode is on.
    """
    settings = PlatformSettings.load()
    context = {
        'platform_settings': settings
    }
    # We pass a 503 status code to inform search engines that the site is temporarily down.
    return render(request, 'core/maintenance.html', context=context, status=503)
