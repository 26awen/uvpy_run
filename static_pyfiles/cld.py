# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click>=8.0.0",
# ]
# ///

"""
Beautiful calendar printer with highlighting features

A command-line calendar tool that displays formatted monthly or yearly calendars
with current day highlighting and customizable week start options.

Version: 1.0.0
Category: Utility
Author: Config-Txt Project

Usage Examples:
    uv run cld.py
    uv run cld.py -m 6 -h
    uv run cld.py -a -h
    uv run cld.py -y 2025 -m 1-3 -s
"""

import calendar
import click
import re
from datetime import datetime
from typing import List, Optional


def print_calendar_header(year: int, month: int) -> None:
    """Print a formatted header for the calendar."""
    month_name = calendar.month_name[month]
    header = f"{month_name} {year}"
    print(f"\n{'=' * 30}")
    print(f"{header:^30}")
    print(f"{'=' * 30}")


def highlight_current_day(
    calendar_text: str, year: int, month: int, today: datetime
) -> str:
    """Highlight the current day in the calendar text."""
    if today.year != year or today.month != month:
        return calendar_text

    current_day = today.day
    lines = calendar_text.split("\n")

    # Process each line to find and highlight the current day
    for i, line in enumerate(lines):
        # Skip the header lines (weekday names)
        if i < 2:
            continue

        # Find all numbers in the line
        words = line.split()
        highlighted_words = []

        for word in words:
            if word.isdigit() and int(word) == current_day:
                # Highlight the current day
                highlighted_word = click.style(
                    f"{word:>2}", bg="red", fg="white", bold=True
                )
                highlighted_words.append(highlighted_word)
            else:
                highlighted_words.append(f"{word:>2}")

        if highlighted_words:
            lines[i] = " ".join(highlighted_words)

    return "\n".join(lines)


def print_single_month(year: int, month: int, highlight_today: bool = False) -> None:
    """Print calendar for a single month with beautiful formatting."""
    print_calendar_header(year, month)

    # Create calendar object with Monday as first day (can be changed to Sunday if preferred)
    cal = calendar.TextCalendar(calendar.MONDAY)
    month_calendar = cal.formatmonth(year, month)

    # Extract the calendar part (skip the first line which contains month/year)
    lines = month_calendar.strip().split("\n")
    calendar_body = "\n".join(lines[1:])  # Skip the first line, keep weekday headers

    # Highlight current day if requested
    if highlight_today:
        today = datetime.now()
        calendar_body = highlight_current_day(calendar_body, year, month, today)

    # Print with proper indentation
    for line in calendar_body.split("\n"):
        print(f"  {line}")
    print()


def print_multiple_months(
    year: int, months: List[int], highlight_today: bool = False
) -> None:
    """Print calendars for multiple months."""
    print(f"\nCalendar for {year}")
    print("=" * 50)

    for month in sorted(months):
        if 1 <= month <= 12:
            print_single_month(year, month, highlight_today)
        else:
            click.echo(f"Warning: Invalid month {month}, skipping...", err=True)


def validate_month(month: int) -> bool:
    """Validate if month is in valid range."""
    return 1 <= month <= 12


def parse_month_range(month_str: str) -> List[int]:
    """Parse month range string like '1-3' or '1,3,5'."""
    months = []

    for part in month_str.split(","):
        part = part.strip()
        if "-" in part:
            # Handle range like "1-3"
            try:
                start, end = map(int, part.split("-"))
                months.extend(range(start, end + 1))
            except ValueError:
                raise click.BadParameter(f"Invalid month range format: {part}")
        else:
            # Handle single month
            try:
                months.append(int(part))
            except ValueError:
                raise click.BadParameter(f"Invalid month: {part}")

    return months


@click.command()
@click.option(
    "--year",
    "-y",
    type=int,
    default=datetime.now().year,
    help="Year to display (default: current year)",
)
@click.option(
    "--month",
    "-m",
    type=str,
    help="Month(s) to display. Can be single month (1), range (1-3), or comma-separated (1,3,5)",
)
@click.option("--all", "-a", is_flag=True, help="Display all months of the year")
@click.option(
    "--highlight",
    "-h",
    is_flag=True,
    help="Highlight today's date based on system timezone",
)
@click.option(
    "--start-sunday",
    "-s",
    is_flag=True,
    help="Start week with Sunday instead of Monday",
)
def calendar_printer(
    year: int, month: Optional[str], all: bool, highlight: bool, start_sunday: bool
) -> None:
    """
    Print beautiful calendar for specified month(s) or year with weekdays displayed.

    Examples:

    \b
    # Print current month
    python script.py

    \b
    # Print specific month with today highlighted
    python script.py -m 6 -h

    \b
    # Print multiple months
    python script.py -m 1,3,6

    \b
    # Print month range with Sunday as first day
    python script.py -m 1-6 -s

    \b
    # Print entire year with today highlighted
    python script.py -a -h

    \b
    # Print for different year
    python script.py -y 2025 -m 1-3 -h
    """

    # Set calendar first day of week
    if start_sunday:
        calendar.setfirstweekday(calendar.SUNDAY)
    else:
        calendar.setfirstweekday(calendar.MONDAY)

    # Show current time info if highlighting
    if highlight:
        now = datetime.now()
        timezone_info = now.astimezone().strftime("%Z %z")
        click.echo(
            f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({timezone_info})"
        )

    if all:
        # Print entire year
        months = list(range(1, 13))
        print_multiple_months(year, months, highlight)
    elif month:
        # Parse and print specified months
        try:
            months = parse_month_range(month)
            invalid_months = [m for m in months if not validate_month(m)]
            if invalid_months:
                raise click.BadParameter(f"Invalid months: {invalid_months}")

            if len(months) == 1:
                print_single_month(year, months[0], highlight)
            else:
                print_multiple_months(year, months, highlight)
        except click.BadParameter as e:
            click.echo(f"Error: {e}", err=True)
            return
    else:
        # Print current month by default
        current_month = datetime.now().month
        print_single_month(year, current_month, highlight)


if __name__ == "__main__":
    calendar_printer()

