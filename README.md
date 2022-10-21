# shepherd_webservice

- alpha prototype state
- nothing really works, but
  - signup and login

## install

TODO: copy secrets

```shell

pipenv shell
pipenv sync

cd web_django
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
# follow dialog

# add initial data
python manage.py loaddata .\testbed\fixture_gpios.yaml
python manage.py loaddata .\testbed\fixture_controllers.yaml
python manage.py loaddata .\testbed\fixture_targets.yaml
python manage.py loaddata .\testbed\fixture_observers.yaml

```

## run django-server

```shell

python manage.py runserver

```

## save state

- copy secret `web_django\setup_secret.py`
- copy database `web_django\db_django.sqlite3`
- or dump database `python manage.py dumpdata`
