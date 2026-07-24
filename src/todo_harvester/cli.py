from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from typing import Iterable, Sequence

from .markers import MarkerRecord, scan_markers


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
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format (default: text).",
    )

    return parser


def _iter_text_lines(markers: Iterable[MarkerRecord]) -> Iterable[str]:
    for marker in markers:
        if marker.text:
            yield f"{marker.path}:{marker.line}: {marker.tag}: {marker.text}"
        else:
            yield f"{marker.path}:{marker.line}: {marker.tag}"


def _render_markdown(markers: list[MarkerRecord]) -> str:
    lines: list[str] = ["# TODO Harvester Report", "", f"Total markers: **{len(markers)}**", ""]

    lines.append("## Summary by tag")
    if markers:
        counts = Counter(marker.tag for marker in markers)
        for tag in sorted(counts):
            lines.append(f"- **{tag}**: {counts[tag]}")
    else:
        lines.append("- _No markers found._")

    lines.append("")
    lines.append("## Markers by file")
    if markers:
        grouped: defaultdict[str, list[MarkerRecord]] = defaultdict(list)
        for marker in markers:
            grouped[marker.path].append(marker)

        for file_path in sorted(grouped):
            lines.append(f"### `{file_path}`")
            for marker in sorted(grouped[file_path], key=lambda item: (item.line, item.tag, item.text)):
                if marker.text:
                    lines.append(f"- L{marker.line} **{marker.tag}**: {marker.text}")
                else:
                    lines.append(f"- L{marker.line} **{marker.tag}**")
            lines.append("")
    else:
        lines.append("- _No markers found._")

    return "\n".join(lines).rstrip()


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
            print(json.dumps([marker.as_json_dict() for marker in markers], indent=2))
            return 0

        if args.format == "markdown":
            print(_render_markdown(markers))
            return 0

        for line in _iter_text_lines(markers):
            print(line)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def main() -> None:
    raise SystemExit(cli())


if __name__ == "__main__":
    main()
