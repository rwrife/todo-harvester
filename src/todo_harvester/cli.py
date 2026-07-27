from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
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
    scan_parser.add_argument(
        "--blame",
        action="store_true",
        help="Annotate markers with git blame author/date when available.",
    )
    scan_parser.add_argument(
        "--sort",
        choices=("path", "age"),
        default="path",
        help="Sort markers by path/line (default) or by oldest blame date first.",
    )
    scan_parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Fail with exit code 1 if total marker count exceeds this threshold.",
    )

    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare markers against a base git ref and report newly added markers.",
    )
    diff_parser.add_argument("ref", help="Base git ref to compare against (e.g. origin/main).")
    diff_parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory).",
    )
    diff_parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated glob patterns or path names to exclude.",
    )
    diff_parser.add_argument(
        "--absolute",
        action="store_true",
        help="Print absolute file paths instead of paths relative to root.",
    )
    diff_parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated marker tags to match (default: TODO,FIXME,HACK,XXX).",
    )
    diff_parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format (default: text).",
    )
    diff_parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disable duplicate marker collapsing (enabled by default).",
    )
    diff_parser.add_argument(
        "--blame",
        action="store_true",
        help="Annotate markers with git blame author/date when available.",
    )
    diff_parser.add_argument(
        "--sort",
        choices=("path", "age"),
        default="path",
        help="Sort markers by path/line (default) or by oldest blame date first.",
    )

    return parser


