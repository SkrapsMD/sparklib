"""
CLI entry point for sparklib.

Usage:
    python -m sparklib.cli metadata /path/to/scripts
"""

import argparse
from pathlib import Path

from .utils.management.core import metadata_dir, find


def main():
    parser = argparse.ArgumentParser(prog="sparklib", description="sparklib CLI tools")
    subparsers = parser.add_subparsers(dest="command")

    # metadata subcommand
    meta_parser = subparsers.add_parser("metadata", help="Extract script metadata from a directory")
    meta_parser.add_argument("path", type=str, help="Directory containing .py scripts")

    args = parser.parse_args()

    if args.command == "metadata":
        target = Path(args.path)
        if not target.exists():
            target = find(Path.cwd(), args.path.strip("/"))
            if target is None:
                print(f"Error: Could not find directory '{args.path}'")
                return
        metadata_dir(target)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
