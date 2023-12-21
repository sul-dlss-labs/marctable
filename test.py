from marctable import to_dataframe, _mapping
from marctable.marc import MARC, make_field

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
    assert len(df) == 10612
    assert df.iloc[0]['008'] == '000110s2000    ohu    f   m        eng  '
    # 245 is not repeatable
    assert df.iloc[0]['245'] == 'Leak testing CD-ROM [computer file] / technical editors, Charles N. Jackson, Jr., Charles N. Sherlock ; editor, Patrick O. Moore.'
    # 650 is repeatable
    assert df.iloc[0]['650'] == ['Leak detectors.', 'Gas leakage.']

def test_custom_fields_df() -> None:
    df = to_dataframe(open('test-data/utf8.marc', 'rb'), mapping=['245', '650'])
    assert len(df) == 10612
    # should only have two columns in the dataframe
    assert len(df.columns) == 2
    assert df.columns[0] == '245'
    assert df.columns[1] == '650'
    assert df.iloc[0]['245'] == 'Leak testing CD-ROM [computer file] / technical editors, Charles N. Jackson, Jr., Charles N. Sherlock ; editor, Patrick O. Moore.'
    assert df.iloc[0]['650'] == ['Leak detectors.', 'Gas leakage.']

def test_custom_subfields_df() -> None:
    df = to_dataframe(open('test-data/utf8.marc', 'rb'), mapping=['245a', '260c'])
    assert len(df) == 10612
    assert len(df.columns) == 2
    assert df.columns[0] == '245a'
    assert df.columns[1] == '260c'
    # 245a is not repeatable
    assert df.iloc[0]['245a'] == 'Leak testing CD-ROM'
    # 260c is repeatable
    assert df.iloc[0]['260c'] == ['c2000.']

def test_field_mapping() -> None:
    m = _mapping(['245', '650'])
    assert m['245'] is None
    assert m['650'] is None

def test_field_subfield_mapping() -> None:
    m = _mapping(['245a', '650ax', '260'])
    assert set(m['245']) == set(['a'])
    assert set(m['650']) == set(['a', 'x'])
    assert m['260'] is None

def test_parens() -> None:
    f = make_field('https://www.loc.gov/marc/bibliographic/bd260.html')
    assert f
