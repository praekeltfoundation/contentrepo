from .base import *

DEBUG = True

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

SECRET_KEY = os.environ.get(
    'SECRET_KEY', 'vg%%_7^bt(68qg50vgp^*f^&_(f)36k1vnyg%49n8*0s86hxj6')

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS', 'localhost')
