from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Sequence

from .markers import MarkerRecord, scan_markers


def _directory_for(path: str) -> str:
    parent = Path(path).parent.as_posix()
    return "." if parent in ("", ".") else parent


def _marker_sort_key(marker: MarkerRecord) -> tuple[str, str, int, str, str]:
    return (
        _directory_for(marker.path),
        marker.path,
        marker.line,
        marker.tag,
        marker.text,
    )


def format_text_report(markers: Sequence[MarkerRecord]) -> list[str]:
    sorted_markers = sorted(markers, key=_marker_sort_key)
    counts = Counter(marker.tag for marker in sorted_markers)

    lines: list[str] = []
    current_directory: str | None = None
    current_file: str | None = None

    for marker in sorted_markers:
        directory = _directory_for(marker.path)
        if directory != current_directory:
            lines.append(f"DIR|{directory}")
            current_directory = directory
            current_file = None

        if marker.path != current_file:
            lines.append(f"FILE|{marker.path}")
            current_file = marker.path

        lines.append(
            f"MARKER|{marker.tag}|{marker.path}|{marker.line}|{marker.text}"
        )

    lines.append("SUMMARY")
    lines.append(f"TOTAL_MARKERS|{len(sorted_markers)}")
    for tag in sorted(counts):
        lines.append(f"TAG_TOTAL|{tag}|{counts[tag]}")

    return lines


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
    scan_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
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

        if args.format == "json":
            print(json.dumps([marker.as_dict() for marker in markers], indent=2))
            return 0

        for line in format_text_report(markers):
            print(line)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def main() -> None:
    raise SystemExit(cli())


if __name__ == "__main__":
    main()
