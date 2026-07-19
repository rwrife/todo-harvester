from __future__ import annotations

import argparse
from typing import Sequence

from .markers import scan_markers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="todo-harvester",
        description="Scan directories for marker comments and related metadata.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Walk a directory recursively and extract TODO/FIXME/HACK/XXX markers.",
    )
    scan_parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory).",
    )
    scan_parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated glob patterns or path names to exclude.",
    )
    scan_parser.add_argument(
        "--absolute",
        action="store_true",
        help="Print absolute file paths instead of paths relative to root.",
    )
    scan_parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated marker tags to match (default: TODO,FIXME,HACK,XXX).",
    )

    return parser


def cli(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        markers = scan_markers(
            args.root,
            exclude_patterns=args.exclude,
            tags=args.tags,
            relative=not args.absolute,
        )
        for marker in markers:
            if marker.text:
                print(f"{marker.path}:{marker.line}: {marker.tag}: {marker.text}")
            else:
                print(f"{marker.path}:{marker.line}: {marker.tag}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def main() -> None:
    raise SystemExit(cli())


if __name__ == "__main__":
    main()
