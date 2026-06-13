# /// script
# requires-python = ">=3.12"
# dependencies = []
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

"""
Verify uv remote script execution with a tiny demo

A tiny script that prints a predictable message so users can confirm that
`uv run <url>` fetched and executed a remote Python file successfully.

Version: 0.2.0
Category: Developer
Author: UVPY.RUN

Usage Examples:
    uv run demo.py
    uv run demo.py --message "Hello from uvpy.run"

Use It For:
    - Confirming that uv can fetch and run a script from a URL
    - Testing a uvpy.run deployment without touching files or services
    - Showing the smallest possible standalone script pattern

Output:
    - Prints one confirmation line and exits
    - Accepts a custom --message when you want a recognizable test string
"""

import argparse


DEFAULT_MESSAGE = "Demo: uv successfully ran this script from uvpy.run."


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a tiny confirmation message for uv remote execution."
    )
    parser.add_argument(
        "--message",
        default=DEFAULT_MESSAGE,
        help="Message to print instead of the default confirmation.",
    )
    args = parser.parse_args()

    print(args.message)


if __name__ == "__main__":
    main()
