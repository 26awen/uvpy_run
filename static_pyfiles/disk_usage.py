# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.2.1",
#     "psutil>=5.9.0",
#     "rich>=14.1.0",
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
Inspect disk space with a readable terminal dashboard

A polished command-line disk usage viewer for local mount points. It summarizes
the most important disks first, hides noisy system mounts by default, and can
inspect one path in detail before a cleanup, download, backup, or deployment.

Version: 1.0.0
Category: System
Author: UVPY.RUN

Usage Examples:
    uv run disk_usage.py
    uv run disk_usage.py --limit 8 --sort free
    uv run disk_usage.py -p /
    uv run disk_usage.py --all
    uv run disk_usage.py --json

Use It For:
    - Checking which local mount points are close to full
    - Inspecting one path before copying, downloading, or backing up files
    - Hiding noisy pseudo/system mounts until you ask for --all
    - Getting terminal-friendly output or machine-readable JSON

Output:
    - Shows mount, device, filesystem, size, used, free, usage bar and status
    - Sorts by highest usage by default, with options for free space or mount
    - Uses practical warning and critical thresholds that you can adjust
    - Reports how many inaccessible or hidden mount points were skipped
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import platform
from typing import Any, Iterable

import click
import psutil
from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


DEFAULT_LIMIT = 12
DEFAULT_WARN = 75.0
DEFAULT_CRITICAL = 90.0

ACCENT = "#7dff9b"
CYAN = "#7cc7ff"
WARN = "#ffcc66"
ERROR = "#ff6b6b"
TEXT = "#dbffe9"
MUTED = "#9ca9a3"
PANEL = "#38d878"

NOISY_FILESYSTEMS = {
    "autofs",
    "binfmt_misc",
    "cgroup",
    "cgroup2",
    "configfs",
    "debugfs",
    "devfs",
    "devpts",
    "devtmpfs",
    "fdesc",
    "fusectl",
    "hugetlbfs",
    "mqueue",
    "proc",
    "pstore",
    "rpc_pipefs",
    "securityfs",
    "sysfs",
    "tmpfs",
    "tracefs",
}

NOISY_MOUNT_PREFIXES = (
    "/dev",
    "/proc",
    "/run",
    "/sys",
    "/private/var/folders/",
)

MACOS_SYSTEM_VOLUME_PREFIX = "/System/Volumes/"
MACOS_USEFUL_SYSTEM_MOUNTS = {
    "/System/Volumes/Data",
}

console = Console()


@dataclass(frozen=True)
class DiskUsage:
    """Readable usage data for one mount point."""

    mountpoint: str
    device: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float
    opts: str = ""

    @property
    def readonly(self) -> bool:
        return "ro" in {option.strip() for option in self.opts.split(",")}


@dataclass(frozen=True)
class UsageStatus:
    """Threshold result for one mount point."""

    label: str
    color: str
    detail: str


def format_bytes(value: int | float | str) -> str:
    """Return a compact human-readable byte value."""

    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if amount < 1024.0:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{amount:.0f} {unit}"
        amount /= 1024.0
    return f"{amount:.1f} PB"


def usage_status(
    percent: float,
    warn_threshold: float = DEFAULT_WARN,
    critical_threshold: float = DEFAULT_CRITICAL,
) -> UsageStatus:
    """Return status labels and colors for a usage percentage."""

    if percent >= critical_threshold:
        return UsageStatus("critical", ERROR, "free space is tight")
    if percent >= warn_threshold:
        return UsageStatus("watch", WARN, "worth watching")
    return UsageStatus("ok", ACCENT, "healthy")


def usage_bar(percent: float, width: int = 8) -> Text:
    """Return a Rich progress bar for disk usage."""

    filled = min(width, max(0, int(width * percent / 100)))
    empty = width - filled
    status = usage_status(percent)
    text = Text()
    text.append("█" * filled, style=status.color)
    text.append("░" * empty, style=f"dim {MUTED}")
    text.append(f" {percent:5.1f}%", style=status.color)
    return text


def partition_attr(partition: Any, name: str, default: str = "") -> str:
    """Return a psutil partition attribute from namedtuple or test doubles."""

    return str(getattr(partition, name, default) or default)


def is_noisy_mount(
    partition: Any,
    has_macos_data_volume: bool = False,
) -> bool:
    """Return whether a mount is usually noise for a quick disk check."""

    mountpoint = partition_attr(partition, "mountpoint")
    fstype = partition_attr(partition, "fstype").lower()
    opts = {option.strip() for option in partition_attr(partition, "opts").split(",")}

    if (
        mountpoint == "/"
        and has_macos_data_volume
        and fstype == "apfs"
        and "ro" in opts
    ):
        return True
    if mountpoint in {"/", *MACOS_USEFUL_SYSTEM_MOUNTS}:
        return False
    if mountpoint.startswith("/Volumes/"):
        return False
    if fstype in NOISY_FILESYSTEMS:
        return True
    if mountpoint.startswith(NOISY_MOUNT_PREFIXES):
        return True
    if (
        mountpoint.startswith(MACOS_SYSTEM_VOLUME_PREFIX)
        and mountpoint not in MACOS_USEFUL_SYSTEM_MOUNTS
    ):
        return True
    return False


