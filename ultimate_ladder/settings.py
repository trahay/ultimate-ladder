"""
Django settings for ultimate_ladder project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os
from pathlib import Path
from environs import Env  # new

env = Env()
env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

LOG_FILE = "/var/log/ultimate_ladder/ultimate_ladder.log"

PATH_URL = '/ladder'
PATH_URL = PATH_URL.strip('/')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

from django.core.management.utils import get_random_secret_key
SECRET_KEY = env.str(
    "SECRET_KEY", 
    default=get_random_secret_key(),
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

APP_NAME = "ultimate-ladder"

ALLOWED_HOSTS = ['127.0.0.1', '0.0.0.0', 'localhost']

SERVER_NAME=env.str("SERVER_NAME", default=None)
if not SERVER_NAME is None:
  ALLOWED_HOSTS.append(f'{SERVER_NAME}')
  CSRF_TRUSTED_ORIGINS = [f"https://{SERVER_NAME}"]

# Application definition

INSTALLED_APPS = [
    "ultimate_ladder.apps.UltimateLadderConfig",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ultimate_ladder.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'ultimate_ladder.wsgi.application'

#DATABASE_URL = 'sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

if env.str("POSTGRES_DB", default=None) is None:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print(DATABASES)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str("POSTGRES_DB"),
            'USER': env.str("POSTGRES_USER"),
            'PASSWORD': env.str("POSTGRES_PASSWORD"),
            'HOST': env.str("POSTGRES_HOST"),
            'PORT': 5432,  # default postgres port
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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

LOGIN_REDIRECT_URL = f'/{PATH_URL}/'


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
if PATH_URL:
    STATIC_URL = f'/{PATH_URL}/static/'
    MEDIA_ROOT = f'/{PATH_URL}/static/'
else:
   STATIC_URL = 'static/'
   STATIC_ROOT = 'static/'


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
