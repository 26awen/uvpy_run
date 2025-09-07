#!/usr/bin/env python3
"""
图片转换工具 - uvpy.run工具
使用方法:
  uv run img-convert.py --input photo.jpg --format webp
  uv run img-convert.py --input *.png --resize 800x600
  uv run img-convert.py --input photo.jpg --compress 80
"""

import argparse
import sys
import os
import glob
from pathlib import Path

from PIL import Image
from PIL.ExifTags import ORIENTATION


def get_file_size_mb(file_path: str):
    """获取文件大小(MB)"""
    return os.path.getsize(file_path) / (1024 * 1024)


def fix_image_orientation(image: Image):
    """修复图片方向(基于EXIF数据)"""
    try:
        for orientation in ORIENTATION.keys():
            if orientation in image._getexif():
                if image._getexif()[orientation] == 3:
                    image = image.rotate(180, expand=True)
                elif image._getexif()[orientation] == 6:
                    image = image.rotate(270, expand=True)
                elif image._getexif()[orientation] == 8:
                    image = image.rotate(90, expand=True)
                break
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
):
    """转换单个图片"""
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return False

    try:
        # 打开图片
        with Image.open(input_path) as img:
            print(f"📂 处理: {input_path.name}")
            print(f"   原始尺寸: {img.size[0]}x{img.size[1]}")
            print(f"   原始格式: {img.format}")
            print(f"   原始大小: {get_file_size_mb(input_path):.2f}MB")

            # 修复图片方向
            img = fix_image_orientation(img)

            # 转换为RGB模式(适用于JPEG等格式)
            if (
                format_type
                and format_type.upper() in ["JPEG", "JPG"]
                and img.mode in ["RGBA", "P"]
            ):
                img = img.convert("RGB")

            # 调整尺寸
            if resize:
                if "x" in resize:
                    width, height = map(int, resize.split("x"))
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                    print(f"   调整尺寸: {width}x{height}")
                else:
                    # 按比例缩放
                    scale = int(resize)
                    original_size = img.size
                    new_size = tuple(int(dim * scale / 100) for dim in original_size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    print(f"   按比例缩放: {scale}% -> {new_size[0]}x{new_size[1]}")

            # 确定输出路径
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

            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存图片
            save_kwargs = {}
            if format_type:
                save_kwargs["format"] = format_type.upper()

            if format_type and format_type.upper() in ["JPEG", "JPG"] or compress:
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True

            img.save(output_path, **save_kwargs)

            # 显示结果
            print(f"   输出格式: {format_type or img.format}")
            print(f"   输出大小: {get_file_size_mb(output_path):.2f}MB")
            print(f"✅ 保存到: {output_path}")

            # 计算压缩率
            original_size = get_file_size_mb(input_path)
            new_size = get_file_size_mb(output_path)
            if original_size > 0:
                compression_ratio = ((original_size - new_size) / original_size) * 100
                if compression_ratio > 0:
                    print(f"📊 压缩率: {compression_ratio:.1f}%")

            print("-" * 50)
            return True

    except Exception as e:
        print(f"❌ 处理失败 {input_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="图片转换和压缩工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s --input photo.jpg --format webp              # 转换为WebP格式
  %(prog)s --input *.png --format jpeg --quality 80     # 批量转换PNG为JPEG
  %(prog)s --input large.jpg --resize 800x600           # 调整图片尺寸
  %(prog)s --input photo.jpg --resize 50                # 缩放到50%
  %(prog)s --input photo.jpg --compress 70              # 压缩图片
  %(prog)s --input images/*.jpg --output-dir converted/ # 批量处理到指定目录
        """,
    )

    parser.add_argument(
        "--input", "-i", required=True, help="输入图片路径 (支持通配符如 *.jpg)"
    )
    parser.add_argument("--output", "-o", help="输出文件路径 (单文件时)")
    parser.add_argument("--output-dir", help="输出目录 (批量处理时)")
    parser.add_argument(
        "--format",
        "-f",
        choices=["jpeg", "jpg", "png", "webp", "bmp", "tiff"],
        help="输出格式",
    )
    parser.add_argument("--resize", "-r", help="调整尺寸: WIDTHxHEIGHT 或百分比")
    parser.add_argument(
        "--quality", "-q", type=int, default=85, help="图片质量 1-100 (默认: 85)"
    )
    parser.add_argument("--compress", "-c", action="store_true", help="启用压缩优化")

    args = parser.parse_args()

    # 获取输入文件列表
    input_files = glob.glob(args.input)
    if not input_files:
        print(f"❌ 没有找到匹配的文件: {args.input}")
        sys.exit(1)

    print(f"🔍 找到 {len(input_files)} 个文件")
    print("=" * 50)

    success_count = 0

    for input_file in input_files:
        output_path = None

        if args.output and len(input_files) == 1:
            # 单文件输出到指定路径
            output_path = args.output
        elif args.output_dir:
            # 批量处理到指定目录
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
        ):
            success_count += 1

    print(f"🎉 处理完成! 成功: {success_count}/{len(input_files)}")


if __name__ == "__main__":
    main()
