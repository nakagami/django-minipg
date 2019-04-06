
import sys
import minipg 
from django.db.backends.base.creation import BaseDatabaseCreation


# The prefix to put on the default database name when creating
# the test database.

class DatabaseCreation(BaseDatabaseCreation):

    def _quote_name(self, name):
        return self.connection.ops.quote_name(name)

    def _get_database_create_suffix(self, encoding=None, template=None):
        suffix = ""
        if encoding:
            suffix += " ENCODING '{}'".format(encoding)
        if template:
            suffix += " TEMPLATE {}".format(self._quote_name(template))
        return suffix and "WITH" + suffix

    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        host = self.connection.settings_dict.get('HOST')
        user = self.connection.settings_dict.get('USER')
        password = self.connection.settings_dict.get('PASSWORD')
        port = self.connection.settings_dict.get('PORT')
        minipg.create_database(parameters['dbname'], host, user, password, port)

    def _destroy_test_db(self, test_database_name, verbosity=0):
        host = self.connection.settings_dict.get('HOST')
        user = self.connection.settings_dict.get('USER')
        password = self.connection.settings_dict.get('PASSWORD')
        port = self.connection.settings_dict.get('PORT')
        minipg.drop_database(
            self.connection.ops.quote_name(test_database_name),
            host, user, password, port
        )

    def _create_test_db(self, verbosity, autoclobber, keepdb=False):
        """
        Internal implementation - create the test db tables.
        """
        test_database_name = self._get_test_db_name()
        test_db_params = {
            'dbname': self.connection.ops.quote_name(test_database_name),
            'suffix': self.sql_table_creation_suffix(),
        }
        # Create the test database and connect to it.
        with self._nodb_connection.cursor() as cursor:
            try:
                self._execute_create_test_db(cursor, test_db_params, keepdb)
            except Exception as e:
                # if we want to keep the db, then no need to do any of the below,
                # just return and skip it all.
                if keepdb:
                    return test_database_name

                sys.stderr.write(
                    "Got an error creating the test database: %s\n" % e)
                if not autoclobber:
                    confirm = input(
                        "Type 'yes' if you would like to try deleting the test "
                        "database '%s', or 'no' to cancel: " % test_database_name)
                if autoclobber or confirm == 'yes':
                    try:
                        if verbosity >= 1:
                            print("Destroying old test database for alias %s..." % (
                                self._get_database_display_str(verbosity, test_database_name),
                            ))
                        self._destroy_test_db(test_db_params['dbname'])
                        self._execute_create_test_db(cursor, test_db_params, keepdb)
                    except Exception as e:
                        sys.stderr.write(
                            "Got an error recreating the test database: %s\n" % e)
                        sys.exit(2)
                else:
                    print("Tests cancelled.")
                    sys.exit(1)

        return test_database_name
