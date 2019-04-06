django-minipg
==============

Django PostgreSQL database backend with minipg

Environment
-------------

* Django 2.2
* minipg (https://github.com/nakagami/minipg)

Restriction
-------------------

* No support postgresql specific feature
* No support PostGIS

Installation
------------

::

    $ pip install django==2.2
    $ pip install django-minipg==0.3.5
    $ pip install minipg

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