def disk_usage_from_partition(partition: Any) -> DiskUsage:
    """Read psutil usage data for one partition."""

    mountpoint = partition_attr(partition, "mountpoint")
    usage = psutil.disk_usage(mountpoint)
    return DiskUsage(
        mountpoint=mountpoint,
        device=partition_attr(partition, "device", "unknown"),
        fstype=partition_attr(partition, "fstype", "unknown"),
        total=int(usage.total),
        used=int(usage.used),
        free=int(usage.free),
        percent=float(usage.percent),
        opts=partition_attr(partition, "opts"),
    )


def collect_disk_usages(include_all: bool = False) -> tuple[list[DiskUsage], int]:
    """Collect readable usage data and return skipped/hidden mount count."""

    usages: list[DiskUsage] = []
    skipped_count = 0
    seen_mounts: set[str] = set()
    partitions = psutil.disk_partitions(all=include_all)
    has_macos_data_volume = any(
        partition_attr(partition, "mountpoint") == "/System/Volumes/Data"
        for partition in partitions
    )

    for partition in partitions:
        mountpoint = partition_attr(partition, "mountpoint")
        if mountpoint in seen_mounts:
            skipped_count += 1
            continue
        seen_mounts.add(mountpoint)

        if not include_all and is_noisy_mount(partition, has_macos_data_volume):
            skipped_count += 1
            continue

        try:
            usage = disk_usage_from_partition(partition)
        except (FileNotFoundError, OSError, PermissionError):
            skipped_count += 1
            continue

        if usage.total <= 0:
            skipped_count += 1
            continue

        usages.append(usage)

    return usages, skipped_count


def sort_disk_usages(usages: Iterable[DiskUsage], sort_by: str) -> list[DiskUsage]:
    """Sort disk rows by the requested user-facing priority."""

    rows = list(usages)
    if sort_by == "free":
        return sorted(rows, key=lambda usage: (usage.free, usage.mountpoint))
    if sort_by == "mount":
        return sorted(rows, key=lambda usage: usage.mountpoint.lower())
    return sorted(rows, key=lambda usage: (-usage.percent, usage.mountpoint.lower()))


def limit_disk_usages(usages: list[DiskUsage], limit: int) -> tuple[list[DiskUsage], int]:
    """Apply a row limit and return the number hidden by that limit."""

    visible = usages[:limit]
    return visible, max(0, len(usages) - len(visible))


def find_partition_for_path(path: str, partitions: Iterable[Any]) -> Any | None:
    """Return the deepest mounted partition that contains a path."""

    absolute_path = os.path.abspath(path)
    matches: list[Any] = []

    for partition in partitions:
        mountpoint = partition_attr(partition, "mountpoint")
        try:
            common_path = os.path.commonpath([absolute_path, mountpoint])
        except ValueError:
            continue
        if common_path == mountpoint:
            matches.append(partition)

    if not matches:
        return None
    return max(matches, key=lambda partition: len(partition_attr(partition, "mountpoint")))


def inspect_path(path: str) -> DiskUsage:
    """Return disk usage for a path, including partition metadata when possible."""

    try:
        usage = psutil.disk_usage(path)
    except (FileNotFoundError, PermissionError, OSError) as error:
        raise click.ClickException(f"Cannot inspect {path}: {error}") from error

    partition = find_partition_for_path(path, psutil.disk_partitions(all=True))
    if partition is None:
        return DiskUsage(
            mountpoint=os.path.abspath(path),
            device="unknown",
            fstype="unknown",
            total=int(usage.total),
            used=int(usage.used),
            free=int(usage.free),
            percent=float(usage.percent),
        )

    return DiskUsage(
        mountpoint=partition_attr(partition, "mountpoint"),
        device=partition_attr(partition, "device", "unknown"),
        fstype=partition_attr(partition, "fstype", "unknown"),
        total=int(usage.total),
        used=int(usage.used),
        free=int(usage.free),
        percent=float(usage.percent),
        opts=partition_attr(partition, "opts"),
    )


def usage_to_dict(usage: DiskUsage) -> dict[str, Any]:
    """Return JSON-friendly usage data."""

    row = asdict(usage)
    row["readonly"] = usage.readonly
    row["status"] = usage_status(usage.percent).label
    return row


