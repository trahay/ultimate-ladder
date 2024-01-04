#!/bin/bash

python -m venv venv
source venv/bin/activate

git submodule init
pip install django
