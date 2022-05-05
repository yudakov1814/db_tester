from collections import defaultdict
import json
import time
import random

from clickhouse import ClickHouseClient
from greenplum import GreenplumClient
from mysql import MysqlClient
from postgresql import PostgresqlClient

FILE_NAME = "result"
FILE = open(FILE_NAME, "w")
BATCH_SIZE = 1
BATCHES = 1

db_config = json.load(open("db_config.json", "r"))
db_schemes = json.load(open("db_schemes.json", "r"))
test_cases = json.load(open("test_cases.json", "r"))

CLICKHOUSE_KEY = "ClickHouse"
MYSQL_KEY = "MySQL"
POSTGRESQL_KEY = "PostgreSQL"
GREENPLUM_KEY = "Greenplum"

DB_KEYS = [
    CLICKHOUSE_KEY,
    MYSQL_KEY,
    POSTGRESQL_KEY,
    GREENPLUM_KEY,
]

key_to_client = {
    CLICKHOUSE_KEY: ClickHouseClient,
    MYSQL_KEY: MysqlClient,
    POSTGRESQL_KEY: PostgresqlClient,
    GREENPLUM_KEY: GreenplumClient,
}

KEYS_TO_LAUNCH = [
    MYSQL_KEY,
    POSTGRESQL_KEY,
]


def get_db_scheme(db_key: str) -> dict:
    return {
        field["Name"]: field[f"{db_key} Type"]
        for field in db_schemes
    }


def random_str(length):
    choices = "0123456789abcdefghijklmnopqrstuvwxyz"
    s = ""
    for _ in range(length):
        s += random.choice(choices)
    return s


def get_random_record():
    record = {}

    for field in db_schemes:
        py_type = field["Python Type"]
        randint = random.randint(field["Min"], field["Max"])
        if py_type == "int":
            record[field["Name"]] = randint
        elif py_type == "str":
            record[field["Name"]] = random_str(randint)
        else:
            raise RuntimeError("Unexpected python type '{py_type}'")

    return record


def get_random_records(count: int) -> list:
    return [get_random_record() for _ in range(count)]


def create_table(launch: dict, table_name: str) -> None:
    launch["client"].create_table(table_name, launch["scheme"])


def add_records(launch: dict, table_name: str, records: list) -> None:
    launch["client"].add_records(table_name, launch["scheme"], records)


def select(launch: dict, query: str) -> list:
    return launch["client"].select(query)


def drop_table(launch: dict, table_name: str) -> None:
    launch["client"].drop_table(table_name)


def exec_all_clients(clients: dict, func, *args) -> dict:
    data = {}

    for key, launch in clients.items():
        start = time.perf_counter()
        func(launch, *args)
        end = time.perf_counter()
        data[f"{key}.{func.__name__}"] = end - start

    return data


def print_data(data: dict) -> None:
    for name, time in sorted(data.items()):
        print(f"{name} in {time:.3f} s", file=FILE)
    print(file=FILE)
    FILE.flush()


def main():
    table_name = f"test_{random_str(5)}"
    launches = {
        key: {
            "client": key_to_client[key](db_config[key]),
            "scheme": get_db_scheme(key),
        }
        for key in KEYS_TO_LAUNCH
    }

    print(f"{BATCH_SIZE * BATCHES} records", file=FILE)
    print(file=FILE)

    try:
        exec_all_clients(launches, create_table, table_name)

        add_records_data = defaultdict(float)
        for _ in range(BATCHES):
            records = get_random_records(BATCH_SIZE)
            temp_data = exec_all_clients(launches, add_records, table_name, records)
            for name, time in temp_data.items():
                add_records_data[name] += time
        print_data(add_records_data)

        all_select_data = defaultdict(float)
        for query in test_cases:
            query = query.format(table_name=table_name)
            print(f"query: {query}", file=FILE)
            select_data = exec_all_clients(launches, select, query)
            print_data(select_data)
            for name, time in select_data.items():
                all_select_data[name] += time
        print("All queries", file=FILE)
        print_data(all_select_data)
    finally:
        exec_all_clients(launches, drop_table, table_name)


if __name__ == "__main__":
    main()
