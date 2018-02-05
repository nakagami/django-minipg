django-minipg
==============

Django PostgreSQL database backend for minipg

------------

* Django 2.0
* minipg (https://github.com/nakagami/minipg)

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

