from .dev import *  # noqa


DATABASES = {"default": env.db("CONTENTREPO_DATABASE", default="sqlite://:memory:")}
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

WHATSAPP_API_URL = "http://whatsapp"
WHATSAPP_ACCESS_TOKEN = "fake-access-token"  # noqa: S105 (This is a test config.)
FB_BUSINESS_ID = "27121231234"

WHATSAPP_CREATE_TEMPLATES = False
