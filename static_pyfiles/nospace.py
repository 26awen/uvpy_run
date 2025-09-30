# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.0.0",
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

"""
Remove all spaces from text strings with flexible input options

A command-line utility for removing spaces from text input.
Supports both direct text input and interactive mode for user convenience.

Version: 0.0.2
Category: Text Processing
Author: UVPY.RUN

Usage Examples:
    uv run nospace.py --text "Hello World"
    uv run nospace.py --interactive
    uv run nospace.py -t "This is a test"
    uv run nospace.py -i
"""

import click


@click.command()
@click.option("--text", "-t", help="Text string to remove spaces from", type=str)
@click.option(
    "--interactive", "-i", is_flag=True, help="Interactive mode to input text"
)
def remove_spaces(text: str | None, interactive: bool) -> None:
    """
    Remove all spaces from a given text string.

    This script can work in two modes:
    1. Direct text input via --text option
    2. Interactive mode via --interactive flag
    """

    if interactive:
        # Interactive mode: prompt user for input
        input_text = click.prompt("Enter the text to remove spaces from", type=str)
    elif text:
        # Direct text input mode
        input_text = text
    else:
        # No input provided, show help
        click.echo(
            "Error: Please provide text using --text option or use --interactive mode"
        )
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        return

    # Remove all spaces from the input text
    result = input_text.replace(" ", "")

    # Display results
    click.echo(f"Original text: {input_text}")
    click.echo(f"Text without spaces: {result}")


if __name__ == "__main__":
    remove_spaces()
