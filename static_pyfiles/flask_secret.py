# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""
Generate a secure secret key for Flask applications.
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
