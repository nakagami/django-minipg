from django.db.backends.postgresql.features import DatabaseFeatures as BaseFeatures

class DatabaseFeatures(BaseFeatures):
    has_native_uuid_field = False

    # callproc is not supported
    create_test_procedure_without_params_sql = ''
    create_test_procedure_with_int_param_sql = ''
    supports_callproc_kwargs = False
