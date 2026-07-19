from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Iterable, Iterator, Sequence

DEFAULT_EXCLUDES = (".git", "node_modules", "dist", "build", "__pycache__")


def parse_exclude_patterns(patterns: str | Sequence[str] | None) -> list[str]:
    if patterns is None:
        return list(DEFAULT_EXCLUDES)

    if isinstance(patterns, str):
        raw_patterns = patterns.split(",")
    else:
        raw_patterns = list(patterns)

    cleaned = [p.strip() for p in raw_patterns if p and p.strip()]

    if not cleaned:
        return list(DEFAULT_EXCLUDES)

    merged = list(DEFAULT_EXCLUDES)
    merged.extend(cleaned)
    return merged


def _matches_pattern(rel_posix: str, parts: tuple[str, ...], pattern: str) -> bool:
    normalized = pattern.strip().strip("/")
    if not normalized:
        return False

    if fnmatch.fnmatch(rel_posix, normalized):
        return True

    if fnmatch.fnmatch(parts[-1], normalized):
        return True

    has_glob = any(ch in normalized for ch in "*?[]")
    if not has_glob:
        if normalized in parts:
            return True
        if rel_posix == normalized:
            return True
        if rel_posix.startswith(normalized + "/"):
            return True

    return False


def should_exclude(path: Path, root: Path, patterns: Sequence[str]) -> bool:
    rel_posix = path.relative_to(root).as_posix()
    parts = tuple(part for part in rel_posix.split("/") if part)

    for pattern in patterns:
        if _matches_pattern(rel_posix, parts, pattern):
            return True

    return False


def is_text_file(path: Path, sniff_bytes: int = 8192) -> bool:
    try:
        data = path.read_bytes()[:sniff_bytes]
    except OSError:
        return False

    if not data:
        return True

    if b"\x00" in data:
        return False

    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False

    return True


def walk_candidate_files(
    root: str | Path,
    exclude_patterns: str | Sequence[str] | None = None,
) -> Iterator[Path]:
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Root path does not exist: {root}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Root path is not a directory: {root}")

    patterns = parse_exclude_patterns(exclude_patterns)

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        current_dir = Path(dirpath)

        kept_dirs: list[str] = []
        for dirname in dirnames:
            child_dir = current_dir / dirname
            if should_exclude(child_dir, root_path, patterns):
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            candidate = current_dir / filename
            if should_exclude(candidate, root_path, patterns):
                continue
            if not is_text_file(candidate):
                continue
            yield candidate


def collect_candidate_files(
    root: str | Path,
    exclude_patterns: str | Sequence[str] | None = None,
    *,
    relative: bool = True,
) -> list[str]:
    files = list(walk_candidate_files(root, exclude_patterns=exclude_patterns))

    if relative:
        root_path = Path(root).resolve()
        return sorted(path.relative_to(root_path).as_posix() for path in files)

    return sorted(path.as_posix() for path in files)
