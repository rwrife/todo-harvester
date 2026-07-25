from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Iterable, Sequence

from .markers import MarkerRecord, deduplicate_markers, scan_markers


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
    scan_parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disable duplicate marker collapsing (enabled by default).",
    )

    return parser


def _format_marker_line(marker: MarkerRecord) -> str:
    if marker.text:
        base = f"{marker.path}:{marker.line}: {marker.tag}: {marker.text}"
    else:
        base = f"{marker.path}:{marker.line}: {marker.tag}"

    if marker.count <= 1:
        return base

    locations = ", ".join(f"{file_path}:{line_number}" for file_path, line_number in marker.locations)
    return f"{base} [count={marker.count}; locations={locations}]"


def _iter_text_lines(markers: Iterable[MarkerRecord]) -> Iterable[str]:
    for marker in markers:
        yield _format_marker_line(marker)


def _render_grouped_text(markers: list[MarkerRecord]) -> str:
    total_markers = sum(marker.count for marker in markers)
    lines: list[str] = ["TODO Harvester Report", "", f"Total markers: {total_markers}", ""]

    lines.append("Grouped markers")
    if markers:
        grouped: defaultdict[str, defaultdict[str, list[MarkerRecord]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for marker in markers:
            directory = Path(marker.path).parent.as_posix() or "."
            grouped[directory][marker.path].append(marker)

        for directory in sorted(grouped):
            lines.append(f"[dir] {directory}")
            for file_path in sorted(grouped[directory]):
                lines.append(f"[file] {file_path}")
                for marker in sorted(
                    grouped[directory][file_path], key=lambda item: (item.line, item.tag, item.text)
                ):
                    lines.append(_format_marker_line(marker))
        lines.append("")
    else:
        lines.append("No markers found.")
        lines.append("")

    lines.append("Summary by tag")
    if markers:
        counts = Counter()
        for marker in markers:
            counts[marker.tag] += marker.count
        for tag in sorted(counts):
            lines.append(f"{tag}: {counts[tag]}")
    else:
        lines.append("(none)")

    return "\n".join(lines).rstrip()


def _render_markdown(markers: list[MarkerRecord]) -> str:
    total_markers = sum(marker.count for marker in markers)
    lines: list[str] = ["# TODO Harvester Report", "", f"Total markers: **{total_markers}**", ""]

    lines.append("## Summary by tag")
    if markers:
        counts = Counter()
        for marker in markers:
            counts[marker.tag] += marker.count
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
                    line = f"- L{marker.line} **{marker.tag}**: {marker.text}"
                else:
                    line = f"- L{marker.line} **{marker.tag}**"

                if marker.count > 1:
                    locations = ", ".join(
                        f"{location_path}:{location_line}"
                        for location_path, location_line in marker.locations
                    )
                    line = f"{line} _(x{marker.count}; locations: {locations})_"

                lines.append(line)
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

        if not args.no_dedup:
            markers = deduplicate_markers(markers)

        if args.format == "json":
            print(json.dumps([marker.as_json_dict() for marker in markers], indent=2))
            return 0

        if args.format == "markdown":
            print(_render_markdown(markers))
            return 0

        print(_render_grouped_text(markers))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def main() -> None:
    raise SystemExit(cli())


if __name__ == "__main__":
    main()
