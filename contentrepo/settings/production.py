from .base import *

DEBUG = False

try:
    from .local import *
except ImportError:
    pass

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DATABASE_NAME','name'),
        'USER': os.environ.get('DATABASE_LOGIN','user'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', 'password'),
        'HOST': os.environ.get('DATABASE_HOST', ''),
        'PORT': '5432',  # Set to empty string for default.
        'CONN_MAX_AGE': 600,
    }
}
