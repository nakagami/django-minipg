django-minipg
==============

Django PostgreSQL database backend with minipg

Environment
-------------

* Django 2.0
* minipg (https://github.com/nakagami/minipg)

Restriction
-------------------

* No support postgresql specific feature  https://docs.djangoproject.com/en/2.0/ref/contrib/postgres/
* No support PostGIS

Installation
------------

::

    $ pip install minipg
    $ pip install django-minipg

Settings
------------

::

    DATABASES = {
        'default': {
            'ENGINE': 'postgresql_minipg',
            'NAME': 'some_what_database',
            'HOST': ...,
            'USER': ...,
            'PASSWORD': ...,
        }
    }

