from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY', DEFAULT_SECRET_KEY)

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS', 'localhost')

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
