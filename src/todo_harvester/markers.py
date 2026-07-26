from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Sequence

from .walker import walk_candidate_files

DEFAULT_TAGS: tuple[str, ...] = ("TODO", "FIXME", "HACK", "XXX")


@dataclass(frozen=True, slots=True)
class MarkerRecord:
    tag: str
    text: str
    path: str
    line: int
    count: int = 1
    locations: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("count must be >= 1")
        if not self.locations:
            object.__setattr__(self, "locations", ((self.path, self.line),))

    def as_dict(self) -> dict[str, str | int | list[dict[str, str | int]]]:
        return {
            "tag": self.tag,
            "text": self.text,
            "path": self.path,
            "line": self.line,
            "count": self.count,
            "locations": [
                {"file": file_path, "line": line_number}
                for file_path, line_number in self.locations
            ],
        }

    def as_json_dict(self) -> dict[str, str | int | list[dict[str, str | int]]]:
        return {
            "tag": self.tag,
            "text": self.text,
            "file": self.path,
            "line": self.line,
            "count": self.count,
            "locations": [
                {"file": file_path, "line": line_number}
                for file_path, line_number in self.locations
            ],
        }


def parse_tags(tags: str | Sequence[str] | None) -> list[str]:
    if tags is None:
        return list(DEFAULT_TAGS)

    if isinstance(tags, str):
        raw_tags = tags.split(",")
    else:
        raw_tags = list(tags)

    cleaned = [tag.strip().upper() for tag in raw_tags if tag and tag.strip()]
    if not cleaned:
        return list(DEFAULT_TAGS)

    unique_tags: list[str] = []
    seen: set[str] = set()
    for tag in cleaned:
        if tag in seen:
            continue
        unique_tags.append(tag)
        seen.add(tag)

    return unique_tags


def build_marker_regex(tags: Sequence[str]) -> re.Pattern[str]:
    escaped_tags = "|".join(re.escape(tag) for tag in tags)
    return re.compile(
        rf"(?P<prefix>#|//|/\*+|--|<!--)\s*(?P<tag>{escaped_tags})\b(?P<text>.*)",
        flags=re.IGNORECASE,
    )


def _normalize_marker_text(prefix: str, text: str) -> str:
    normalized = text.strip()

    if normalized.startswith(":"):
        normalized = normalized[1:].lstrip()
    elif normalized.startswith("-"):
        normalized = normalized[1:].lstrip()

    if prefix.startswith("/*"):
        normalized = re.sub(r"\s*\*/\s*$", "", normalized)
    elif prefix == "<!--":
        normalized = re.sub(r"\s*-->\s*$", "", normalized)
    else:
        normalized = re.sub(r"\s*(?:\*/|-->)\s*$", "", normalized)

    return normalized.strip()


def _extract_marker_from_line(
    line_text: str,
    *,
    marker_regex: re.Pattern[str],
) -> tuple[str, str] | None:
    match = marker_regex.search(line_text)
    if not match:
        return None

    tag = match.group("tag").upper()
    prefix = match.group("prefix")
    text = _normalize_marker_text(prefix, match.group("text") or "")
    return tag, text


def _normalize_for_dedup(text: str) -> str:
    return " ".join(text.casefold().split())


def deduplicate_markers(markers: Sequence[MarkerRecord]) -> list[MarkerRecord]:
    grouped: dict[tuple[str, str], list[MarkerRecord]] = {}

    for marker in markers:
        key = (marker.tag, _normalize_for_dedup(marker.text))
        grouped.setdefault(key, []).append(marker)

    deduped: list[MarkerRecord] = []
    for duplicate_set in grouped.values():
        ordered_duplicates = sorted(duplicate_set, key=lambda item: (item.path, item.line))
        representative = ordered_duplicates[0]
        ordered_locations = tuple((item.path, item.line) for item in ordered_duplicates)
        deduped.append(
            MarkerRecord(
                tag=representative.tag,
                text=representative.text,
                path=ordered_locations[0][0],
                line=ordered_locations[0][1],
                count=len(duplicate_set),
                locations=ordered_locations,
            )
        )

    return sorted(deduped, key=lambda item: (item.path, item.line, item.tag, item.text.casefold()))


def scan_markers(
    root: str | Path,
    *,
    exclude_patterns: str | Sequence[str] | None = None,
    tags: str | Sequence[str] | None = None,
    relative: bool = True,
) -> list[MarkerRecord]:
    root_path = Path(root).resolve()
    marker_regex = build_marker_regex(parse_tags(tags))

    records: list[MarkerRecord] = []
    for candidate in walk_candidate_files(root_path, exclude_patterns=exclude_patterns):
        display_path = (
            candidate.relative_to(root_path).as_posix() if relative else candidate.as_posix()
        )

        try:
            with candidate.open("r", encoding="utf-8") as handle:
                for line_number, line_text in enumerate(handle, start=1):
                    marker = _extract_marker_from_line(
                        line_text,
                        marker_regex=marker_regex,
                    )
                    if marker is None:
                        continue

                    tag, text = marker
                    records.append(
                        MarkerRecord(
                            tag=tag,
                            text=text,
                            path=display_path,
                            line=line_number,
                        )
                    )
        except OSError:
            continue

    return records
