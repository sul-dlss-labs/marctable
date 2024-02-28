from collections.abc import Callable
from io import IOBase
from typing import BinaryIO, TextIO

import click

import marctable.marc

from .utils import to_csv, to_jsonl, to_parquet


@click.group()
def cli() -> None:
    pass


def io_params(f: Callable) -> Callable:
    """
    Decorator for specifying input/output arguments.
    """
    f = click.argument("outfile", type=click.File("wb"), default="-")(f)
    f = click.argument("infile", type=click.File("rb"), default="-")(f)
    return f


def rule_params(f: Callable) -> Callable:
    f = click.option(
        "--rule",
        "-r",
        "rules",
        multiple=True,
        help="Specify a rule for extracting, e.g. 245 or 245a or 245ac",
    )(f)
    f = click.option(
        "--batch", "-b", default=1000, help="Batch n records when converting"
    )(f)
    return f


def avram_params(f: Callable) -> Callable:
    """
    Decorator for selecting an avram schema.
    """
    f = click.option(
        "--schema",
        "-s",
        "avram_file",
        type=click.File("rb"),
        help="Specify avram schema file",
    )(f)
    return f


@cli.command()
@io_params
@rule_params
@avram_params
def csv(infile: BinaryIO, outfile: TextIO, rules: list, batch: int, avram_file: BinaryIO) -> None:
    """
    Convert MARC to CSV.
    """
    to_csv(infile, outfile, rules=rules, batch=batch, avram_file=avram_file)


@cli.command()
@io_params
@rule_params
@avram_params
def parquet(infile: BinaryIO, outfile: IOBase, rules: list, batch: int, avram_file: BinaryIO) -> None:
    """
    Convert MARC to Parquet.
    """
    to_parquet(infile, outfile, rules=rules, batch=batch, avram_file=avram_file)


@cli.command()
@io_params
@rule_params
@avram_params
def jsonl(infile: BinaryIO, outfile: BinaryIO, rules: list, batch: int, avram_file: BinaryIO) -> None:
    """
    Convert MARC to JSON Lines (JSONL)
    """
    to_jsonl(infile, outfile, rules=rules, batch=batch, avram_file=avram_file)


@cli.command()
@click.argument("outfile", type=click.File("w"), default="-")
def avram(outfile: TextIO) -> None:
    """
    Generate an Avram schema (JSON) from the Library of Congress MARC bibliographic web.
    """
    marctable.marc.crawl(outfile=outfile)


def main() -> None:
    cli()
