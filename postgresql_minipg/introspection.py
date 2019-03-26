from django.db.backends.postgresql.introspection import DatabaseIntrospection as BaseIntrospection


class DatabaseIntrospection(BaseIntrospection):

    def _clear_error(self, cursor):
        if cursor.connection._trans_status == b'E':
            cursor.connection._rollback()

    def get_table_list(self, cursor):
        self._clear_error(cursor)
        return super().get_table_list(cursor)

    def get_table_description(self, cursor, table_name):
        self._clear_error(cursor)
        return super().get_table_description(cursor, table_name)

    def get_sequences(self, cursor, table_name, table_fields=()):
        self._clear_error(cursor)
        return super().get_sequences(cursor, table_name, table_fields)

    def get_relations(self, cursor, table_name):
        self._clear_error(cursor)
        return super().get_relations(cursor, table_name)

    def get_key_columns(self, cursor, table_name):
        self._clear_error(cursor)
        return super().get_key_columns(cursor, table_name)

    def get_constraints(self, cursor, table_name):
        self._clear_error(cursor)
        return super().get_constraints(cursor, table_name)
