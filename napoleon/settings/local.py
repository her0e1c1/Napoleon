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
