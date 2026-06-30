import base64
import hashlib
import io
import json
import time
from pathlib import Path
import zipfile

from django.conf import settings
from django.urls import reverse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs7


_DEFAULT_ICON_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f"
    b"\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc```\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xb1\x00\x00"
    b"\x00\x00IEND\xaeB`\x82"
)


def _build_pass_payload(card, token):
    share_url = f"{settings.BASE_URL.rstrip('/')}" + reverse("profile_cards:public_profile", kwargs={"token": token.token})
    return {
        "formatVersion": 1,
        "organizationName": (
            getattr(card.template, "company_name", "") or getattr(settings, "SITE_NAME", "Noir Tools Kit")
        ),
        "description": f"Profilo di {card.first_name} {card.last_name}",
        "serialNumber": f"profile-card-{card.id}-v{getattr(card, 'applied_template_version', 1)}",
        "teamIdentifier": getattr(settings, "PROFILE_CARDS_APPLE_TEAM_IDENTIFIER", "UNSIGNED-MVP"),
        "passTypeIdentifier": getattr(settings, "PROFILE_CARDS_APPLE_PASS_TYPE_IDENTIFIER", "pass.noirtools.profile"),
        "foregroundColor": "rgb(255,255,255)",
        "backgroundColor": (getattr(card.template, "primary_color", None) or "#000000"),
        "labelColor": (getattr(card.template, "secondary_color", None) or "#ffffff"),
        "generic": {
            "primaryFields": [
                {
                    "key": "name",
                    "label": "Nome",
                    "value": f"{card.first_name} {card.last_name}",
                }
            ],
            "secondaryFields": [
                {"key": "role", "label": "Ruolo", "value": card.role},
                {"key": "email", "label": "Email", "value": card.email},
            ],
            "backFields": [
                {"key": "url", "label": "Profilo Online", "value": share_url},
                {"key": "dept", "label": "Reparto", "value": card.department or "-"},
            ],
        },
        "barcodes": [
            {
                "format": "PKBarcodeFormatQR",
                "message": share_url,
                "messageEncoding": "iso-8859-1",
                "altText": "Scansiona per il contatto",
            }
        ],
        # Fallback for older iOS
        "barcode": {
            "format": "PKBarcodeFormatQR",
            "message": share_url,
            "messageEncoding": "iso-8859-1",
        },
    }


def _has_signing_config():
    return bool(
        getattr(settings, "PROFILE_CARDS_APPLE_PASS_CERT_PATH", "")
        and getattr(settings, "PROFILE_CARDS_APPLE_PASS_KEY_PATH", "")
        and getattr(settings, "PROFILE_CARDS_APPLE_WWDR_CERT_PATH", "")
    )


def _build_manifest(bundle_files):
    return {
        filename: hashlib.sha1(content).hexdigest()
        for filename, content in sorted(bundle_files.items(), key=lambda item: item[0])
    }


def _sign_manifest(manifest_bytes):
    cert_path = Path(settings.PROFILE_CARDS_APPLE_PASS_CERT_PATH)
    key_path = Path(settings.PROFILE_CARDS_APPLE_PASS_KEY_PATH)
    wwdr_path = Path(settings.PROFILE_CARDS_APPLE_WWDR_CERT_PATH)
    key_password = getattr(settings, "PROFILE_CARDS_APPLE_PASS_KEY_PASSWORD", "")

    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    wwdr_cert = x509.load_pem_x509_certificate(wwdr_path.read_bytes())
    private_key = serialization.load_pem_private_key(
        key_path.read_bytes(),
        password=key_password.encode("utf-8") if key_password else None,
    )

    options = [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary]
    return (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(manifest_bytes)
        .add_signer(cert, private_key, hashes.SHA256())
        .add_certificate(wwdr_cert)
        .sign(serialization.Encoding.DER, options)
    )


