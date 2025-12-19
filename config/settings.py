"""ط¥ط¹ط¯ط§ط¯ط§طھ ظ…ط´ط±ظˆط¹ Django ظ„ظ€ task_exchange_project."""
from pathlib import Path

from django.contrib.messages import constants as messages

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["*"]


CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:8000", "http://localhost:8000","https://*.ondigitalocean.app"]

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts.apps.AccountsConfig",
    "apps.web",
    "apps.courses",
    "apps.assignments",
    "apps.submissions",
    "apps.messaging",  # ظ…ظ‡ظ…
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ar"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
# STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

MESSAGE_TAGS = {
    messages.DEBUG: "secondary",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

JAZZMIN_SETTINGS = {
    "site_title": "لوحة منصة المهام",
    "site_header": "منصة المهام",
    "site_brand": "منصة المهام",
    "welcome_sign": "مرحباً بك في لوحة التحكم",
    "search_model": "accounts.Profile",
    "rtl_support": True,
    "show_sidebar": True,
    "navigation_expanded": True,
    "related_modal_active": True,
    "topmenu_links": [
        {"name": "الرئيسية", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "الواجهة", "url": "web:home", "new_window": False},
    ],
    "usermenu_links": [
        {"name": "صفحتي", "url": "web:profile"},
    ],
    "order_with_respect_to": [
        "accounts.Profile",
        "accounts.Invitation",
        "accounts.SiteSetting",
        "courses.Course",
        "assignments.Assignment",
        "submissions.Submission",
        "submissions.SubmissionAttachment",
        "messaging.Conversation",
        "messaging.Message",
    ],
    "icons": {
        "accounts.Profile": "fas fa-id-badge",
        "accounts.Invitation": "fas fa-ticket-alt",
        "accounts.SiteSetting": "fas fa-cog",
        "courses.Course": "fas fa-book",
        "assignments.Assignment": "fas fa-tasks",
        "submissions.Submission": "fas fa-inbox",
        "submissions.Submissionattachment": "fas fa-paperclip",
        "messaging.Conversation": "fas fa-comments",
        "messaging.Message": "fas fa-comment-dots",
        "auth.User": "fas fa-user",
        "auth.Group": "fas fa-users",
    },
    "menu": [
        {"label": "الحسابات", "icon": "fas fa-users", "models": ("accounts.Profile", "accounts.Invitation", "accounts.SiteSetting")},
        {"label": "الدورات", "icon": "fas fa-book-open", "models": ("courses.Course",)},
        {"label": "الواجبات", "icon": "fas fa-tasks", "models": ("assignments.Assignment",)},
        {"label": "التسليمات", "icon": "fas fa-inbox", "models": ("submissions.Submission", "submissions.SubmissionAttachment")},
        {"label": "المراسلات", "icon": "fas fa-comments", "models": ("messaging.Conversation", "messaging.Message")},
        {"label": "إدارة المستخدمين", "icon": "fas fa-user-shield", "models": ("auth.User", "auth.Group")},
    ],
    "custom_links": {
        "assignments": [
            {
                "name": "إنشاء واجب",
                "url": "admin:assignments_assignment_add",
                "icon": "fas fa-plus",
            }
        ],
    },
    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
    "body_small_text": False,
    "navbar": "navbar-dark bg-primary",
    "footer_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": True,
    "brand_colour": "navbar-dark bg-primary",
    "actions_sticky_top": True,
}
