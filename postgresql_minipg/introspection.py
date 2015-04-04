from __future__ import unicode_literals

from collections import namedtuple
try:
    from django.db.backends import BaseDatabaseIntrospection, FieldInfo
    TableInfo = None
except ImportError:
    from django.db.backends.base.introspection import (
        BaseDatabaseIntrospection, FieldInfo, TableInfo,
    )
    FieldInfo = namedtuple('FieldInfo', FieldInfo._fields + ('default',))

from django.utils.encoding import force_text


class DatabaseIntrospection(BaseDatabaseIntrospection):
    # Maps type codes to Django Field types.
    data_types_reverse = {
        16: 'BooleanField',
        17: 'BinaryField',
        20: 'BigIntegerField',
        21: 'SmallIntegerField',
        23: 'IntegerField',
        25: 'TextField',
        700: 'FloatField',
        701: 'FloatField',
        869: 'GenericIPAddressField',
        1042: 'CharField',  # blank-padded
        1043: 'CharField',
        1082: 'DateField',
        1083: 'TimeField',
        1114: 'DateTimeField',
        1184: 'DateTimeField',
        1266: 'TimeField',
        1700: 'DecimalField',
        2950: 'UUIDField',
    }

    ignored_tables = []

    def get_field_type(self, data_type, description):
        field_type = super(DatabaseIntrospection, self).get_field_type(data_type, description)
        if hasattr(description, 'default'):   # 1.8
            if field_type == 'IntegerField' and description.default and 'nextval' in description.default:
                return 'AutoField'
        return field_type

    def get_table_list(self, cursor):
        if TableInfo:   # 1.8
            """
            Returns a list of table and view names in the current database.
            """
            cursor.execute("""
                SELECT c.relname, c.relkind
                FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'v')
                    AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                    AND pg_catalog.pg_table_is_visible(c.oid)""")
            return [TableInfo(row[0], {'r': 't', 'v': 'v'}.get(row[1]))
                    for row in cursor.fetchall()
                    if row[0] not in self.ignored_tables]
        else:
            "Returns a list of table names in the current database."
            cursor.execute("""
                SELECT c.relname
                FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'v', '')
                    AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                    AND pg_catalog.pg_table_is_visible(c.oid)""")
            return [row[0] for row in cursor.fetchall() if row[0] not in self.ignored_tables]

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        # As cursor.description does not return reliably the nullable property,
        # we have to query the information_schema (#7783)
        if TableInfo:   # 1.8
            cursor.execute("""
                SELECT column_name, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s""", [table_name])
            field_map = {line[0]: line[1:] for line in cursor.fetchall()}
            cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
            return [FieldInfo(*((force_text(line[0]),) + line[1:6]
                                + (field_map[force_text(line[0])][0] == 'YES', field_map[force_text(line[0])][1])))
                    for line in cursor.description]
        else:
            cursor.execute("""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s""", [table_name])
            null_map = dict(cursor.fetchall())
            cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
            return [FieldInfo(*((force_text(line[0]),) + line[1:6] + (null_map[force_text(line[0])] == 'YES',)))
                    for line in cursor.description]

    def get_relations(self, cursor, table_name):
        if TableInfo:   # 1.8
            """
            Returns a dictionary of {field_name: (field_name_other_table, other_table)}
            representing all relationships to the given table.
            """
            cursor.execute("""
                SELECT c2.relname, a1.attname, a2.attname
                FROM pg_constraint con
                LEFT JOIN pg_class c1 ON con.conrelid = c1.oid
                LEFT JOIN pg_class c2 ON con.confrelid = c2.oid
                LEFT JOIN pg_attribute a1 ON c1.oid = a1.attrelid AND a1.attnum = con.conkey[1]
                LEFT JOIN pg_attribute a2 ON c2.oid = a2.attrelid AND a2.attnum = con.confkey[1]
                WHERE c1.relname = %s
                    AND con.contype = 'f'""", [table_name])
            relations = {}
            for row in cursor.fetchall():
                relations[row[1]] = (row[2], row[0])
            return relations
        else:
            """
            Returns a dictionary of {field_index: (field_index_other_table, other_table)}
            representing all relationships to the given table. Indexes are 0-based.
            """
            cursor.execute("""
                SELECT con.conkey, con.confkey, c2.relname
                FROM pg_constraint con, pg_class c1, pg_class c2
                WHERE c1.oid = con.conrelid
                    AND c2.oid = con.confrelid
                    AND c1.relname = %s
                    AND con.contype = 'f'""", [table_name])
            relations = {}
            for row in cursor.fetchall():
                # row[0] and row[1] are single-item lists, so grab the single item.
                relations[row[0][0] - 1] = (row[1][0] - 1, row[2])
            return relations

    def get_key_columns(self, cursor, table_name):
        key_columns = []
        cursor.execute("""
            SELECT kcu.column_name, ccu.table_name AS referenced_table, ccu.column_name AS referenced_column
            FROM information_schema.constraint_column_usage ccu
            LEFT JOIN information_schema.key_column_usage kcu
                ON ccu.constraint_catalog = kcu.constraint_catalog
                    AND ccu.constraint_schema = kcu.constraint_schema
                    AND ccu.constraint_name = kcu.constraint_name
            LEFT JOIN information_schema.table_constraints tc
                ON ccu.constraint_catalog = tc.constraint_catalog
                    AND ccu.constraint_schema = tc.constraint_schema
                    AND ccu.constraint_name = tc.constraint_name
            WHERE kcu.table_name = %s AND tc.constraint_type = 'FOREIGN KEY'""", [table_name])
        key_columns.extend(cursor.fetchall())
        return key_columns

    def get_indexes(self, cursor, table_name):
        # This query retrieves each index on the given table, including the
        # first associated field name
        cursor.execute("""
            SELECT attr.attname, idx.indkey, idx.indisunique, idx.indisprimary
            FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
                pg_catalog.pg_index idx, pg_catalog.pg_attribute attr
            WHERE c.oid = idx.indrelid
                AND idx.indexrelid = c2.oid
                AND attr.attrelid = c.oid
                AND attr.attnum = idx.indkey[0]
                AND c.relname = %s""", [table_name])
        indexes = {}
        for row in cursor.fetchall():
            # row[1] (idx.indkey) is stored in the DB as an array. 
            # It comes out as an array of integers. This designates the field
            # indexes (1-based) of the fields that have indexes on the table.
            # Here, we skip any indexes across multiple fields.
            if len(row[1]) > 1:
                continue
            if row[0] not in indexes:
                indexes[row[0]] = {'primary_key': False, 'unique': False}
            # It's possible to have the unique and PK constraints in separate indexes.
            if row[3]:
                indexes[row[0]]['primary_key'] = True
            if row[2]:
                indexes[row[0]]['unique'] = True
        return indexes

    def get_constraints(self, cursor, table_name):
        """
        Retrieves any constraints or keys (unique, pk, fk, check, index) across one or more columns.
        """
        constraints = {}
        # Loop over the key table, collecting things as constraints
        # This will get PKs, FKs, and uniques, but not CHECK
        cursor.execute("""
            SELECT
                kc.constraint_name,
                kc.column_name,
                c.constraint_type,
                array(SELECT table_name::text || '.' || column_name::text FROM information_schema.constraint_column_usage WHERE constraint_name = kc.constraint_name)
            FROM information_schema.key_column_usage AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                kc.table_schema = %s AND
                kc.table_name = %s
            ORDER BY kc.ordinal_position ASC
        """, ["public", table_name])
        for constraint, column, kind, used_cols in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": kind.lower() == "primary key",
                    "unique": kind.lower() in ["primary key", "unique"],
                    "foreign_key": tuple(used_cols[0].split(".", 1)) if kind.lower() == "foreign key" else None,
                    "check": False,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Now get CHECK constraint columns
        cursor.execute("""
            SELECT kc.constraint_name, kc.column_name
            FROM information_schema.constraint_column_usage AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                c.constraint_type = 'CHECK' AND
                kc.table_schema = %s AND
                kc.table_name = %s
        """, ["public", table_name])
        for constraint, column in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": None,
                    "check": True,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Now get indexes
        cursor.execute("""
            SELECT
                c2.relname,
                ARRAY(
                    SELECT (SELECT attname FROM pg_catalog.pg_attribute WHERE attnum = i AND attrelid = c.oid)
                    FROM unnest(idx.indkey) i
                ),
                idx.indisunique,
                idx.indisprimary
            FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
                pg_catalog.pg_index idx
            WHERE c.oid = idx.indrelid
                AND idx.indexrelid = c2.oid
                AND c.relname = %s
        """, [table_name])
        for index, columns, unique, primary in cursor.fetchall():
            if index not in constraints:
                constraints[index] = {
                    "columns": list(columns),
                    "primary_key": primary,
                    "unique": unique,
                    "foreign_key": None,
                    "check": False,
                    "index": True,
                }
        return constraints
