"""
CLI entry point for sparklib.

Usage:
    python -m sparklib.cli metadata /path/to/scripts
"""

import argparse
from pathlib import Path

from .utils.management.core import metadata_dir, find
from .codebook import build_codebook


def main():
    parser = argparse.ArgumentParser(prog="sparklib", description="sparklib CLI tools")
    subparsers = parser.add_subparsers(dest="command")

    # metadata subcommand
    meta_parser = subparsers.add_parser("metadata", help="Extract script metadata from a directory")
    meta_parser.add_argument("path", type=str, help="Directory containing .py scripts")

    # codebook subcommand
    cb_parser = subparsers.add_parser("codebook", help="Generate a codebook document for a dataset")
    cb_parser.add_argument("data", type=str, help="Path to the dataset to document")
    cb_parser.add_argument("-o", "--output", type=str, default=None, help="Output path for the rendered codebook")

    args = parser.parse_args()

    if args.command == "metadata":
        target = Path(args.path)
        if not target.exists():
            target = find(Path.cwd(), args.path.strip("/"))
            if target is None:
                print(f"Error: Could not find directory '{args.path}'")
                return
        metadata_dir(target)
    elif args.command == "codebook":
        build_codebook(args.data, output_path=args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
