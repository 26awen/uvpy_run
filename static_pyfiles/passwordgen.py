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
Generate secure passwords with customizable options

A password generator for daily account registration with configurable length,
character sets, and security options. Uses Python's cryptographic `secrets`
module and excludes ambiguous characters by default.

Version: 0.9.0
Category: Security
Author: UVPY.RUN

Usage Examples:
    uv run passwordgen.py
    uv run passwordgen.py -l 16 -c 3
    uv run passwordgen.py --no-symbols --length 12
    uv run passwordgen.py --quiet --count 1

Use It For:
    - Generating multiple account passwords at once
    - Avoiding ambiguous characters like 0, O, 1, and l by default
    - Creating passwords with or without symbols depending on site rules

Output:
    - Prints a compact policy summary and numbered password list by default
    - Use --quiet to print raw password values, one per line

Security Notes:
    - Uses Python's secrets-backed SystemRandom
    - Includes at least one lowercase letter, uppercase letter, and digit
    - Adds a symbol requirement unless --no-symbols is used
"""

import argparse
import secrets
import string
import sys


RANDOM = secrets.SystemRandom()
SYMBOLS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


def build_character_sets(
    include_symbols: bool = True, exclude_ambiguous: bool = True
) -> dict[str, str]:
    """
    Build the character sets used for password generation.

    Args:
        include_symbols: Whether to include special characters.
        exclude_ambiguous: Whether to exclude confusing characters like 0, O, 1, l.

    Returns:
        Mapping of class names to allowed characters.
    """
    character_sets = {
        "lowercase": string.ascii_lowercase,
        "uppercase": string.ascii_uppercase,
        "digits": string.digits,
    }

    if include_symbols:
        character_sets["symbols"] = SYMBOLS

    if exclude_ambiguous:
        character_sets["lowercase"] = remove_characters(
            character_sets["lowercase"], "lo"
        )
        character_sets["uppercase"] = remove_characters(
            character_sets["uppercase"], "IO"
        )
        character_sets["digits"] = remove_characters(character_sets["digits"], "01")
        if "symbols" in character_sets:
            character_sets["symbols"] = remove_characters(
                character_sets["symbols"], "|`"
            )

    return character_sets


def remove_characters(source: str, characters: str) -> str:
    """Return source without any of the characters listed in characters."""
    return "".join(character for character in source if character not in characters)


def generate_password(
    length: int = 12, include_symbols: bool = True, exclude_ambiguous: bool = True
) -> str:
    """
    Generate a random password with specified criteria.

    Args:
        length: Password length (default: 12)
        include_symbols: Whether to include special characters
        exclude_ambiguous: Whether to exclude confusing characters like 0, O, 1, l

    Returns:
        Generated password string
    """
    character_sets = build_character_sets(include_symbols, exclude_ambiguous)
    required_length = len(character_sets)
    if length < required_length:
        raise ValueError(f"Password length must be at least {required_length}")

    char_pool = "".join(character_sets.values())

    # Ensure at least one character from each required type.
    password: list[str] = []
    for characters in character_sets.values():
        password.append(RANDOM.choice(characters))

    # Fill remaining length with random characters
    remaining_length = length - len(password)
    for _ in range(remaining_length):
        password.append(RANDOM.choice(char_pool))

    # Shuffle the password to randomize position of required characters
    RANDOM.shuffle(password)

    return "".join(password)


def render_summary(
    count: int, length: int, include_symbols: bool, exclude_ambiguous: bool
) -> str:
    """Return a compact printable summary of the password policy."""
    character_sets = build_character_sets(include_symbols, exclude_ambiguous)
    classes = ", ".join(character_sets.keys())
    ambiguous = "excluded" if exclude_ambiguous else "allowed"
    symbols = "on" if include_symbols else "off"
    pool_size = sum(len(characters) for characters in character_sets.values())

    return "\n".join(
        [
            "Password Generator",
            "==================",
            "",
            "Settings",
            f"  length:     {length}",
            f"  count:      {count}",
            f"  symbols:    {symbols}",
            f"  ambiguous:  {ambiguous}",
            f"  classes:    {classes}",
            f"  pool size:  {pool_size} characters",
            "",
            "Passwords",
            "---------",
        ]
    )


def render_password_line(index: int, password: str, total: int) -> str:
    """Return one indexed password line with stable alignment."""
    index_width = len(str(total))
    return f"  {index:>{index_width}}  {password}"


def render_tips() -> str:
    """Return practical, low-noise password handling tips."""
    return "\n".join(
        [
            "",
            "Tips",
            "----",
            "  Store passwords in a password manager.",
            "  Use a different password for every account.",
            "  Enable two-factor authentication on important accounts.",
            "  Use --quiet when you only want the password values.",
        ]
    )


def fail(message: str) -> None:
    """Print a CLI validation error and exit with argparse-style status code 2."""
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(2)


def main() -> None:
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
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Print only generated passwords, one per line",
    )

    args = parser.parse_args()

    # Validate length
    min_length = 4 if not args.no_symbols else 3
    if args.length < min_length:
        fail(f"Password length must be at least {min_length}")
    if args.count <= 0:
        fail("Password count must be greater than 0")

    passwords = [
        generate_password(
            length=args.length,
            include_symbols=not args.no_symbols,
            exclude_ambiguous=not args.allow_ambiguous,
        )
        for _ in range(args.count)
    ]

    if args.quiet:
        print("\n".join(passwords))
        return

    print(
        render_summary(
            count=args.count,
            length=args.length,
            include_symbols=not args.no_symbols,
            exclude_ambiguous=not args.allow_ambiguous,
        )
    )
    for index, password in enumerate(passwords, 1):
        print(render_password_line(index, password, args.count))
    print(render_tips())


if __name__ == "__main__":
    main()
