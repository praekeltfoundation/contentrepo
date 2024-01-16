from .base import *  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

<<<<<<< HEAD

=======
#WHATSAPP_API_URL = "http://whatsapp"
#WHATSAPP_ACCESS_TOKEN = "fake-access-token"  # noqa: S105 (This is a test config.)
#FB_BUSINESS_ID = "27121231234"
>>>>>>> main


# We default to using local memory for dev and tests, so that Redis isn't a dependancy
# We test against Redis in the CI
CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}
