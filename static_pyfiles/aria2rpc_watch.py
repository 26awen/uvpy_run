# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.2.1",
#     "requests>=2.31.0",
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
# - Requests: Apache-2.0 License (https://github.com/psf/requests)
# - Rich: MIT License (https://github.com/Textualize/rich)

"""
Watch aria2c downloads over JSON-RPC

A terminal dashboard for an aria2c process with JSON-RPC enabled. It connects
to the aria2 RPC endpoint, refreshes until interrupted, and shows active,
waiting and recent stopped downloads with progress, speed, ETA and connection
details.

Version: 1.1.0
Category: Network
Author: UVPY.RUN

Usage Examples:
    uv run aria2rpc_watch.py
    uv run aria2rpc_watch.py --once --no-screen
    uv run aria2rpc_watch.py 192.168.1.100 --port 6800 --interval 1
    uv run aria2rpc_watch.py localhost --token "$ARIA2_RPC_TOKEN" --rows 16
    uv run aria2rpc_watch.py --hide-stopped --no-screen

Use It For:
    - Watching an aria2c download service without opening a browser UI
    - Checking active, waiting and recent stopped transfers in one terminal
    - Keeping transfer speed, progress, ETA and RPC health visible
    - Monitoring a local aria2c process or a trusted machine on your network

Connection Notes:
    - aria2c is the command-line downloader; aria2 is the project/RPC namespace
    - Start aria2c with --enable-rpc before using this watcher
    - The default endpoint is http://127.0.0.1:6800/jsonrpc
    - Use --token when your aria2c RPC server has --rpc-secret configured
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import click
import requests
from requests import exceptions
from rich import box
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6800
DEFAULT_INTERVAL = 2
DEFAULT_ROWS = 12
RPC_TIMEOUT = 5

ACCENT = "#7dff9b"
CYAN = "#7cc7ff"
WARN = "#ffcc66"
ERROR = "#ff6b6b"
TEXT = "#dbffe9"
MUTED = "#9ca9a3"
PANEL = "#38d878"

console = Console()


class Aria2RpcError(RuntimeError):
    """Raised when aria2 returns a JSON-RPC error payload."""


@dataclass(frozen=True)
class Aria2Snapshot:
    """One completed poll of aria2 RPC state."""

    stats: dict[str, Any]
    active: list[dict[str, Any]]
    waiting: list[dict[str, Any]]
    stopped: list[dict[str, Any]]

    @property
    def active_count(self) -> int:
        return len(self.active)

    @property
    def waiting_count(self) -> int:
        return len(self.waiting)

    @property
    def stopped_count(self) -> int:
        return len(self.stopped)

    @property
    def transfer_count(self) -> int:
        return self.active_count + self.waiting_count + self.stopped_count


def rpc_url(host: str, port: int) -> str:
    """Return the aria2 JSON-RPC endpoint URL."""

    return f"http://{host}:{port}/jsonrpc"


def token_params(token: str | None) -> list[str]:
    """Return aria2's token parameter format when a secret is configured."""

    return [f"token:{token}"] if token else []


def extract_rpc_result(payload: dict[str, Any]) -> Any:
    """Return a JSON-RPC result or raise a readable aria2 error."""

    if "error" in payload:
        error = payload.get("error") or {}
        code = error.get("code", "unknown")
        message = error.get("message", "Unknown aria2 RPC error")
        raise Aria2RpcError(f"aria2 RPC {code}: {message}")
    return payload.get("result")


def call_aria2_rpc(
    url: str,
    method: str,
    params: list[Any] | None = None,
) -> Any:
    """Call an aria2 JSON-RPC method and return its result."""

    payload = {
        "jsonrpc": "2.0",
        "id": "uvpy-run-watch",
        "method": method,
        "params": params or [],
    }

    response = requests.post(url, json=payload, timeout=RPC_TIMEOUT)
    response.raise_for_status()
    return extract_rpc_result(response.json())


def fetch_snapshot(
    endpoint: str,
    token: str | None,
    rows: int,
    include_stopped: bool,
) -> Aria2Snapshot:
    """Fetch current transfer queues and global stats from aria2."""

    params: list[Any] = token_params(token)

    active = call_aria2_rpc(endpoint, "aria2.tellActive", params) or []
    waiting = (
        call_aria2_rpc(endpoint, "aria2.tellWaiting", params + [0, rows]) or []
    )
    stopped = []
    if include_stopped:
        stopped = (
            call_aria2_rpc(endpoint, "aria2.tellStopped", params + [0, rows]) or []
        )
    stats = call_aria2_rpc(endpoint, "aria2.getGlobalStat", params) or {}

    return Aria2Snapshot(stats=stats, active=active, waiting=waiting, stopped=stopped)