def create_header(
    visible_count: int,
    skipped_count: int,
    include_all: bool,
    sort_by: str,
) -> Panel:
    """Build the report header."""

    host = platform.node() or "local machine"
    mode = "all mounts" if include_all else "noise filtered"

    heading = Text()
    heading.append("disk usage", style=f"bold {ACCENT}")
    heading.append("  ")
    heading.append(host, style=CYAN)
    heading.append("\n")
    heading.append(f"{visible_count} visible", style=TEXT)
    heading.append("  ")
    heading.append(f"{skipped_count} hidden/skipped", style=f"dim {MUTED}")
    heading.append("  ")
    heading.append(mode, style=f"dim {MUTED}")
    heading.append("  ")
    heading.append(f"sorted by {sort_by}", style=f"dim {MUTED}")

    return Panel.fit(
        heading,
        border_style=PANEL,
        box=box.SQUARE,
        padding=(0, 1),
    )


def create_summary_panel(
    usages: list[DiskUsage],
    warn_threshold: float,
    critical_threshold: float,
) -> Panel:
    """Build a quick summary of the visible mounts."""

    table = Table.grid(padding=(0, 2))
    table.add_column(style=f"dim {MUTED}", justify="right")
    table.add_column(style=TEXT)

    if not usages:
        table.add_row("status", f"[{WARN}]no readable mounts[/]")
        table.add_row("hint", "try --all or inspect one path with -p")
    else:
        highest = max(usages, key=lambda usage: usage.percent)
        tightest = min(usages, key=lambda usage: usage.free)
        highest_status = usage_status(
            highest.percent,
            warn_threshold,
            critical_threshold,
        )
        table.add_row(
            "highest use",
            (
                f"[{highest_status.color}]{highest.percent:.1f}%[/] "
                f"{highest.mountpoint}"
            ),
        )
        table.add_row("least free", f"{format_bytes(tightest.free)} {tightest.mountpoint}")
        table.add_row(
            "thresholds",
            f"watch >= {warn_threshold:.0f}%  critical >= {critical_threshold:.0f}%",
        )

    return Panel(
        table,
        title="[bold]summary[/bold]",
        border_style=CYAN,
        box=box.SQUARE,
        padding=(1, 1),
    )


def usage_row(
    usage: DiskUsage,
    warn_threshold: float,
    critical_threshold: float,
) -> Text:
    """Return one readable multi-line mount summary."""

    status = usage_status(usage.percent, warn_threshold, critical_threshold)
    detail = "  ".join(
        part
        for part in [
            usage.device or "unknown device",
            usage.fstype or "unknown fs",
            "read-only" if usage.readonly else "",
        ]
        if part
    )

    row = Text()
    row.append(usage.mountpoint, style=f"bold {TEXT}")
    row.append("  ")
    row.append(f"{usage.percent:.1f}%", style=f"bold {status.color}")
    row.append("  ")
    row.append(status.label, style=status.color)
    row.append("\n")
    if detail:
        row.append(detail, style=f"dim {MUTED}")
        row.append("\n")
    row.append_text(usage_bar(usage.percent, width=18))
    row.append("\n")
    row.append("total ", style=f"dim {MUTED}")
    row.append(format_bytes(usage.total), style=TEXT)
    row.append("  ")
    row.append("used ", style=f"dim {MUTED}")
    row.append(
        format_bytes(usage.used),
        style=WARN if usage.percent >= warn_threshold else TEXT,
    )
    row.append("  ")
    row.append("free ", style=f"dim {MUTED}")
    row.append(format_bytes(usage.free), style=ACCENT)
    return row


def usage_rows(
    usages: list[DiskUsage],
    warn_threshold: float,
    critical_threshold: float,
) -> Group:
    """Return readable mount rows separated by light rules."""

    rows: list[RenderableType] = []
    for index, usage in enumerate(usages):
        if index:
            rows.append(Text("─" * 40, style=f"dim {MUTED}"))
        rows.append(usage_row(usage, warn_threshold, critical_threshold))
    return Group(*rows)


def create_table_panel(
    usages: list[DiskUsage],
    hidden_by_limit: int,
    warn_threshold: float,
    critical_threshold: float,
) -> Panel:
    """Build the table panel or an empty state."""

    if not usages:
        empty = Text()
        empty.append("No readable disk usage rows.", style=f"bold {TEXT}")
        empty.append("\n")
        empty.append("Try --all or inspect a specific path with -p.", style=f"dim {MUTED}")
        return Panel(
            empty,
            title="[bold]mounts[/bold]",
            border_style=PANEL,
            box=box.SQUARE,
            padding=(1, 1),
        )

    subtitle = f"{hidden_by_limit} more hidden by --limit" if hidden_by_limit else None
    return Panel(
        usage_rows(usages, warn_threshold, critical_threshold),
        title="[bold]mounts[/bold]",
        subtitle=Text(subtitle, style=f"dim {MUTED}") if subtitle else None,
        border_style=PANEL,
        box=box.SQUARE,
        padding=(0, 1),
    )


