import psycopg2

from base_client import DbClient


class PostgresqlClient(DbClient):
    def __init__(self, config: dict) -> None:
        self.conn = psycopg2.connect("""
            host={host}
            port={port}
            dbname={db}
            user={user}
            password={password}
            target_session_attrs=read-write
            {sslmode}
        """.format(
            host=config["host"],
            port=config["port"],
            db=config["db"],
            user=config["user"],
            password=config["password"],
            sslmode=config.get("sslmode", "")
        ))

        self.conn.autocommit = True
        self.cur = self.conn.cursor()

    def select(self, query: str) -> list:
        self.cur.execute(query)
        return self.cur.fetchall()

    def create_table(self, table_name: str, schema: dict) -> None:
        query = self._get_create_table_query(table_name, schema)
        self.cur.execute(query)

    def add_records(self, table_name: str, schema: dict, records: list) -> None:
        query = self._get_add_record_query(table_name, schema, records)
        self.cur.execute(query)

    def drop_table(self, table_name: str) -> None:
        query = self._get_drop_table_query(table_name)
        self.cur.execute(query)
