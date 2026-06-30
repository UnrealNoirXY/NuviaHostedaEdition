"""
Django settings for gestione_manutenzioni project.
"""

from pathlib import Path
import os
import sys
import pymysql
import environ

# Initialize django-environ
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# --- Core Settings ---
SECRET_KEY = env('SECRET_KEY', default='django-insecure-dummy-key-for-testing')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'testserver'])
BASE_URL = env('BASE_URL', default='https://www.noirtech.online')
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    "https://noirtech.online",
    "https://www.noirtech.online",
])

# --- Security & Session Settings ---
# Allow the CSRF token cookie to be read by JavaScript
CSRF_COOKIE_HTTPONLY = False
# Use a shared domain for cookies to support www and non-www subdomains
SESSION_COOKIE_DOMAIN = env('SESSION_COOKIE_DOMAIN', default=None) # e.g., '.noirtech.online'
# Enforce secure cookies in production
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# --- API Keys ---
APIFY_API_TOKEN = env('APIFY_API_TOKEN', default=None)
WEB_PUSH_VAPID_PUBLIC_KEY = env('WEB_PUSH_VAPID_PUBLIC_KEY', default='')
WEB_PUSH_VAPID_PRIVATE_KEY = env('WEB_PUSH_VAPID_PRIVATE_KEY', default='')
WEB_PUSH_CONTACT_EMAIL = env('WEB_PUSH_CONTACT_EMAIL', default='mailto:support@noirtech.online')

# --- Database Configuration ---
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
}

# Application definition
INSTALLED_APPS = [
    'jazzmin',
    'accounts',
    'resort',
    'tickets',
    'core',
    'notifications',
    'reviews',
    'clients',
    'documents',
    'it_support',
    'assets',
    'svago',
    'communications',
    'purchase_orders',
    'inventory',
    'economato',
    'procedures',
    'competitors',
    'skills',
    'desk',
    'financials',
    'hr_portal',
    'bookings.apps.BookingsConfig',  # App per prenotazioni e check-in
    'menu_generator',
    'document_verification',
    'profile_cards',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'impersonate',
    'channels',
    'django_celery_beat',
    'django_celery_results',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_htmx',
    'django_vite',
    'rest_framework',
    'corsheaders',
]

SITE_ID = 1
AUTH_USER_MODEL = 'accounts.User'
ASGI_APPLICATION = 'gestione_manutenzioni.asgi.application'

if 'test' in sys.argv:
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
else:
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels_redis.core.RedisChannelLayer', 'CONFIG': {"hosts": [('127.0.0.1', 6379)]}}}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'hr_portal.middleware.StructuredLogMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'core.middleware.MaintenanceModeMiddleware',
    'core.middleware.UpdateLastSeenMiddleware',
    'core.middleware.GamerTagRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',
]

X_FRAME_OPTIONS = 'SAMEORIGIN'

ROOT_URLCONF = 'gestione_manutenzioni.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.active_chats_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'gestione_manutenzioni.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True

# --- Static files & Media ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    ("vite", os.path.join(BASE_DIR, "frontend", "dist")),
    os.path.join(BASE_DIR, 'static'),
]

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# --- Django Vite Configuration ---
# Allow forcing production assets even when DEBUG=True (e.g., on staging servers
# without a running Vite dev server) via DJANGO_VITE_DEV_MODE=False.
DJANGO_VITE_DEV_MODE = env.bool("DJANGO_VITE_DEV_MODE", default=False if DEBUG else False)

