# ultimate-ladder
A matchmaking website for creating balanced teams when playing ultimate frisbee


## Usage

First, you need to initialize stuff using the `init.sh` script:
```
bash  init.sh 
```

Then, you can start the server by running:
```
poetry run python manage.py runserver
```

Now, you can access the website at this address: http://127.0.0.1:8000/ultimate_ladder

## Real life deployement of the website

You can deploy the website on your [YunoHost](https://yunohost.org/#/) instance using the following YNH package: https://github.com/trahay/ultimate_ladder_ynh 
