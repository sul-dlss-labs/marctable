import json
import typing
from typing import Generator

import pyarrow
import pymarc
from pandas import DataFrame
from pyarrow.parquet import ParquetWriter

from .marc import MARC

marc = MARC()


def to_dataframe(marc_input: typing.BinaryIO, rules: list = []) -> DataFrame:
    """
    Return a single DataFrame for the entire dataset.
    """
    return next(dataframe_iter(marc_input, rules, batch=0))


def to_csv(
    marc_input: typing.BinaryIO,
    csv_output: typing.TextIO,
    rules: list = [],
    batch: int = 1000,
) -> None:
    """
    Convert MARC to CSV.
    """
    first_batch = True
    for df in dataframe_iter(marc_input, rules=rules, batch=batch):
        df.to_csv(csv_output, header=first_batch, index=False)


def to_jsonl(
    marc_input: typing.BinaryIO,
    jsonl_output: typing.BinaryIO,
    rules: list = [],
    batch: int = 1000,
) -> None:
    """
    Convert MARC to JSON Lines (JSONL).
    """
    for records in records_iter(marc_input, rules=rules, batch=batch):
        for record in records:
            jsonl_output.write(json.dumps(record).encode("utf8") + b"\n")


def to_parquet(
    marc_input: typing.BinaryIO,
    parquet_output: typing.BinaryIO,
    rules: list = [],
    batch: int = 1000,
) -> None:
    """
    Convert MARC to Parquet.
    """
    schema = _make_parquet_schema(rules)
    writer = ParquetWriter(parquet_output, schema, compression="gzip")
    for records_batch in records_iter(marc_input, rules=rules, batch=batch):
        table = pyarrow.Table.from_pylist(records_batch, schema)
        writer.write_table(table)

    writer.close()


def dataframe_iter(
    marc_input: typing.BinaryIO, rules: list = [], batch: int = 1000
) -> Generator[DataFrame, None, None]:
    columns = _columns(_mapping(rules))
    for records_batch in records_iter(marc_input, rules, batch):
        yield DataFrame.from_records(records_batch, columns=columns)


def records_iter(
    marc_input: typing.BinaryIO, rules: list = [], batch: int = 1000
) -> Generator[DataFrame, None, None]:
    """
    Read MARC input and generate a list of dictionaries, where each list element
    represents a MARC record.
    """
    mapping = _mapping(rules)

    rows = []
    for record in pymarc.MARCReader(marc_input):
        # if pymarc can't make sense of a record it returns None
        if record is None:
            continue

        r = {}
        for field in record.fields:
            if field.tag not in mapping:
                continue

            subfields = mapping[field.tag]

            # if subfields aren't specified stringify them
            if subfields is None:
                key = f"F{field.tag}"
                if marc.get_field(field.tag).repeatable:
                    value = r.get(key, [])
                    value.append(_stringify_field(field))
                else:
                    value = _stringify_field(field)

                r[key] = value

            # otherwise only add the subfields that were requested in the mapping
            else:
                for sf in field.subfields:
                    if sf.code not in subfields:
                        continue

                    key = f"F{field.tag}{sf.code}"
                    if marc.get_subfield(field.tag, sf.code).repeatable:
                        value = r.get(key, [])
                        value.append(sf.value)
                    else:
                        value = sf.value

                    r[key] = value

        rows.append(r)

        # yield a batch of rows when it is ready
        if batch > 0 and len(rows) == batch:
            yield rows
            rows = []

    # return any remaining rows
    if len(rows) > 0:
        yield rows


def _stringify_field(field: pymarc.Field) -> str:
    if field.is_control_field():
        return field.data
    else:
        return " ".join([sf.value for sf in field.subfields])


def _mapping(rules: list) -> dict:
    """
    unpack the mapping rules into a dictionary for easy lookup

    >>> _mapping(["245", "260ac"])
    {'245': None, '260': ['a', 'c']}
    """
    if rules is None or len(rules) == 0:
        rules = marc.fields.keys()

    m = {}
    for rule in rules:
        field_tag = rule[0:3]
        if marc.get_field(field_tag) is None:
            raise Exception(f"unknown MARC field in mapping rule: {rule}")

        subfields = set(list(rule[3:]))
        for subfield_code in subfields:
            if marc.get_subfield(field_tag, subfield_code) is None:
                raise Exception(f"unknown MARC subfield in mapping rule: {rule}")

        m[field_tag] = subfields or None

    return m


def _columns(mapping: dict) -> list:
    """
    unpack the mapping to get a list of columns for the table
    """
    cols = []
    for field_tag, subfields in mapping.items():
        if subfields is None:
            cols.append(f"F{field_tag}")
        else:
            for sf in subfields:
                cols.append(f"F{field_tag}{sf}")
    return cols


def _make_pandas_schema(rules: list) -> pyarrow.Schema:
    mapping = _mapping(rules)
    schema = {}
    for field_tag, subfields in mapping.items():
        if subfields is None:
            schema[f"F{field_tag}"] = (
                "object" if marc.get_field(field_tag).repeatable else "str"
            )
        else:
            for sf in subfields:
                schema[f"F{field_tag}{sf}"] = (
                    "object" if marc.get_subfield(field_tag, sf).repeatable else "str"
                )
    return schema


def _make_parquet_schema(rules: list) -> pyarrow.Schema:
    mapping = _mapping(rules)
    cols = []
    for field_tag, subfields in mapping.items():
        if subfields is None:
            if marc.get_field(field_tag).repeatable:
                typ = pyarrow.list_(pyarrow.string())
            else:
                typ = pyarrow.string()
            cols.append((f"F{field_tag}", typ))
        else:
            for sf in subfields:
                if marc.get_subfield(field_tag, sf).repeatable:
                    typ = pyarrow.list_(pyarrow.string())
                else:
                    typ = pyarrow.string()
                cols.append((f"F{field_tag}{sf}", typ))
    return pyarrow.schema(cols)
