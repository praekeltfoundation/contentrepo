FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /bin/

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        build-essential \
        libfreetype6-dev \
        libjpeg-dev \
        liblcms2-dev \
        libopenjp2-7-dev \
        libpq-dev \
        libtiff-dev \
        libwebp-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local
ENV UV_PYTHON_DOWNLOADS=0

RUN uv sync --locked --no-dev --inexact

ENV DJANGO_SETTINGS_MODULE=contentrepo.settings.production

RUN django-admin collectstatic --noinput --settings=contentrepo.settings.base

FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        libfreetype6 \
        libjpeg62-turbo \
        liblcms2-2 \
        libopenjp2-7 \
        libpq5 \
        libtiff6 \
        libwebp7 \
        libwebpdemux2 \
        libwebpmux3 \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=build /usr/local /usr/local
COPY --from=build /app /app

ENV DJANGO_SETTINGS_MODULE=contentrepo.settings.production

EXPOSE 8000

CMD ["gunicorn", "--bind=0.0.0.0:8000", "contentrepo.wsgi:application", "--timeout=120", "--workers=1", "--threads=4", "--worker-class=gthread", "--worker-tmp-dir=/dev/shm"]
