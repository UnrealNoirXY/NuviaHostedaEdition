from cryptography.fernet import Fernet
from django.conf import settings
import base64

def get_encryptor():
    # We use SECRET_KEY to derive a consistent key for Fernet
    # Fernet key must be 32 url-safe base64-encoded bytes
    key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].ljust(32, '0').encode())
    return Fernet(key)

def encrypt_value(value: str) -> str:
    if not value:
        return ""
    f = get_encryptor()
    return f.encrypt(value.encode()).decode()

def decrypt_value(token: str) -> str:
    if not token:
        return ""
    f = get_encryptor()
    try:
        return f.decrypt(token.encode()).decode()
    except Exception:
        return ""
