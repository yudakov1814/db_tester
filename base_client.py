class DbClient:
    def __init__(self, config: dict) -> None:
        raise NotImplementedError()

    def select(self, query: str) -> list:
        raise NotImplementedError()

    def create_table(self, table_name: str, schema: dict) -> None:
        raise NotImplementedError()

    def _get_create_table_query(self, table_name: str, schema: dict, db: str = None) -> str:
        return "CREATE TABLE {db}{table_name} ({schema})".format(
            db=f"{db}." if db else "",
            table_name=table_name,
            schema=",".join(
                "{name} {type}".format(name=name, type=type)
                for name, type in schema.items()
            ),
        )

    def add_record(self, table_name: str, schema: dict, records: dict) -> None:
        raise NotImplementedError()

    def _get_add_record_query(self, table_name: str, schema: dict, records: dict, db: str = None) -> str:
        fields = tuple(sorted(schema.keys()))
        values = [
            "({data})".format(
                data=",".join(
                    self._prepare_value(record[field]) for field in fields
                )
            )
            for record in records
        ]

        query = "INSERT INTO {db}{table_name} ({schema}) VALUES {values}".format(
            db=f"{db}." if db else "",
            table_name=table_name,
            schema=",".join(fields),
            values=",".join(values),
        )

        return query

    def drop_table(self, table_name: str,) -> None:
        raise NotImplementedError()

    def _get_drop_table_query(self, table_name: str, db: str = None) -> str:
        return "DROP TABLE IF EXISTS {db}{table_name}".format(
            db=f"{db}." if db else "",
            table_name=table_name,
        )

    def _prepare_value(self, value):
        if isinstance(value, str):
            return "'{value}'".format(value=value)
        else:
            return str(value)
