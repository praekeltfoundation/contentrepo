FROM ghcr.io/praekeltfoundation/docker-django-bootstrap-nw:py3.10-buster

RUN pip install poetry==1.7.1
COPY . /app
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-dev --no-interaction --no-ansi --no-cache

ENV DJANGO_SETTINGS_MODULE contentrepo.settings.production

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
