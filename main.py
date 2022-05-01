from collections import defaultdict
import json
import time
import random

from base_client import DbClient
from mysql import MysqlClient
from postgresql import PostgresqlClient


FILE_NAME = "result4"
FILE = open(FILE_NAME, "w")
BATCH_SIZE = 10000
BATCHES = 1000

db_config = json.load(open("db_config.json", "r"))
test_cases = json.load(open("test_cases.json", "r"))
test_config = {
    "MySQL": {
        "client": MysqlClient,
        "schema": {
            "Timestamp": "INT",
            "UserID": "CHAR(16)",
            "RequestID": "CHAR(32)",
            "ClickType": "SMALLINT",
            "ClickCost": "INT",
            "ElementType": "SMALLINT",
            "ElementName": "VARCHAR(200)",
            "Position": "SMALLINT",
        },
    },
    "PostgreSQL": {
        "client": PostgresqlClient,
        "schema": {
            "Timestamp": "integer",
            "UserID": "char(16)",
            "RequestID": "char(32)",
            "ClickType": "smallint",
            "ClickCost": "integer",
            "ElementType": "smallint",
            "ElementName": "varchar(200)",
            "Position": "smallint",
        },
    },
}


def random_str(length):
    choices = "0123456789abcdefghijklmnopqrstuvwxyz"
    s = ""
    for _ in range(length):
        s += random.choice(choices)
    return s


def get_clients() -> dict:
    return {
        name: data["client"](db_config[name])
        for name, data in test_config.items()
    }


def get_records(count: int) -> list:
    return [
        {
            "Timestamp": random.randint(1650855600, 1650891600),
            "UserID": random_str(16),
            "RequestID": random_str(32),
            "ClickType": random.randint(1, 5),
            "ClickCost": random.randint(0, 1000),
            "ElementType": random.randint(1, 50),
            "ElementName": random_str(random.randint(15, 100)),
            "Position": random.randint(0, 100),
        }
        for _ in range(count)
    ]


def create_table(name: str, client: DbClient, table_name: str) -> None:
    client.create_table(table_name, test_config[name]["schema"])


def add_records(name: str, client: DbClient, table_name: str, records: list) -> None:
    client.add_records(table_name, test_config[name]["schema"], records)


def select(name: str, client: DbClient, query: str) -> list:
    return client.select(query)


def drop_table(name: str, client: DbClient, table_name: str) -> None:
    client.drop_table(table_name)


def exec_all_clients(clients: dict, func, *args) -> dict:
    data = {}

    for name, client in clients.items():
        start = time.perf_counter()
        func(name, client, *args)
        end = time.perf_counter()
        data[f"{type(client).__name__}.{func.__name__}"] = end - start

    return data


def print_data(data: dict) -> None:
    for name, time in sorted(data.items()):
        print(f"{name} in {time:.3f} s", file=FILE)
    print(file=FILE)
    FILE.flush()


def main():
    table_name = f"test_{random_str(5)}"
    clients = get_clients()
    try:
        exec_all_clients(clients, create_table, table_name)

        add_records_data = defaultdict(float)
        for _ in range(BATCHES):
            records = get_records(BATCH_SIZE)
            temp_data = exec_all_clients(clients, add_records, table_name, records)
            for name, time in temp_data.items():
                add_records_data[name] += time
        print_data(add_records_data)

        all_select_data = defaultdict(float)
        for query in test_cases:
            query = query.format(table_name=table_name)
            print(f"query: {query}", file=FILE)
            select_data = exec_all_clients(clients, select, query)
            print_data(select_data)
            for name, time in select_data.items():
                all_select_data[name] += time
        print("All queries", file=FILE)
        print_data(all_select_data)
    finally:
        exec_all_clients(clients, drop_table, table_name)


if __name__ == "__main__":
    main()
