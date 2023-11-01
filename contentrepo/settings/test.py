from .dev import *  # noqa


DATABASES = {"default": env.db("CONTENTREPO_DATABASE", default="sqlite://:memory:")}
