from napoleon.settings.base import *  # NOQA
logger.info("Loading settings for local")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'kq@0rv+%=1@d^6w53+-24+p$^02%2@c28b+vv0rc&=#^hpgwsn'

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

FIXTURE_DIRS = [os.path.join(BASE_DIR, 'fixtures')]

WEBSOCKET_PROTOCOL = "ws"

TORNADO_PORT = 8001


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'WARNING',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['sentry'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'raven': {
            'level': 'WARNING',
            'handlers': ['sentry'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'WARNING',
            'handlers': ['sentry'],
            'propagate': False,
        },
    }
}
