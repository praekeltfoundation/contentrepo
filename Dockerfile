FROM ghcr.io/praekeltfoundation/docker-django-bootstrap-nw:py3.10-buster

COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /bin/

COPY . /app
WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local
ENV UV_PYTHON_DOWNLOADS=0

# Keep the base image's Gunicorn and other runtime packages.
RUN uv sync --locked --no-dev --inexact

ENV DJANGO_SETTINGS_MODULE=contentrepo.settings.production

RUN django-admin collectstatic --noinput --settings=contentrepo.settings.base

CMD [\
    "contentrepo.wsgi:application",\
    "--timeout=120",\
    # Only a single worker allowed due to uploads happening in a thread
    "--workers=1",\
    "--threads=4",\
    "--worker-class=gthread",\
    "--worker-tmp-dir=/dev/shm"\
]
