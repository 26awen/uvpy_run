# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=11.0.0",
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
# - Pillow: HPND License (https://github.com/python-pillow/Pillow)
# - Click: BSD-3-Clause License (https://github.com/pallets/click)

"""
Transform, convert and compress images in one command

A unified image tool for single-file edits and batch workflows. It converts
JPEG, PNG, WebP, BMP and TIFF files, normalizes EXIF orientation, resizes,
crops, rotates, adjusts brightness or contrast, and applies blur, sharpen or
grayscale effects with safe output defaults.

Version: 1.0.0
Category: Image
Author: UVPY.RUN

Usage Examples:
    uv run image.py photo.jpg --resize 1200 --format webp
    uv run image.py --input "*.png" --format webp --output-dir converted
    uv run image.py photo.jpg --grayscale --blur 2 --output moody.jpg
    uv run image.py --input "images/*.jpg" --scale 50% --quality 75 --dry-run

Use It For:
    - Converting or compressing one image or a wildcard batch
    - Resizing, cropping, rotating, or previewing visual edits from the terminal
    - Normalizing phone-camera orientation before publishing images

Workflow Notes:
    - Quote wildcard inputs so the script can expand them consistently
    - Use --output for one image and --output-dir for batches
    - By default, single-file output gets an _processed suffix and metadata is stripped

Safety Notes:
    - Existing output files are not overwritten unless --force is provided
    - Use --dry-run to preview matched files and output paths before writing
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from pathlib import Path

import click
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError


SUPPORTED_FORMATS = {
    "jpeg": "JPEG",
    "jpg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "tiff": "TIFF",
    "tif": "TIFF",
}
FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "TIFF": ".tiff",
}
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


@dataclass(frozen=True)
class ResizeSpec:
    mode: str
    value: int | float | tuple[int, int]
    label: str


@dataclass(frozen=True)
class CropBox:
    left: int
    top: int
    width: int
    height: int

    @property
    def pillow_box(self) -> tuple[int, int, int, int]:
        return (
            self.left,
            self.top,
            self.left + self.width,
            self.top + self.height,
        )


@dataclass(frozen=True)
class ProcessResult:
    input_path: Path
    output_path: Path
    original_size: tuple[int, int]
    final_size: tuple[int, int]
    original_bytes: int
    final_bytes: int | None
    dry_run: bool


def positive_int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise click.ClickException(f"{label} must be a whole number: {value}") from exc
    if parsed <= 0:
        raise click.ClickException(f"{label} must be greater than zero: {value}")
    return parsed


def parse_percent(value: str, label: str) -> float:
    cleaned = value.strip().removesuffix("%")
    try:
        parsed = float(cleaned)
    except ValueError as exc:
        raise click.ClickException(f"{label} must be a percentage: {value}") from exc
    if parsed <= 0:
        raise click.ClickException(f"{label} must be greater than zero: {value}")
    return parsed / 100


def parse_pair(value: str, label: str) -> tuple[int, int]:
    separator = "x" if "x" in value.lower() else ","
    parts = value.lower().split(separator)
    if len(parts) != 2:
        raise click.ClickException(f"{label} must look like WIDTHxHEIGHT")
    width = positive_int(parts[0], "width")
    height = positive_int(parts[1], "height")
    return width, height


def parse_resize_spec(
    resize: str | None,
    scale: str | None,
    used_input_option: bool,
) -> ResizeSpec | None:
    if resize and scale:
        raise click.ClickException("Use either --resize or --scale, not both.")
    if scale:
        return ResizeSpec("scale", parse_percent(scale, "scale"), scale)
    if not resize:
        return None

    cleaned = resize.strip().lower().replace(" ", "")
    if not cleaned:
        return None
    if cleaned.endswith("%"):
        return ResizeSpec("scale", parse_percent(cleaned, "resize"), cleaned)
    if "x" in cleaned or "," in cleaned:
        return ResizeSpec("box", parse_pair(cleaned, "resize"), cleaned)

    width = positive_int(cleaned, "resize")
    if used_input_option and width <= 100:
        return ResizeSpec("scale", width / 100, f"{width}%")
    return ResizeSpec("width", width, f"{width}px wide")


def parse_crop_box(crop: str | None) -> CropBox | None:
    if not crop:
        return None
    parts = crop.replace(" ", "").split(",")
    if len(parts) != 4:
        raise click.ClickException("crop must look like x,y,width,height")
    try:
        left, top, width, height = map(int, parts)
    except ValueError as exc:
        raise click.ClickException("crop values must be whole numbers") from exc
    if left < 0 or top < 0:
        raise click.ClickException("crop x and y must be zero or greater")
    if width <= 0 or height <= 0:
        raise click.ClickException("crop width and height must be greater than zero")
    return CropBox(left, top, width, height)


def normalize_format(format_name: str | None) -> str | None:
    if not format_name:
        return None
    return SUPPORTED_FORMATS[format_name.lower()]


def infer_format_from_suffix(path: Path) -> str | None:
    suffix = path.suffix.lower().lstrip(".")
    return SUPPORTED_FORMATS.get(suffix)


def format_extension(save_format: str) -> str:
    return FORMAT_EXTENSIONS.get(save_format, f".{save_format.lower()}")


def has_glob_magic(pattern: str | Path) -> bool:
    return glob.has_magic(str(pattern))


def expand_directory(path: Path, recursive: bool) -> list[Path]:
    iterator = path.rglob("*") if recursive else path.iterdir()
    return sorted(
        child
        for child in iterator
        if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS
    )


def resolve_input_files(
    positional_inputs: tuple[Path, ...],
    input_patterns: tuple[Path, ...],
    recursive: bool,
) -> list[Path]:
    patterns = [*positional_inputs, *input_patterns]
    if not patterns:
        raise click.ClickException("Provide at least one image path, directory, or --input pattern.")

    resolved: list[Path] = []
    missing: list[str] = []

    for pattern in patterns:
        pattern_text = str(pattern)
        if has_glob_magic(pattern):
            matches = [Path(match) for match in sorted(glob.glob(pattern_text))]
            if not matches:
                missing.append(pattern_text)
            for match in matches:
                if match.is_dir():
                    resolved.extend(expand_directory(match, recursive))
                elif match.is_file():
                    resolved.append(match)
            continue

        path = Path(pattern)
        if path.is_dir():
            resolved.extend(expand_directory(path, recursive))
        elif path.is_file():
            resolved.append(path)
        else:
            missing.append(pattern_text)

    unique_files: list[Path] = []
    seen: set[Path] = set()
    for file_path in resolved:
        normalized = file_path.resolve()
        if normalized not in seen:
            seen.add(normalized)
            unique_files.append(file_path)

    if missing and not unique_files:
        raise click.ClickException(f"No files matched: {', '.join(missing)}")
    if not unique_files:
        raise click.ClickException("No image files were found.")
    return unique_files


def resize_image(image: Image.Image, resize: ResizeSpec, fit: bool) -> Image.Image:
    if resize.mode == "width":
        width = int(resize.value)
        height = max(1, round(image.height * width / image.width))
        return image.resize((width, height), Image.Resampling.LANCZOS)
    if resize.mode == "scale":
        scale = float(resize.value)
        width = max(1, round(image.width * scale))
        height = max(1, round(image.height * scale))
        return image.resize((width, height), Image.Resampling.LANCZOS)
    if resize.mode == "box":
        width, height = resize.value
        if fit:
            resized = image.copy()
            resized.thumbnail((width, height), Image.Resampling.LANCZOS)
            return resized
        return image.resize((width, height), Image.Resampling.LANCZOS)
    raise click.ClickException(f"Unsupported resize mode: {resize.mode}")


def apply_edits(
    image: Image.Image,
    crop: CropBox | None,
    resize: ResizeSpec | None,
    fit: bool,
    rotate: float | None,
    brightness: float | None,
    contrast: float | None,
    blur: float | None,
    sharpen: bool,
    grayscale: bool,
) -> Image.Image:
    edited = image
    if crop:
        edited = edited.crop(crop.pillow_box)
    if resize:
        edited = resize_image(edited, resize, fit)
    if rotate is not None:
        edited = edited.rotate(rotate, expand=True)
    if grayscale:
        edited = edited.convert("L")
    if brightness is not None:
        edited = ImageEnhance.Brightness(edited).enhance(brightness)
    if contrast is not None:
        edited = ImageEnhance.Contrast(edited).enhance(contrast)
    if blur is not None:
        edited = edited.filter(ImageFilter.GaussianBlur(radius=blur))
    if sharpen:
        edited = edited.filter(ImageFilter.SHARPEN)
    return edited


def target_output_path(
    input_path: Path,
    output: Path | None,
    output_dir: Path | None,
    suffix: str,
    requested_format: str | None,
    input_count: int,
) -> Path:
    if output and input_count > 1:
        raise click.ClickException("Use --output only with one input; use --output-dir for batches.")

    extension = (
        format_extension(requested_format)
        if requested_format
        else input_path.suffix.lower()
    )

    if output:
        output_path = output
        if requested_format or not output_path.suffix:
            output_path = output_path.with_suffix(extension)
        return output_path

    if output_dir:
        return output_dir / f"{input_path.stem}{extension}"

    return input_path.with_name(f"{input_path.stem}{suffix}{extension}")


def prepare_for_save(image: Image.Image, save_format: str) -> Image.Image:
    if save_format in {"JPEG", "BMP"} and image.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", image.size, (255, 255, 255))
        alpha = image.getchannel("A")
        background.paste(image, mask=alpha)
        return background
    if save_format in {"JPEG", "BMP"} and image.mode not in {"RGB", "L"}:
        return image.convert("RGB")
    return image


def save_options(save_format: str, quality: int, compress: bool) -> dict[str, object]:
    options: dict[str, object] = {"format": save_format}
    if save_format in {"JPEG", "WEBP"}:
        options["quality"] = quality
        options["optimize"] = True
    elif save_format == "PNG":
        options["optimize"] = True
        if compress:
            options["compress_level"] = 9
    return options


def file_size_label(byte_count: int | None) -> str:
    if byte_count is None:
        return "not written"
    if byte_count < 1024:
        return f"{byte_count} B"
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count / (1024 * 1024):.2f} MB"


def compression_label(original_bytes: int, final_bytes: int | None) -> str:
    if final_bytes is None or original_bytes <= 0:
        return ""
    change = (1 - final_bytes / original_bytes) * 100
    if change > 0:
        return f" ({change:.1f}% smaller)"
    if change < 0:
        return f" ({abs(change):.1f}% larger)"
    return " (same size)"


def process_one_image(
    input_path: Path,
    output_path: Path,
    requested_format: str | None,
    resize: ResizeSpec | None,
    fit: bool,
    crop: CropBox | None,
    rotate: float | None,
    brightness: float | None,
    contrast: float | None,
    blur: float | None,
    sharpen: bool,
    grayscale: bool,
    quality: int,
    compress: bool,
    force: bool,
    dry_run: bool,
) -> ProcessResult:
    try:
        with Image.open(input_path) as opened:
            source_format = opened.format
            original_size = opened.size
            image = ImageOps.exif_transpose(opened).copy()
    except UnidentifiedImageError as exc:
        raise click.ClickException(f"{input_path} is not a recognized image file") from exc

    edited = apply_edits(
        image=image,
        crop=crop,
        resize=resize,
        fit=fit,
        rotate=rotate,
        brightness=brightness,
        contrast=contrast,
        blur=blur,
        sharpen=sharpen,
        grayscale=grayscale,
    )

    save_format = (
        requested_format
        or infer_format_from_suffix(output_path)
        or source_format
        or "PNG"
    )
    final_output_path = output_path
    if not final_output_path.suffix:
        final_output_path = final_output_path.with_suffix(format_extension(save_format))

    original_bytes = input_path.stat().st_size
    if final_output_path.exists() and not force and not dry_run:
        raise click.ClickException(
            f"{final_output_path} already exists; use --force to overwrite it."
        )

    if dry_run:
        return ProcessResult(
            input_path=input_path,
            output_path=final_output_path,
            original_size=original_size,
            final_size=edited.size,
            original_bytes=original_bytes,
            final_bytes=None,
            dry_run=True,
        )

    final_output_path.parent.mkdir(parents=True, exist_ok=True)
    image_to_save = prepare_for_save(edited, save_format)
    image_to_save.save(final_output_path, **save_options(save_format, quality, compress))

    return ProcessResult(
        input_path=input_path,
        output_path=final_output_path,
        original_size=original_size,
        final_size=image_to_save.size,
        original_bytes=original_bytes,
        final_bytes=final_output_path.stat().st_size,
        dry_run=False,
    )


def print_result(result: ProcessResult, quiet: bool) -> None:
    if quiet:
        click.echo(result.output_path)
        return

    prefix = "Would write" if result.dry_run else "Wrote"
    click.echo(f"{result.input_path} -> {result.output_path}")
    click.echo(
        f"  {prefix}: {result.final_size[0]}x{result.final_size[1]}, "
        f"{file_size_label(result.final_bytes)}"
        f"{compression_label(result.original_bytes, result.final_bytes)}"
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("input_paths", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--input",
    "input_patterns",
    multiple=True,
    type=click.Path(path_type=Path),
    help="Input file, directory, or glob pattern. Repeat to combine inputs.",
)
@click.option("--recursive", is_flag=True, help="Recurse when an input is a directory.")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file for one input.")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Output directory for batches.",
)
@click.option("--suffix", default="_processed", show_default=True, help="Suffix for single-file default output.")
@click.option(
    "--format",
    "-f",
    "format_name",
    type=click.Choice(sorted(SUPPORTED_FORMATS), case_sensitive=False),
    help="Output format.",
)
@click.option(
    "--resize",
    "-r",
    "resize_value",
    help="Resize to WIDTH, WIDTHxHEIGHT, WIDTH,HEIGHT, or 50%.",
)
@click.option("--scale", help="Scale by percentage, such as 50 or 50%.")
@click.option("--fit", is_flag=True, help="Fit inside WIDTHxHEIGHT instead of stretching.")
@click.option("--crop", help="Crop before resizing: x,y,width,height.")
@click.option("--rotate", type=float, help="Rotate degrees after resizing.")
@click.option("--brightness", type=click.FloatRange(0), help="Brightness factor, such as 0.8 or 1.2.")
@click.option("--contrast", type=click.FloatRange(0), help="Contrast factor, such as 0.8 or 1.2.")
@click.option("--blur", type=click.FloatRange(0), help="Gaussian blur radius.")
@click.option("--sharpen", is_flag=True, help="Apply a sharpen filter.")
@click.option("--grayscale", is_flag=True, help="Convert to grayscale.")
@click.option(
    "--quality",
    "-q",
    type=click.IntRange(1, 100),
    default=85,
    show_default=True,
    help="JPEG/WebP quality.",
)
@click.option("--compress", "-c", is_flag=True, help="Use stronger compression where supported.")
@click.option("--force", is_flag=True, help="Overwrite existing output files.")
@click.option("--dry-run", is_flag=True, help="Preview matched files and output paths.")
@click.option("--quiet", is_flag=True, help="Only print output paths for successful writes.")
@click.option("--verbose", "-v", is_flag=True, help="Print matched file count and summary.")
def main(
    input_paths: tuple[Path, ...],
    input_patterns: tuple[Path, ...],
    recursive: bool,
    output: Path | None,
    output_dir: Path | None,
    suffix: str,
    format_name: str | None,
    resize_value: str | None,
    scale: str | None,
    fit: bool,
    crop: str | None,
    rotate: float | None,
    brightness: float | None,
    contrast: float | None,
    blur: float | None,
    sharpen: bool,
    grayscale: bool,
    quality: int,
    compress: bool,
    force: bool,
    dry_run: bool,
    quiet: bool,
    verbose: bool,
) -> None:
    """Transform, convert and compress one image or a batch."""
    requested_format = normalize_format(format_name)
    resize = parse_resize_spec(resize_value, scale, used_input_option=bool(input_patterns))
    crop_box = parse_crop_box(crop)
    input_files = resolve_input_files(input_paths, input_patterns, recursive)

    if verbose and not quiet:
        mode = "dry run" if dry_run else "processing"
        click.echo(f"{len(input_files)} file(s) matched for {mode}.")

    successes = 0
    failures: list[str] = []

    for input_path in input_files:
        try:
            output_path = target_output_path(
                input_path=input_path,
                output=output,
                output_dir=output_dir,
                suffix=suffix,
                requested_format=requested_format,
                input_count=len(input_files),
            )
            result = process_one_image(
                input_path=input_path,
                output_path=output_path,
                requested_format=requested_format,
                resize=resize,
                fit=fit,
                crop=crop_box,
                rotate=rotate,
                brightness=brightness,
                contrast=contrast,
                blur=blur,
                sharpen=sharpen,
                grayscale=grayscale,
                quality=quality,
                compress=compress,
                force=force,
                dry_run=dry_run,
            )
            successes += 1
            print_result(result, quiet)
        except (OSError, click.ClickException) as exc:
            message = str(exc)
            failures.append(f"{input_path}: {message}")
            if not quiet:
                click.echo(f"Failed: {input_path}: {message}", err=True)

    if verbose and not quiet:
        action = "would be processed" if dry_run else "processed"
        click.echo(f"Done: {successes}/{len(input_files)} file(s) {action}.")

    if failures:
        raise click.ClickException(
            f"{len(failures)} of {len(input_files)} file(s) failed."
        )


if __name__ == "__main__":
    main()
