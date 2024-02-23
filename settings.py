################################################################################
################################################################################

# Please do not modify this file, it will be reset at the next update.
# You can edit the file /opt/yunohost/ultimate_ladder/local_settings.py and add/modify the settings you need.
# The parameters you add in local_settings.py will overwrite these,
# but you can use the options and documentation in this file to find out what can be done.

################################################################################
################################################################################

from pathlib import Path as __Path
import os
from ultimate_ladder.settings import *  # noqa:F401,F403

current_dir=os.path.dirname(__file__)

FINALPATH = current_dir
PUBLIC_PATH = current_dir
LOG_FILE = current_dir+"/ultimate_ladder/ultimate_ladder.log"

PATH_URL = '/ultimate_ladder'  # $YNH_APP_ARG_PATH
PATH_URL = PATH_URL.strip('/')

DEBUG_ENABLED = '1'
DEBUG = bool(int(DEBUG_ENABLED))

LOG_LEVEL = 'WARNING'
ADMIN_EMAIL = 'admin@example.com'
DEFAULT_FROM_EMAIL = 'admin@example.com'


# -----------------------------------------------------------------------------

# Function that will be called to finalize a user profile:
SECRET_KEY = 'django-insecure-d9oorxbcx!a!x+x=36v5q3!q&5sbt$rcbg&qr9&69$rh#$-fe!'


ROOT_URLCONF = 'urls'

# -----------------------------------------------------------------------------

ADMINS = (('admin', ADMIN_EMAIL),)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Title of site to use
SITE_TITLE = 'ultimate_ladder'

# Site domain
SITE_DOMAIN = 'trahay.nohost.me'

# Subject of emails includes site title
EMAIL_SUBJECT_PREFIX = f'[{SITE_TITLE}] '


# E-mail address that error messages come from.
SERVER_EMAIL = ADMIN_EMAIL

# Default email address to use for various automated correspondence from
# the site managers. Used for registration emails.

# List of URLs your site is supposed to serve
ALLOWED_HOSTS = []

# _____________________________________________________________________________
# Static files (CSS, JavaScript, Images)

if PATH_URL:
    STATIC_URL = f'/{PATH_URL}/static/'
    MEDIA_URL = f'/{PATH_URL}/media/'
else:
    # Installed to domain root, without a path prefix?
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'

STATIC_ROOT = str(PUBLIC_PATH + '/static')
MEDIA_ROOT = str(PUBLIC_PATH + '/media')


# -----------------------------------------------------------------------------

try:
    from local_settings import *  # noqa:F401,F403
except ImportError:
    pass
