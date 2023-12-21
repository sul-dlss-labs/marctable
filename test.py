import pandas
from marctable.marc import MARC, make_field
from marctable.utils import _mapping, dataframe_iter, to_csv, to_dataframe

marc = MARC()

def test_marc() -> None:
    assert len(marc.fields) == 215

def test_get_field() -> None:
    assert marc.get_field('245')
    assert not marc.get_field('abc')

def test_get_subfield() -> None:
    assert marc.get_subfield('245', 'a').name =='Title'
    assert marc.get_subfield('245', '-') is None

def test_non_repeatable_field() -> None:
    f245 = marc.get_field('245')
    assert f245.tag == "245"
    assert f245.name == "Title Statement"
    assert f245.repeatable is False

def test_repeatable_field() -> None:
    f650 = marc.get_field('650')
    assert f650.tag == "650"
    assert f650.name == "Subject Added Entry-Topical Term"
    assert f650.repeatable is True

def test_df() -> None:
    df = to_dataframe(open('test-data/utf8.marc', 'rb'))
    assert len(df.columns) == 215
    assert len(df) == 10612
    assert df.iloc[0]['F008'] == '000110s2000    ohu    f   m        eng  '
    # 245 is not repeatable
    assert df.iloc[0]['F245'] == 'Leak testing CD-ROM [computer file] / technical editors, Charles N. Jackson, Jr., Charles N. Sherlock ; editor, Patrick O. Moore.'
    # 650 is repeatable
    assert df.iloc[0]['F650'] == ['Leak detectors.', 'Gas leakage.']

def test_custom_fields_df() -> None:
    df = to_dataframe(open('test-data/utf8.marc', 'rb'), rules=['245', '650'])
    assert len(df) == 10612
    # should only have two columns in the dataframe
    assert len(df.columns) == 2
    assert df.columns[0] == 'F245'
    assert df.columns[1] == 'F650'
    assert df.iloc[0]['F245'] == 'Leak testing CD-ROM [computer file] / technical editors, Charles N. Jackson, Jr., Charles N. Sherlock ; editor, Patrick O. Moore.'
    assert df.iloc[0]['F650'] == ['Leak detectors.', 'Gas leakage.']

def test_custom_subfields_df() -> None:
    df = to_dataframe(open('test-data/utf8.marc', 'rb'), rules=['245a', '260c'])
    assert len(df) == 10612
    assert len(df.columns) == 2
    assert df.columns[0] == 'F245a'
    assert df.columns[1] == 'F260c'
    # 245a is not repeatable
    assert df.iloc[0]['F245a'] == 'Leak testing CD-ROM'
    # 260c is repeatable
    assert df.iloc[0]['F260c'] == ['c2000.']

def test_field_mapping() -> None:
    m = _mapping(['245', '650'])
    assert m['245'] is None
    assert m['650'] is None

def test_field_subfield_mapping() -> None:
    m = _mapping(['245a', '650ax', '260'])
    assert set(m['245']) == set(['a'])
    assert set(m['650']) == set(['a', 'x'])
    assert m['260'] is None

def test_batch() -> None:
    dfs = dataframe_iter(open('test-data/utf8.marc', 'rb'), batch=1000)
    df = next(dfs)
    assert type(df), pandas.DataFrame
    assert len(df) == 1000

def test_to_csv() -> None:
    to_csv(open('test-data/utf8.marc', 'rb'), open('test-data/utf8.csv', 'w'), batch=1000)
    df = pandas.read_csv('test-data/utf8.csv')
    assert len(df) == 10622
    assert len(df.columns) == 215
    assert df.iloc[0]['F245'] == 'Leak testing CD-ROM [computer file] / technical editors, Charles N. Jackson, Jr., Charles N. Sherlock ; editor, Patrick O. Moore.'

