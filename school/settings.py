import os
from datetime import timedelta, date
from pathlib import Path

import dj_database_url
import environ
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import MinValueValidator

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------
# No default: the app must fail loudly if SECRET_KEY is missing.
SECRET_KEY = env("SECRET_KEY")

# Safe default: set DEBUG=True explicitly in your local .env only.
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
render_hostname = env("RENDER_EXTERNAL_HOSTNAME", default="").strip()
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

# Needed if your frontend posts to Django (e.g. admin) from another domain.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
TENANCY_PREPARATION = env.bool("TENANCY_PREPARATION", default=False)
TENANCY_ENABLED = env.bool("TENANCY_ENABLED", default=False)
TENANCY_CONFIGURED = TENANCY_PREPARATION or TENANCY_ENABLED
TENANCY_DATA_MIGRATION_COMPLETE = env.bool(
    "TENANCY_DATA_MIGRATION_COMPLETE", default=False
)
TENANT_SUBFOLDER_PREFIX = "t"

DATE_VALIDATORS = [MinValueValidator(date(1970, 1, 1))]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
LEGACY_INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "academic.apps.AcademicConfig",
    "administration.apps.AdministrationConfig",
    "attendance.apps.AttendanceConfig",
    "examination.apps.ExaminationConfig",
    "finance.apps.FinanceConfig",
    "notes.apps.NotesConfig",
    "schedule.apps.ScheduleConfig",
    "sis.apps.SisConfig",
    "users.apps.UsersConfig",
]

SHARED_APPS = [
    "django_tenants",
    "tenants.apps.TenantsConfig",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "administration.apps.AdministrationConfig",
    "users.apps.UsersConfig",
]

TENANT_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "academic.apps.AcademicConfig",
    "administration.apps.AdministrationConfig",
    "attendance.apps.AttendanceConfig",
    "examination.apps.ExaminationConfig",
    "finance.apps.FinanceConfig",
    "notes.apps.NotesConfig",
    "schedule.apps.ScheduleConfig",
    "sis.apps.SisConfig",
]

if TENANCY_CONFIGURED:
    if TENANCY_ENABLED and not TENANCY_DATA_MIGRATION_COMPLETE:
        raise ImproperlyConfigured(
            "Set TENANCY_DATA_MIGRATION_COMPLETE only after existing school data "
            "has been migrated and verified in PostgreSQL tenant schemas."
        )

    if dj_database_url.parse(
        env("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=not DEBUG,
    )["ENGINE"] != "django.db.backends.postgresql":
        raise ImproperlyConfigured(
            "django-tenants requires DATABASE_URL to point to PostgreSQL."
        )

    INSTALLED_APPS = list(SHARED_APPS) + [
        app for app in TENANT_APPS if app not in SHARED_APPS
    ]
else:
    INSTALLED_APPS = [
        *LEGACY_INSTALLED_APPS,
        "tenants.apps.TenantsConfig",
    ]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "api.middleware.CustomExceptionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tenants.middleware.TenantMembershipMiddleware",
    'utils.middleware.CurrentRequestMiddleware',
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "school.urls"
TENANT_MODEL = "tenants.SchoolTenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"

if TENANCY_CONFIGURED:
    DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

if TENANCY_ENABLED:
    PUBLIC_SCHEMA_URLCONF = "school.public_urls"
    MIDDLEWARE.insert(0, "django_tenants.middleware.subfolder.TenantSubfolderMiddleware")

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "static/dist"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "school.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# SSL is required in production (Render) but not for a local Postgres.
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=not DEBUG,
    )
}
if TENANCY_CONFIGURED:
    DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kampala"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATICFILES_DIRS = [BASE_DIR / "static"]
DIST_ASSETS_DIR = BASE_DIR / "static" / "dist" / "assets"
if DIST_ASSETS_DIR.is_dir():
    STATICFILES_DIRS.append(DIST_ASSETS_DIR)

STATIC_ROOT = BASE_DIR / "staticfiles"

