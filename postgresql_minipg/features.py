from django.db.backends import postgresql

class DatabaseFeatures(postgresql.features.BaseDatabaseFeatures):
    has_native_uuid_field = False
