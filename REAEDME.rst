
==========
 Napoleon
==========

.. contents::

Introduction
============

Napoleon is a card game.
You can play Napoleon at https://napolo.herokuapp.com if you want.


Install
=======

FreeBSD::

   pkg install devel/py-setuptools34
   cd /usr/ports/databases/py-sqlite3   
   make reinstall clean

   # project root
   python manage.py makemigrations game


Heroku
======

Napoleon is served at heroku server.

I'm not used to heroku commands, so I'll write it down here.

install the heroku command ::

    wget -qO- https://toolbelt.heroku.com/install.sh | sh

login ::

    heroku auth:login --app napolo

log ::

    heroku logs --app napolo --tail

When using django, you need to migrate and create a super user ::

    heroku run --app napolo python manage.py makemigrations
    heroku run --app napolo python manage.py migrate
    heroku run --app napolo python manage.py createsuperuser

connect to postgres ::

    heroku pg:psql --app napolo

Automatical Deploy
------------------

heroku supports this but you also need to configure settings of github.

https://developer.github.com/guides/automating-deployments-to-integrators/


Django
======
run server ::

    python manage.py runserver 0.0.0.0:8001 --noreload --settings=napoleon.settings.local

so you need to set an environment valiable on heroku ::

    heroku config:set DJANGO_SETTINGS_MODULE=napoleon.settings.production --app napolo
