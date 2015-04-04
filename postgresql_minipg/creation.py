import sys
import time
try:
    from django.db.backends.creation import BaseDatabaseCreation
except ImportError:
    from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.backends.utils import truncate_name


class DatabaseCreation(BaseDatabaseCreation):
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

    def sql_table_creation_suffix(self):
        test_settings = self.connection.settings_dict['TEST']
        assert test_settings['COLLATION'] is None, "PostgreSQL does not support collation setting at database creation time."
        if test_settings['CHARSET']:
            return "WITH ENCODING '%s'" % test_settings['CHARSET']
        return ''

    def sql_indexes_for_field(self, model, f, style):
        output = []
        db_type = f.db_type(connection=self.connection)
        if db_type is not None and (f.db_index or f.unique):
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table
            tablespace = f.db_tablespace or model._meta.db_tablespace
            if tablespace:
                tablespace_sql = self.connection.ops.tablespace_sql(tablespace)
                if tablespace_sql:
                    tablespace_sql = ' ' + tablespace_sql
            else:
                tablespace_sql = ''

            def get_index_sql(index_name, opclass=''):
                return (style.SQL_KEYWORD('CREATE INDEX') + ' ' +
                        style.SQL_TABLE(qn(truncate_name(index_name, self.connection.ops.max_name_length()))) + ' ' +
                        style.SQL_KEYWORD('ON') + ' ' +
                        style.SQL_TABLE(qn(db_table)) + ' ' +
                        "(%s%s)" % (style.SQL_FIELD(qn(f.column)), opclass) +
                        "%s;" % tablespace_sql)

            if not f.unique:
                output = [get_index_sql('%s_%s' % (db_table, f.column))]

            # Fields with database column types of `varchar` and `text` need
            # a second index that specifies their operator class, which is
            # needed when performing correct LIKE queries outside the
            # C locale. See #12234.
            if db_type.startswith('varchar'):
                output.append(get_index_sql('%s_%s_like' % (db_table, f.column),
                                            ' varchar_pattern_ops'))
            elif db_type.startswith('text'):
                output.append(get_index_sql('%s_%s_like' % (db_table, f.column),
                                            ' text_pattern_ops'))
        return output

    def _create_test_db(self, verbosity, autoclobber, keepdb=False):
        """
        Internal implementation - creates the test db tables.
        """
        from django.utils.six.moves import input
        suffix = self.sql_table_creation_suffix()

        test_database_name = self._get_test_db_name()

        qn = self.connection.ops.quote_name

        # Create the test database and connect to it.
        with self._nodb_connection.cursor() as cursor:
            try:
                cursor.connection._execute(
                    "CREATE DATABASE %s %s" % (qn(test_database_name), suffix), None)
            except Exception as e:
                sys.stderr.write(
                    "Got an error creating the test database: %s\n" % e)
                if not autoclobber:
                    confirm = input(
                        "Type 'yes' if you would like to try deleting the test "
                        "database '%s', or 'no' to cancel: " % test_database_name)
                if autoclobber or confirm == 'yes':
                    try:
                        if verbosity >= 1:
                            print("Destroying old test database '%s'..."
                                  % self.connection.alias)
                        cursor.connection._execute(
                            "DROP DATABASE %s" % qn(test_database_name), None)
                        cursor.connection._execute(
                            "CREATE DATABASE %s %s" % (qn(test_database_name),
                                                       suffix), None)
                    except Exception as e:
                        sys.stderr.write(
                            "Got an error recreating the test database: %s\n" % e)
                        sys.exit(2)
                else:
                    print("Tests cancelled.")
                    sys.exit(1)

    def _destroy_test_db(self, test_database_name, verbosity):
        """
        Internal implementation - remove the test db tables.
        """
        # Remove the test database to clean up after
        # ourselves. Connect to the previous database (not the test database)
        # to do so, because it's not allowed to delete a database while being
        # connected to it.
        with self._nodb_connection.cursor() as cursor:
            # Wait to avoid "database is being accessed by other users" errors.
            time.sleep(1)
            cursor.connection._execute("DROP DATABASE %s"
                           % self.connection.ops.quote_name(test_database_name), None)

