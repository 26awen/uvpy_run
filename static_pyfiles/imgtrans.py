# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=11.0.0",
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
# - Pillow: HPND License (https://github.com/python-pillow/Pillow)

"""
Image conversion and compression utility

A batch image converter supporting multiple formats (JPEG, PNG, WebP, BMP, TIFF)
with resize, compression, and EXIF orientation correction capabilities.

Version: 0.8.0
Category: Media
Author: UVPY.RUN

Usage Examples:
    uv run imgtrans.py --input photo.jpg --format webp
    uv run imgtrans.py --input *.png --resize 800x600
    uv run imgtrans.py --input photo.jpg --compress --quality 80
"""

import argparse
import sys
import os
import glob
from pathlib import Path

from PIL import Image


def get_file_size_mb(file_path: str | Path):
    """Get file size in MB"""
    return os.path.getsize(file_path) / (1024 * 1024)


def fix_image_orientation(image: Image.Image):
    """Fix image orientation (based on EXIF data)"""
    try:
        exif_data = image.getexif()
        if not exif_data:
            return image

        orientation = exif_data.get(274)
        if orientation:
            if orientation == 3:
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                image = image.rotate(270, expand=True)
            elif orientation == 8:
                image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, TypeError):
        pass
    return image


def convert_image(
    input_path,
    output_path=None,
    format_type=None,
    resize=None,
    quality=85,
    compress=False,
    verbose=False,
):
    """Convert a single image"""
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"Error: File does not exist {input_path}")
        return False

    try:
        with Image.open(input_path) as img:
            if verbose:
                print(f"Processing: {input_path.name}")
                print(
                    f"  Original: {img.size[0]}x{img.size[1]}, {img.format}, {get_file_size_mb(input_path):.2f}MB"
                )

            # Fix orientation
            img = fix_image_orientation(img)

            # Convert to RGB (for JPEG, etc.)
            if (
                format_type
                and format_type.upper() in ["JPEG", "JPG"]
                and img.mode in ["RGBA", "P"]
            ):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert("RGB")

            # Resize
            if resize:
                if "x" in resize:
                    try:
                        width, height = map(int, resize.split("x"))
                        img = img.resize((width, height), Image.Resampling.LANCZOS)
                        if verbose:
                            print(f"  Resized: {width}x{height}")
                    except ValueError:
                        print(f"Error: Invalid resize format {resize}")
                        return False
                else:
                    try:
                        scale = int(resize)
                        if scale <= 0 or scale > 1000:
                            print(f"Error: Invalid scale {scale}%")
                            return False
                        original_size = img.size
                        new_size = tuple(
                            int(dim * scale / 100) for dim in original_size
                        )
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                        if verbose:
                            print(f"  Scaled: {scale}% -> {new_size[0]}x{new_size[1]}")
                    except ValueError:
                        print(f"Error: Invalid scale {resize}")
                        return False

            # Determine output path
            if not output_path:
                if format_type:
                    ext = format_type.lower()
                    if ext == "jpg":
                        ext = "jpeg"
                    output_path = input_path.with_suffix(f".{ext}")
                else:
                    output_path = input_path.with_suffix(
                        f".converted{input_path.suffix}"
                    )
            else:
                output_path = Path(output_path)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save image
            save_kwargs = {}
            if format_type:
                save_kwargs["format"] = format_type.upper()

            if (format_type and format_type.upper() in ["JPEG", "JPG"]) or compress:
                quality = max(1, min(100, quality))
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True

            img.save(output_path, **save_kwargs)

            # Show results
            if verbose:
                original_size = get_file_size_mb(input_path)
                new_size = get_file_size_mb(output_path)
                compression_ratio = (
                    ((original_size - new_size) / original_size) * 100
                    if original_size > 0
                    else 0
                )

                print(
                    f"  Output: {format_type or img.format}, {get_file_size_mb(output_path):.2f}MB"
                )
                if compression_ratio > 0:
                    print(f"  Compression: {compression_ratio:.1f}%")
                elif compression_ratio < 0:
                    print(f"  File increased: {abs(compression_ratio):.1f}%")
                print(f"  Saved to: {output_path}")
            else:
                print(f"{input_path.name} -> {output_path.name}")

            return True

    except Exception as e:
        print(f"Error: Failed to process {input_path} - {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Image conversion and compression tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input photo.jpg --format webp              # Convert to WebP
  %(prog)s --input *.png --format jpeg --quality 80     # Batch convert PNG to JPEG
  %(prog)s --input large.jpg --resize 800x600           # Resize image
  %(prog)s --input photo.jpg --resize 50                # Scale to 50%
  %(prog)s --input photo.jpg --compress --quality 70    # Compress image
  %(prog)s --input images/*.jpg --output-dir converted/ # Batch process to a directory
        """,
    )

    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input image path (supports wildcards like *.jpg)",
    )
    parser.add_argument("--output", "-o", help="Output file path (for single file)")
    parser.add_argument("--output-dir", help="Output directory (for batch processing)")
    parser.add_argument(
        "--format",
        "-f",
        choices=["jpeg", "jpg", "png", "webp", "bmp", "tiff"],
        help="Output format",
    )
    parser.add_argument("--resize", "-r", help="Resize: WIDTHxHEIGHT or percentage")
    parser.add_argument(
        "--quality",
        "-q",
        type=int,
        default=85,
        help="Image quality 1-100 (default: 85)",
    )
    parser.add_argument(
        "--compress", "-c", action="store_true", help="Enable compression optimization"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed info"
    )

    args = parser.parse_args()

    # Validate quality
    if args.quality < 1 or args.quality > 100:
        print(f"Error: Quality must be between 1-100, got {args.quality}")
        sys.exit(1)

    # Get input files
    input_files = glob.glob(args.input)
    if not input_files:
        print(f"Error: No files matched {args.input}")
        sys.exit(1)

    if args.verbose:
        print(f"Found {len(input_files)} files")
        print("=" * 50)

    success_count = 0

    for input_file in input_files:
        output_path = None

        if args.output and len(input_files) == 1:
            output_path = args.output
        elif args.output_dir:
            input_path = Path(input_file)
            output_dir = Path(args.output_dir)

            if args.format:
                ext = args.format
                if ext == "jpg":
                    ext = "jpeg"
                output_path = output_dir / f"{input_path.stem}.{ext}"
            else:
                output_path = output_dir / input_path.name

        if convert_image(
            input_path=input_file,
            output_path=output_path,
            format_type=args.format,
            resize=args.resize,
            quality=args.quality,
            compress=args.compress,
            verbose=args.verbose,
        ):
            success_count += 1

    print(f"Done: {success_count}/{len(input_files)} files processed successfully")


if __name__ == "__main__":
    main()

