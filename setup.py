#!/usr/bin/env python3
"""
Yet another Django PostgreSQL database backend for minipg
"""
from distutils.core import setup, Command

classifiers = [
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Topic :: Database',
]

setup(name='django-minipg', 
        version='0.3.2',
        description = __doc__, 
        url='https://github.com/nakagami/django-minipg/',
        classifiers=classifiers,
        keywords=['PostgreSQL', 'minipg'],
        license='BSD',
        author='Hajime Nakagami',
        author_email='nakagami@gmail.com',
        packages = ['postgresql_minipg'],
        long_description=open('README.rst').read(),
)
