import os
from datetime import timedelta, date
from pathlib import Path

import dj_database_url
import environ
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

# Needed if your frontend posts to Django (e.g. admin) from another domain.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

DATE_VALIDATORS = [MinValueValidator(date(1970, 1, 1))]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
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

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "api.middleware.CustomExceptionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "school.urls"

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

STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "static/dist/assets",
]

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
        "rest_framework_simplejwt.authentication.JWTAuthentication",
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
    "default_theme_mode": "auto",  # "light", "dark" or "auto" (follows the OS); replaces dark_mode_theme in Jazzmin 3.0.3+
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