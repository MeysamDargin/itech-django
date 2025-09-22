from pathlib import Path
import os
from decouple import config
from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default='True', cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework',
    'channels',
    'whitenoise.runserver_nostatic',
    # Local apps
    'accounts',
    'profiles',
    'otp',
    'ai',
    'articles',
    'comments',
    'following',
    'temporalBehavior',
    'feedback',
    'report',
    'search',
    # Uncomment if using django-celery-beat for dynamic schedules
    # 'django_celery_beat',
]

MIDDLEWARE = [
    'iTech.middleware.DisableCSRFCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  # Disabled via custom middleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'iTech.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Add BASE_DIR / 'templates' if you have global templates
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

WSGI_APPLICATION = 'iTech.wsgi.application'
ASGI_APPLICATION = 'iTech.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': config('DATABASE_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DATABASE_NAME', default=BASE_DIR / 'db.sqlite3'),
    }
}

# PostgreSQL overrides if configured
if config('DATABASE_ENGINE', default='') == 'django.db.backends.postgresql':
    DATABASES['default'].update({
        'USER': config('DATABASE_USER'),
        'PASSWORD': config('DATABASE_PASSWORD'),
        'HOST': config('DATABASE_HOST'),
        'PORT': config('DATABASE_PORT'),
    })

# MongoDB (for non-Django models)
MONGODB_URI = config('MONGODB_URI', default='mongodb://localhost:27017/itech')

# Channel Layers
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(config('REDIS_HOST', default='localhost'), int(config('REDIS_PORT', default=6379)))],
        },
    },
}

# Sessions
SESSION_COOKIE_NAME = 'sessionid'
SESSION_COOKIE_AGE = 157680000
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Internationalization
LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = config('USE_I18N', default=True, cast=bool)
USE_TZ = config('USE_TZ', default=True, cast=bool)

# Static and Media files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = config('CELERY_ACCEPT_CONTENT', cast=lambda v: [v] if isinstance(v, str) else v)
CELERY_TASK_SERIALIZER = config('CELERY_TASK_SERIALIZER')
CELERY_RESULT_SERIALIZER = config('CELERY_RESULT_SERIALIZER')
CELERY_TIMEZONE = config('CELERY_TIMEZONE')

# Celery Beat Schedule (static; use django-celery-beat for dynamic)
CELERY_BEAT_SCHEDULE = {
    'generate-user-embeddings-every-6-hours': {
        'task': 'ai.tasks.tasks.run_user_embedding',
        'schedule': crontab(minute=0, hour='*/6'),  # هر ۶ ساعت در دقیقه صفر
    },
}
# Uncomment for django-celery-beat (recommended for production)
# CELERYBEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'following': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'profiles': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Add for Celery debugging
        'celery': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Change to INFO in production
            'propagate': False,
        },
    },
}

# App-specific (e.g., from your env)
BASE_URL = config('BASE_URL', default='http://localhost:8001')
EMBEDDING_SERVER_URL = config('EMBEDDING_SERVER_URL')