def create_report(
    usages: list[DiskUsage],
    skipped_count: int,
    include_all: bool,
    sort_by: str,
    hidden_by_limit: int,
    warn_threshold: float,
    critical_threshold: float,
) -> RenderableType:
    """Create the full disk usage dashboard."""

    return Group(
        create_header(
            visible_count=len(usages),
            skipped_count=skipped_count,
            include_all=include_all,
            sort_by=sort_by,
        ),
        create_summary_panel(usages, warn_threshold, critical_threshold),
        create_table_panel(
            usages,
            hidden_by_limit,
            warn_threshold,
            critical_threshold,
        ),
    )


def create_detail_panel(
    path: str,
    usage: DiskUsage,
    warn_threshold: float,
    critical_threshold: float,
) -> Panel:
    """Create a detailed one-path inspection panel."""

    status = usage_status(usage.percent, warn_threshold, critical_threshold)
    info = Table.grid(padding=(0, 2))
    info.add_column(style=f"dim {MUTED}", justify="right")
    info.add_column(style=TEXT)
    info.add_row("path", os.path.abspath(path))
    info.add_row("mount", usage.mountpoint)
    info.add_row("device", usage.device or "unknown")
    info.add_row("filesystem", usage.fstype or "unknown")
    info.add_row("total", format_bytes(usage.total))
    info.add_row("used", format_bytes(usage.used))
    info.add_row("free", format_bytes(usage.free))
    info.add_row("status", f"[{status.color}]{status.label}[/]  {status.detail}")
    info.add_row("usage", usage_bar(usage.percent, width=24))

    return Panel(
        info,
        title="[bold]disk detail[/bold]",
        border_style=status.color,
        box=box.SQUARE,
        padding=(1, 1),
    )


def emit_json(payload: dict[str, Any]) -> None:
    """Print stable JSON output."""

    click.echo(json.dumps(payload, indent=2, sort_keys=True))


def validate_thresholds(warn_threshold: float, critical_threshold: float) -> None:
    """Ensure warning thresholds are ordered."""

    if warn_threshold >= critical_threshold:
        raise click.UsageError("--warn must be below --critical.")


@click.command(context_settings={"help_option_names": ["--help"]})
@click.option(
    "-p",
    "--partition",
    type=str,
    help="Inspect one path or mount point.",
)
@click.option(
    "--all",
    "include_all",
    is_flag=True,
    help="Include pseudo, system, and usually noisy mounts.",
)
@click.option(
    "--limit",
    "-n",
    type=click.IntRange(1, 100),
    default=DEFAULT_LIMIT,
    show_default=True,
    help="Maximum mount rows to display.",
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["percent", "free", "mount"]),
    default="percent",
    show_default=True,
    help="Sort mount rows.",
)
@click.option(
    "--warn",
    "warn_threshold",
    type=click.FloatRange(1, 99),
    default=DEFAULT_WARN,
    show_default=True,
    help="Usage percent that should be watched.",
)
@click.option(
    "--critical",
    "critical_threshold",
    type=click.FloatRange(1, 100),
    default=DEFAULT_CRITICAL,
    show_default=True,
    help="Usage percent treated as critical.",
)
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON.")
def main(
    partition: str | None,
    include_all: bool,
    limit: int,
    sort_by: str,
    warn_threshold: float,
    critical_threshold: float,
    json_output: bool,
) -> None:
    """
    Inspect local disk usage without the noisy mount clutter.

    Examples:

    \b
    uv run disk_usage.py

    \b
    uv run disk_usage.py --limit 8 --sort free

    \b
    uv run disk_usage.py -p /

    \b
    uv run disk_usage.py --all --json
    """

    validate_thresholds(warn_threshold, critical_threshold)

    if partition:
        usage = inspect_path(partition)
        if json_output:
            emit_json({"path": os.path.abspath(partition), "usage": usage_to_dict(usage)})
            return
        console.print(create_detail_panel(partition, usage, warn_threshold, critical_threshold))
        return

    usages, skipped_count = collect_disk_usages(include_all=include_all)
    sorted_usages = sort_disk_usages(usages, sort_by)
    visible_usages, hidden_by_limit = limit_disk_usages(sorted_usages, limit)

    if json_output:
        emit_json(
            {
                "include_all": include_all,
                "sort": sort_by,
                "skipped_count": skipped_count,
                "hidden_by_limit": hidden_by_limit,
                "partitions": [usage_to_dict(usage) for usage in visible_usages],
            }
        )
        return

    console.print(
        create_report(
            visible_usages,
            skipped_count,
            include_all,
            sort_by,
            hidden_by_limit,
            warn_threshold,
            critical_threshold,
        )
    )


if __name__ == "__main__":
    main()
