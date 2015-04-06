"""
PostgreSQL database backend for Django.

Requires minipg: https://pypi.python.org/pypi/minipg
"""
from __future__ import unicode_literals

import django
try:
    from django.db.backends import BaseDatabaseFeatures
except ImportError: # 1.8
    from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import ProgrammingError

class DatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False
    can_return_id_from_insert = True
    requires_rollback_on_dirty_transaction = True
    has_real_datatype = True
    has_native_uuid_field = True
    has_native_duration_field = True
    driver_supports_timedelta_args = True
    can_defer_constraint_checks = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_bulk_insert = True
    uses_savepoints = True
    can_release_savepoints = True
    supports_tablespaces = True
    supports_transactions = True
    can_introspect_autofield = django.VERSION[1] > 7
    can_introspect_ip_address_field = False
    can_introspect_small_integer_field = True
    can_distinct_on_fields = True
    can_rollback_ddl = True
    supports_combined_alters = True
    nulls_order_largest = True
    closed_cursor_error_class = ProgrammingError
    has_case_insensitive_like = False
    requires_sqlparse_for_splitting = False
    supports_paramstyle_pyformat = False
    has_zoneinfo_database = False

