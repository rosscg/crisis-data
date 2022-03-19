FROM python:3.6-slim

WORKDIR .

COPY requirements.txt requirements.txt

# libpq-dev gcc -> psycopg2 (postgres) libxml2-dev libxslt1-dev -> lxml python-dev build-essential -> Cython for pyzmq pkconfig -> matplotlib (ft2build.h) postgresql-client -> restoring DB
ENV BUILD_DEPS="git libpq-dev gcc libxml2-dev libxslt1-dev zlib1g-dev python-dev build-essential cython3 pkgconf postgresql-client libfreetype6-dev " \
#    APP_DEPS="curl libpq-dev"

RUN apt-get -y update \
  && apt-get install -y ${BUILD_DEPS}
  && pip install -r requirements.txt --no-cache-dir \
  && apt-get purge -y --auto-remove ${BUILD_DEPS} \
  && apt-get clean

COPY . .