def safe_int(value: Any, default: int = 0) -> int:
    """Parse aria2's string-heavy numeric fields."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_size(size: int | float | str) -> str:
    """Format bytes as a compact human-readable size."""

    amount = float(safe_int(size))
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if amount < 1024.0:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{amount:.0f} {unit}"
        amount /= 1024.0
    return f"{amount:.1f} PB"


def format_speed(speed: int | str) -> str:
    """Format a byte-per-second speed."""

    return f"{format_size(speed)}/s"


def format_eta(seconds: int | None) -> str:
    """Format remaining seconds as a short ETA label."""

    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def shorten_text(value: str, max_length: int) -> str:
    """Shorten long table labels without hiding the useful ending."""

    clean_value = " ".join(value.split()) or "unknown"
    if len(clean_value) <= max_length:
        return clean_value
    if max_length <= 4:
        return clean_value[:max_length]
    return f"{clean_value[: max_length - 4]} ..."


def first_uri(download: dict[str, Any]) -> str:
    """Return the first aria2 source URI if one is available."""

    for file_info in download.get("files", []):
        for uri_info in file_info.get("uris", []):
            uri = uri_info.get("uri")
            if uri:
                return uri
    return ""


def download_name(download: dict[str, Any]) -> str:
    """Return the best human-facing name for an aria2 transfer."""

    bittorrent = download.get("bittorrent") or {}
    info = bittorrent.get("info") or {}
    if info.get("name"):
        return str(info["name"])

    files = download.get("files", [])
    for file_info in files:
        path = file_info.get("path")
        if path:
            return str(path).replace("\\", "/").rstrip("/").split("/")[-1]

    uri = first_uri(download)
    if uri:
        tail = uri.rstrip("/").split("/")[-1]
        return tail or uri

    gid = download.get("gid")
    return f"aria2 transfer {gid}" if gid else "unknown transfer"


def progress_percent(download: dict[str, Any]) -> float | None:
    """Return the transfer progress as a percent if the total size is known."""

    total = safe_int(download.get("totalLength"))
    if total <= 0:
        return None
    completed = min(safe_int(download.get("completedLength")), total)
    return completed / total * 100


def eta_seconds(download: dict[str, Any]) -> int | None:
    """Return estimated seconds remaining for active downloads."""

    total = safe_int(download.get("totalLength"))
    completed = safe_int(download.get("completedLength"))
    speed = safe_int(download.get("downloadSpeed"))
    if total <= 0 or speed <= 0 or completed >= total:
        return None
    return max(0, (total - completed) // speed)


def size_label(download: dict[str, Any]) -> str:
    """Return completed and total size text for a transfer."""

    total = safe_int(download.get("totalLength"))
    completed = safe_int(download.get("completedLength"))
    if total > 0:
        return f"{format_size(completed)} / {format_size(total)}"
    return format_size(completed)


def name_cell(download: dict[str, Any], max_length: int) -> Text:
    """Return a two-line name cell with a short gid for inspection."""

    text = Text(shorten_text(download_name(download), max_length), style=TEXT)
    gid = str(download.get("gid", ""))[:8]
    if gid:
        text.append(f"\n#{gid}", style=f"dim {MUTED}")
    return text


def progress_cell(
    download: dict[str, Any],
    width: int = 14,
    show_size: bool = False,
) -> Text:
    """Return a compact progress bar cell for the transfer table."""

    progress = progress_percent(download)
    if progress is None:
        text = Text("unknown", style=f"dim {MUTED}")
        if show_size:
            text.append(f"\n{size_label(download)}", style=f"dim {MUTED}")
        return text

    filled = min(width, max(0, int(width * progress / 100)))
    empty = width - filled
    text = Text()
    text.append("█" * filled, style=ACCENT)
    text.append("░" * empty, style=f"dim {MUTED}")
    text.append(f" {progress:5.1f}%", style=TEXT)
    if show_size:
        text.append(f"\n{size_label(download)}", style=f"dim {MUTED}")
    return text


def status_cell(status: str) -> Text:
    """Return a colored status label."""

    labels = {
        "active": ("active", ACCENT),
        "waiting": ("waiting", CYAN),
        "paused": ("paused", WARN),
        "complete": ("done", CYAN),
        "removed": ("removed", MUTED),
        "error": ("error", ERROR),
    }
    label, style = labels.get(status, (status or "unknown", MUTED))
    text = Text()
    text.append("● ", style=style)
    text.append(label, style=style if status != "error" else f"bold {ERROR}")
    return text


def transfer_speed_cell(download: dict[str, Any]) -> Text:
    """Return download/upload speed text for a transfer row."""

    down = safe_int(download.get("downloadSpeed"))
    up = safe_int(download.get("uploadSpeed"))
    text = Text()
    if down > 0:
        text.append("↓ ", style=ACCENT)
        text.append(format_speed(down), style=ACCENT)
    else:
        text.append("idle", style=f"dim {MUTED}")
    if up > 0:
        text.append("  ↑ ", style="#d7a6ff")
        text.append(format_speed(up), style="#d7a6ff")
    return text


def peer_cell(download: dict[str, Any]) -> str:
    """Return connection and seed information for one transfer."""

    parts: list[str] = []
    connections = safe_int(download.get("connections"))
    if connections:
        parts.append(f"{connections} conn")
    seeders = download.get("numSeeders")
    if seeders is not None:
        parts.append(f"{safe_int(seeders)} seeds")
    return ", ".join(parts) or "-"


def visible_downloads(
    snapshot: Aria2Snapshot,
    rows: int,
    include_stopped: bool,
) -> tuple[list[dict[str, Any]], int]:
    """Return transfers to render and the number hidden by the row limit."""

    transfers = [*snapshot.active, *snapshot.waiting]
    if include_stopped:
        transfers.extend(snapshot.stopped)
    visible = transfers[:rows]
    return visible, max(0, len(transfers) - len(visible))


def create_header(host: str, port: int, interval: int, token: str | None) -> Panel:
    """Create the dashboard header."""

    heading = Text()
    heading.append("aria2c RPC watcher", style=f"bold {ACCENT}")
    heading.append("\n")
    heading.append(rpc_url(host, port), style=CYAN)
    heading.append("  ")
    heading.append(f"refresh {interval}s", style=f"dim {MUTED}")
    heading.append("  ")
    heading.append("token set" if token else "no token", style=WARN if token else MUTED)

    return Panel.fit(
        heading,
        border_style=PANEL,
        box=box.SQUARE,
        padding=(0, 1),
    )


def create_stats_panel(snapshot: Aria2Snapshot | None) -> Panel:
    """Create global transfer stats."""

    table = Table.grid(padding=(0, 2))
    table.add_column(style=f"dim {MUTED}", justify="right")
    table.add_column(style=TEXT)
    table.add_column(style=f"dim {MUTED}", justify="right")
    table.add_column(style=TEXT)

    if snapshot is None:
        table.add_row("status", f"[{WARN}]waiting[/]", "rpc", "not connected")
        table.add_row("active", "0", "waiting", "0")
        table.add_row("down", "0 B/s", "up", "0 B/s")
    else:
        stats = snapshot.stats
        table.add_row(
            "active",
            f"[bold {ACCENT}]{snapshot.active_count}[/]",
            "waiting",
            f"[bold {CYAN}]{snapshot.waiting_count}[/]",
        )
        table.add_row(
            "recent",
            f"[bold {MUTED}]{snapshot.stopped_count}[/]",
            "total",
            f"{snapshot.transfer_count}",
        )
        table.add_row(
            "down",
            f"[bold {ACCENT}]{format_speed(stats.get('downloadSpeed', 0))}[/]",
            "up",
            f"[#d7a6ff]{format_speed(stats.get('uploadSpeed', 0))}[/]",
        )

    return Panel(
        table,
        title="[bold]live stats[/bold]",
        border_style=CYAN,
        box=box.SQUARE,
        padding=(1, 1),
    )


def create_connection_panel(
    rows: int,
    include_stopped: bool,
    screen: bool,
    once: bool,
) -> Panel:
    """Create a small panel with watcher settings and practical reminders."""

    stopped_label = "shown" if include_stopped else "hidden"
    screen_label = "full-screen" if screen else "inline"
    mode_label = "one-shot" if once else "watching"

    content = Text()
    if once:
        content.append("one poll", style=f"bold {WARN}")
        content.append(" then exit\n", style=f"dim {MUTED}")
    else:
        content.append("Ctrl+C", style=f"bold {WARN}")
        content.append(" stops watching\n", style=f"dim {MUTED}")
    content.append(f"{rows} rows", style=TEXT)
    content.append("  ")
    content.append(f"stopped {stopped_label}", style=TEXT)
    content.append("  ")
    content.append(screen_label, style=TEXT)
    content.append("  ")
    content.append(mode_label, style=TEXT)
    content.append("\n")
    content.append("aria2c needs --enable-rpc", style=f"dim {MUTED}")

    return Panel(
        content,
        title="[bold]watcher[/bold]",
        border_style=PANEL,
        box=box.SQUARE,
        padding=(1, 1),
    )


def create_transfer_table(
    downloads: list[dict[str, Any]],
    compact: bool = False,
) -> Table:
    """Create the transfer table."""

    table = Table(
        show_header=True,
        header_style=f"bold {CYAN}",
        box=box.SIMPLE_HEAD,
        expand=True,
        padding=(0, 1),
    )
    table.add_column("name", ratio=4, overflow="fold", min_width=16)
    table.add_column("state", width=9, no_wrap=True)
    table.add_column("progress", ratio=3, min_width=18)
    table.add_column("speed", ratio=2, min_width=10 if compact else 18)
    if not compact:
        table.add_column("eta", justify="right", width=8, no_wrap=True)
        table.add_column("peers", justify="right", width=16, no_wrap=True)

    for download in downloads:
        status = str(download.get("status", "unknown"))
        row = [
            name_cell(download, 64 if not compact else 36),
            status_cell(status),
            progress_cell(download, width=12 if compact else 14, show_size=True),
            transfer_speed_cell(download),
        ]
        if not compact:
            row.extend([format_eta(eta_seconds(download)), peer_cell(download)])
        table.add_row(*row)

    return table


def create_empty_queue_panel() -> Panel:
    """Create an empty state when aria2 is reachable but no transfers exist."""

    message = Text()
    message.append("No visible downloads right now.", style=f"bold {TEXT}")
    message.append("\n")
    message.append(
        "Add a URL to aria2c or leave this watcher open for the next transfer.",
        style=f"dim {MUTED}",
    )

    return Panel(
        message,
        title="[bold]queue[/bold]",
        border_style=PANEL,
        box=box.SQUARE,
        padding=(1, 1),
    )


def create_queue_panel(
    downloads: list[dict[str, Any]],
    hidden_count: int,
    compact: bool = False,
) -> Panel:
    """Create the queue panel with a visible row-limit hint."""

    if not downloads:
        return create_empty_queue_panel()

    subtitle = f"{hidden_count} more hidden by --rows" if hidden_count else None
    return Panel(
        create_transfer_table(downloads, compact=compact),
        title="[bold]queue[/bold]",
        subtitle=Text(subtitle, style=f"dim {MUTED}") if subtitle else None,
        border_style=PANEL,
        box=box.SQUARE,
        padding=(0, 1),
    )


def create_error_panel(
    title: str,
    message: str,
    endpoint: str,
    token: str | None,
) -> Panel:
    """Create a helpful error panel for connection and RPC failures."""

    content = Text()
    content.append(message, style=f"bold {ERROR}")
    content.append("\n\n")
    content.append("Start local aria2c RPC:\n", style=f"bold {TEXT}")
    content.append(
        "aria2c --enable-rpc --rpc-listen-all=false --rpc-listen-port=6800",
        style=CYAN,
    )
    content.append("\n\n")
    content.append("Endpoint: ", style=f"dim {MUTED}")
    content.append(endpoint, style=TEXT)
    content.append("\n")
    if token:
        content.append("Token is set in this watcher.", style=WARN)
    else:
        content.append(
            "If aria2c uses --rpc-secret, run this watcher with --token.",
            style=f"dim {MUTED}",
        )

    return Panel(
        content,
        title=f"[bold]{title}[/bold]",
        border_style=ERROR,
        box=box.SQUARE,
        padding=(1, 1),
    )


def create_dashboard(
    host: str,
    port: int,
    interval: int,
    token: str | None,
    rows: int,
    include_stopped: bool,
    screen: bool,
    once: bool = False,
    snapshot: Aria2Snapshot | None = None,
    error: tuple[str, str] | None = None,
    width: int | None = None,
) -> RenderableType:
    """Create the full terminal dashboard for Live rendering."""

    header = create_header(host, port, interval, token)
    stats_panel = create_stats_panel(snapshot)
    connection_panel = create_connection_panel(rows, include_stopped, screen, once)
    top_panels: RenderableType

    terminal_width = width or console.width
    compact = terminal_width < 92

    if compact:
        top_panels = Group(stats_panel, connection_panel)
    else:
        top_panels = Columns([stats_panel, connection_panel], equal=True, expand=True)

    if error:
        queue_panel = create_error_panel(error[0], error[1], rpc_url(host, port), token)
    elif snapshot is None:
        queue_panel = create_empty_queue_panel()
    else:
        downloads, hidden_count = visible_downloads(snapshot, rows, include_stopped)
        queue_panel = create_queue_panel(downloads, hidden_count, compact=compact)

    return Group(header, top_panels, queue_panel)


@click.command(context_settings={"help_option_names": ["--help"]})
@click.argument("host", required=False, default=DEFAULT_HOST, metavar="[HOST]")
@click.option(
    "--port",
    "-p",
    type=click.IntRange(1, 65535),
    default=DEFAULT_PORT,
    show_default=True,
    help="aria2c JSON-RPC port.",
)
@click.option(
    "--interval",
    "-i",
    type=click.IntRange(1),
    default=DEFAULT_INTERVAL,
    show_default=True,
    help="Refresh interval in seconds.",
)
@click.option("--token", "-t", default=None, help="aria2c RPC secret token.")
@click.option(
    "--rows",
    "-r",
    type=click.IntRange(1, 50),
    default=DEFAULT_ROWS,
    show_default=True,
    help="Maximum transfer rows to show.",
)
@click.option(
    "--stopped/--hide-stopped",
    "include_stopped",
    default=True,
    show_default=True,
    help="Show recent stopped transfers in the queue.",
)
@click.option(
    "--screen/--no-screen",
    "screen",
    default=True,
    show_default=True,
    help="Use Rich's full-screen live view.",
)
@click.option("--once", is_flag=True, help="Poll once, render the dashboard, and exit.")
def monitor(
    host: str,
    port: int,
    interval: int,
    token: str | None,
    rows: int,
    include_stopped: bool,
    screen: bool,
    once: bool,
) -> None:
    """
    Watch an aria2c JSON-RPC server from the terminal.

    HOST defaults to 127.0.0.1. Start aria2c with --enable-rpc, then keep this
    watcher open while downloads run.
    """

    endpoint = rpc_url(host, port)
    live_screen = screen and console.is_terminal
    once_error: str | None = None

    try:
        with Live(
            console=console,
            refresh_per_second=4,
            screen=live_screen,
            transient=False,
        ) as live:
            while True:
                once_error = None
                try:
                    snapshot = fetch_snapshot(endpoint, token, rows, include_stopped)
                    live.update(
                        create_dashboard(
                            host,
                            port,
                            interval,
                            token,
                            rows,
                            include_stopped,
                            live_screen,
                            once=once,
                            snapshot=snapshot,
                            width=console.width,
                        )
                    )
                except exceptions.ConnectionError:
                    once_error = "Cannot reach aria2c JSON-RPC."
                    live.update(
                        create_dashboard(
                            host,
                            port,
                            interval,
                            token,
                            rows,
                            include_stopped,
                            live_screen,
                            once=once,
                            error=(
                                "connection error",
                                "Cannot reach aria2c JSON-RPC.",
                            ),
                            width=console.width,
                        )
                    )
                except exceptions.Timeout:
                    once_error = "aria2c did not respond in time."
                    live.update(
                        create_dashboard(
                            host,
                            port,
                            interval,
                            token,
                            rows,
                            include_stopped,
                            live_screen,
                            once=once,
                            error=("timeout", "aria2c did not respond in time."),
                            width=console.width,
                        )
                    )
                except Aria2RpcError as error:
                    once_error = str(error)
                    live.update(
                        create_dashboard(
                            host,
                            port,
                            interval,
                            token,
                            rows,
                            include_stopped,
                            live_screen,
                            once=once,
                            error=("RPC error", str(error)),
                            width=console.width,
                        )
                    )
                except exceptions.RequestException as error:
                    once_error = str(error)
                    live.update(
                        create_dashboard(
                            host,
                            port,
                            interval,
                            token,
                            rows,
                            include_stopped,
                            live_screen,
                            once=once,
                            error=("request error", str(error)),
                            width=console.width,
                        )
                    )

                if once:
                    break
                time.sleep(interval)

        if once and once_error:
            raise click.ClickException(once_error)
    except KeyboardInterrupt:
        console.print("[yellow]aria2c watcher stopped[/yellow]")


if __name__ == "__main__":
    monitor()
