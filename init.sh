#!/bin/bash

git submodule init
git submodule update

poetry update

poetry run python manage.py makemigrations ultimate_ladder
poetry run python manage.py migrate ultimate_ladder
poetry run python manage.py migrate

echo -n "Admin username: "
read DJANGO_SUPERUSER_USERNAME
export DJANGO_SUPERUSER_USERNAME

echo -n "Admin email:"
read DJANGO_SUPERUSER_EMAIL
export DJANGO_SUPERUSER_EMAIL

echo -n "Admin passwd:"
read -s DJANGO_SUPERUSER_PASSWORD
export DJANGO_SUPERUSER_PASSWORD

poetry run  python manage.py createsuperuser --noinput

