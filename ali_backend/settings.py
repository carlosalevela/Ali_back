"""
Django settings for ali_backend project.
Compatibles con Azure App Service (Linux) y entorno local.
Django 5.1.x
"""

from pathlib import Path
from datetime import timedelta
import os

from decouple import config, Csv
import dj_database_url

# =========================
# Paths
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# Claves y flags
# =========================
SECRET_KEY = config('SECRET_KEY')  # Defínela en Azure / .env
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Opcional: cabecera para HTTPS detrás de proxy (Azure)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# =========================
# Apps
# =========================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_extensions',

    # Apps del proyecto
    'Usuario',
    'test_grado9',
    'test_grado_10_11',
]

AUTH_USER_MODEL = 'Usuario.Usuario'

# =========================
# DRF / JWT
# =========================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# =========================
# CORS
# =========================
CORS_ALLOW_ALL_ORIGINS = True  # Si quieres restringir, usa CORS_ALLOWED_ORIGINS desde env.

# =========================
# Middleware
# =========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # estáticos en Azure
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',        # CORS antes de CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =========================
# URLs / WSGI
# =========================
ROOT_URLCONF = 'ali_backend.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'ali_backend.wsgi.application'

# =========================
# Base de Datos
# Prioriza DATABASE_URL; fallback local
# =========================
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgres://postgres:Volcano21!@localhost:5432/psicoorientacion_bd'),
        conn_max_age=600,
        ssl_require=False  # cambia a True o usa ?sslmode=require si tu servidor lo exige
    )
}

# =========================
# Password validators
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =========================
# Internationalization
# =========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TIME_ZONE', default='UTC')  # si quieres: 'America/Bogota'
USE_I18N = True
USE_TZ = True

# =========================
# Static files (WhiteNoise)
# =========================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =========================
# Default PK
# =========================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# =========================
# Email / Password reset
# =========================
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = False  # con puerto 587 no se usa SSL
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='aliorientadora@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='ALI Soporte <no-reply@tu-dominio.com>')

SITE_DOMAIN = config('SITE_DOMAIN', default='localhost:8000')
FRONTEND_RESET_URL = config('FRONTEND_RESET_URL', default='')
PASSWORD_RESET_TIMEOUT = config('PASSWORD_RESET_TIMEOUT', default=86400, cast=int)
FRONTEND_RESET_PATH = "/recuperacion/contrasena-confirmada"

# =========================
# Otros (APIs)
# =========================
GROQ_API_KEY = config('GROQ_API_KEY', default='')
