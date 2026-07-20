from __future__ import annotations

import json
from pathlib import Path

from todo_harvester.cli import cli
from todo_harvester.markers import scan_markers


def test_scan_detects_default_tags_across_comment_styles(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(
        "# TODO: python todo\n"
        "value = 1  # FIXME inline python fix\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "b.js").write_text(
        "// HACK: javascript workaround\n"
        "const x = 1; // XXX legacy path\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "c.c").write_text("/* TODO: c-style block */\n", encoding="utf-8")
    (tmp_path / "pkg" / "d.sql").write_text("-- FIXME: sql workaround\n", encoding="utf-8")
    (tmp_path / "pkg" / "e.html").write_text("<!-- HACK: html cleanup -->\n", encoding="utf-8")

    records = scan_markers(tmp_path)

    assert {(record.path, record.line, record.tag, record.text) for record in records} == {
        ("pkg/a.py", 1, "TODO", "python todo"),
        ("pkg/a.py", 2, "FIXME", "inline python fix"),
        ("pkg/b.js", 1, "HACK", "javascript workaround"),
        ("pkg/b.js", 2, "XXX", "legacy path"),
        ("pkg/c.c", 1, "TODO", "c-style block"),
        ("pkg/d.sql", 1, "FIXME", "sql workaround"),
        ("pkg/e.html", 1, "HACK", "html cleanup"),
    }


def test_scan_tags_filter_restricts_results(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "# TODO: keep me\n"
        "# FIXME: keep me too\n"
        "# HACK: should be filtered\n",
        encoding="utf-8",
    )

    records = scan_markers(tmp_path, tags="TODO,FIXME")

    assert [(record.tag, record.text) for record in records] == [
        ("TODO", "keep me"),
        ("FIXME", "keep me too"),
    ]


def test_cli_scan_outputs_structured_marker_lines(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("# TODO: wire endpoint\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path)])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == ["pkg/mod.py:1: TODO: wire endpoint"]


def test_cli_scan_json_output(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("# TODO: ship it\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path), "--format", "json"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert json.loads(output) == [
        {
            "tag": "TODO",
            "text": "ship it",
            "path": "pkg/mod.py",
            "line": 1,
        }
    ]
