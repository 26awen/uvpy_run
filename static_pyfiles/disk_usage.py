# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.0",
#     "psutil>=5.9.0",
#     "rich>=13.7.0",
# ]
# ///

# MIT License
#
# Copyright (c) 2025 UVPY.RUN
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
# - psutil: BSD-3-Clause License (https://github.com/giampaolo/psutil)
# - Rich: MIT License (https://github.com/Textualize/rich)

"""
Monitor disk usage with beautiful visualization and color-coded alerts

A command-line utility for monitoring disk space usage across all partitions
or specific mount points. Features elegant table display with progress bars,
color-coded usage levels, and detailed partition information.

Version: 0.0.5
Category: System Monitoring
Author: UVPY.RUN

Usage Examples:
    uv run disk_usage.py
    uv run disk_usage.py -p /
    uv run disk_usage.py --partition /home
"""

import click
import psutil
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from typing import Optional


console = Console()


def format_bytes(bytes: float) -> str:
    """
    Convert bytes to human readable format.

    Args:
        bytes: Size in bytes

    Returns:
        Human readable string with appropriate unit
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024.0:
            return f"{bytes:.1f}{unit}"
        bytes /= 1024.0
    return f"{bytes:.1f}PB"


def get_usage_color(percent: float) -> str:
    """
    Get color based on usage percentage.

    Args:
        percent: Usage percentage

    Returns:
        Color name for rich
    """
    if percent >= 90:
        return "red"
    elif percent >= 75:
        return "yellow"
    else:
        return "green"


def create_usage_bar(percent: float, width: int = 20) -> str:
    """
    Create a simple ASCII usage bar.

    Args:
        percent: Usage percentage
        width: Width of the bar

    Returns:
        ASCII bar string
    """
    filled = int(width * percent / 100)
    empty = width - filled
    return "█" * filled + "░" * empty


def display_partition_table(partitions_data: list[dict]) -> None:
    """
    Display partition information in a beautiful table.

    Args:
        partitions_data: List of partition information dictionaries
    """
    table = Table(
        show_header=True, header_style="bold cyan", border_style="bright_black"
    )

    table.add_column("Mount", style="cyan", no_wrap=True)
    table.add_column("Size", justify="right", style="white")
    table.add_column("Used", justify="right", style="magenta")
    table.add_column("Free", justify="right", style="green")
    table.add_column("Usage", justify="center", width=24)
    table.add_column("%", justify="right", style="yellow")

    for data in partitions_data:
        color = get_usage_color(data["percent"])
        usage_bar = create_usage_bar(data["percent"])

        table.add_row(
            data["mountpoint"],
            format_bytes(data["total"]),
            format_bytes(data["used"]),
            format_bytes(data["free"]),
            f"[{color}]{usage_bar}[/{color}]",
            f"[{color}]{data['percent']:.1f}[/{color}]",
        )

    console.print()
    console.print(table)
    console.print()


def display_single_partition(partition: str) -> None:
    """
    Display detailed information for a single partition.

    Args:
        partition: Mount point or device path
    """
    try:
        usage = psutil.disk_usage(partition)
        percent = usage.percent
        color = get_usage_color(percent)

        info = Text()
        info.append(f"{partition}\n\n", style="bold cyan")
        info.append(f"Total    {format_bytes(usage.total):>12}\n", style="white")
        info.append(f"Used     {format_bytes(usage.used):>12}\n", style="magenta")
        info.append(f"Free     {format_bytes(usage.free):>12}\n", style="green")
        info.append(f"\n{create_usage_bar(percent, 30)}\n", style=color)
        info.append(f"{percent:.1f}% used", style=f"bold {color}")

        panel = Panel(
            info,
            border_style=color,
            padding=(1, 2),
        )

        console.print()
        console.print(panel)
        console.print()

    except (PermissionError, FileNotFoundError) as e:
        console.print(f"\n[red]Error: {e}[/red]\n")


def get_all_partitions_data() -> list[dict]:
    """
    Get usage data for all partitions.

    Returns:
        List of dictionaries containing partition data
    """
    partitions = psutil.disk_partitions()
    data = []

    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            data.append(
                {
                    "mountpoint": partition.mountpoint,
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            )
        except PermissionError:
            continue

    return data


@click.command()
@click.option(
    "-p",
    "--partition",
    type=str,
    help="Specific partition to display",
)
def main(partition: Optional[str]) -> None:
    """
    Disk usage monitor with elegant design.

    Examples:

        uv run disk_usage.py

        uv run disk_usage.py -p /

        uv run disk_usage.py -p /home
    """
    if partition:
        display_single_partition(partition)
    else:
        partitions_data = get_all_partitions_data()

        if not partitions_data:
            console.print("\n[yellow]No accessible partitions found[/yellow]\n")
            return

        display_partition_table(partitions_data)


if __name__ == "__main__":
    main()
