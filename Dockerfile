FROM ghcr.io/praekeltfoundation/docker-django-bootstrap-nw:py3.10-buster

COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /bin/

COPY . /app
WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"
ENV UV_PYTHON_DOWNLOADS=0

RUN uv sync --locked --no-dev --no-install-project

ENV DJANGO_SETTINGS_MODULE=contentrepo.settings.production

RUN python manage.py collectstatic --noinput --settings=contentrepo.settings.base

CMD [\
    "contentrepo.wsgi:application",\
    "--timeout=120",\
    # Only a single worker allowed due to uploads happening in a thread
    "--workers=1",\
    "--threads=4",\
    "--worker-class=gthread",\
    "--worker-tmp-dir=/dev/shm"\
]
