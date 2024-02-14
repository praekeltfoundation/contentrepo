from .base import *  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# We default to using local memory for dev and tests, so that Redis isn't a dependancy
# We test against Redis in the CI
CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
