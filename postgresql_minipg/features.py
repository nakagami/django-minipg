from django.db.backends.postgresql.features import DatabaseFeatures as BaseDatabaseFeatures


class DatabaseFeatures(BaseDatabaseFeatures):
    gis_enabled = False
    can_clone_databases = False
