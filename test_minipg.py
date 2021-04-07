DATABASES = {
    'default': {
        'ENGINE': 'postgresql_minipg',
        'NAME': 'minipg',
        'USER': 'postgres',
        'HOST': 'localhost',

    },
    'other': {
        'ENGINE': 'postgresql_minipg',
        'NAME': 'minipg2',
        'USER': 'postgres',
        'HOST': 'localhost',
    }
}

SECRET_KEY = "django_tests_secret_key"

# Use a fast hasher to speed up tests.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
