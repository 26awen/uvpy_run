# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""
Password Generator for Daily Account Registration
A simple script to generate secure passwords with customizable options.
"""

import random
import string
import argparse


def generate_password(
    length: int = 12, include_symbols: bool = True, exclude_ambiguous: bool = True
):
    """
    Generate a random password with specified criteria.

    Args:
        length: Password length (default: 12)
        include_symbols: Whether to include special characters
        exclude_ambiguous: Whether to exclude confusing characters like 0, O, 1, l

    Returns:
        Generated password string
    """
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Remove ambiguous characters if requested
    if exclude_ambiguous:
        lowercase = lowercase.replace("l", "").replace("o", "")
        uppercase = uppercase.replace("I", "").replace("O", "")
        digits = digits.replace("0", "").replace("1", "")
        symbols = symbols.replace("|", "").replace("`", "")

    # Build character pool
    char_pool = lowercase + uppercase + digits
    if include_symbols:
        char_pool += symbols

    # Ensure at least one character from each required type
    password: list[str] = []
    password.append(random.choice(lowercase))
    password.append(random.choice(uppercase))
    password.append(random.choice(digits))

    if include_symbols:
        password.append(random.choice(symbols))

    # Fill remaining length with random characters
    remaining_length = length - len(password)
    for _ in range(remaining_length):
        password.append(random.choice(char_pool))

    # Shuffle the password to randomize position of required characters
    random.shuffle(password)

    return "".join(password)


def main():
    parser = argparse.ArgumentParser(
        description="Generate secure passwords for account registration"
    )
    parser.add_argument(
        "-l", "--length", type=int, default=12, help="Password length (default: 12)"
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=5,
        help="Number of passwords to generate (default: 5)",
    )
    parser.add_argument(
        "--no-symbols", action="store_true", help="Exclude special characters"
    )
    parser.add_argument(
        "--allow-ambiguous",
        action="store_true",
        help="Allow confusing characters like 0, O, 1, l",
    )

    args = parser.parse_args()

    # Validate length
    min_length = 4 if not args.no_symbols else 3
    if args.length < min_length:
        print(f"Error: Password length must be at least {min_length}")
        return

    print(f"Generating {args.count} password(s) with {args.length} characters:")
    print("-" * 50)

    for i in range(args.count):
        password = generate_password(
            length=args.length,
            include_symbols=not args.no_symbols,
            exclude_ambiguous=not args.allow_ambiguous,
        )
        print(f"{i + 1:2d}. {password}")

    print("-" * 50)
    print("Tips for strong passwords:")
    print("- Use different passwords for different accounts")
    print("- Consider using a password manager")
    print("- Enable two-factor authentication when available")


if __name__ == "__main__":
    main()
