from django.db.backends.postgresql.features import DatabaseFeatures as BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    gis_enabled = False
    can_clone_databases = False

    @cached_property
    def test_collations(self):
        return {}

    @cached_property
    def django_test_skips(self):
        skips = super().django_test_skips
        skips.update({
            "skip on django-minipg": {
                'schema.tests.SchemaTests',
                'model_fields.test_jsonfield.TestQuerying',
            }
        })
        return skips
