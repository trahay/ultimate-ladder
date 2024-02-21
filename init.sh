#!/bin/bash

git submodule init
git submodule update

poetry update

poetry run python manage.py makemigrations ultimate_ladder
poetry run python manage.py migrate ultimate_ladder
poetry run python manage.py migrate
