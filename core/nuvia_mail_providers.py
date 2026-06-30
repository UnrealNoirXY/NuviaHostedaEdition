from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional
from uuid import uuid4
from urllib.parse import urlencode
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from imapclient import IMAPClient

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import NuviaMailAccount


class NuviaMailProviderError(Exception):
    """Typed error raised by provider adapters."""


@dataclass
class ProviderTokenResult:
    access_token: str
    refresh_token: str
    expires_at: timezone.datetime


@dataclass
class ProviderSendResult:
    provider_message_id: str


class ProviderAdapter(ABC):
    """Base adapter contract for Nuvia Mail providers (Phase 6 foundation)."""

    def __init__(self, account: Optional[NuviaMailAccount]):
        self.account = account

    @abstractmethod
    def authorize_url(self, *, state: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def exchange_code(self, *, code: str) -> ProviderTokenResult:
        raise NotImplementedError

    @abstractmethod
    def refresh_access_token(self, *, refresh_token: str) -> ProviderTokenResult:
        raise NotImplementedError

    @abstractmethod
    def list_folders(self):
        raise NotImplementedError

    @abstractmethod
    def list_messages_delta(self, *, cursor: Optional[str] = None, folder_id: Optional[str] = None):
        raise NotImplementedError

    @abstractmethod
    def get_message(self, *, message_id: str):
        raise NotImplementedError

    @abstractmethod
    def send_message(self, *, to_email: str, subject: str, body: str) -> ProviderSendResult:
        raise NotImplementedError

    @abstractmethod
    def test_authentication(self) -> bool:
        raise NotImplementedError


class ImapSmtpAdapter(ProviderAdapter):
    def test_authentication(self) -> bool:
        if not self.account:
            return False
        try:
            # Test IMAP
            with self._get_imap_client() as client:
                client.noop()

            # Test SMTP
            server_class = smtplib.SMTP_SSL if self.account.use_ssl else smtplib.SMTP
            with server_class(self.account.smtp_host, self.account.smtp_port, timeout=5) as server:
                if self.account.use_starttls and not self.account.use_ssl:
                    server.starttls()
                server.login(self.account.username or self.account.email_address, self.account.get_password())
            return True
        except Exception as e:
            raise NuviaMailProviderError(f"Autenticazione fallita: {str(e)}")

    def authorize_url(self, *, state: str) -> str:
        return ''

    def exchange_code(self, *, code: str) -> ProviderTokenResult:
        raise NuviaMailProviderError('IMAP/SMTP non supporta OAuth code exchange nativo.')

    def refresh_access_token(self, *, refresh_token: str) -> ProviderTokenResult:
        raise NuviaMailProviderError('IMAP/SMTP non supporta refresh token OAuth nativo.')

    def _get_imap_client(self):
        if not self.account:
            raise NuviaMailProviderError("Account non configurato.")
        try:
            client = IMAPClient(self.account.imap_host, port=self.account.imap_port, use_uid=True, ssl=self.account.use_ssl)
            client.login(self.account.username or self.account.email_address, self.account.get_password())
            return client
        except Exception as e:
            raise NuviaMailProviderError(f"Errore connessione IMAP: {str(e)}")

    def list_folders(self):
        with self._get_imap_client() as client:
            folders = client.list_folders()
            result = []
            for attrs, delimiter, name in folders:
                is_inbox = 'INBOX' in name.upper()
                is_sent = any(s in name.upper() for s in ['SENT', 'INVIATA', 'INVIATI'])
                result.append({
                    'id': name,
                    'name': name,
                    'is_inbox': is_inbox,
                    'is_sent': is_sent
                })
            return result

    def list_messages_delta(self, *, cursor: Optional[str] = None, folder_id: Optional[str] = None):
        folder = folder_id or 'INBOX'
        with self._get_imap_client() as client:
            client.select_folder(folder, readonly=True)
            # Simple implementation: fetch last 50 messages if no cursor
            if not cursor:
                messages = client.search(['ALL'])
                messages = sorted(messages, reverse=True)[:50]
            else:
                try:
                    messages = client.search(['UID', f'{cursor}:*'])
                except Exception:
                    messages = client.search(['ALL'])
                    messages = sorted(messages, reverse=True)[:50]

            if not messages:
                return {'messages': [], 'next_cursor': cursor or ''}

            fetch_data = client.fetch(messages, ['ENVELOPE', 'RFC822.TEXT'])

            result_messages = []
            max_uid = int(cursor) if cursor and cursor.isdigit() else 0
            for uid, data in fetch_data.items():
                env = data[b'ENVELOPE']
                max_uid = max(max_uid, uid)
                result_messages.append({
                    'provider_message_id': str(uid),
                    'subject': env.subject.decode(errors='ignore') if env.subject else '',
                    'from_email': f"{env.from_[0].mailbox.decode()}@{env.from_[0].host.decode()}" if env.from_ else '',
                    'received_at': env.date,
                    'body_text': data.get(b'RFC822.TEXT', b'').decode(errors='ignore'),
                })

            return {'messages': result_messages, 'next_cursor': str(max_uid + 1)}

    def get_message(self, *, message_id: str):
        # Implementation for full message retrieval
        pass

    def send_message(self, *, to_email: str, subject: str, body: str) -> ProviderSendResult:
        if not self.account:
            # Fallback for testing/system notifications if no account is linked
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
            return ProviderSendResult(provider_message_id=f"sys_{uuid4().hex}")
        try:
            msg = MIMEMultipart()
            msg['From'] = self.account.email_address
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server_class = smtplib.SMTP_SSL if self.account.use_ssl else smtplib.SMTP
            with server_class(self.account.smtp_host, self.account.smtp_port) as server:
                if self.account.use_starttls and not self.account.use_ssl:
                    server.starttls()
                server.login(self.account.username or self.account.email_address, self.account.get_password())
                server.send_message(msg)

            return ProviderSendResult(provider_message_id=uuid4().hex)
        except Exception as e:
            raise NuviaMailProviderError(f"Errore invio SMTP: {str(e)}")


class _OAuthBaseAdapter(ProviderAdapter):
    provider_name = 'oauth'
    authorize_endpoint = ''
    token_endpoint = ''
    scopes = []

    def authorize_url(self, *, state: str) -> str:
        if not self.authorize_endpoint:
            raise NuviaMailProviderError(f'{self.provider_name} authorize endpoint non configurato.')

        client_id = getattr(settings, f'NUVIA_MAIL_{self.provider_name.upper()}_CLIENT_ID', 'dummy_id')
        redirect_uri = f"{settings.BASE_URL}/api/nuvia-mail/accounts/oauth/callback/"

        params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': ' '.join(self.scopes),
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        return f'{self.authorize_endpoint}?{urlencode(params)}'

    def exchange_code(self, *, code: str) -> ProviderTokenResult:
        if getattr(settings, 'NUVIA_MAIL_ENABLE_DEMO_OAUTH', True):
            return build_demo_token_result()

        import requests
        client_id = getattr(settings, f'NUVIA_MAIL_{self.provider_name.upper()}_CLIENT_ID', '')
        client_secret = getattr(settings, f'NUVIA_MAIL_{self.provider_name.upper()}_CLIENT_SECRET', '')
        redirect_uri = f"{settings.BASE_URL}/api/nuvia-mail/accounts/oauth/callback/"

        data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }

        response = requests.post(self.token_endpoint, data=data)
        if not response.ok:
            raise NuviaMailProviderError(f"Errore scambio codice {self.provider_name}: {response.text}")

        res_data = response.json()
        return ProviderTokenResult(
            access_token=res_data['access_token'],
            refresh_token=res_data.get('refresh_token', ''),
            expires_at=timezone.now() + timedelta(seconds=res_data.get('expires_in', 3600))
        )

    def refresh_access_token(self, *, refresh_token: str) -> ProviderTokenResult:
        if getattr(settings, 'NUVIA_MAIL_ENABLE_DEMO_OAUTH', True):
            return build_demo_token_result()

        import requests
        client_id = getattr(settings, f'NUVIA_MAIL_{self.provider_name.upper()}_CLIENT_ID', '')
        client_secret = getattr(settings, f'NUVIA_MAIL_{self.provider_name.upper()}_CLIENT_SECRET', '')

        data = {
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token'
        }

        response = requests.post(self.token_endpoint, data=data)
        if not response.ok:
            raise NuviaMailProviderError(f"Errore refresh token {self.provider_name}: {response.text}")

        res_data = response.json()
        return ProviderTokenResult(
            access_token=res_data['access_token'],
            refresh_token=res_data.get('refresh_token', refresh_token),
            expires_at=timezone.now() + timedelta(seconds=res_data.get('expires_in', 3600))
        )

    def list_folders(self):
        # Implementation depends on API (Gmail vs Graph)
        raise NuviaMailProviderError(f'{self.provider_name} list_folders non ancora implementato.')

    def list_messages_delta(self, *, cursor: Optional[str] = None, folder_id: Optional[str] = None):
        raise NuviaMailProviderError(f'{self.provider_name} delta sync non ancora implementato.')

    def get_message(self, *, message_id: str):
        raise NuviaMailProviderError(f'{self.provider_name} get_message non ancora implementato.')

    def send_message(self, *, to_email: str, subject: str, body: str) -> ProviderSendResult:
        raise NuviaMailProviderError(f'{self.provider_name} send_message non ancora implementato.')

    def test_authentication(self) -> bool:
        if not self.account: return False
        try:
            # For OAuth, just try to list folders to verify token
            self.list_folders()
            return True
        except Exception as e:
            raise NuviaMailProviderError(f"Token OAuth non valido o scaduto: {str(e)}")


