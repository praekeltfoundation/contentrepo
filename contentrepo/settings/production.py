from os.path import abspath, dirname, join

import dj_database_url

from .base import *  # noqa

DEBUG = env.bool("DEBUG", False)

PROJECT_ROOT = os.environ.get("PROJECT_ROOT") or dirname(dirname(abspath(__file__)))
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///%s" % (join(PROJECT_ROOT, "contentrepo.db"),)
    )
}

SECRET_KEY = env.str("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

SENTRY_DSN = env.str("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", 0.0)
    SENTRY_SEND_DEFAULT_PII = env.bool("SENTRY_SEND_DEFAULT_PII", False)

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=SENTRY_SEND_DEFAULT_PII,
    )
