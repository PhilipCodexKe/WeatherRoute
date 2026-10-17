"""
Django settings for server project.
Stateless backend configured for Weather-Aware Truck Routing.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file into environment (stdlib only — no python-dotenv needed)
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _val.strip())


SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-weather-aware-truck-routing-secret-key-development'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'corsheaders',
    # Project apps
    'routing',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'server.urls'

WSGI_APPLICATION = 'server.wsgi.application'

# Fully stateless: No DB required for live routing/weather computation
DATABASES = {}

# In-memory caching for repeated weather queries
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'weather-routing-cache',
        'TIMEOUT': 900,  # 15 minutes default cache
    }
}

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'UNAUTHENTICATED_USER': None,
}

# CORS Configuration - permit React frontend during local dev
CORS_ALLOW_ALL_ORIGINS = True

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True

STATIC_URL = 'static/'
