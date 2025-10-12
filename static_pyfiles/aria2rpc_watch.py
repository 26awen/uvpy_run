# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "requests",
#     "rich",
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
Real-time aria2 download monitor with elegant terminal interface

A command-line utility for monitoring aria2 RPC server download status.
Features a beautiful terminal interface with real-time updates, progress bars,
download statistics, and connection information.

Version: 1.0.0
Category: Network/Download
Author: UVPY.RUN

Usage Examples:
    uv run aria2rpc_watch.py 127.0.0.1
    uv run aria2rpc_watch.py 192.168.1.100 --port 6800 --interval 1
    uv run aria2rpc_watch.py localhost --token mytoken --interval 3
"""

import click
import requests
from requests import exceptions
import time
from typing import Any
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich.text import Text
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

console = Console()


def call_aria2_rpc(
    url: str, method: str, params: list[Any] | None = None
) -> dict[str, Any]:
    """Call aria2 JSON-RPC method and return response"""
    if params is None:
        params = []

    payload = {"jsonrpc": "2.0", "id": "monitor", "method": method, "params": params}

    response = requests.post(url, json=payload, timeout=5)
    response.raise_for_status()
    return response.json()


def format_size(size: int | float) -> str:
    """Format bytes to human readable size"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def format_speed(speed: int) -> str:
    """Format download speed to human readable format"""
    return f"{format_size(speed)}/s"


def create_header(ip_address: str, port: int) -> Panel:
    """Create header panel"""
    title = Text("aria2 Download Monitor", style="bold cyan")
    subtitle = Text(f"{ip_address}:{port}", style="dim")
    content = Text.assemble(title, "\n", subtitle)
    return Panel(content, style="cyan", border_style="bright_cyan")


def create_stats_panel(
    stats: dict[str, Any] | None,
    active_count: int,
    waiting_count: int,
    stopped_count: int,
) -> Panel:
    """Create statistics panel"""
    if not stats:
        return Panel("Statistics unavailable", title="Global Stats", style="yellow")

    download_speed = int(stats.get("downloadSpeed", 0))
    upload_speed = int(stats.get("uploadSpeed", 0))

    stats_table = Table.grid(padding=(0, 2))
    stats_table.add_column(style="cyan", justify="right")
    stats_table.add_column(style="green")

    stats_table.add_row("Active:", f"[bold]{active_count}[/bold]")
    stats_table.add_row("Waiting:", f"[bold]{waiting_count}[/bold]")
    stats_table.add_row("Stopped:", f"[bold]{stopped_count}[/bold]")
    stats_table.add_row("", "")
    stats_table.add_row(
        "Download:", f"[bold green]{format_speed(download_speed)}[/bold green]"
    )
    stats_table.add_row(
        "Upload:", f"[bold magenta]{format_speed(upload_speed)}[/bold magenta]"
    )

    return Panel(
        stats_table,
        title="[bold]Global Stats[/bold]",
        style="blue",
        border_style="blue",
    )


