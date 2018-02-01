from django.db.backends import postgresql
from django.db.utils import InterfaceError
from django.utils.functional import cached_property


class DatabaseFeatures(postgresql.features.BaseDatabaseFeatures):
    has_native_uuid_field = False
