# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.0.0",
#     "qrcode[pil]>=7.0.0",
# ]
# ///

# MIT License
#
# Copyright (c) 2025 Config-Txt Project
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

"""
Generate QR codes with customizable styles and options

A command-line utility for creating QR codes from text input.
Supports square and rounded styles with adjustable size settings.

Version: 1.0.0
Category: Utility
Author: Config-Txt Project

Usage Examples:
    uv run qr.py "Hello World"
    uv run qr.py "https://example.com" --output myqr.png --style rounded
    uv run qr.py "Contact info" --size 15 --border 2
"""

import click
from pathlib import Path
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer


@click.command()
@click.argument("text", type=str)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="qrcode.png",
    help="Output file name (default: qrcode.png)",
)
@click.option(
    "--size", "-s", type=int, default=10, help="Box size for each module (default: 10)"
)
@click.option(
    "--border", "-b", type=int, default=4, help="Border size in modules (default: 4)"
)
@click.option(
    "--style",
    type=click.Choice(["square", "rounded"]),
    default="square",
    help="QR code style (default: square)",
)
def generate_qrcode(text: str, output: str, size: int, border: int, style: str) -> None:
    """Generate QR code from input text."""

    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,  # Auto-adjust version based on data
        error_correction=qrcode.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )

    # Add data to QR code
    qr.add_data(text)
    qr.make(fit=True)

    # Generate image based on style
    if style == "rounded":
        img = qr.make_image(
            image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer()
        )
    else:
        img = qr.make_image(fill_color="black", back_color="white")

    # Save the image
    output_path = Path(output)
    img.save(output_path)

    click.echo(f"QR code generated successfully: {output_path.absolute()}")
    click.echo(f"Content: {text}")
    click.echo(f"Size: {size}x{size} pixels per module")
    click.echo(f"Border: {border} modules")
    click.echo(f"Style: {style}")


if __name__ == "__main__":
    generate_qrcode()
