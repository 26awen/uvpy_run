# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.0.0",
#     "qrcode[pil]>=7.0.0",
# ]
# ///

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
