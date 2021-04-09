django-minipg
==============

Django PostgreSQL database backend with minipg.

minipg and django-minipg written in pure python.
So, this may work in environments where psycopg2 does not work.

Environment
-------------

* Django 2.2, 3.0, 3.1, 3.2
* minipg (https://github.com/nakagami/minipg)

Restriction
-------------------

* No support postgresql specific feature
* No support PostGIS

Versions
--------------------

============= ======================
Django(a.b)   django-minipg(x.y.z)
============= ======================
2.2           0.3.5
3.0           0.4.0
3.1           0.4.1
3.2           0.4.2
============= ======================



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

