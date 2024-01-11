import json
import pathlib
from io import StringIO

import pandas
from marctable.marc import MARC, SchemaFieldError, SchemaSubfieldError, crawl
from marctable.utils import _mapping, dataframe_iter, to_csv, to_dataframe, to_parquet
from pytest import raises

marc = MARC.from_avram()


def test_crawl() -> None:
    # crawl the first 10 field definitions from the loc site (to save time)
    outfile = StringIO()
    crawl(10, quiet=True, outfile=outfile)
    outfile.seek(0)

    # ensure the Avram JSON parses and looks ok
    schema = json.load(outfile)
    assert schema
    assert len(schema["fields"]) == 10

    # ensure that the Avram JSON for a field looks ok
    assert schema["fields"]["015"]
    f015 = schema["fields"]["015"]
    assert f015["label"] == "National Bibliography Number"
    assert f015["url"] == "https://www.loc.gov/marc/bibliographic/bd015.html"
    assert len(f015["subfields"]) == 6

    # ensure that the Avram JSON for a subfield looks ok
    assert f015["subfields"]["2"]
    f0152 = f015["subfields"]["2"]
    assert f0152["label"] == "Source"
    assert f0152["code"] == "2"
    assert f0152["repeatable"] is False


def test_marc() -> None:
    assert len(marc.fields) == 215


def test_get_field() -> None:
    assert marc.get_field("245")
    with raises(SchemaFieldError, match="abc is not a defined field tag in Avram"):
        marc.get_field("abc")


def test_get_subfield() -> None:
    assert marc.get_subfield("245", "a").label == "Title"
    with raises(SchemaSubfieldError, match="- is not a valid subfield in field 245"):
        marc.get_subfield("245", "-") is None


def test_non_repeatable_field() -> None:
    f245 = marc.get_field("245")
    assert f245.tag == "245"
    assert f245.label == "Title Statement"
    assert f245.repeatable is False


def test_repeatable_field() -> None:
    f650 = marc.get_field("650")
    assert f650.tag == "650"
    assert f650.label == "Subject Added Entry-Topical Term"
    assert f650.repeatable is True


def test_df() -> None:
    df = to_dataframe(open("test-data/utf8.marc", "rb"))
    assert len(df.columns) == 215
    assert len(df) == 10612
    assert df.iloc[0]["F008"] == "000110s2000    ohu    f   m        eng  "
    # 245 is not repeatable
    assert (
        df.iloc[0]["F245"]
        == "Leak testing CD-ROM [computer file] / technical editors, Charles N. "
        "Jackson, Jr., Charles N. Sherlock ; editor, Patrick O. Moore."
    )
    # 650 is repeatable
    assert df.iloc[0]["F650"] == ["Leak detectors.", "Gas leakage."]


def test_custom_fields_df() -> None:
    df = to_dataframe(open("test-data/utf8.marc", "rb"), rules=["245", "650"])
    assert len(df) == 10612
    # should only have two columns in the dataframe
    assert len(df.columns) == 2
    assert df.columns[0] == "F245"
    assert df.columns[1] == "F650"
    assert (
        df.iloc[0]["F245"]
        == "Leak testing CD-ROM [computer file] / technical editors, Charles N. "
        "Jackson, Jr., Charles N. Sherlock ; editor, Patrick O. Moore."
    )
    assert df.iloc[0]["F650"] == ["Leak detectors.", "Gas leakage."]


def test_custom_subfields_df() -> None:
    df = to_dataframe(open("test-data/utf8.marc", "rb"), rules=["245a", "260c"])
    assert len(df) == 10612
    assert len(df.columns) == 2
    assert df.columns[0] == "F245a"
    assert df.columns[1] == "F260c"
    # 245a is not repeatable
    assert df.iloc[0]["F245a"] == "Leak testing CD-ROM"
    # 260c is repeatable
    assert df.iloc[0]["F260c"] == ["c2000."]


def test_field_mapping() -> None:
    m = _mapping(["245", "650"])
    assert m["245"] is None
    assert m["650"] is None


def test_field_subfield_mapping() -> None:
    m = _mapping(["245a", "650ax", "260"])
    assert set(m["245"]) == set(["a"])
    assert set(m["650"]) == set(["a", "x"])
    assert m["260"] is None


def test_batch() -> None:
    dfs = dataframe_iter(open("test-data/utf8.marc", "rb"), batch=1000)
    df = next(dfs)
    assert type(df), pandas.DataFrame
    assert len(df) == 1000


def test_to_csv() -> None:
    to_csv(
        open("test-data/utf8.marc", "rb"), open("test-data/utf8.csv", "w"), batch=1000
    )
    df = pandas.read_csv("test-data/utf8.csv")
    assert len(df) == 10612
    assert len(df.columns) == 215
    assert (
        df.iloc[0]["F245"]
        == "Leak testing CD-ROM [computer file] / technical editors, Charles N. "
        "Jackson, Jr., Charles N. Sherlock ; editor, Patrick O. Moore."
    )


def test_to_parquet() -> None:
    to_parquet(
        open("test-data/utf8.marc", "rb"),
        open("test-data/utf8.parquet", "wb"),
        batch=1000,
    )
    assert pathlib.Path("test-data/utf8.parquet").is_file()
    df = pandas.read_parquet("test-data/utf8.parquet")
    assert len(df) == 10612
    assert len(df.columns) == 215


def test_to_parquet_with_rules() -> None:
    to_parquet(
        open("test-data/utf8.marc", "rb"),
        open("test-data/utf8.parquet", "wb"),
        batch=1000,
        rules=["001", "245", "650v"],
    )
    assert pathlib.Path("test-data/utf8.parquet").is_file()
    df = pandas.read_parquet("test-data/utf8.parquet")
    assert len(df) == 10612
    assert len(df.columns) == 3