def _get_git_repo_context(root: str | Path) -> tuple[Path, str] | None:
    root_path = Path(root).resolve()
    repo_result = subprocess.run(
        ["git", "-C", str(root_path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if repo_result.returncode != 0:
        return None

    repo_root = Path(repo_result.stdout.strip()).resolve()
    try:
        relative_root = root_path.relative_to(repo_root).as_posix()
    except ValueError:
        return None

    if relative_root == ".":
        relative_root = ""

    return repo_root, relative_root


def _parse_blame_porcelain(output: str) -> tuple[str, str, int] | None:
    author: str | None = None
    authored_timestamp: int | None = None

    for line in output.splitlines():
        if line.startswith("author "):
            author = line.removeprefix("author ").strip()
        elif line.startswith("author-time "):
            try:
                authored_timestamp = int(line.removeprefix("author-time ").strip())
            except ValueError:
                authored_timestamp = None

        if author is not None and authored_timestamp is not None:
            break

    if author is None or authored_timestamp is None:
        return None

    authored_date = datetime.fromtimestamp(authored_timestamp, tz=timezone.utc).date().isoformat()
    return author, authored_date, authored_timestamp


def _with_git_blame(markers: list[MarkerRecord], root: str | Path) -> list[MarkerRecord]:
    if not markers:
        return markers

    context = _get_git_repo_context(root)
    if context is None:
        return markers

    repo_root, relative_root = context
    blame_cache: dict[tuple[str, int], tuple[str, str, int] | None] = {}
    enriched: list[MarkerRecord] = []

    for marker in markers:
        repo_relative_path = (
            Path(relative_root, marker.path).as_posix() if relative_root else Path(marker.path).as_posix()
        )
        cache_key = (repo_relative_path, marker.line)

        if cache_key not in blame_cache:
            blame_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "blame",
                    "--porcelain",
                    "-L",
                    f"{marker.line},{marker.line}",
                    "--",
                    repo_relative_path,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if blame_result.returncode != 0:
                blame_cache[cache_key] = None
            else:
                blame_cache[cache_key] = _parse_blame_porcelain(blame_result.stdout)

        blame = blame_cache[cache_key]
        if blame is None:
            enriched.append(marker)
            continue

        author, authored_date, authored_timestamp = blame
        enriched.append(
            MarkerRecord(
                tag=marker.tag,
                text=marker.text,
                path=marker.path,
                line=marker.line,
                count=marker.count,
                locations=marker.locations,
                author=author,
                authored_date=authored_date,
                authored_timestamp=authored_timestamp,
            )
        )

    return enriched


def _sort_markers(markers: list[MarkerRecord], sort_mode: str) -> list[MarkerRecord]:
    if sort_mode == "age":
        return sorted(
            markers,
            key=lambda item: (
                item.authored_timestamp is None,
                item.authored_timestamp if item.authored_timestamp is not None else 0,
                item.path,
                item.line,
                item.tag,
                item.text.casefold(),
            ),
        )

    return sorted(markers, key=lambda item: (item.path, item.line, item.tag, item.text.casefold()))


def _format_marker_line(marker: MarkerRecord) -> str:
    if marker.text:
        base = f"{marker.path}:{marker.line}: {marker.tag}: {marker.text}"
    else:
        base = f"{marker.path}:{marker.line}: {marker.tag}"

    metadata: list[str] = []
    if marker.count > 1:
        locations = ", ".join(f"{file_path}:{line_number}" for file_path, line_number in marker.locations)
        metadata.append(f"count={marker.count}")
        metadata.append(f"locations={locations}")

    if marker.author is not None:
        metadata.append(f"author={marker.author}")
    if marker.authored_date is not None:
        metadata.append(f"date={marker.authored_date}")

    if metadata:
        return f"{base} [{'; '.join(metadata)}]"

    return base


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

                metadata_notes: list[str] = []
                if marker.count > 1:
                    locations = ", ".join(
                        f"{location_path}:{location_line}"
                        for location_path, location_line in marker.locations
                    )
                    metadata_notes.append(f"x{marker.count}; locations: {locations}")

                if marker.author is not None:
                    metadata_notes.append(f"author: {marker.author}")
                if marker.authored_date is not None:
                    metadata_notes.append(f"date: {marker.authored_date}")

                if metadata_notes:
                    line = f"{line} _({'; '.join(metadata_notes)})_"

                lines.append(line)
            lines.append("")
    else:
        lines.append("- _No markers found._")

    return "\n".join(lines).rstrip()


def _print_markers(markers: list[MarkerRecord], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps([marker.as_json_dict() for marker in markers], indent=2))
        return

    if output_format == "markdown":
        print(_render_markdown(markers))
        return

    print(_render_grouped_text(markers))


def _with_absolute_paths(markers: list[MarkerRecord], root: str | Path) -> list[MarkerRecord]:
    root_path = Path(root).resolve()
    absolute_markers: list[MarkerRecord] = []

    for marker in markers:
        absolute_locations = tuple(
            ((root_path / file_path).resolve().as_posix(), line_number)
            for file_path, line_number in marker.locations
        )
        absolute_markers.append(
            MarkerRecord(
                tag=marker.tag,
                text=marker.text,
                path=absolute_locations[0][0],
                line=absolute_locations[0][1],
                count=marker.count,
                locations=absolute_locations,
                author=marker.author,
                authored_date=marker.authored_date,
                authored_timestamp=marker.authored_timestamp,
            )
        )

    return absolute_markers


def _normalize_for_compare(text: str) -> str:
    return " ".join(text.casefold().split())


def _marker_diff_key(marker: MarkerRecord) -> tuple[str, int, str, str]:
    return (marker.path, marker.line, marker.tag, _normalize_for_compare(marker.text))


def _scan_markers_at_git_ref(
    ref: str,
    root: str | Path,
    *,
    exclude_patterns: str | Sequence[str] | None,
    tags: str | Sequence[str] | None,
) -> list[MarkerRecord]:
    root_path = Path(root).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise RuntimeError(f"root path does not exist or is not a directory: {root}")

    repo_result = subprocess.run(
        ["git", "-C", str(root_path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if repo_result.returncode != 0:
        error = repo_result.stderr.strip() or repo_result.stdout.strip() or "not a git repository"
        raise RuntimeError(error)

    repo_root = Path(repo_result.stdout.strip()).resolve()
    try:
        relative_root = root_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"root path is outside repository: {root_path}") from exc

    if relative_root == ".":
        relative_root = ""

    archive_cmd = ["git", "-C", str(repo_root), "archive", "--format=tar", ref]
    if relative_root:
        archive_cmd.append(relative_root)

    archive_result = subprocess.run(archive_cmd, capture_output=True, check=False)
    if archive_result.returncode != 0:
        error = archive_result.stderr.decode("utf-8", errors="replace").strip() or "unknown git error"
        raise RuntimeError(f"unable to read ref '{ref}': {error}")

    with tempfile.TemporaryDirectory(prefix="todo-harvester-ref-") as tmp_dir:
        extract_root = Path(tmp_dir) / "tree"
        extract_root.mkdir(parents=True, exist_ok=True)

        with tarfile.open(fileobj=io.BytesIO(archive_result.stdout), mode="r:") as archive:
            archive.extractall(extract_root)

        scan_root = extract_root / relative_root if relative_root else extract_root
        if not scan_root.exists():
            return []

        return scan_markers(scan_root, exclude_patterns=exclude_patterns, tags=tags, relative=True)


def cli(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        if args.max is not None and args.max < 0:
            print("error: --max must be >= 0")
            return 2

        markers = scan_markers(
            args.root,
            exclude_patterns=args.exclude,
            tags=args.tags,
            relative=True,
        )

        if not args.no_dedup:
            markers = deduplicate_markers(markers)

        if args.blame or args.sort == "age":
            markers = _with_git_blame(markers, args.root)

        markers = _sort_markers(markers, args.sort)

        if args.absolute:
            markers = _with_absolute_paths(markers, args.root)

        _print_markers(markers, args.format)

        if args.max is not None:
            total_markers = sum(marker.count for marker in markers)
            if total_markers > args.max:
                return 1

        return 0

    if args.command == "diff":
        current_markers = scan_markers(
            args.root,
            exclude_patterns=args.exclude,
            tags=args.tags,
            relative=True,
        )

        try:
            base_markers = _scan_markers_at_git_ref(
                args.ref,
                args.root,
                exclude_patterns=args.exclude,
                tags=args.tags,
            )
        except RuntimeError as exc:
            print(f"error: {exc}")
            return 2

        base_keys = {_marker_diff_key(marker) for marker in base_markers}
        added_markers = [marker for marker in current_markers if _marker_diff_key(marker) not in base_keys]

        if not args.no_dedup:
            added_markers = deduplicate_markers(added_markers)

        if args.blame or args.sort == "age":
            added_markers = _with_git_blame(added_markers, args.root)

        added_markers = _sort_markers(added_markers, args.sort)

        if args.absolute:
            added_markers = _with_absolute_paths(added_markers, args.root)

        _print_markers(added_markers, args.format)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def main() -> None:
    raise SystemExit(cli())


if __name__ == "__main__":
    main()