DJANGO_VITE = {
    "default": {
        # Dev server can be explicitly enabled by setting DJANGO_VITE_DEV_MODE=true.
        "dev_mode": DJANGO_VITE_DEV_MODE,
        "manifest_path": os.path.join(BASE_DIR, "frontend", "dist", ".vite", "manifest.json"),
        "static_url_prefix": "/vite/",
        "app_client_class": "core.vite.NuviaViteAppClient",
    }
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Email Configuration ---
# --- Email Configuration ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='webmaster@localhost')
HR_EMAIL_HOST = env('HR_EMAIL_HOST', default=EMAIL_HOST)
HR_EMAIL_PORT = env.int('HR_EMAIL_PORT', default=EMAIL_PORT)
HR_EMAIL_HOST_USER = env('HR_EMAIL_HOST_USER', default=EMAIL_HOST_USER)
HR_EMAIL_HOST_PASSWORD = env('HR_EMAIL_HOST_PASSWORD', default=EMAIL_HOST_PASSWORD)
HR_EMAIL_USE_TLS = env.bool('HR_EMAIL_USE_TLS', default=EMAIL_USE_TLS)
HR_EMAIL_USE_SSL = env.bool('HR_EMAIL_USE_SSL', default=EMAIL_USE_SSL)
HR_FROM_EMAIL = env('HR_FROM_EMAIL', default=DEFAULT_FROM_EMAIL)
SITE_NAME = env('SITE_NAME', default='Nuvia Program')

# --- Structured Logging & Observability ---
LOG_COLLECTOR_ENDPOINT = env("LOG_COLLECTOR_ENDPOINT", default="")
LOG_COLLECTOR_TOKEN = env("LOG_COLLECTOR_TOKEN", default="")

LOGGING_HANDLERS = ["console_json"]
if LOG_COLLECTOR_ENDPOINT:
    LOGGING_HANDLERS.append("collector")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "core.logging_utils.StructuredJsonFormatter"},
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
        "collector": {
            "class": "core.logging_utils.CollectorHTTPHandler",
            "formatter": "json",
            "endpoint": LOG_COLLECTOR_ENDPOINT,
            "token": LOG_COLLECTOR_TOKEN,
            "level": "INFO",
        },
    },
    "loggers": {
        "": {
            "handlers": LOGGING_HANDLERS,
            "level": "INFO",
        },
        "django": {
            "handlers": LOGGING_HANDLERS,
            "level": "INFO",
            "propagate": False,
        },
        "bookings": {"handlers": LOGGING_HANDLERS, "level": "INFO", "propagate": False},
    },
}


# --- Jazzmin (Admin Theme) Configuration ---
JAZZMIN_SETTINGS = {
    "site_title": "Noir Tools Kit Admin",
    "site_header": "Noir Tools Kit",
    "site_brand": "Noir Tools Kit",
    "welcome_sign": "Benvenuto in Noir Tools Kit",
    "copyright": "Noir Tools Kit Ltd",
    "theme": "darkly", "dark_mode_theme": "darkly", "show_ui_builder": True,
    "changeform_format": "horizontal_tabs", "related_modal_active": True,
    "ui_tweaks": {
        "navbar_small_text": False, "footer_small_text": False, "body_small_text": True,
        "brand_small_text": False, "brand_colour": "navbar-dark", "accent": "accent-primary",
        "navbar": "navbar-dark", "no_navbar_border": False, "navbar_fixed": True,
        "layout_boxed": False, "footer_fixed": False, "sidebar_fixed": True,
        "sidebar": "sidebar-dark-primary", "sidebar_nav_small_text": False,
        "sidebar_disable_expand": False, "sidebar_nav_child_indent": False,
        "sidebar_nav_compact_style": False, "sidebar_nav_legacy_style": False,
        "sidebar_nav_flat_style": False, "theme": "darkly", "dark_mode_theme": "darkly",
        "button_classes": {
            "primary": "btn-primary", "secondary": "btn-secondary", "info": "btn-info",
            "warning": "btn-warning", "danger": "btn-danger", "success": "btn-success"
        },
        "actions_sticky_top": True
    },
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Vai al Portale", "url": "home", "new_window": True},
    ],
    "order_with_respect_to": ["accounts", "clients", "resort", "tickets", "reviews"],
    "apps_order": {
        "accounts": 1, "clients": 2, "resort": 3, "tickets": 4,
        "reviews": 5, "notifications": 6, "auth": 7,
    },
    "icons": {
        "auth": "fas fa-users-cog", "auth.user": "fas fa-user", "auth.Group": "fas fa-users",
        "accounts.user": "fas fa-user-circle", "clients.company": "fas fa-building",
        "resort.resort": "fas fa-hotel", "resort.room": "fas fa-door-open",
        "tickets.ticket": "fas fa-ticket-alt", "reviews.review": "fas fa-star",
    },
}

# --- Celery Configuration ---
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_DEFAULT_QUEUE = env('CELERY_TASK_DEFAULT_QUEUE', default='menu-generator')

# --- Menu Creation Studio document retention ---
MENU_DOCUMENT_RETENTION_DAYS = env.int('MENU_DOCUMENT_RETENTION_DAYS', default=7)
MENU_DOCUMENT_MAX_AGE_DAYS = env.int('MENU_DOCUMENT_MAX_AGE_DAYS', default=30)

# --- Crispy Forms Configuration ---
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# --- Django REST Framework Configuration ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}

# --- CORS Headers Configuration ---
# In production, the frontend and backend are served from the same domain.
# However, to be flexible, we can allow requests from the main domain and its subdomains.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://\w+\.noirtech\.online$",
    r"^https://noirtech\.online$",
]
# Allow cookies to be sent with cross-origin requests
CORS_ALLOW_CREDENTIALS = True


# --- Login URL ---
LOGIN_URL = '/login/'
