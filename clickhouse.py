import json
import requests


from base_client import DbClient


class ClickHouseClient(DbClient):
    def __init__(self, config: dict) -> None:
        self.db = config["db"]

        self.base_url = "https://{host}:{port}/".format(
            host=config["host"],
            port=config["port"],
        )

        self.auth_headers = {
            "X-ClickHouse-User": config["user"],
            "X-ClickHouse-Key": config["password"],
        }

    def select(self, query: str) -> list:
        params = {
            "database": self.db,
            "query": "{query} FORMAT JSONCompact".format(query=query),
        }
        text = self._request_get(params=params)

        return json.loads(text)["data"]

    def create_table(self, table_name: str, schema: dict) -> None:
        query = self._get_create_table_query(table_name, schema, db=self.db)
        data = f"{query} ENGINE = Log()"
        self._request_post(data=data)

    def add_records(self, table_name: str, schema: dict, records: list) -> None:
        query = self._get_add_record_query(
            table_name, schema, records, db=self.db)
        self._request_post(data=query)

    def drop_table(self, table_name: str) -> None:
        query = self._get_drop_table_query(table_name, db=self.db)
        self._request_post(data=query)

    def _request_get(self, params={}, headers={}) -> str:
        res = requests.get(
            self.base_url,
            params=params,
            headers={**headers, **self.auth_headers},
            verify="/usr/local/share/ca-certificates/Yandex/YandexInternalRootCA.crt")
        res.raise_for_status()

        return res.text

    def _request_post(self, data={}, headers={}) -> str:
        res = requests.post(
            self.base_url,
            data=data,
            headers={**headers, **self.auth_headers},
            verify="/usr/local/share/ca-certificates/Yandex/YandexInternalRootCA.crt")
        res.raise_for_status()

        return res.text
