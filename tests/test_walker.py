from __future__ import annotations

from pathlib import Path

from todo_harvester.cli import cli
from todo_harvester.walker import collect_candidate_files


def test_recursive_walk_yields_all_files(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "nested").mkdir()

    (tmp_path / "a.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "src" / "b.js").write_text("// TODO: test\n", encoding="utf-8")
    (tmp_path / "src" / "nested" / "c.sql").write_text("-- FIXME\n", encoding="utf-8")

    files = collect_candidate_files(tmp_path)

    assert files == ["a.py", "src/b.js", "src/nested/c.sql"]


def test_exclude_globs_skip_matching_paths(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "dist").mkdir()
    (tmp_path / ".git").mkdir()

    (tmp_path / "src" / "keep.py").write_text("# ok\n", encoding="utf-8")
    (tmp_path / "node_modules" / "skip.js").write_text("// skip\n", encoding="utf-8")
    (tmp_path / "dist" / "artifact.txt").write_text("skip\n", encoding="utf-8")
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")

    files = collect_candidate_files(tmp_path, exclude_patterns="node_modules,dist,.git")

    assert files == ["src/keep.py"]


def test_binary_and_undecodable_files_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()

    (tmp_path / "src" / "keep.py").write_text("# text\n", encoding="utf-8")
    (tmp_path / "src" / "binary.bin").write_bytes(b"\x00\x01\x02\x03")
    (tmp_path / "src" / "bad-encoding.txt").write_bytes(b"\xff\xfe\xfd")

    files = collect_candidate_files(tmp_path)

    assert files == ["src/keep.py"]


def test_cli_scan_prints_marker_records(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("# TODO\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path)])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == [
        "DIR|pkg",
        "FILE|pkg/mod.py",
        "MARKER|TODO|pkg/mod.py|1|",
        "SUMMARY",
        "TOTAL_MARKERS|1",
        "TAG_TOTAL|TODO|1",
    ]