class GoogleWorkspaceAdapter(_OAuthBaseAdapter):
    provider_name = 'google'
    authorize_endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'
    token_endpoint = 'https://oauth2.googleapis.com/token'
    scopes = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/userinfo.email'
    ]

    def _get_service(self):
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials

        access_token, _ = self.account.get_oauth_tokens()
        if '...' in access_token:
            from django.conf import settings
            if getattr(settings, 'NUVIA_MAIL_ENABLE_DEMO_OAUTH', True):
                access_token = "demo_token"
        creds = Credentials(token=access_token)
        return build('gmail', 'v1', credentials=creds)

    def list_folders(self):
        service = self._get_service()
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        return [{
            'id': l['id'],
            'name': l['name'],
            'is_inbox': l['id'] == 'INBOX',
            'is_sent': l['id'] == 'SENT'
        } for l in labels]

    def list_messages_delta(self, *, cursor: Optional[str] = None, folder_id: Optional[str] = None):
        service = self._get_service()
        query = f'label:{folder_id}' if folder_id else 'label:INBOX'
        results = service.users().messages().list(userId='me', q=query, maxResults=50, pageToken=cursor).execute()

        messages = results.get('messages', [])
        result_messages = []
        for msg_meta in messages:
            msg = service.users().messages().get(userId='me', id=msg_meta['id']).execute()
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')

            result_messages.append({
                'provider_message_id': msg['id'],
                'provider_thread_id': msg['threadId'],
                'subject': subject,
                'from_email': from_email,
                'received_at': timezone.datetime.fromtimestamp(int(msg['internalDate'])/1000, tz=timezone.utc),
                'body_text': msg.get('snippet', ''),
            })

        return {'messages': result_messages, 'next_cursor': results.get('nextPageToken')}

    def send_message(self, *, to_email: str, subject: str, body: str) -> ProviderSendResult:
        import base64
        from email.message import EmailMessage
        service = self._get_service()

        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_email
        message['From'] = self.account.email_address
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        send_res = service.users().messages().send(userId='me', body=create_message).execute()
        return ProviderSendResult(provider_message_id=send_res['id'])


