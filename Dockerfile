FROM ghcr.io/praekeltfoundation/docker-django-bootstrap-nw:py3.10-buster

COPY . /app
RUN pip install -e .

ENV DJANGO_SETTINGS_MODULE contentrepo.settings.production

RUN django-admin collectstatic --noinput --settings=contentrepo.settings.base

CMD ["contentrepo.wsgi:application"]
