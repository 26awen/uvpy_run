# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.0",
#     "psutil>=5.9.0",
# ]
# ///

import click
import psutil
from typing import Optional


def format_bytes(bytes: int) -> str:
    """
    Convert bytes to human readable format.

    Args:
        bytes: Size in bytes

    Returns:
        Human readable string with appropriate unit
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} PB"


def display_partition_info(partition: str) -> None:
    """
    Display disk usage information for a specific partition.

    Args:
        partition: Mount point or device path
    """
    try:
        usage = psutil.disk_usage(partition)

        click.echo(f"\nPartition: {partition}")
        click.echo("-" * 60)
        click.echo(f"Total:     {format_bytes(usage.total)}")
        click.echo(f"Used:      {format_bytes(usage.used)}")
        click.echo(f"Free:      {format_bytes(usage.free)}")
        click.echo(f"Percent:   {usage.percent}%")

    except (PermissionError, FileNotFoundError) as e:
        click.echo(f"Error accessing partition {partition}: {e}", err=True)


def display_all_partitions() -> None:
    """
    Display disk usage information for all mounted partitions.
    """
    partitions = psutil.disk_partitions()

    if not partitions:
        click.echo("No partitions found.")
        return

    click.echo("\nAll Disk Partitions Usage:")
    click.echo("=" * 60)

    for partition in partitions:
        click.echo(f"\nDevice:    {partition.device}")
        click.echo(f"Mountpoint: {partition.mountpoint}")
        click.echo(f"Filesystem: {partition.fstype}")
        click.echo(f"Options:   {partition.opts}")

        try:
            usage = psutil.disk_usage(partition.mountpoint)
            click.echo(f"Total:     {format_bytes(usage.total)}")
            click.echo(f"Used:      {format_bytes(usage.used)}")
            click.echo(f"Free:      {format_bytes(usage.free)}")
            click.echo(f"Percent:   {usage.percent}%")
        except PermissionError:
            click.echo("Permission denied to access this partition")

        click.echo("-" * 60)


@click.command()
@click.option(
    "-p",
    "--partition",
    type=str,
    help="Specific partition mount point to display (e.g., / or /home)",
)
@click.option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    default=True,
    help="Display all partitions (default)",
)
def main(partition: Optional[str], show_all: bool) -> None:
    """
    Display disk usage information for all partitions or a specific partition.

    Examples:

        uv run disk_usage.py

        uv run disk_usage.py -p /

        uv run disk_usage.py --partition /home
    """
    if partition:
        display_partition_info(partition)
    else:
        display_all_partitions()


if __name__ == "__main__":
    main()
