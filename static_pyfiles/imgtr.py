# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=10.0.0",
#     "click>=8.0.0",
# ]
# ///

import click
from PIL import Image, ImageFilter, ImageEnhance
import os
from pathlib import Path


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output file path")
@click.option("--resize", "-r", help="Resize image (width,height or width)")
@click.option("--quality", "-q", default=85, help="JPEG quality (1-100)")
@click.option("--format", "-f", help="Output format (jpeg, png, webp)")
@click.option("--rotate", help="Rotate image (degrees)")
@click.option("--crop", help="Crop image (x,y,width,height)")
@click.option("--brightness", type=float, help="Adjust brightness (0.5-2.0)")
@click.option("--contrast", type=float, help="Adjust contrast (0.5-2.0)")
@click.option("--blur", type=float, help="Apply blur effect (radius)")
@click.option("--sharpen", is_flag=True, help="Apply sharpen filter")
@click.option("--grayscale", is_flag=True, help="Convert to grayscale")
def process_image(
    input_file,
    output,
    resize,
    quality,
    format,
    rotate,
    crop,
    brightness,
    contrast,
    blur,
    sharpen,
    grayscale,
):
    """
    Image processing tool with various operations.

    Examples:
    uv run image_processor.py photo.jpg --resize 800,600 --output resized.jpg
    uv run image_processor.py photo.jpg --grayscale --blur 2.0
    """

    try:
        # Load image
        img = Image.open(input_file)
        click.echo(f"Loaded image: {input_file} ({img.size[0]}x{img.size[1]})")

        # Convert to grayscale
        if grayscale:
            img = img.convert("L")
            click.echo("Applied grayscale filter")

        # Resize image
        if resize:
            if "," in resize:
                width, height = map(int, resize.split(","))
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            else:
                width = int(resize)
                height = int(img.height * width / img.width)
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            click.echo(f"Resized to: {img.size[0]}x{img.size[1]}")

        # Rotate image
        if rotate:
            img = img.rotate(float(rotate), expand=True)
            click.echo(f"Rotated by {rotate} degrees")

        # Crop image
        if crop:
            x, y, width, height = map(int, crop.split(","))
            img = img.crop((x, y, x + width, y + height))
            click.echo(f"Cropped to: {width}x{height}")

        # Adjust brightness
        if brightness:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
            click.echo(f"Adjusted brightness: {brightness}")

        # Adjust contrast
        if contrast:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
            click.echo(f"Adjusted contrast: {contrast}")

        # Apply blur
        if blur:
            img = img.filter(ImageFilter.GaussianBlur(radius=blur))
            click.echo(f"Applied blur with radius: {blur}")

        # Apply sharpen
        if sharpen:
            img = img.filter(ImageFilter.SHARPEN)
            click.echo("Applied sharpen filter")

        # Determine output path and format
        input_path = Path(input_file)
        if output:
            output_path = Path(output)
        else:
            suffix = "_processed"
            output_path = (
                input_path.parent / f"{input_path.stem}{suffix}{input_path.suffix}"
            )

        # Determine save format
        if format:
            save_format = format.upper()
            if format.lower() == "jpeg":
                output_path = output_path.with_suffix(".jpg")
            elif format.lower() == "png":
                output_path = output_path.with_suffix(".png")
            elif format.lower() == "webp":
                output_path = output_path.with_suffix(".webp")
        else:
            save_format = img.format or "JPEG"

        # Save image
        save_kwargs = {}
        if save_format == "JPEG":
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
            # Convert to RGB if necessary for JPEG
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
        elif save_format == "PNG":
            save_kwargs["optimize"] = True
        elif save_format == "WEBP":
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True

        img.save(output_path, format=save_format, **save_kwargs)

        # Display results
        final_size = os.path.getsize(output_path)
        original_size = os.path.getsize(input_file)
        compression_ratio = (1 - final_size / original_size) * 100

        click.echo(f"Saved to: {output_path}")
        click.echo(f"Final size: {img.size[0]}x{img.size[1]}")
        click.echo(
            f"File size: {final_size:,} bytes (original: {original_size:,} bytes)"
        )
        if compression_ratio > 0:
            click.echo(f"Compression: {compression_ratio:.1f}% smaller")
        else:
            click.echo(f"File size increased by {abs(compression_ratio):.1f}%")

    except Exception as e:
        click.echo(f"Error processing image: {str(e)}", err=True)
        return 1


if __name__ == "__main__":
    process_image()
