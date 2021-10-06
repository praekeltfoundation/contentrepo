FROM python:3.8.1-slim-buster

RUN useradd wagtail

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system packages required by Wagtail and Django.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential \
    libpq-dev \
    libmariadbclient-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    redis \

 && rm -rf /var/lib/apt/lists/*

RUN pip install "gunicorn==20.0.4"

COPY requirements.txt /
RUN pip install -r /requirements.txt

WORKDIR /app
RUN chown wagtail:wagtail /app

COPY --chown=wagtail:wagtail . .

USER wagtail

ENV DJANGO_SETTINGS_MODULE=contentrepo.settings.production

CMD set -xe; gunicorn contentrepo.wsgi:application
