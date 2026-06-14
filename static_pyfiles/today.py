# /// script
# requires-python = ">=3.10"
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
Show today-first calendars in the terminal

A polished command-line calendar that opens on the current month, highlights
today by default, and can render a specific month, month range, or full year in
compact Rich panels. The header includes the local timezone used for today's
date.

Version: 1.0.0
Category: Time
Author: UVPY.RUN

Usage Examples:
    uv run today.py
    uv run today.py --no-highlight
    uv run today.py -m 6
    uv run today.py -a
    uv run today.py -y 2025 -m 1-3 -s

Use It For:
    - Seeing today in context without opening a full calendar app
    - Reviewing one month, a short month range, or a whole year
    - Copying a readable terminal calendar into notes or planning threads
    - Checking week layouts with either Monday-first or Sunday-first weeks

Display Options:
    - Today is highlighted by default when it appears in the selected months
    - The header shows the local timezone used to decide what today means
    - Use --no-highlight when you want plain date cells
    - Weeks start on Monday by default
    - Use --start-sunday when you prefer Sunday-first calendars
    - Month input accepts single values, comma lists, and ranges
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

import click
from rich import box
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


MONTHS_PER_ROW = 3

MONTH_PANEL_STYLE = "#7cc7ff"
TODAY_STYLE = "bold white on #d75f00"
CURRENT_MONTH_STYLE = "bold #7dff9b"
ADJACENT_MONTH_STYLE = "dim #7f8d8a"
WEEKEND_STYLE = "#ffcc66"
WEEKDAY_STYLE = "#dbffe9"
HEADER_STYLE = "bold #7cc7ff"
MUTED_STYLE = "dim #9ca9a3"


@dataclass(frozen=True)
class CalendarSelection:
    """Resolved calendar options for rendering."""

    year: int
    months: list[int]
    first_weekday: int
    highlight_today: bool
    today: date
    current_time: datetime


def parse_month_range(month_text: str) -> list[int]:
    """Parse month input like '1-3' or '1,3,5' into unique month numbers."""

    months: list[int] = []

    for raw_part in month_text.split(","):
        part = raw_part.strip()
        if not part:
            raise click.BadParameter("Month lists cannot contain empty values.")

        if "-" in part:
            bounds = [value.strip() for value in part.split("-", 1)]
            try:
                start, end = (int(value) for value in bounds)
            except ValueError as error:
                raise click.BadParameter(
                    f"Invalid month range format: {part}"
                ) from error
            if start > end:
                raise click.BadParameter(
                    f"Month range must ascend from low to high: {part}"
                )
            months.extend(range(start, end + 1))
        else:
            try:
                months.append(int(part))
            except ValueError as error:
                raise click.BadParameter(f"Invalid month: {part}") from error

    unique_months = list(dict.fromkeys(months))
    invalid_months = [month for month in unique_months if not validate_month(month)]
    if invalid_months:
        raise click.BadParameter(f"Invalid months: {invalid_months}")

    return unique_months


def validate_month(month: int) -> bool:
    """Return whether a month number is in the calendar range."""

    return 1 <= month <= 12


def resolve_months(
    year: int,
    month_text: str | None,
    show_all: bool,
    today: date,
) -> list[int]:
    """Resolve CLI month options into the month list to display."""

    if show_all:
        return list(range(1, 13))
    if month_text:
        return parse_month_range(month_text)
    if year == today.year:
        return [today.month]
    return [1]


def weekday_labels(first_weekday: int) -> list[str]:
    """Return short weekday labels in the requested order."""

    labels = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    if first_weekday == calendar.SUNDAY:
        return ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
    return labels


def is_weekend(day: date) -> bool:
    """Return whether a date falls on a Saturday or Sunday."""

    return day.weekday() >= 5


def date_cell(
    day: date,
    target_year: int,
    target_month: int,
    today: date,
    highlight_today: bool,
) -> Text:
    """Build a styled date cell for the month grid."""

    is_current_month = day.year == target_year and day.month == target_month
    is_today = is_current_month and day == today
    label = f"{day.day:2}"

    if highlight_today and is_today:
        return Text(label, style=TODAY_STYLE)
    if not is_current_month:
        return Text(label, style=ADJACENT_MONTH_STYLE)
    if is_weekend(day):
        return Text(label, style=WEEKEND_STYLE)
    return Text(label, style=WEEKDAY_STYLE)


def build_month_panel(selection: CalendarSelection, month: int) -> Panel:
    """Render one month as a compact Rich panel."""

    month_calendar = calendar.Calendar(selection.first_weekday)
    weeks = month_calendar.monthdatescalendar(selection.year, month)

    table = Table.grid(padding=(0, 1))
    for _ in range(7):
        table.add_column(justify="center", width=2)

    table.add_row(
        *[
            Text(
                label,
                style=HEADER_STYLE if label not in {"Sa", "Su"} else WEEKEND_STYLE,
            )
            for label in weekday_labels(selection.first_weekday)
        ]
    )

    for week in weeks:
        table.add_row(
            *[
                date_cell(
                    day,
                    selection.year,
                    month,
                    selection.today,
                    selection.highlight_today,
                )
                for day in week
            ]
        )

    month_name = calendar.month_name[month]
    subtitle = ""
    if (
        selection.highlight_today
        and selection.today.year == selection.year
        and selection.today.month == month
    ):
        subtitle = f"today {selection.today.day}"

    return Panel.fit(
        table,
        title=Text(f"{month_name} {selection.year}", style=CURRENT_MONTH_STYLE),
        subtitle=Text(subtitle, style=TODAY_STYLE) if subtitle else None,
        border_style=MONTH_PANEL_STYLE,
        box=box.SQUARE,
        padding=(0, 1),
    )


