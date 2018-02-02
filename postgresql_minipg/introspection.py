from django.db.backends.base.introspection import FieldInfo
from django.db.backends.postgresql import introspection as pg_introspection

class DatabaseIntrospection(pg_introspection.DatabaseIntrospection):

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface.
        """
        # As cursor.description does not return reliably the nullable property,
        # we have to query the information_schema (#7783)
        cursor.execute("""
            SELECT column_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s""", [table_name])
        field_map = {line[0]: line[1:] for line in cursor.fetchall()}
        cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
        return [
            FieldInfo(*line[0:6], field_map[line[0]][0] == 'YES', field_map[line[0]][1])
            for line in cursor.description
        ]



