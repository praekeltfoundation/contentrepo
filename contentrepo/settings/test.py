from .dev import *  # noqa


DATABASES = {"default": env.db("CONTENTREPO_DATABASE", default="sqlite://:memory:")}
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
