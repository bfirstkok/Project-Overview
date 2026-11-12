import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Set SECRET_KEY in .env (see .env.example)')
    SECRET_KEY = get_random_secret_key()
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
CSRF_TRUSTED_ORIGINS = list(filter(None, os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')))
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'work.apps.WorkConfig']
INSTALLED_APPS += ['allauth', 'allauth.account', 'allauth.socialaccount', 'allauth.socialaccount.providers.openid_connect']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
MIDDLEWARE += ['allauth.account.middleware.AccountMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages', 'work.context.navigation']}}]
WSGI_APPLICATION = 'config.wsgi.application'
if os.getenv('DB_ENGINE', 'postgres') == 'sqlite':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.getenv('POSTGRES_DB', 'projectwork'), 'USER': os.getenv('POSTGRES_USER', 'projectwork'), 'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''), 'HOST': os.getenv('POSTGRES_HOST', 'db'), 'PORT': os.getenv('POSTGRES_PORT', '5432'), 'CONN_MAX_AGE': 60}}
AUTH_USER_MODEL = 'work.User'
AUTHENTICATION_BACKENDS = ['work.sso.LocalDevelopmentBackend', 'work.sso.SSOBackend']
ALLOW_LOCAL_LOGIN = os.getenv('ALLOW_LOCAL_LOGIN', 'false').lower() == 'true'
MICROSOFT_TENANT_ID = os.getenv('MICROSOFT_TENANT_ID', '').strip()
MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID', '').strip()
MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET', '')
MICROSOFT_SSO_READY = bool(MICROSOFT_TENANT_ID and MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET)
if MICROSOFT_TENANT_ID:
    import uuid
    try: uuid.UUID(MICROSOFT_TENANT_ID)
    except ValueError: raise ImproperlyConfigured('MICROSOFT_TENANT_ID must be the company tenant UUID, not common/organizations')
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_ADAPTER = 'work.sso.ClosedAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'work.sso.CorporateSocialAdapter'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_PROVIDERS = {'openid_connect': {'APPS': [{
    'provider_id': 'microsoft', 'name': 'Microsoft 365',
    'client_id': MICROSOFT_CLIENT_ID, 'secret': MICROSOFT_CLIENT_SECRET,
    'settings': {'server_url': f'https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/v2.0', 'token_auth_method': 'client_secret_post', 'fetch_userinfo': False, 'oauth_pkce_enabled': True, 'uid_field': 'oid'},
}]}} if MICROSOFT_SSO_READY else {}
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'th'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
