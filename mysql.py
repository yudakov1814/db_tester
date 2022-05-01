import MySQLdb


from base_client import DbClient


class MysqlClient(DbClient):
    def __init__(self, config: dict) -> None:
        self.db = MySQLdb.connect(
            host=config["host"],
            port=int(config["port"]),
            user=config["user"],
            passwd=config["password"],
            db=config["db"],
            ssl={"ca": "~/.mysql/root.crt"}
        )

        self.db.autocommit(on=True)

    def select(self, query: str) -> list:
        self.db.query(query)
        r = self.db.store_result()
        return r.fetch_row(maxrows=0)

    def create_table(self, table_name: str, schema: dict) -> None:
        query = self._get_create_table_query(table_name, schema)
        self.db.query(query)

    def add_records(self, table_name: str, schema: dict, records: list) -> None:
        query = self._get_add_record_query(table_name, schema, records)
        self.db.query(query)

    def drop_table(self, table_name: str) -> None:
        query = self._get_drop_table_query(table_name)
        self.db.query(query)
