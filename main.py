import argparse
import json
import time
import random
import sys

from io import TextIOWrapper
from collections import defaultdict

from clickhouse import ClickHouseClient
from greenplum import GreenplumClient
from mysql import MysqlClient
from postgresql import PostgresqlClient
from ydb_client import YdbClient

KEYS_TO_CLIENT = {
    "ClickHouse": ClickHouseClient,
    "MySQL": MysqlClient,
    "PostgreSQL": PostgresqlClient,
    "Greenplum": GreenplumClient,
    "Ydb": YdbClient,
}


def get_db_scheme(db_key: str, db_schemes: list) -> dict:
    return {
        field["Name"]: field[f"{db_key} Type"]
        for field in db_schemes
    }


def random_str(length: int) -> str:
    choices = "0123456789abcdefghijklmnopqrstuvwxyz"
    s = ""

    for _ in range(length):
        s += random.choice(choices)

    return s


def get_random_record(db_schemes: list):
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


def get_random_records(count: int, db_schemes: list) -> list:
    return [get_random_record(db_schemes) for _ in range(count)]


def get_records_from_file(file: TextIOWrapper, count: int) -> list:
    result = []
    for _ in range(count):
        line = file.readline()
        if not line:
            break

        result.append(json.loads(line))

    return result


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


def print_data(data: dict, file: TextIOWrapper) -> None:
    for name, time in sorted(data.items()):
        print(f"{name} in {time:.3f} s", file=file)
    print(file=file)
    file.flush()


def generate_data(opts: argparse.Namespace) -> None:
    if opts.output:
        output_file = open(opts.output, "w")
    else:
        output_file = sys.stdout

    scheme = json.load(open(opts.scheme, "r"))

    for _ in range(opts.size):
        print(json.dumps(get_random_record(scheme)), file=output_file)

    if opts.output:
        output_file.close()


def run_tests(opts: argparse.Namespace) -> None:
    if opts.output:
        output_file = open(opts.output, "w")
    else:
        output_file = sys.stdout

    if opts.data:
        data_file = open(opts.data, "r")

    scheme = json.load(open(opts.scheme, "r"))
    conn = json.load(open(opts.conn, "r"))
    launches = {
        key: {
            "client": KEYS_TO_CLIENT[key](conn[key]),
            "scheme": get_db_scheme(key, scheme),
        }
        for key in opts.database
    }

    print(f"Launches={tuple(launches.keys())}", file=output_file)
    print(f"Batch size={opts.batch}", file=output_file)

    try:
        table_name = f"test_{random_str(5)}"

        exec_all_clients(launches, create_table, table_name)
        print(f"Created table '{table_name}'", file=output_file)

        inserted = 0
        add_records_data = defaultdict(float)
        for _ in range((opts.size + opts.batch - 1) // opts.batch):
            size = min(opts.size - inserted, opts.batch)
            if opts.data:
                records = get_records_from_file(data_file, size)
            else:
                records = get_random_records(size, scheme)
            
            if len(records) == 0:
                break

            inserted += len(records)
            temp_data = exec_all_clients(
                launches, add_records, table_name, records)

            for name, time in temp_data.items():
                add_records_data[name] += time

        print(f"Inserted {inserted} records\n", file=output_file)
        print_data(add_records_data, output_file)

        all_select_data = defaultdict(float)
        for query in json.load(open(opts.tests, "r")):
            query = query.format(table_name=table_name)
            print(f"query: {query}", file=output_file)
            select_data = exec_all_clients(launches, select, query)
            print_data(select_data, output_file)
            for name, time in select_data.items():
                all_select_data[name] += time
        print("All queries", file=output_file)
        print_data(all_select_data, output_file)
    finally:
        exec_all_clients(launches, drop_table, table_name)
        print(f"Dropped table '{table_name}'", file=output_file)

    if opts.data:
        data_file.close()

    if opts.output:
        output_file.close()


def init_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="db_tester",
        add_help=True,
    )
    subparsers = parser.add_subparsers()

    parser_generate = subparsers.add_parser(
        "generate",
        description="generate data for tests",
    )
    parser_generate.add_argument(
        "-s",
        "--size",
        type=int,
        required=True,
        help="data set size",
    )
    parser_generate.add_argument(
        "--scheme",
        type=str,
        required=True,
        help="path to file with schema of data",
    )
    parser_generate.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="path to output file",
    )
    parser_generate.set_defaults(func=generate_data)

    parser_run = subparsers.add_parser(
        "run",
        description="run performance tests",
    )
    parser_run.add_argument(
        "-db",
        "--database",
        type=str,
        action="append",
        choices=KEYS_TO_CLIENT.keys(),
        help="name of database for test",
    )
    parser_run.add_argument(
        "-b",
        "--batch",
        type=int,
        required=False,
        default=5000,
        help="size of batch for INSERT INTO",
    )
    parser_run.add_argument(
        "-s",
        "--size",
        type=int,
        required=True,
        help="data set size",
    )
    parser_run.add_argument(
        "--conn",
        type=str,
        required=True,
        help="path to file with data for database connections",
    )
    parser_run.add_argument(
        "--scheme",
        type=str,
        required=True,
        help="path to file with schema of data",
    )
    parser_run.add_argument(
        "-t",
        "--tests",
        type=str,
        required=True,
        help="path to file with test cases",
    )
    parser_run.add_argument(
        "-d",
        "--data",
        type=str,
        required=False,
        help="path to file with data for tests",
    )
    parser_run.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="path to output file",
    )
    parser_run.set_defaults(func=run_tests)

    return parser


def main():
    parser = init_parser()

    opts = parser.parse_args()

    opts.func(opts)


if __name__ == '__main__':
    main()
