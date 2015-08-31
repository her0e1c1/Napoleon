from napoleon.settings.base import *  # NOQA

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# python manage.py collectstatic --dry-run --noinput
# STATIC_ROOT = 'staticfiles'

# http://django-debug-toolbar.readthedocs.org/en/latest/installation.html
INTERNAL_IPS = ['127.0.0.1', '0.0.0.0', '192.168.56.1']
