FROM ghcr.io/praekeltfoundation/docker-django-bootstrap-nw:py3.10-buster

COPY . /app
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -e .

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
