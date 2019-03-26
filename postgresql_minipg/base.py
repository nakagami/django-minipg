"""
PostgreSQL database backend for Django.

Requires minipg: https://pypi.python.org/pypi/minipg
"""
import threading
import warnings
import datetime

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.utils import DatabaseError as WrappedDatabaseError
from django.utils.functional import cached_property
from django.utils import timezone

try:
    import minipg as Database
except ImportError as e:
    raise ImproperlyConfigured("Error loading minipg")

# Some of these import psycopg2, so import them after checking if it's installed.
from django.db.backends.postgresql.client import DatabaseClient                # NOQA isort:skip
from .creation import DatabaseCreation                      # NOQA isort:skip
from .features import DatabaseFeatures            # NOQA isort:skip
from .introspection import DatabaseIntrospection  # NOQA isort:skip
from .operations import DatabaseOperations                  # NOQA isort:skip
from .schema import DatabaseSchemaEditor                    # NOQA isort:skip
from django.db.backends.postgresql.utils import utc_tzinfo_factory             # NOQA isort:skip

class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'postgresql_subset'
    display_name = 'PostgreSQL'
    # This dictionary maps Field objects to their associated PostgreSQL column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = {
        'AutoField': 'serial',
        'BigAutoField': 'bigserial',
        'BinaryField': 'bytea',
        'BooleanField': 'boolean',
        'CharField': 'varchar(%(max_length)s)',
        'DateField': 'date',
        'DateTimeField': 'timestamp with time zone',
        'DecimalField': 'numeric(%(max_digits)s, %(decimal_places)s)',
        'DurationField': 'interval',
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
        'UUIDField': 'uuid',
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
    pattern_esc = r"REPLACE(REPLACE(REPLACE({}, E'\\', E'\\\\'), E'%%', E'\\%%'), E'_', E'\\_')"
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
    # Classes instantiated in __init__().
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations
    # PostgreSQL backend-specific attributes.
    _named_cursor_idx = 0

    def get_connection_params(self):
        settings_dict = self.settings_dict
        # None may be used to connect to the default 'postgres' db
        if settings_dict['NAME'] == '':
            raise ImproperlyConfigured(
                "settings.DATABASES is improperly configured. "
                "Please supply the NAME value.")
        if len(settings_dict['NAME'] or '') > self.ops.max_name_length():
            raise ImproperlyConfigured(
                "The database name '%s' (%d characters) is longer than "
                "PostgreSQL's limit of %d characters. Supply a shorter NAME "
                "in settings.DATABASES." % (
                    settings_dict['NAME'],
                    len(settings_dict['NAME']),
                    self.ops.max_name_length(),
                )
            )
        conn_params = {
            'database': settings_dict['NAME'] or 'postgres',
            **settings_dict['OPTIONS'],
        }
        conn_params.pop('isolation_level', None)
        if settings_dict['USER']:
            conn_params['user'] = settings_dict['USER']
        if settings_dict['PASSWORD']:
            conn_params['password'] = settings_dict['PASSWORD']
        if settings_dict['HOST']:
            conn_params['host'] = settings_dict['HOST']
        if settings_dict['PORT']:
            conn_params['port'] = settings_dict['PORT']
        return conn_params

    def get_new_connection(self, conn_params):
        connection = Database.connect(**conn_params)

        # self.isolation_level must be set:
        # - after connecting to the database in order to obtain the database's
        #   default when no value is explicitly specified in options.
        # - before calling _set_autocommit() because if autocommit is on, that
        #   will set connection.isolation_level to ISOLATION_LEVEL_AUTOCOMMIT.
        options = self.settings_dict['OPTIONS']
        try:
            self.isolation_level = options['isolation_level']
        except KeyError:
            self.isolation_level = connection.isolation_level
        else:
            # Set the isolation level to the value from OPTIONS.
            if self.isolation_level != connection.isolation_level:
                with connection.cursor() as cursor:
                    cursor.execute('SET ISOLATION LEVEL {}'.format(self.isolation_level))
        with connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

        return connection

    def ensure_timezone(self):
        if self.connection is None:
            return False
        conn_timezone_name = self.connection.get_parameter_status('TimeZone')
        timezone_name = self.timezone_name
        if timezone_name and conn_timezone_name != timezone_name:
            with self.connection.cursor() as cursor:
                cursor.execute(self.ops.set_time_zone_sql(), [timezone_name])
            return True
        return False

    def init_connection_state(self):
        timezone_changed = self.ensure_timezone()
        if timezone_changed:
            # Commit after setting the time zone (see #17062)
            if not self.get_autocommit():
                self.connection.commit()
        pass

    def create_cursor(self, name=None):
        cursor = self.connection.cursor(factory=CursorWrapper)
        cursor.tzinfo_factory = utc_tzinfo_factory if settings.USE_TZ else None
        return cursor


    def chunked_cursor(self):
        self._named_cursor_idx += 1
        return self._cursor(
            name='_django_curs_%d_%d' % (
                # Avoid reusing name in other threads
                threading.current_thread().ident,
                self._named_cursor_idx,
            )
        )

    def _set_autocommit(self, autocommit):
        with self.wrap_database_errors:
            self.connection.autocommit = autocommit

    def check_constraints(self, table_names=None):
        """
        Check constraints by setting them to immediate. Return them to deferred
        afterward.
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

    @property
    def _nodb_connection(self):
        nodb_connection = super()._nodb_connection
        try:
            nodb_connection.ensure_connection()
        except (Database.DatabaseError, WrappedDatabaseError):
            warnings.warn(
                "Normally Django will use a connection to the 'postgres' database "
                "to avoid running initialization queries against the production "
                "database when it's not needed (for example, when running tests). "
                "Django was unable to create a connection to the 'postgres' database "
                "and will use the default database instead.",
                RuntimeWarning
            )
            for connection in connections.all():
                if connection.vendor == 'postgresql_subset' and connection.settings_dict['NAME'] != 'postgres':
                    return self.__class__(
                        {**self.settings_dict, 'NAME': connection.settings_dict['NAME']},
                        alias=self.alias,
                    )
        return nodb_connection

    @cached_property
    def pg_version(self):
        with self.temporary_connection():
            return self.connection.server_version


class CursorWrapper(Database.Cursor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def execute(self, query, params=None):
        if (query.split()[0].upper() == 'DELETE'
            and self.connection._trans_status == b'E'):
            self.connection._rollback()
        return super().execute(query, params)

    def executemany(self, query, param_list):
        if (query.split()[0].upper() == 'DELETE'
            and self.connection._trans_status == b'E'):
            self.connection._rollback()
        super().executemany(query, param_list)

    def _convert(self, r):
        r = list(r)
        for i in range(len(r)):
            if (
                settings.USE_TZ and
                isinstance(r[i], datetime.datetime) and
                timezone.is_naive(r[i])
            ):
                r[i] = r[i].replace(tzinfo=timezone.utc)
            elif (
                not settings.USE_TZ and
                isinstance(r[i], datetime.datetime) and
                timezone.is_aware(r[i])
            ):
                r[i] = r[i].replace(tzinfo=None)

        return tuple(r)

    def fetchone(self):
        r = super().fetchone()
        if r:
            r = self._convert(r)
        return r

    def fetchmany(self, size=1):
        rs = super().fetchmany(size)
        for i in range(len(rs)):
            rs[i] = self._convert(rs[i])
        return rs

    def fetchall(self):
        rs = super().fetchall()
        for i in range(len(rs)):
            rs[i] = self._convert(rs[i])
        return rs

    def close(self):
        super().close()

