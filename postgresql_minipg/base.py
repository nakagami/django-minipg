"""
PostgreSQL database backend for Django.

Requires minipg: https://pypi.python.org/pypi/minipg
"""

from django.conf import settings
from django.db.backends import (BaseDatabaseFeatures, BaseDatabaseWrapper,
    BaseDatabaseValidation)
from postgresql_minipg.operations import DatabaseOperations
from postgresql_minipg.client import DatabaseClient
from postgresql_minipg.creation import DatabaseCreation
from postgresql_minipg.version import get_version
from postgresql_minipg.introspection import DatabaseIntrospection
from postgresql_minipg.schema import DatabaseSchemaEditor
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.safestring import SafeText, SafeBytes
from django.utils.timezone import utc
from django.utils import six

try:
    import minipg as Database
#    import psycopg2.extensions
except ImportError as e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading minipg module: %s" % e)

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

class DatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False
    can_return_id_from_insert = True
    requires_rollback_on_dirty_transaction = True
    has_real_datatype = True
    can_defer_constraint_checks = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_bulk_insert = True
    uses_savepoints = True
    supports_tablespaces = True
    supports_transactions = True
    can_introspect_ip_address_field = True
    can_introspect_small_integer_field = True
    can_distinct_on_fields = True
    can_rollback_ddl = True
    supports_combined_alters = True
    nulls_order_largest = True
    has_case_insensitive_like = False
    requires_sqlparse_for_splitting = False
    supports_paramstyle_pyformat = False
    has_zoneinfo_database = False


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'postgresql'
    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': 'LIKE %s',
        'icontains': 'LIKE UPPER(%s)',
        'regex': '~ %s',
        'iregex': '~* %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'LIKE UPPER(%s)',
        'iendswith': 'LIKE UPPER(%s)',
    }

    pattern_ops = {
        'startswith': "LIKE %s || '%%%%'",
        'istartswith': "LIKE UPPER(%s) || '%%%%'",
    }

    Database = Database

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        opts = self.settings_dict["OPTIONS"]

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def get_connection_params(self):
        settings_dict = self.settings_dict
        # None may be used to connect to the default 'postgres' db
        if settings_dict['NAME'] == '':
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "settings.DATABASES is improperly configured. "
                "Please supply the NAME value.")
        conn_params = {
            'database': settings_dict['NAME'] or 'postgres',
        }
        conn_params.update(settings_dict['OPTIONS'])
        if 'autocommit' in conn_params:
            del conn_params['autocommit']
        if 'isolation_level' in conn_params:
            del conn_params['isolation_level']
        if settings_dict['USER']:
            conn_params['user'] = settings_dict['USER']
        if settings_dict['PASSWORD']:
            conn_params['password'] = force_str(settings_dict['PASSWORD'])
        if settings_dict['HOST']:
            conn_params['host'] = settings_dict['HOST']
        if settings_dict['PORT']:
            conn_params['port'] = settings_dict['PORT']
        return conn_params

    def get_new_connection(self, conn_params):
        conn = Database.connect(**conn_params)
        conn.encoders[SafeText] = lambda v: u"'" + v.replace(u"'", u"''") + u"'"
        conn.encoders[SafeBytes] = lambda v: u"'" + (v.decode('utf-8')).replace(u"'", u"''") + u"'"
        return conn

    def init_connection_state(self):
        settings_dict = self.settings_dict
        tz = 'UTC' if settings.USE_TZ else settings_dict.get('TIME_ZONE')
        if tz:
            if settings.USE_TZ:
                self.connection.use_tzinfo = True
                self.connection.tzinfo = utc
            else:
                self.connection.use_tzinfo = False
                self.connection.tzinfo = None
            cursor = self.connection.cursor()
            try:
                cursor.execute(self.ops.set_time_zone_sql(), [tz])
            finally:
                cursor.close()
            # Commit after setting the time zone (see #17062)
            if not self.get_autocommit():
                self.connection.commit()

    def create_cursor(self):
        cursor = self.connection.cursor()
        return cursor

    def _set_autocommit(self, autocommit):
        with self.wrap_database_errors:
            self.connection.autocommit = autocommit

    def check_constraints(self, table_names=None):
        """
        To check constraints, we set constraints to immediate. Then, when, we're done we must ensure they
        are returned to deferred.
        """
        self.cursor().execute('SET CONSTRAINTS ALL IMMEDIATE')
        self.cursor().execute('SET CONSTRAINTS ALL DEFERRED')

    def is_usable(self):
        try:
            # Use a psycopg cursor directly, bypassing Django's utilities.
            self.connection.cursor().execute("SELECT 1")
        except Database.Error:
            return False
        else:
            return True

    def schema_editor(self, *args, **kwargs):
        "Returns a new instance of this backend's SchemaEditor"
        return DatabaseSchemaEditor(self, *args, **kwargs)

    @cached_property
    def minipg_version(self):
        version = minipg.__version__.split(' ', 1)[0]
        return tuple(int(v) for v in version.split('.'))

    @cached_property
    def pg_version(self):
        with self.temporary_connection():
            return get_version(self.connection)

    def _savepoint_rollback(self, sid):
        with self.temporary_connection():
            return self.connection._execute(self.ops.savepoint_rollback_sql(sid))


