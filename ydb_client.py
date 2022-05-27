import os
import ydb


from base_client import DbClient


Query = ""


def execute_query(session):
    global Query

    return session.transaction().execute(
        Query,
        commit_tx=True,
    )


class YdbClient(DbClient):
    def __init__(self, config: dict) -> None:
        driver_config = ydb.DriverConfig(
            config['endpoint'],
            database=config['database'],
            credentials=ydb.AccessTokenCredentials(
                os.getenv("YDB_ACCESS_TOKEN_CREDENTIALS")
            ),
            root_certificates=ydb.load_ydb_root_certificate(),
        )

        self.driver = ydb.Driver(driver_config)
        self.pool = ydb.SessionPool(self.driver)

    def select(self, query: str) -> list:
        global Query
        Query = query
        return self.pool.retry_operation_sync(execute_query)[0]

    def create_table(self, table_name: str, schema: dict) -> None:
        query = self._get_create_table_query(table_name, schema)
        query = query.replace(")", ", PRIMARY KEY (UserID));")

        def callee(session):
            session.execute_scheme(query)

        self.pool.retry_operation_sync(callee)

    def add_records(self, table_name: str, schema: dict, records: list) -> None:
        global Query
        Query = self._get_add_record_query(table_name, schema, records)
        self.pool.retry_operation_sync(execute_query)

    def drop_table(self, table_name: str) -> None:
        query = self._get_drop_table_query(table_name)
        query = query.replace("IF EXISTS ", "")

        def callee(session):
            session.execute_scheme(query)

        self.pool.retry_operation_sync(callee)
