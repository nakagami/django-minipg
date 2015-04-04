"""
PostgreSQL database backend for Django.

Requires minipg: https://pypi.python.org/pypi/minipg
"""

from django.conf import settings
try:
    from django.db.backends import BaseDatabaseWrapper
except ImportError: # 1.8
    from django.db.backends.base.base import BaseDatabaseWrapper
try:
    from django.db.backends import BaseDatabaseValidation
except ImportError: # 1.8
    from django.db.backends.base.validation import BaseDatabaseValidation
from postgresql_minipg.client import DatabaseClient
from postgresql_minipg.creation import DatabaseCreation
from postgresql_minipg.features import DatabaseFeatures
from postgresql_minipg.introspection import DatabaseIntrospection
from postgresql_minipg.operations import DatabaseOperations
from postgresql_minipg.schema import DatabaseSchemaEditor
from postgresql_minipg.version import get_version
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.safestring import SafeText, SafeBytes
from django.utils.timezone import utc
from django.utils import six

try:
    import minipg as Database
except ImportError as e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading minipg module: %s" % e)

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

def _escape_str(conn, v):
    return u"'" + v.replace(u"'", u"''") + u"'"

def _escape_bytes(conn, v):
    return u"'" + (v.decode('utf-8')).replace(u"'", u"''") + u"'"

def _escape_array(conn, v):
    s = u','.join([conn.escape_parameter(e) for e in v])
    return s

class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'minipg'
    # This dictionary maps Field objects to their associated PostgreSQL column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = {
        'AutoField': 'serial',
        'BinaryField': 'bytea',
        'BooleanField': 'boolean',
        'CharField': 'varchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'varchar(%(max_length)s)',
        'DateField': 'date',
        'DateTimeField': 'timestamp with time zone',
        'DecimalField': 'numeric(%(max_digits)s, %(decimal_places)s)',
        'FileField': 'varchar(%(max_length)s)',
        'FilePathField': 'varchar(%(max_length)s)',
        'FloatField': 'double precision',
        'IntegerField': 'integer',
        'BigIntegerField': 'bigint',
        'IPAddressField': 'inet',
        'GenericIPAddressField': 'inet',
        'NullBooleanField': 'boolean',
        'OneToOneField': 'integer',
        'PositiveIntegerField': 'integer',
        'PositiveSmallIntegerField': 'smallint',
        'SlugField': 'varchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField': 'text',
        'TimeField': 'time',
    }
    data_type_check_constraints = {
        'PositiveIntegerField': '"%(column)s" >= 0',
        'PositiveSmallIntegerField': '"%(column)s" >= 0',
    }
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

    # The patterns below are used to generate SQL pattern lookup clauses when
    # the right-hand side of the lookup isn't a raw string (it might be an expression
    # or the result of a bilateral transformation).
    # In those cases, special characters for LIKE operators (e.g. \, *, _) should be
    # escaped on database side.
    #
    # Note: we use str.format() here for readability as '%' is used as a wildcard for
    # the LIKE operator.
    pattern_esc = r"REPLACE(REPLACE(REPLACE({}, '\', '\\'), '%%', '\%%'), '_', '\_')"
    pattern_ops = {
        'contains': "LIKE '%%' || {} || '%%'",
        'icontains': "LIKE '%%' || UPPER({}) || '%%'",
        'startswith': "LIKE {} || '%%'",
        'istartswith': "LIKE UPPER({}) || '%%'",
        'endswith': "LIKE '%%' || {}",
        'iendswith': "LIKE '%%' || UPPER({})",
    }


    Database = Database
    SchemaEditorClass = DatabaseSchemaEditor

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
        conn.encoders[SafeText] = _escape_str
        conn.encoders[SafeBytes] = _escape_bytes
        conn.encoders[list] = _escape_array
        conn.encoders[tuple] = _escape_array
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
        try:
            from django.db.backends.postgresql_psycopg2.utils import utc_tzinfo_factory
            cursor.tzinfo_factory = utc_tzinfo_factory if settings.USE_TZ else None
        except ImportError:
            pass
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
            return self.connection._execute(self.ops.savepoint_rollback_sql(sid), None)


