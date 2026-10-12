import os
import dj_database_url
import environ
from pathlib import Path
from datetime import timedelta, date
from django.core.validators import MinValueValidator  # Could use MaxValueValidator too

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "SECRET_KEY", default="2_5ub5rqi!%3v#xk$0e4z-jg22zg_$ejz&t3s0g$5lt*vvu!b@"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


DATE_VALIDATORS = [MinValueValidator(date(1970, 1, 1))]  # Unix epoch!


# Application definition

INSTALLED_APPS = [
    'jazzmin',
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
    "api.middleware.CustomExceptionMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
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


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/


STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATICFILES_DIRS = [
    BASE_DIR / "static",  # your app-level static (optional)
    BASE_DIR / "static/dist/assets",  # vite/react build output
]

STATIC_ROOT = BASE_DIR / "staticfiles"  # final destination after collectstatic
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_ROOT = BASE_DIR / "media"  # uploads

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "EXCEPTION_HANDLER": "api.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
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


CORS_ALLOW_ALL_ORIGINS = True

AUTH_USER_MODEL = "users.CustomUser"

INTERNAL_IPS = [
    "127.0.0.1",
]

JAZZMIN_SETTINGS = {
    "custom_css": "css/custom_admin.css",
    # Title & Branding
    "site_title": "School Management Portal",
    "site_header": "School Administration",
    "site_brand": "School Management",
    "site_logo": None,  # You can add a path to a logo image in your static files later if you want
    "welcome_sign": "Welcome back, Administrator!",
    "copyright": "School Management System",
    
    # Search model configuration
    "search_model": ["users.customuser", "academic.classlevel"],

    # Top Menu Links
    import os
import dj_database_url
import environ
from pathlib import Path
from datetime import timedelta, date
from django.core.validators import MinValueValidator  # Could use MaxValueValidator too

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "SECRET_KEY", default="2_5ub5rqi!%3v#xk$0e4z-jg22zg_$ejz&t3s0g$5lt*vvu!b@"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


DATE_VALIDATORS = [MinValueValidator(date(1970, 1, 1))]  # Unix epoch!


# Application definition

INSTALLED_APPS = [
    'jazzmin',
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
    "api.middleware.CustomExceptionMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
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


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/


STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATICFILES_DIRS = [
    BASE_DIR / "static",  # your app-level static (optional)
    BASE_DIR / "static/dist/assets",  # vite/react build output
]

STATIC_ROOT = BASE_DIR / "staticfiles"  # final destination after collectstatic
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_ROOT = BASE_DIR / "media"  # uploads

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "EXCEPTION_HANDLER": "api.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
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


CORS_ALLOW_ALL_ORIGINS = True

AUTH_USER_MODEL = "users.CustomUser"

INTERNAL_IPS = [
    "127.0.0.1",
]

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

    # Top Menu Links (Properly nested inside JAZZMIN_SETTINGS)
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"], "icon": "fas fa-home"},
        {"name": "View Live Site", "url": "/", "new_window": True, "icon": "fas fa-globe"},
    ],

    # User Menu (Includes Support & Profile with Icons)
    "usermenu_links": [
        {"name": "Support", "url": "https://github.com/Kabuna31/SCHOOL_SYSTEM", "new_window": True, "icon": "fas fa-question-circle"},
        {"model": "users.customuser", "icon": "fas fa-user-shield"},
    ],

    # --- SIDEBAR ICON MAPPING (Font Awesome 5/6) ---
    "icons": {
        # Authentication & Users
        "auth": "fas fa-users-cog",
        "users.customuser": "fas fa-user-shield",
        "users.accountant": "fas fa-calculator",
        
        # Administration & School Info
        "administration.school": "fas fa-school",
        
        # Academic Module
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
        
        # Attendance Module
        "attendance": "fas fa-user-check",
        "attendance.studentattendance": "fas fa-user-check",
        "attendance.teachersattendance": "fas fa-user-clock",
        
        # Examination Module
        "examination": "fas fa-file-alt",
        "examination.result": "fas fa-poll",
        
        # Finance Module
        "finance": "fas fa-wallet",
        "finance.payment": "fas fa-money-bill-wave",
        "finance.receipt": "fas fa-receipt",
        
        # Notes & Learning
        "notes": "fas fa-sticky-note",
        "notes.assignment": "fas fa-tasks",
        
        # SIS Module
        "sis": "fas fa-graduation-cap",
        "sis.student": "fas fa-user-graduate",
    },

    # UI Tweaks & Layout
    "show_sidebar": True,
    "navigation_expanded": True,
    "related_modal_active": True,
    "custom_css": "css/custom_admin.css",
    "custom_js": None,
    "show_ui_builder": False,
    
    # UI Theme Options
    "theme": "pulse",
    "dark_mode_theme": "darkly",
}

# Optional UI Customizations for Jazzmin UI Builder
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

# Top Menu Links
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"], "icon": "fas fa-home"},
        {"name": "View Live Site", "url": "/", "new_window": True, "icon": "fas fa-globe"},
    ],

    # User Menu (Includes Logout & Profile)
    "usermenu_links": [
        {"name": "Support", "url": "https://github.com/Kabuna31/SCHOOL_SYSTEM", "new_window": True, "icon": "fas fa-question-circle"},
        {"model": "users.customuser", "icon": "fas fa-user-shield"},
    ],

    # User Menu
    "usermenu_links": [
        {"name": "Support", "url": "https://github.com/Kabuna31/SCHOOL_SYSTEM", "new_window": True},
        {"model": "users.customuser"}
    ],

    # --- SIDEBAR ICON MAPPING (Font Awesome 5/6) ---
    "icons": {
        # Authentication & Users
        "auth": "fas fa-users-cog",
        "users.customuser": "fas fa-user-shield",
        "users.accountant": "fas fa-file-invoice-dollar",
        
        # Administration & School Info
        "administration.school": "fas fa-school",
        
        # Academic Module
        "academic.allocatedsubject": "fas fa-book-reader",
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
        
        # Other Modules
        "attendance": "fas fa-user-check",
        "examination": "fas fa-file-alt",
        "finance": "fas fa-wallet",
        "notes": "fas fa-sticky-note",
        "schedule": "fas fa-clock",
        "sis": "fas fa-graduation-cap",
    },

    # UI Tweaks & Layout
    "show_sidebar": True,
    "navigation_expanded": True,
    "related_modal_active": True,
    "custom_css": None,
    "custom_js": None,
    "show_ui_builder": False,  # Enables a live theme switcher widget in the bottom-right corner for admins!
    
    # UI Theme Options
    "theme": "pulse",  # Modern, clean Bootstrap theme (or try "flatly", "cosmo", "darkly")
    "dark_mode_theme": "darkly",
}

# Optional UI Customizations for Jazzmin UI Builder
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

