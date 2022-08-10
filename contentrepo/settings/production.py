from os.path import abspath, dirname, join

import dj_database_url

from .base import *  # noqa

DEBUG = True

PROJECT_ROOT = os.environ.get("PROJECT_ROOT") or dirname(dirname(abspath(__file__)))
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///%s" % (join(PROJECT_ROOT, "contentrepo.db"),)
    )
}

SECRET_KEY = env.str("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
