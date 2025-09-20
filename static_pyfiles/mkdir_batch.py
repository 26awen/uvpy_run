# /// script
# requires-python = ">=3.12"
# dependencies = ["click>=8.0.0"]
# ///

# MIT License
#
# Copyright (c) 2025 Config-Txt Project
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Third-party Dependencies:
# - Click: BSD-3-Clause License (https://github.com/pallets/click)

"""
Create multiple numbered directories in batch

A command-line utility for efficiently creating multiple folders with numbered suffixes.
Supports customizable base names, starting indices, and destination directories.

Version: 1.0.0
Category: File Management
Author: Config-Txt Project

Usage Examples:
    uv run mkdir_batch.py ./test_dirs
    uv run mkdir_batch.py ./projects --base-name project --count 5
    uv run mkdir_batch.py ./data --base-name dataset --count 10 --start 1
    uv run mkdir_batch.py ./folders --base-name folder --count 3 --verbose
"""

import os
from pathlib import Path
from typing import Optional

import click


def create_folders_batch(
    dest_dir: str | Path, base_name: str, count: int, start_index: int = 0
) -> list[str]:
    """
    Create multiple folders with numbered suffixes.

    Args:
        dest_dir: Target directory where folders will be created
        base_name: Base name for the folders
        count: Number of folders to create
        start_index: Starting index for numbering

    Returns:
        List of created folder paths
    """
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    created_folders = []

    for i in range(start_index, start_index + count):
        folder_name = f"{base_name}_{i}"
        folder_path = dest_path / folder_name
        folder_path.mkdir(exist_ok=True)
        created_folders.append(str(folder_path))

    return created_folders


@click.command()
@click.argument("dest_dir", type=click.Path())
@click.option(
    "--base-name",
    "-n",
    default="new_folder",
    help="Base name for the folders (default: new_folder)",
)
@click.option(
    "--count",
    "-c",
    default=3,
    type=int,
    help="Number of folders to create (default: 3)",
)
@click.option(
    "--start",
    "-s",
    default=0,
    type=int,
    help="Starting index for numbering (default: 0)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def main(dest_dir: str, base_name: str, count: int, start: int, verbose: bool) -> None:
    """
    Create multiple numbered folders in the specified directory.

    DEST_DIR is the target directory where folders will be created.
    """
    if count <= 0:
        click.echo("Error: Count must be greater than 0", err=True)
        raise click.Abort()

    try:
        created_folders = create_folders_batch(
            dest_dir=dest_dir, base_name=base_name, count=count, start_index=start
        )

        if verbose:
            click.echo(f"Successfully created {len(created_folders)} folders:")
            for folder in created_folders:
                click.echo(f"  - {folder}")
        else:
            click.echo(
                f"Successfully created {len(created_folders)} folders in {dest_dir}"
            )

    except PermissionError:
        click.echo(
            f"Error: Permission denied when creating folders in {dest_dir}", err=True
        )
        raise click.Abort()
    except OSError as e:
        click.echo(f"Error: Failed to create folders - {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
