import typing

import pandas
import pymarc

from .marc import MARC

marc = MARC()

def to_dataframe(marc_input: typing.BinaryIO, mapping=None) -> pandas.DataFrame:

    # if not defined give them ALL the MARC fields; otherwise unpack them
    if mapping is None:
        mapping = _mapping(marc.fields.keys())
    else:
        mapping = _mapping(mapping)

    rows = []
    for record in pymarc.MARCReader(marc_input):
        r = {}
        for field in record.fields:
            if field.tag not in mapping:
                continue

            subfields = mapping[field.tag]

            # if subfields aren't specified stringify them
            if subfields is None:
                if marc.get_field(field.tag).repeatable:
                    value = r.get(field.tag, [])
                    value.append(_stringify_field(field))
                else:
                    value = _stringify_field(field)

                r[field.tag] = value

            # otherwise only add the subfields that were requested in the mapping
            else:
                for sf in field.subfields:
                    if sf.code not in subfields:
                        continue

                    key = f"{field.tag}{sf.code}"
                    if marc.get_subfield(field.tag, sf.code).repeatable:
                        value = r.get(key, [])
                        value.append(sf.value)
                    else:
                        value = sf.value

                    r[key] = value

        rows.append(r)

    return pandas.DataFrame.from_records(rows)


def _stringify_field(field: pymarc.Field) -> str:
    if field.is_control_field():
        return field.data
    else:
        return ' '.join([sf.value for sf in field.subfields])

def _mapping(mapping: list) -> dict:
    """
    unpack the mapping rules into a dictionary for easy lookup

    >>> _mapping["245", "260ac"]
    {'245': None, '260': ['a', 'c']}
    """
    m = {}
    for rule in mapping:
        field_tag = rule[0:3]
        if marc.get_field(field_tag) is None:
            raise Exception(f"unknown MARC field in mapping rule: {rule}")

        subfields = set(list(rule[3:]))
        for subfield_code in subfields:
            if marc.get_subfield(field_tag, subfield_code) is None:
                raise Exception(f"unknown MARC subfield in mapping rule: {rule}")

        m[field_tag] = subfields or None

    return m
