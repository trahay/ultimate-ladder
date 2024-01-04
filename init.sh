#!/bin/bash

python -m venv venv
source venv/bin/activate

git submodule init
git submodule update

pip install django pandas

python manage.py makemigrations ladder
python manage.py migrate ladder
python manage.py migrate
