from django.db.backends.postgresql.features import DatabaseFeatures as BaseFeatures

class DatabaseFeatures(BaseFeatures):
    has_native_uuid_field = False
