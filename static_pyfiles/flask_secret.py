# /// script
# requires-python = ">=3.12"
# dependencies = []
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

"""
Generate secure secret keys for Flask applications

A cryptographically secure secret key generator for Flask web applications.
Produces hexadecimal keys suitable for session management and security.

Version: 1.0.0
Category: Security
Author: Config-Txt Project

Usage Examples:
    uv run flask_secret.py
"""

import secrets
import sys


def generate_secret_key(length: int = 32):
    """
    Generate a cryptographically secure secret key.

    Args:
        length (int): Length of the secret key in bytes. Default is 32.

    Returns:
        str: A hexadecimal string representation of the secret key.
    """
    try:
        # Generate random bytes and convert to hex string
        secret_bytes = secrets.token_bytes(length)
        secret_key = secret_bytes.hex()
        return secret_key
    except Exception as e:
        print(f"Error generating secret key: {e}")
        sys.exit(1)


def main():
    """Main function to generate and display the secret key."""
    try:
        # Generate a 32-byte (256-bit) secret key
        secret_key = generate_secret_key(32)

        print("Generated Flask Secret Key:")
        print(f"'{secret_key}'")
        print()
        print("Usage in Flask app:")
        print(f"app.config['SECRET_KEY'] = '{secret_key}'")
        print()
        print("Or set as environment variable:")
        print(f"export FLASK_SECRET_KEY='{secret_key}'")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
