#!/bin/bash

git submodule init
git submodule update

python manage.py makemigrations ultimate_ladder
python manage.py migrate ultimate_ladder
python manage.py migrate

echo -n "Admin username: "
read DJANGO_SUPERUSER_USERNAME
export DJANGO_SUPERUSER_USERNAME

echo -n "Admin email:"
read DJANGO_SUPERUSER_EMAIL
export DJANGO_SUPERUSER_EMAIL

echo -n "Admin passwd:"
read -s DJANGO_SUPERUSER_PASSWORD
export DJANGO_SUPERUSER_PASSWORD

python manage.py createsuperuser --noinput

