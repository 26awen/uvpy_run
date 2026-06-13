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
Generate secure secrets for Flask and other Python apps

A cryptographically secure secret generator for Flask session keys, environment
variables, API tokens and other application secrets.

Version: 0.4.0
Category: Security
Author: UVPY.RUN

Usage Examples:
    uv run flask_secret.py
    uv run flask_secret.py --bytes 48 --format urlsafe
    uv run flask_secret.py --env-name FLASK_SECRET --quiet

Use It For:
    - Creating Flask SECRET_KEY values
    - Generating environment variable secrets for Python apps
    - Producing hex, URL-safe, or Base64-style tokens from secure random bytes

Output:
    - Prints a generated secret and example Flask/environment usage
    - Use --quiet when you only want the raw secret for scripting
    - Refuses very short secrets that are not suitable for app configuration
"""

import argparse
import base64
import secrets
import sys


def generate_secret(byte_count: int = 32, output_format: str = "hex") -> str:
    """
    Generate a cryptographically secure secret.

    Args:
        byte_count: Number of random bytes to generate.
        output_format: Output encoding: hex, urlsafe or base64.

    Returns:
        Encoded secret string.
    """
    if output_format == "hex":
        return secrets.token_hex(byte_count)
    if output_format == "urlsafe":
        return secrets.token_urlsafe(byte_count)
    if output_format == "base64":
        secret_bytes = secrets.token_bytes(byte_count)
        return base64.urlsafe_b64encode(secret_bytes).decode("ascii").rstrip("=")

    raise ValueError(f"Unsupported output format: {output_format}")


def main() -> None:
    """Parse CLI options and display the generated secret."""
    parser = argparse.ArgumentParser(
        description="Generate cryptographically secure application secrets."
    )
    parser.add_argument(
        "--bytes",
        dest="byte_count",
        type=int,
        default=32,
        help="Number of random bytes before encoding (default: 32).",
    )
    parser.add_argument(
        "--format",
        choices=["hex", "urlsafe", "base64"],
        default="hex",
        help="Output encoding (default: hex).",
    )
    parser.add_argument(
        "--env-name",
        default="FLASK_SECRET_KEY",
        help="Environment variable name shown in the example output.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Print only the generated secret.",
    )

    args = parser.parse_args()

    if args.byte_count < 16:
        print("Error: --bytes must be at least 16 for application secrets.", file=sys.stderr)
        sys.exit(2)

    try:
        secret = generate_secret(args.byte_count, args.format)

        if args.quiet:
            print(secret)
            return

        print("Generated Secret:")
        print(secret)
        print()
        print("Usage in a Flask app:")
        print(f"app.config['SECRET_KEY'] = '{secret}'")
        print()
        print("Or set as an environment variable:")
        print(f"export {args.env_name}='{secret}'")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