# NOTE: Render's disk is ephemeral, so files in MEDIA_ROOT are lost on every
# redeploy. Move uploads to S3, Cloudinary or similar before real use.
MEDIA_ROOT = BASE_DIR / "media"

# Requires Django 4.2+. (Replaces the deprecated STATICFILES_STORAGE setting.)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework + JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # Locked down by default. Public views (e.g. login) must opt in with
    # permission_classes = [AllowAny].
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "tenants.authentication.SchoolJWTAuthentication",
    ),
    "EXCEPTION_HANDLER": "api.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Open only in local development. In production, set CORS_ALLOWED_ORIGINS,
# e.g. CORS_ALLOWED_ORIGINS=https://school.example.com,https://www.example.com
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

AUTH_USER_MODEL = "users.CustomUser"

INTERNAL_IPS = [
    "127.0.0.1",
]

# ---------------------------------------------------------------------------
# Production security (only when DEBUG is False)
# ---------------------------------------------------------------------------
if not DEBUG:
    # Render terminates SSL at its proxy; without this header setting the
    # redirect below loops forever.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ---------------------------------------------------------------------------
# Jazzmin configuration
# ---------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    # Title & Branding
    "site_title": "School Management Portal",
    "site_header": "School Administration",
    "site_brand": "School Management",
    "site_logo": None,
    "welcome_sign": "Welcome back, Administrator!",
    "copyright": "School Management System",

    # Search model configuration
    "search_model": ["users.customuser", "academic.classlevel"],

    # Top Menu Links
    "topmenu_links": [
        {"name": "Home", "url": "/admin/", "icon": "fas fa-home"},
        {"name": "View Live Site", "url": "/", "new_window": True, "icon": "fas fa-globe"},
    ],

    # User Menu
    "usermenu_links": [
        {
            "name": "Support",
            "url": "https://github.com/Kabuna31/SCHOOL_SYSTEM",
            "new_window": True,
            "icon": "fas fa-question-circle",
        },
        {"name": "Profile & Account", "url": "/admin/users/customuser/", "icon": "fas fa-user-shield"},
    ],

    # Sidebar icon mapping
    "icons": {
        "auth": "fas fa-users-cog",
        "users.customuser": "fas fa-user-shield",
        "users.accountant": "fas fa-calculator",
        "administration.school": "fas fa-school",
        "academic.allocatedsubject": "fas fa-book-open",
        "academic.classlevel": "fas fa-layer-group",
        "academic.classroom": "fas fa-door-open",
        "academic.classyear": "fas fa-calendar-alt",
        "academic.department": "fas fa-building",
        "academic.dormitory": "fas fa-bed",
        "academic.dormitoryallocation": "fas fa-clipboard-list",
        "academic.gradelevel": "fas fa-award",
        "academic.parent": "fas fa-user-friends",
        "academic.messagetoparent": "fas fa-sms",
        "academic.messagetoteacher": "fas fa-comments",
        "academic.subject": "fas fa-book",
        "academic.teacher": "fas fa-chalkboard-teacher",
        "attendance": "fas fa-user-check",
        "attendance.studentattendance": "fas fa-user-check",
        "attendance.teachersattendance": "fas fa-user-clock",
        "examination": "fas fa-file-alt",
        "examination.result": "fas fa-poll",
        "finance": "fas fa-wallet",
        "finance.payment": "fas fa-money-bill-wave",
        "finance.receipt": "fas fa-receipt",
        "notes": "fas fa-sticky-note",
        "notes.assignment": "fas fa-tasks",
        "sis": "fas fa-graduation-cap",
        "sis.student": "fas fa-user-graduate",
    },

    # UI tweaks & layout
    "show_sidebar": True,
    "navigation_expanded": True,
    "related_modal_active": True,
    "custom_css": "css/custom_admin.css",
    "custom_js": None,
    "show_ui_builder": False,

    # UI theme options
    "theme": "pulse",
    "default_theme_mode": "auto",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-navy",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-navy",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_fixed": True,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
}
