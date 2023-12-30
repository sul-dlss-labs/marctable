"""
This module contains classes to make it easier to work with MARC as an Avram
schema, which is loaded from the marc.json that is alongside this file. The
Avram schema lets marctable know which MARC fields and subfields are allowed,
and whether they should be encoded as lists rather than single values. It also
includes functions used for regenerating the Avram schema by crawling the MARC
specification the Library of Congress website.

For more about Avram see https://format.gbv.de/schema/avram/specification
"""

import json
import pathlib
import re
import sys
from functools import cache
from typing import IO, Generator
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class Subfield:
    def __init__(self, code: str, label: str, repeatable: bool = False) -> None:
        self.code = code
        self.label = label
        self.repeatable = repeatable

    @classmethod
    def from_dict(_, d: dict):
        return Subfield(d.get("code"), d.get("label"), d.get("repeatable"))

    def to_dict(self) -> dict:
        return {"code": self.code, "label": self.label, "repeatable": self.repeatable}


class Field:
    def __init__(
        self, tag: str, label: str, subfields: dict, repeatable: False, url: str = None
    ) -> None:
        self.tag = tag
        self.label = label
        self.subfields = subfields
        self.repeatable = repeatable
        self.url = url

    def __str__(self) -> str:
        if len(self.subfields) > 0:
            subfields = ": " + (",".join(self.subfields.keys()))
        else:
            subfields = ""
        return (
            f"{self.tag} {self.label}: {'R' if self.repeatable else 'NR'} {subfields}"
        )

    @classmethod
    def from_dict(klass, d: dict):
        return Field(
            tag=d.get("tag"),
            label=d.get("label"),
            repeatable=d.get("repeatable"),
            url=d.get("url"),
            subfields=[Subfield.from_dict(d) for d in d["subfields"].values()],
        )

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "label": self.label,
            "repeatable": self.repeatable,
            "url": self.url,
            "subfields": {sf.code: sf.to_dict() for sf in self.subfields.values()},
        }

    def get_subfield(self, code: str) -> Subfield:
        for sf in self.subfields:
            if sf.code == code:
                return sf
        return None


class MARC:
    def __init__(self) -> None:
        self.fields = []

    @cache
    def get_field(self, tag: str) -> Field:
        for field in self.fields:
            if field.tag == tag:
                return field
        return None

    @cache
    def get_subfield(self, tag: str, code: str) -> Subfield:
        field = self.get_field(tag)
        if field:
            return field.get_subfield(code)
        else:
            return None

    @property
    def avram_file(self):
        return pathlib.Path(__file__).parent / "marc.json"

    @classmethod
    @cache
    def from_avram(cls, avram_file: IO = None) -> dict:
        marc = MARC()

        if avram_file is None:
            avram_file = marc.avram_file.open("r")

        for d in json.load(avram_file)["fields"].values():
            marc.fields.append(Field.from_dict(d))

        return marc

    def to_avram(self, avram_file: IO = None) -> None:
        if avram_file is None:
            avram_file = self.avram_file.open("w")

        d = {"fields": {f.tag: f.to_dict() for f in self.fields}}
        json.dump(d, avram_file, indent=2)


def fields() -> Generator[Field, None, None]:
    toc_url = "https://www.loc.gov/marc/bibliographic/"
    toc_doc = _soup(toc_url)
    for group_link in toc_doc.select(".contentslist a"):
        if re.match(r"^\d+", group_link.text):
            group_url = urljoin(toc_url, group_link.attrs["href"])
            group_doc = _soup(group_url)
            for field_link in group_doc.select("a"):
                if field_link.text == "Full":
                    field_url = urljoin(group_url, field_link.attrs["href"])
                    if field := make_field(field_url):
                        yield field


def make_field(url: str) -> Field:
    soup = _soup(url)
    h1 = soup.select_one("h1", first=True).text.strip()
    if m1 := re.match(r"^(\d+) - (.+) \((.+)\)$", h1):
        tag, label, repeatable = m1.groups()

        # most pages put the subfield info in a list
        subfields = {}
        for el in soup.select("table.subfields li"):
            if m2 := re.match(r"^\$(.) - (.+) \((.+)\)$", el.text):
                subfields[m2.group(1)] = Subfield(
                    m2.group(1), m2.group(2), m2.group(3) == "R"
                )

        # some pages use a different layout, of course
        if len(subfields) == 0:
            for el in soup.select('td[colspan="1"]'):
                for text in el.text.split("$"):
                    text = text.strip()
                    if m2 := re.match(r"^(.) - (.+) \((.+)\)$", text):
                        subfields[m2.group(1)] = Subfield(
                            code=m2.group(1),
                            label=m2.group(2),
                            repeatable=m2.group(3) == "R",
                        )

        return Field(
            tag=tag,
            label=label.strip(),
            repeatable=repeatable == "R",
            url=url,
            subfields=subfields,
        )


# scrape the loc website for the marc fields
def crawl(n: int = 0, quiet: bool = False, outfile: IO = sys.stdout) -> None:
    marc = MARC()
    for f in fields():
        marc.fields.append(f)
        if not quiet:
            print(f)
        if n != 0 and len(marc.fields) >= n:
            break
    marc.to_avram(outfile)


def _soup(url: str) -> BeautifulSoup:
    return BeautifulSoup(requests.get(url).text, "html.parser")
