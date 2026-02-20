from dotenv import load_dotenv
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR / "vendor"))

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key")

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = []

FEATURES = {
    "ACCOUNTS": True,
    "PEOPLE": False,
    "BLOG": False,
    "SITEMAP": False,
    'ADMIN_PANEL': False,
    'DOCUMENTS': True
}

BASE_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.core',
    'widget_tweaks',
    'apps.documents',
]

BASE_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


if FEATURES['ACCOUNTS']:
    BASE_MIDDLEWARE += ['allauth.account.middleware.AccountMiddleware',]
    LOGIN_REDIRECT_URL = 'index'
    LOGIN_URL = 'account_login'
    AUTH_USER_MODEL = 'accounts.User'
    BASE_APPS.extend(
        [
            'apps.accounts',
            'allauth',
            'allauth.account'
        ]
    )

if FEATURES['PEOPLE']:
    BASE_APPS.append('apps.people')

if FEATURES['BLOG']:
    BASE_APPS.extend(
        [
            'ckeditor',
            'apps.blogs',

        ]
    )

if FEATURES['SITEMAP']:
    DOMAIN = "http://localhost:8000"
    BASE_APPS.extend(
        [
            'django.contrib.sites',
            'django.contrib.sitemaps',
            'apps.sitemaps.apps.SitemapsConfig',
        ]
    )
    SITE_ID = 1

if FEATURES['ADMIN_PANEL']:
    BASE_APPS.append('apps.admin_panel')


INSTALLED_APPS = BASE_APPS
MIDDLEWARE = BASE_MIDDLEWARE


ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.site_features',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

SESSION_COOKIE_AGE = 60 * 60 * 24 * 30

SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

STATIC_URL = 'static/'
ACCOUNT_SESSION_REMEMBER = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ACCOUNT_EMAIL_VERIFICATION = 'none'
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500000


STATICFILES_DIRS = [
    BASE_DIR / "static",
]
