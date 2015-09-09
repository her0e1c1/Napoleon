import dj_database_url
from napoleon.settings.base import *  # NOQA

# https://devcenter.heroku.com/articles/getting-started-with-django

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
ALLOWED_HOSTS = ['*']

DATABASES['default'] = dj_database_url.config()

STATIC_ROOT = 'staticfiles'

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SECURE = True

MIDDLEWARE_CLASSES += [
    'sslify.middleware.SSLifyMiddleware',
]


# https://ultimatedjango.com/learn-django/lessons/configure-error-logging-reporting/
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
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['sentry'],
            'level': 'WARNING',
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

WEBSOCKET_PROTOCOL = "wss"

REDIS_CHAT_EXPRITE_TIME = 60 * 60 * 24 * 7