def build_apple_pkpass(card, token):
    pass_payload = _build_pass_payload(card, token)

    bundle_files = {
        "pass.json": json.dumps(pass_payload, ensure_ascii=False, indent=2).encode("utf-8"),
        "icon.png": _DEFAULT_ICON_PNG,
        "icon@2x.png": _DEFAULT_ICON_PNG,
        "logo.png": _DEFAULT_ICON_PNG,
        "logo@2x.png": _DEFAULT_ICON_PNG,
    }

    has_signing = _has_signing_config()
    manifest_bytes = json.dumps(_build_manifest(bundle_files), ensure_ascii=False, indent=2).encode("utf-8")
    signature_bytes = _sign_manifest(manifest_bytes) if has_signing else None

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in bundle_files.items():
            zf.writestr(filename, content)
        zf.writestr("manifest.json", manifest_bytes)
        if signature_bytes:
            zf.writestr("signature", signature_bytes)
        else:
            zf.writestr(
                "README.txt",
                "Unsigned fallback pass. Configure PROFILE_CARDS_APPLE_* certificate settings for production signing.",
            )

    return mem.getvalue()


def _b64url(payload):
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _build_google_wallet_object(card, token):
    issuer_id = getattr(settings, "PROFILE_CARDS_GOOGLE_WALLET_ISSUER_ID", "").strip()
    class_suffix = getattr(settings, "PROFILE_CARDS_GOOGLE_WALLET_CLASS_SUFFIX", "profile_card").strip() or "profile_card"
    issuer_name = getattr(settings, "PROFILE_CARDS_GOOGLE_WALLET_ISSUER_NAME", "Noir Tools Kit").strip() or "Noir Tools Kit"
    object_id = f"{issuer_id}.profile_card_{card.id}_{token.id}"
    class_id = f"{issuer_id}.{class_suffix}"

    return {
        "id": object_id,
        "classId": class_id,
        "state": "active",
        "cardTitle": {"defaultValue": {"language": "it-IT", "value": f"{card.first_name} {card.last_name}"}},
        "subheader": {"defaultValue": {"language": "it-IT", "value": card.role}},
        "header": {"defaultValue": {"language": "it-IT", "value": issuer_name}},
        "barcode": {
            "type": "qrCode",
            "value": f"{settings.BASE_URL.rstrip('/')}" + reverse("profile_cards:public_profile", kwargs={"token": token.token}),
        },
        "textModulesData": [
            {
                "id": "email",
                "header": "Email",
                "body": card.email,
            }
        ],
    }


def _build_google_wallet_jwt(card, token):
    service_account_email = getattr(settings, "PROFILE_CARDS_GOOGLE_WALLET_CLIENT_EMAIL", "").strip()
    private_key_pem = getattr(settings, "PROFILE_CARDS_GOOGLE_WALLET_PRIVATE_KEY", "")
    private_key_path = getattr(settings, "PROFILE_CARDS_GOOGLE_WALLET_PRIVATE_KEY_PATH", "").strip()
    issuer_id = getattr(settings, "PROFILE_CARDS_GOOGLE_WALLET_ISSUER_ID", "").strip()

    if not (service_account_email and issuer_id and (private_key_pem or private_key_path)):
        return ""

    if private_key_path and not private_key_pem:
        private_key_pem = Path(private_key_path).read_text(encoding="utf-8")

    private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)

    now = int(time.time())
    claims = {
        "iss": service_account_email,
        "aud": "google",
        "typ": "savetowallet",
        "iat": now,
        "origins": [getattr(settings, "BASE_URL", "").rstrip("/")],
        "payload": {
            "genericObjects": [_build_google_wallet_object(card, token)],
        },
    }

    header = {"alg": "RS256", "typ": "JWT"}
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}.{_b64url(json.dumps(claims, separators=(',', ':')).encode('utf-8'))}"
    signature = private_key.sign(signing_input.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{_b64url(signature)}"


def build_google_wallet_url(token):
    custom = getattr(settings, "PROFILE_CARDS_GOOGLE_WALLET_URL", "").strip()
    if custom:
        return f"{custom.rstrip('/')}/{token.token}"

    jwt_token = _build_google_wallet_jwt(token.card, token)
    if jwt_token:
        return f"https://pay.google.com/gp/v/save/{jwt_token}"

    return reverse("profile_cards:public_profile", kwargs={"token": token.token}) + "?wallet=google"
