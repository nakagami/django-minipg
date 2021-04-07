from django.db.backends.postgresql.features import DatabaseFeatures as BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    gis_enabled = False
    can_clone_databases = False

    @cached_property
    def test_collations(self):
        return {
            'non_default': 'sv-x-icu',
            'swedish_ci': 'sv-x-icu',
        }
        return {}