def create_downloads_table(downloads: list[dict[str, Any]]) -> Table:
    """Create downloads table"""
    table = Table(show_header=True, header_style="bold magenta", box=None, expand=True)

    table.add_column("File", style="cyan", no_wrap=False, ratio=3)
    table.add_column("Progress", justify="right", style="yellow", ratio=2)
    table.add_column("Size", justify="right", style="green", ratio=1)
    table.add_column("Speed", justify="right", style="bright_green", ratio=1)
    table.add_column("ETA", justify="right", style="blue", ratio=1)
    table.add_column("Status", justify="center", style="magenta", ratio=1)

    if not downloads:
        table.add_row("[dim]No active downloads[/dim]", "", "", "", "", "")
        return table

    for download in downloads:
        # Extract file information
        files = download.get("files", [])
        filename = (
            files[0]["path"].split("/")[-1]
            if files and files[0].get("path")
            else "Unknown"
        )
        if len(filename) > 50:
            filename = filename[:47] + "..."

        # Extract download metrics
        total_length = int(download.get("totalLength", 0))
        completed_length = int(download.get("completedLength", 0))
        download_speed = int(download.get("downloadSpeed", 0))
        status = download.get("status", "unknown")

        # Calculate progress and ETA
        progress = 0.0
        eta_text = "-"
        if total_length > 0:
            progress = (completed_length / total_length) * 100
            if download_speed > 0:
                eta_seconds = (total_length - completed_length) // download_speed
                if eta_seconds < 60:
                    eta_text = f"{eta_seconds}s"
                elif eta_seconds < 3600:
                    eta_text = f"{eta_seconds // 60}m {eta_seconds % 60}s"
                else:
                    hours = eta_seconds // 3600
                    minutes = (eta_seconds % 3600) // 60
                    eta_text = f"{hours}h {minutes}m"

        # Create progress bar
        bar_width = 20
        filled = int(bar_width * progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        progress_text = f"{bar} {progress:.1f}%"

        # Status style
        status_style = {
            "active": "[bold green]●[/bold green] Active",
            "paused": "[bold yellow]●[/bold yellow] Paused",
            "waiting": "[bold blue]●[/bold blue] Waiting",
            "error": "[bold red]●[/bold red] Error",
            "complete": "[bold cyan]●[/bold cyan] Done",
        }.get(status, f"[dim]●[/dim] {status}")

        # Add connections info to filename
        connections = download.get("connections", "0")
        seeders = download.get("numSeeders", None)
        file_info = f"{filename}"
        if connections != "0":
            file_info += f" [dim]({connections} conn)[/dim]"
        if seeders is not None:
            file_info += f" [dim]({seeders} seeds)[/dim]"

        table.add_row(
            file_info,
            progress_text,
            f"{format_size(completed_length)}/{format_size(total_length)}",
            format_speed(download_speed),
            eta_text,
            status_style,
        )

    return table


def create_layout(
    ip_address: str,
    port: int,
    stats: dict[str, Any] | None,
    downloads: list[dict[str, Any]],
    active_count: int,
    waiting_count: int,
    stopped_count: int,
) -> Layout:
    """Create main layout"""
    layout = Layout()

    layout.split_column(
        Layout(create_header(ip_address, port), size=5, name="header"),
        Layout(name="body"),
    )

    layout["body"].split_row(
        Layout(
            create_stats_panel(stats, active_count, waiting_count, stopped_count),
            size=30,
            name="stats",
        ),
        Layout(
            Panel(
                create_downloads_table(downloads),
                title="[bold]Downloads[/bold]",
                border_style="green",
            ),
            name="downloads",
        ),
    )

    return layout


@click.command()
@click.argument("ip_address")
@click.option("--port", "-p", default=6800, help="aria2 RPC port (default: 6800)")
@click.option(
    "--interval", "-i", default=2, help="Update interval in seconds (default: 2)"
)
@click.option("--token", "-t", default=None, help="aria2 RPC secret token")
def monitor(ip_address: str, port: int, interval: int, token: str | None) -> None:
    """Monitor aria2 RPC server download status with elegant interface

    IP_ADDRESS: aria2 server IP address (e.g., 127.0.0.1 or 192.168.1.100)
    """
    rpc_url = f"http://{ip_address}:{port}/jsonrpc"

    try:
        with Live(console=console, refresh_per_second=4, screen=True) as live:
            while True:
                try:
                    # Prepare parameters with token if provided
                    params: list[Any] = [f"token:{token}"] if token else []

                    # Get downloads
                    active_result = call_aria2_rpc(rpc_url, "aria2.tellActive", params)
                    active_downloads = active_result.get("result", [])

                    waiting_result = call_aria2_rpc(
                        rpc_url, "aria2.tellWaiting", params + [0, 100]
                    )
                    waiting_downloads = waiting_result.get("result", [])

                    stopped_result = call_aria2_rpc(
                        rpc_url, "aria2.tellStopped", params + [0, 100]
                    )
                    stopped_downloads = stopped_result.get("result", [])

                    # Get global statistics
                    stats_result = call_aria2_rpc(
                        rpc_url, "aria2.getGlobalStat", params
                    )
                    global_stats = stats_result.get("result", {})

                    # Create and update layout
                    layout = create_layout(
                        ip_address,
                        port,
                        global_stats,
                        active_downloads,
                        len(active_downloads),
                        len(waiting_downloads),
                        len(stopped_downloads),
                    )

                    live.update(layout)
                    time.sleep(interval)

                except exceptions.ConnectionError:
                    error_panel = Panel(
                        f"[bold red]Cannot connect to aria2 RPC at {rpc_url}[/bold red]\n"
                        "[yellow]Please check if aria2 is running and RPC is enabled[/yellow]",
                        title="Connection Error",
                        style="red",
                    )
                    live.update(error_panel)
                    time.sleep(interval)

                except exceptions.RequestException as e:
                    error_panel = Panel(
                        f"[bold red]Error: {str(e)}[/bold red]",
                        title="Request Error",
                        style="red",
                    )
                    live.update(error_panel)
                    time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")


if __name__ == "__main__":
    monitor()

