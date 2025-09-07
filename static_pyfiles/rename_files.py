# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "click",
# ]
# ///

import os
from pathlib import Path
from typing import Optional

import click


@click.command()
@click.argument(
    "directory", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option("--pattern", default="*", help="File pattern to match, e.g., '*.txt'")
@click.option("--prefix", default="", help="Prefix to add to filenames")
@click.option("--suffix", default="", help="Suffix to add to filenames")
@click.option("--start", default=1, type=int, help="Starting number for numbering")
@click.option(
    "--digits", default=3, type=int, help="Number of digits for numbering, e.g., 001"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be renamed without actually doing it",
)
def rename_files(
    directory: str,
    pattern: str,
    prefix: str,
    suffix: str,
    start: int,
    digits: int,
    dry_run: bool,
) -> None:
    """
    Rename files in a directory by adding sequential numbers.

    Example: uv run script.py /path/to/dir --pattern '*.jpg' --prefix 'image_' --start 1 --digits 3
    """
    dir_path = Path(directory)
    files = list(dir_path.glob(pattern))
    files.sort()  # Sort files to ensure consistent ordering

    if not files:
        click.echo("No files found matching the pattern.")
        return

    for i, file_path in enumerate(files, start=start):
        if file_path.is_file():
            number_str = f"{i:0{digits}d}"
            new_name = f"{prefix}{number_str}_{file_path.name}{suffix}"
            new_path = file_path.parent / new_name

            if dry_run:
                click.echo(f"Would rename: {file_path.name} -> {new_name}")
            else:
                try:
                    file_path.rename(new_path)
                    click.echo(f"Renamed: {file_path.name} -> {new_name}")
                except OSError as e:
                    click.echo(f"Error renaming {file_path.name}: {e}", err=True)


if __name__ == "__main__":
    rename_files()

