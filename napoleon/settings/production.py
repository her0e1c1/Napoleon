import dj_database_url
from napoleon.settings.base import *  # NOQA

# https://devcenter.heroku.com/articles/getting-started-with-django

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
ALLOWED_HOSTS = ['*']

DATABASES['default'] = dj_database_url.config()
