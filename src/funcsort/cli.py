"""Command-line interface for funcsort."""

import logging
from pathlib import Path

import click

from .core import process_path

logger = logging.getLogger(__name__)


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, path_type=Path),
    required=False,
    default=Path("."),
)
@click.option(
    "--fix", is_flag=True, help="Automatically fix sorting instead of just checking"
)
@click.option("-v", "--verbose", is_flag=True, help="Print detailed output")
def main(path: Path = Path("."), fix: bool = False, verbose: bool = False) -> None:
    """Sort Python functions and methods by call hierarchy.

    PATH can be a file or directory (defaults to current directory).

    Raises:
        SystemExit: With exit code 1 if files need sorting (check mode).
    """
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(message)s")

    _, changed = process_path(path, fix)

    if changed:
        if fix:
            print(f"✓ Fixed {len(changed)} file(s)")
        else:
            for file_path in changed:
                logger.warning("Would reorder: %s", file_path)
            logger.warning("✗ %d file(s) need sorting (use --fix)", len(changed))
            raise SystemExit(1)
    else:
        print("✓ All files already sorted")
