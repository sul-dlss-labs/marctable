from collections.abc import Callable

import click

import marctable.marc

from .utils import to_dataframe, to_csv


@click.group()
def cli() -> None:
    pass

def common_params(f: Callable) -> Callable:
    """
    Decorator for specifying input/output arguments and rules.
    """
    f = click.argument("outfile", type=click.File("w"), default="-")(f)
    f = click.argument("infile", type=click.File("rb"), default="-")(f)
    f = click.option("--rule", "-r", "rules", multiple=True, help="Specify a rule for a field or field/subfield to extract, e.g. 245 or 245a")(f)
    f = click.option("--batch", "-b", default=1000, help="Batch n records when converting")(f)
    return f

@cli.command()
@common_params
def csv(infile: click.File, outfile: click.File, rules: list, batch: int) -> None:
    """
    Convert MARC to CSV.
    """
    to_csv(infile, outfile, rules=rules, batch=batch)

@cli.command()
def yaml() -> None:
    """
    Generate YAML for the MARC specification by scraping the Library of Congress.
    """
    marctable.marc.main()

def main() -> None:
    cli()
