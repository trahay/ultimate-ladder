ARG PYTHON_VERSION=3.11-slim-bookworm

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies, and gettext to update the translations
# (python manage.py makemessages / compilemessages).
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    gettext \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /code

WORKDIR /code

COPY requirements.txt /tmp/requirements.txt
RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/
COPY . /code