def build_header(selection: CalendarSelection) -> Panel:
    """Build the small status panel above the rendered calendar."""

    week_start = "Sunday" if selection.first_weekday == calendar.SUNDAY else "Monday"
    month_label = format_month_selection(selection.months)
    highlight_label = "highlight on" if selection.highlight_today else "highlight off"
    timezone_label = format_timezone(selection.current_time)
    today_label = (
        f"{selection.today:%A}, {selection.today:%B} "
        f"{selection.today.day}, {selection.today.year}"
    )

    heading = Text()
    heading.append("today", style="bold #7dff9b")
    heading.append("  ")
    heading.append(today_label, style=WEEKDAY_STYLE)
    heading.append("\n")
    heading.append(f"{selection.year}: {month_label}", style=MUTED_STYLE)
    heading.append("  ")
    heading.append(f"timezone {timezone_label}", style=MUTED_STYLE)
    heading.append("\n")
    heading.append(f"weeks start {week_start}", style=MUTED_STYLE)
    heading.append("  ")
    heading.append(
        highlight_label,
        style=TODAY_STYLE if selection.highlight_today else MUTED_STYLE,
    )

    return Panel.fit(
        heading,
        border_style="#38d878",
        box=box.SQUARE,
        padding=(0, 1),
    )


def format_timezone(current_time: datetime) -> str:
    """Return a readable local timezone label with a UTC offset."""

    zone_name = current_time.tzname() or "local"
    offset = current_time.strftime("%z")
    if not offset:
        return zone_name

    utc_offset = f"UTC{offset[:3]}:{offset[3:]}"
    if zone_name == "UTC":
        return utc_offset
    return f"{zone_name} ({utc_offset})"


def format_month_selection(months: list[int]) -> str:
    """Return a compact display label for the selected months."""

    sorted_months = sorted(months)
    if sorted_months == list(range(1, 13)):
        return "all months"
    if len(sorted_months) > 6:
        start = calendar.month_abbr[sorted_months[0]]
        end = calendar.month_abbr[sorted_months[-1]]
        return f"{start}-{end} ({len(sorted_months)} months)"
    return ", ".join(calendar.month_abbr[month] for month in sorted_months)


def month_rows(renderables: Iterable[RenderableType]) -> list[Columns]:
    """Group month panels into stable three-column rows."""

    panels = list(renderables)
    return [
        Columns(panels[index : index + MONTHS_PER_ROW], equal=True, expand=False)
        for index in range(0, len(panels), MONTHS_PER_ROW)
    ]


def render_calendar(
    selection: CalendarSelection,
    console: Console | None = None,
) -> None:
    """Render the selected calendar months to the terminal."""

    target_console = console or Console()
    panels = [
        build_month_panel(selection, month)
        for month in sorted(selection.months)
    ]
    target_console.print(Group(build_header(selection), *month_rows(panels)))


@click.command(context_settings={"help_option_names": ["--help"]})
@click.option(
    "--year",
    "-y",
    type=int,
    default=lambda: datetime.now().astimezone().year,
    show_default="current year",
    help="Year to display.",
)
@click.option(
    "--month",
    "-m",
    type=str,
    help="Month(s) to display: single month (1), range (1-3), or comma list (1,3,5).",
)
@click.option("--all", "-a", "show_all", is_flag=True, help="Display every month.")
@click.option(
    "--highlight/--no-highlight",
    "-h",
    default=True,
    show_default=True,
    help="Highlight today's date when it appears in the selected months.",
)
@click.option(
    "--start-sunday",
    "-s",
    is_flag=True,
    help="Start weeks with Sunday instead of Monday.",
)
def today_calendar(
    year: int,
    month: str | None,
    show_all: bool,
    highlight: bool,
    start_sunday: bool,
) -> None:
    """
    Show a polished terminal calendar, with today's date highlighted by default.

    Examples:

    \b
    # Show the current month with today highlighted
    uv run today.py

    \b
    # Show the current month without highlighting
    uv run today.py --no-highlight

    \b
    # Show a specific month
    uv run today.py -m 6

    \b
    # Show a month range with Sunday as the first weekday
    uv run today.py -y 2025 -m 1-3 -s

    \b
    # Show the whole year
    uv run today.py -a
    """

    current_time = datetime.now().astimezone()
    current_day = current_time.date()
    first_weekday = calendar.SUNDAY if start_sunday else calendar.MONDAY
    months = resolve_months(year, month, show_all, current_day)
    selection = CalendarSelection(
        year=year,
        months=months,
        first_weekday=first_weekday,
        highlight_today=highlight,
        today=current_day,
        current_time=current_time,
    )

    render_calendar(selection)


if __name__ == "__main__":
    today_calendar()
