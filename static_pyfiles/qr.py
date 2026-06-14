# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.2.1",
#     "qrcode[pil]>=8.2.0",
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
# - qrcode: BSD License (https://github.com/lincolnloop/python-qrcode)
# - Rich: MIT License (https://github.com/Textualize/rich)

"""
Generate QR codes with a terminal preview and PNG output

A command-line QR generator for URLs, short messages, and shareable text. It
validates sizing options, supports square or rounded modules, exposes QR error
correction levels, shows the code directly in the terminal by default, and
refuses to overwrite existing files unless you opt in.

Version: 1.0.0
Category: Image
Author: UVPY.RUN

Usage Examples:
    uv run qr.py "https://uvpy.run" --dry-run
    uv run qr.py "https://example.com" --output example.png --style rounded
    uv run qr.py "Contact info" --size 12 --border 2 --error-correction q
    uv run qr.py "dark mode" --fill "#111827" --back "#f9fafb"
    uv run qr.py "release link" -o build/release-qr.png
    uv run qr.py "ci artifact" --no-terminal --output build/ci-qr.png
    uv run qr.py "https://docs.astral.sh/uv/" --dry-run
    uv run qr.py "replace file" --force --output qrcode.png

Use It For:
    - Turning URLs, contact text, or short messages into QR code PNG files
    - Creating a quick code without opening a design tool
    - Choosing square or rounded modules for simple visual styling
    - Raising error correction when a code may be printed, compressed, or scuffed

Output:
    - Displays the generated QR code directly in the terminal by default
    - Saves a PNG file, defaulting to qrcode.png
    - Creates missing output directories when needed
    - Refuses to overwrite an existing file unless --force is provided
    - Supports --dry-run for terminal preview without writing a file
    - Shows the absolute output path, image dimensions, style, and correction level
    - Prints the encoded content in a review-friendly summary
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click
import qrcode
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer


DEFAULT_OUTPUT = "qrcode.png"

PANEL_STYLE = "#7cc7ff"
SUCCESS_STYLE = "bold #7dff9b"
MUTED_STYLE = "dim #9ca9a3"

ERROR_CORRECTION_LEVELS = {
    "l": qrcode.ERROR_CORRECT_L,
    "m": qrcode.ERROR_CORRECT_M,
    "q": qrcode.ERROR_CORRECT_Q,
    "h": qrcode.ERROR_CORRECT_H,
}


@dataclass(frozen=True)
class QRResult:
    """Metadata for a generated QR code file."""

    output_path: Path
    content: str
    box_size: int
    border: int
    style: str
    error_correction: str
    fill_color: str
    back_color: str
    dimensions: tuple[int, int]
    matrix: list[list[bool]]
    written: bool
    dry_run: bool


def generate_qr_image(
    content: str,
    output_path: Path,
    box_size: int,
    border: int,
    style: str,
    error_correction: str,
    fill_color: str,
    back_color: str,
    force: bool = False,
    dry_run: bool = False,
) -> QRResult:
    """Generate a QR image and return metadata about the planned or written file."""

    resolved_output = output_path.expanduser()
    if resolved_output.exists() and not force and not dry_run:
        raise click.ClickException(
            f"Output file already exists: {resolved_output}. "
            "Use --force to overwrite it or choose a different --output path."
        )

    normalized_level = error_correction.lower()
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECTION_LEVELS[normalized_level],
        box_size=box_size,
        border=border,
    )
    qr.add_data(content)
    qr.make(fit=True)

    if style == "rounded":
        image = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            fill_color=fill_color,
            back_color=back_color,
        )
    else:
        image = qr.make_image(fill_color=fill_color, back_color=back_color)

    if not dry_run:
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        image.save(resolved_output)

    return QRResult(
        output_path=resolved_output.resolve(),
        content=content,
        box_size=box_size,
        border=border,
        style=style,
        error_correction=normalized_level.upper(),
        fill_color=fill_color,
        back_color=back_color,
        dimensions=image.size,
        matrix=qr.get_matrix(),
        written=not dry_run,
        dry_run=dry_run,
    )


def render_terminal_qr(matrix: list[list[bool]]) -> Text:
    """Render a QR matrix as compact terminal blocks."""

    rows = [list(row) for row in matrix]
    if len(rows) % 2:
        rows.append([False] * len(rows[0]))

    qr_text = Text()
    for row_index in range(0, len(rows), 2):
        top_row = rows[row_index]
        bottom_row = rows[row_index + 1]
        for top, bottom in zip(top_row, bottom_row):
            if top and bottom:
                glyph = "█"
            elif top:
                glyph = "▀"
            elif bottom:
                glyph = "▄"
            else:
                glyph = " "
            qr_text.append(glyph, style="#111827 on #f8fafc")
        if row_index < len(rows) - 2:
            qr_text.append("\n")
    return qr_text


def render_result(
    result: QRResult,
    show_terminal: bool = True,
    console: Console | None = None,
) -> None:
    """Render a Rich summary for a generated QR image."""

    target_console = console or Console()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(justify="left")
    summary.add_column(justify="right")
    summary.add_row("status", "dry run (not written)" if result.dry_run else "written")
    summary.add_row("file", str(result.output_path))
    summary.add_row("dimensions", f"{result.dimensions[0]}x{result.dimensions[1]} px")
    summary.add_row("module size", f"{result.box_size}px")
    summary.add_row("border", f"{result.border} modules")
    summary.add_row("style", result.style)
    summary.add_row("correction", result.error_correction)
    summary.add_row("colors", f"{result.fill_color} on {result.back_color}")

    heading = Text()
    heading.append("qr", style=SUCCESS_STYLE)
    heading.append("  ")
    if result.dry_run:
        status = "terminal preview + dry run" if show_terminal else "dry run"
    else:
        status = "terminal preview + PNG generated" if show_terminal else "PNG generated"
    heading.append(status, style=MUTED_STYLE)

    content_panel = Panel(
        Text(result.content, style="#dbffe9", overflow="fold"),
        title="encoded content",
        border_style=PANEL_STYLE,
        box=box.SQUARE,
        padding=(0, 1),
    )
    summary_panel = Panel.fit(
        Group(heading, summary),
        border_style=SUCCESS_STYLE,
        box=box.SQUARE,
        padding=(0, 1),
    )

    panels = [summary_panel]
    if show_terminal:
        panels.insert(
            0,
            Panel.fit(
                render_terminal_qr(result.matrix),
                title="terminal preview",
                border_style=SUCCESS_STYLE,
                box=box.SQUARE,
                padding=(0, 1),
            ),
        )
    panels.append(content_panel)
    target_console.print(Group(*panels))


@click.command(context_settings={"help_option_names": ["--help"]})
@click.argument("text", type=str)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path(DEFAULT_OUTPUT),
    show_default=True,
    help="Output PNG path.",
)
@click.option(
    "--size",
    "-s",
    "box_size",
    type=click.IntRange(1, 80),
    default=10,
    show_default=True,
    help="Pixel size for each QR module.",
)
@click.option(
    "--border",
    "-b",
    type=click.IntRange(0, 20),
    default=4,
    show_default=True,
    help="Quiet-zone border in modules.",
)
@click.option(
    "--style",
    type=click.Choice(["square", "rounded"]),
    default="square",
    show_default=True,
    help="Module drawing style.",
)
@click.option(
    "--error-correction",
    "-e",
    type=click.Choice(["l", "m", "q", "h"], case_sensitive=False),
    default="m",
    show_default=True,
    help="QR error correction level: l, m, q, or h.",
)
@click.option(
    "--fill",
    default="black",
    show_default=True,
    help="Foreground/module color accepted by Pillow.",
)
@click.option(
    "--back",
    default="white",
    show_default=True,
    help="Background color accepted by Pillow.",
)
@click.option(
    "--terminal/--no-terminal",
    "show_terminal",
    default=True,
    show_default=True,
    help="Display the QR code directly in the terminal.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite the output file if it already exists.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show the terminal preview and summary without writing a PNG file.",
)
def generate_qrcode(
    text: str,
    output: Path,
    box_size: int,
    border: int,
    style: str,
    error_correction: str,
    fill: str,
    back: str,
    show_terminal: bool,
    force: bool,
    dry_run: bool,
) -> None:
    """Generate a QR code PNG from input text."""

    try:
        result = generate_qr_image(
            content=text,
            output_path=output,
            box_size=box_size,
            border=border,
            style=style,
            error_correction=error_correction,
            fill_color=fill,
            back_color=back,
            force=force,
            dry_run=dry_run,
        )
    except click.ClickException:
        raise
    except Exception as error:
        raise click.ClickException(f"Could not generate QR code: {error}") from error

    render_result(result, show_terminal=show_terminal)


if __name__ == "__main__":
    generate_qrcode()