class Microsoft365Adapter(_OAuthBaseAdapter):
    provider_name = 'microsoft'
    authorize_endpoint = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
    token_endpoint = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
    scopes = ['https://graph.microsoft.com/Mail.Read', 'https://graph.microsoft.com/Mail.Send', 'offline_access', 'User.Read']

    def _get_access_token(self):
        access_token, refresh_token = self.account.get_oauth_tokens()
        # Handle masked/demo tokens
        if '...' in access_token:
            from django.conf import settings
            if getattr(settings, 'NUVIA_MAIL_ENABLE_DEMO_OAUTH', True):
                return "demo_token"
        return access_token

    def list_folders(self):
        import requests
        token = self._get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        res = requests.get('https://graph.microsoft.com/v1.0/me/mailFolders', headers=headers)
        if not res.ok:
            raise NuviaMailProviderError(f"Graph API error: {res.text}")

        folders = res.json().get('value', [])
        return [{
            'id': f['id'],
            'name': f['displayName'],
            'is_inbox': f['displayName'].lower() == 'inbox',
            'is_sent': f['displayName'].lower() == 'sent items'
        } for f in folders]

    def list_messages_delta(self, *, cursor: Optional[str] = None, folder_id: Optional[str] = None):
        import requests
        token = self._get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        url = cursor if cursor else f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id or 'inbox'}/messages?$top=50"

        res = requests.get(url, headers=headers)
        if not res.ok:
            raise NuviaMailProviderError(f"Graph API error: {res.text}")

        data = res.json()
        messages = data.get('value', [])
        result_messages = []
        for msg in messages:
            result_messages.append({
                'provider_message_id': msg['id'],
                'provider_thread_id': msg['conversationId'],
                'subject': msg['subject'],
                'from_email': msg['from']['emailAddress']['address'],
                'received_at': msg['receivedDateTime'],
                'body_text': msg.get('bodyPreview', ''),
            })

        return {'messages': result_messages, 'next_cursor': data.get('@odata.nextLink')}

    def send_message(self, *, to_email: str, subject: str, body: str) -> ProviderSendResult:
        import requests
        token = self._get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            }
        }
        res = requests.post('https://graph.microsoft.com/v1.0/me/sendMail', headers=headers, json=payload)
        if not res.ok:
            raise NuviaMailProviderError(f"Graph API error: {res.text}")

        return ProviderSendResult(provider_message_id=uuid4().hex) # Graph sendMail doesn't return ID in body


def build_demo_token_result() -> ProviderTokenResult:
    return ProviderTokenResult(
        access_token=f'access_{uuid4().hex}',
        refresh_token=f'refresh_{uuid4().hex}',
        expires_at=timezone.now() + timedelta(hours=1),
    )


def get_provider_adapter(account: Optional[NuviaMailAccount]) -> ProviderAdapter:
    provider = account.provider if account else NuviaMailAccount.PROVIDER_IMAP
    if provider == NuviaMailAccount.PROVIDER_GOOGLE:
        return GoogleWorkspaceAdapter(account)
    if provider == NuviaMailAccount.PROVIDER_MICROSOFT:
        return Microsoft365Adapter(account)
    return ImapSmtpAdapter(account)
