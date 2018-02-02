
import sys
import minipg 
from django.db.backends.base.creation import BaseDatabaseCreation


# The prefix to put on the default database name when creating
# the test database.

class DatabaseCreation(BaseDatabaseCreation):

    def _quote_name(self, name):
        return self.connection.ops.quote_name(name)

    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        host = self.connection.settings_dict.get('HOST')
        user = self.connection.settings_dict.get('USER')
        password = self.connection.settings_dict.get('PASSWORD')
        port = self.connection.settings_dict.get('PORT')
        use_ssl = self.connection.settings_dict.get('USE_SSL', False)
        minipg.create_database(parameters['dbname'], host, user, password, port, use_ssl)

    def _destroy_test_db(self, test_database_name, verbosity):
        host = self.connection.settings_dict.get('HOST')
        user = self.connection.settings_dict.get('USER')
        password = self.connection.settings_dict.get('PASSWORD')
        port = self.connection.settings_dict.get('PORT')
        use_ssl = self.connection.settings_dict.get('USE_SSL', False)
        minipg.drop_database(
            self.connection.ops.quote_name(test_database_name),
            host, user, password, port, use_ssl
        )
