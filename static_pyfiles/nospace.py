# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.2.1",
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
# - Rich: MIT License (https://github.com/Textualize/rich)

"""
Remove spaces from text with a copy-friendly terminal summary

A small command-line text cleaner that removes literal space characters by
default, shows exactly what changed, and can also read from stdin or an
interactive prompt.

Version: 1.0.0
Category: Text
Author: UVPY.RUN

Usage Examples:
    uv run nospace.py "Hello World"
    uv run nospace.py --text "This is a test"
    uv run nospace.py --stdin
    uv run nospace.py --all-whitespace "tabs	and spaces"
    uv run nospace.py --quiet "copy ready"

Use It For:
    - Removing literal spaces from labels, identifiers, and short snippets
    - Cleaning pasted text without hiding what changed
    - Reading text from an argument, stdin, or an interactive prompt
    - Producing a plain result for scripts with --quiet

Output:
    - Shows a compact Rich summary by default
    - Prints the cleaned text in its own copy-friendly panel
    - Reports how many characters were removed
    - Leaves tabs and newlines untouched unless --all-whitespace is enabled
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import Enum

import click
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


SPACE_PATTERN = re.compile(" ")
WHITESPACE_PATTERN = re.compile(r"\s+")

PANEL_STYLE = "#7cc7ff"
SUCCESS_STYLE = "bold #7dff9b"
MUTED_STYLE = "dim #9ca9a3"


class InputMode(Enum):
    """Supported input sources for text cleanup."""

    ARGUMENT = "argument"
    OPTION = "option"
    STDIN = "stdin"
    INTERACTIVE = "interactive"


@dataclass(frozen=True)
class NoSpaceResult:
    """Result metadata for a nospace transformation."""

    original: str
    cleaned: str
    removed: int
    mode: InputMode
    all_whitespace: bool


def clean_text(text: str, all_whitespace: bool = False) -> NoSpaceResult:
    """Remove spaces or all whitespace from text and return transformation data."""

    pattern = WHITESPACE_PATTERN if all_whitespace else SPACE_PATTERN
    cleaned = pattern.sub("", text)
    return NoSpaceResult(
        original=text,
        cleaned=cleaned,
        removed=len(text) - len(cleaned),
        mode=InputMode.ARGUMENT,
        all_whitespace=all_whitespace,
    )


def resolve_input(
    argument: str | None,
    option_text: str | None,
    use_stdin: bool,
    interactive: bool,
) -> tuple[str, InputMode]:
    """Resolve exactly one input source from CLI options."""

    sources = [
        (argument is not None, InputMode.ARGUMENT),
        (option_text is not None, InputMode.OPTION),
        (use_stdin, InputMode.STDIN),
        (interactive, InputMode.INTERACTIVE),
    ]
    active_sources = [mode for enabled, mode in sources if enabled]

    if len(active_sources) > 1:
        source_names = ", ".join(mode.value for mode in active_sources)
        raise click.UsageError(f"Choose one input source, not: {source_names}.")
    if not active_sources:
        raise click.UsageError(
            "Provide text as an argument, with --text, with --stdin, or use --interactive."
        )

    mode = active_sources[0]
    if mode == InputMode.ARGUMENT:
        return argument or "", mode
    if mode == InputMode.OPTION:
        return option_text or "", mode
    if mode == InputMode.STDIN:
        return sys.stdin.read(), mode

    return click.prompt("Enter text to clean", type=str), mode


def build_result(
    text: str,
    mode: InputMode,
    all_whitespace: bool,
) -> NoSpaceResult:
    """Clean text and attach the original input mode."""

    result = clean_text(text, all_whitespace=all_whitespace)
    return NoSpaceResult(
        original=result.original,
        cleaned=result.cleaned,
        removed=result.removed,
        mode=mode,
        all_whitespace=result.all_whitespace,
    )


def render_result(result: NoSpaceResult, console: Console | None = None) -> None:
    """Render a copy-friendly Rich summary for a cleanup result."""

    target_console = console or Console()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(justify="left")
    summary.add_column(justify="right")
    summary.add_row("input", result.mode.value)
    summary.add_row(
        "removed",
        f"{result.removed} character{'s' if result.removed != 1 else ''}",
    )
    summary.add_row(
        "mode",
        "all whitespace" if result.all_whitespace else "literal spaces",
    )

    heading = Text()
    heading.append("nospace", style=SUCCESS_STYLE)
    heading.append("  ")
    heading.append("text cleaned", style=MUTED_STYLE)

    output_panel = Panel(
        Text(result.cleaned or "(empty result)", style=SUCCESS_STYLE),
        title="cleaned text",
        border_style=SUCCESS_STYLE,
        box=box.SQUARE,
        padding=(0, 1),
    )
    summary_panel = Panel.fit(
        Group(heading, summary),
        border_style=PANEL_STYLE,
        box=box.SQUARE,
        padding=(0, 1),
    )

    target_console.print(Group(summary_panel, output_panel))


@click.command(context_settings={"help_option_names": ["--help"]})
@click.argument("argument", required=False)
@click.option("--text", "-t", "option_text", help="Text string to clean.")
@click.option(
    "--stdin",
    "use_stdin",
    is_flag=True,
    help="Read text from standard input.",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Prompt for text interactively.",
)
@click.option(
    "--all-whitespace",
    is_flag=True,
    help="Remove tabs, newlines, and other whitespace too.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Print only the cleaned text.",
)
def remove_spaces(
    argument: str | None,
    option_text: str | None,
    use_stdin: bool,
    interactive: bool,
    all_whitespace: bool,
    quiet: bool,
) -> None:
    """Remove spaces from text and print a copy-friendly result."""

    input_text, mode = resolve_input(argument, option_text, use_stdin, interactive)
    result = build_result(input_text, mode, all_whitespace)

    if quiet:
        click.echo(result.cleaned)
        return

    render_result(result)


if __name__ == "__main__":
    remove_spaces()
