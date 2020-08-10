django-minipg
==============

Django PostgreSQL database backend with minipg

Environment
-------------

* Django 2.2, 3.0, 3.1
* minipg (https://github.com/nakagami/minipg)

Restriction
-------------------

* No support postgresql specific feature
* No support PostGIS

Versions
--------------------

============= ===================
Django(a.b)   django-minipg
============= ===================
2.2           0.3.5
3.0           0.4.0
3.1           0.4.1
============= ===================



Installation
------------

::

    $ pip install django==a.b
    $ pip install django-minipg==x.y.z
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

