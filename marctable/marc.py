import pathlib
import re
from functools import cache
from typing import Generator
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup

_yaml_file = pathlib.Path(__file__).parent / 'marc.yaml'
_marc = yaml.safe_load(_yaml_file.open())

class Subfield:
    def __init__(self, code: str, name: str, repeatable: bool=False) -> None:
        self.code = code
        self.name = name
        self.repeatable = repeatable

    @classmethod
    def from_dict(_, d: dict):
        return Subfield(
            d.get('code'),
            d.get('name'),
            d.get('repeatable')
        )

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "repeatable": self.repeatable
        }

class Field:
    def __init__(self, tag: str, name: str, subfields: list[Subfield],
                 repeatable: False) -> None:
        self.tag = tag
        self.name = name
        self.subfields = subfields
        self.repeatable = repeatable

    def __str__(self) -> str:
        if len(self.subfields) > 0:
            subfields = ': ' + (','.join([sf.code for sf in self.subfields]))
        else:
            subfields = ''
        return f"{self.tag} {self.name}: {'R' if self.repeatable else 'NR'} {subfields}"

    @classmethod
    def from_dict(klass, d: dict):
        return Field(
            tag=d.get('tag'),
            name=d.get('name'),
            repeatable=d.get('repeatable'),
            subfields=[Subfield.from_dict(d) for d in d['subfields']]
        )

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "repeatable": self.repeatable,
            "subfields": [sf.to_dict() for sf in self.subfields]
        }

    def get_subfield(self, code: str) -> Subfield:
        for sf in self.subfields:
            if sf.code == code:
                return sf
        return None

class MARC:
    def __init__(self) -> None:
        self.fields = self._load()

    @cache
    def get_field(self, tag: str) -> Field:
        return self.fields.get(tag, None)

    @cache
    def get_subfield(self, tag: str, code: str) -> Subfield:
        field = self.get_field(tag)
        if field:
            return field.get_subfield(code)
        else:
            return None

    def _load(self) -> dict:
        fields = {}
        for d in _marc:
            field = Field.from_dict(d)
            fields[field.tag] = field
        return fields


def fields() -> Generator[Field, None, None]:
    toc_url = 'https://www.loc.gov/marc/bibliographic/'
    toc_doc = _soup(toc_url)
    for group_link in toc_doc.select('.contentslist a'):
        if re.match(r'^\d+', group_link.text):
            group_url = urljoin(toc_url, group_link.attrs['href'])
            group_doc = _soup(group_url)
            for field_link in group_doc.select('a'):
                if field_link.text == 'Full':
                    field_url = urljoin(group_url, field_link.attrs['href'])
                    if field := make_field(field_url):
                        yield field

def make_field(url: str) -> Field:
    soup = _soup(url)
    h1 = soup.select_one('h1', first=True).text.strip()
    if m1 := re.match(r'^(\d+) - (.+) \((.+)\)$', h1):
        tag, name, repeatable = m1.groups()

        # most pages put the subfield info in a list
        subfields = []
        for el in soup.select('table.subfields li'):
            if m2 := re.match(r'^\$(.) - (.+) \((.+)\)$', el.text):
                subfields.append(Subfield(m2.group(1), m2.group(2), m2.group(3) == "R"))

        # some pages use a different layout, of course
        if len(subfields) == 0:
            for el in soup.select('td[colspan="1"]'):
                for text in el.text.split('$'):
                    text = text.strip()
                    if m2 := re.match(r'^(.) - (.+) \((.+)\)$', text):
                        subfields.append(Subfield(m2.group(1), m2.group(2), m2.group(3) == "R"))

        return Field(tag, name, subfields, repeatable == "R")

# scrape the loc website for the marc fields
def main() -> None:
    marc_fields = []
    for f in fields():
        print(f)
        marc_fields.append(f.to_dict())
    # write out the collected data
    yaml.dump(marc_fields, _yaml_file.open('w'), default_flow_style=False)

def _soup(url: str) -> BeautifulSoup:
    return BeautifulSoup(requests.get(url).text, 'html.parser')

if __name__ == "__main__":
    main()
