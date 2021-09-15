from .base import *  # noqa
import dj_database_url
from os.path import abspath, dirname, join


DEBUG = True

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': os.environ.get('DATABASE_NAME', 'name'),
#         'USER': os.environ.get('DATABASE_LOGIN', 'user'),
#         'PASSWORD': os.environ.get(
#             'DATABASE_PASSWORD', 'password'),
#         'HOST': os.environ.get('DATABASE_HOST', ''),
#         'PORT': '5432',
#         'CONN_MAX_AGE': 600,
#     }
# }
PROJECT_ROOT = os.environ.get("PROJECT_ROOT") or dirname(dirname(abspath(__file__)))
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///%s" % (join(PROJECT_ROOT, "contentrepo.db"),)
    )
}

SECRET_KEY = env.str("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
