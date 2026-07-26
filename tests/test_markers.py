from __future__ import annotations

import json
from pathlib import Path
import subprocess

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


def test_cli_scan_text_output_is_grouped_with_summary(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("# TODO: wire endpoint\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path)])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == [
        "TODO Harvester Report",
        "",
        "Total markers: 1",
        "",
        "Grouped markers",
        "[dir] pkg",
        "[file] pkg/mod.py",
        "pkg/mod.py:1: TODO: wire endpoint",
        "",
        "Summary by tag",
        "TODO: 1",
    ]


def test_cli_scan_json_output_schema_round_trip(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("# TODO: ship it\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path), "--format", "json"])
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 0
    assert payload == [
        {
            "tag": "TODO",
            "text": "ship it",
            "file": "pkg/mod.py",
            "line": 1,
            "count": 1,
            "locations": [{"file": "pkg/mod.py", "line": 1}],
        }
    ]
    assert set(payload[0]) == {"tag", "text", "file", "line", "count", "locations"}
    assert json.loads(json.dumps(payload)) == payload


def test_cli_scan_markdown_output(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("# TODO: first\n", encoding="utf-8")
    (tmp_path / "pkg" / "b.py").write_text("# FIXME: second\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path), "--format", "markdown"])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == [
        "# TODO Harvester Report",
        "",
        "Total markers: **2**",
        "",
        "## Summary by tag",
        "- **FIXME**: 1",
        "- **TODO**: 1",
        "",
        "## Markers by file",
        "### `pkg/a.py`",
        "- L1 **TODO**: first",
        "",
        "### `pkg/b.py`",
        "- L1 **FIXME**: second",
    ]


def test_cli_scan_text_output_groups_by_directory_and_file(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg" / "sub").mkdir(parents=True)
    (tmp_path / "pkg" / "a.py").write_text("# TODO: one\n# FIXME: two\n", encoding="utf-8")
    (tmp_path / "pkg" / "sub" / "b.py").write_text("# HACK: three\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path), "--format", "text"])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == [
        "TODO Harvester Report",
        "",
        "Total markers: 3",
        "",
        "Grouped markers",
        "[dir] pkg",
        "[file] pkg/a.py",
        "pkg/a.py:1: TODO: one",
        "pkg/a.py:2: FIXME: two",
        "[dir] pkg/sub",
        "[file] pkg/sub/b.py",
        "pkg/sub/b.py:1: HACK: three",
        "",
        "Summary by tag",
        "FIXME: 1",
        "HACK: 1",
        "TODO: 1",
    ]


def test_cli_scan_deduplicates_normalized_markers_by_default(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("# TODO: Fill In\n", encoding="utf-8")
    (tmp_path / "pkg" / "b.py").write_text("# TODO:  fill   in\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == [
        {
            "tag": "TODO",
            "text": "Fill In",
            "file": "pkg/a.py",
            "line": 1,
            "count": 2,
            "locations": [
                {"file": "pkg/a.py", "line": 1},
                {"file": "pkg/b.py", "line": 1},
            ],
        }
    ]


def test_cli_scan_no_dedup_keeps_duplicate_markers(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("# TODO: Fill In\n", encoding="utf-8")
    (tmp_path / "pkg" / "b.py").write_text("# TODO:  fill   in\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path), "--format", "json", "--no-dedup"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == [
        {
            "tag": "TODO",
            "text": "Fill In",
            "file": "pkg/a.py",
            "line": 1,
            "count": 1,
            "locations": [{"file": "pkg/a.py", "line": 1}],
        },
        {
            "tag": "TODO",
            "text": "fill   in",
            "file": "pkg/b.py",
            "line": 1,
            "count": 1,
            "locations": [{"file": "pkg/b.py", "line": 1}],
        },
    ]


def test_cli_scan_max_threshold_exits_nonzero_when_exceeded(tmp_path: Path, capsys) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("# TODO: one\n", encoding="utf-8")

    exit_code = cli(["scan", str(tmp_path), "--max", "0"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Total markers: 1" in output


def test_cli_scan_max_threshold_succeeds_when_within_limit(tmp_path: Path, capsys) -> None:
    exit_code = cli(["scan", str(tmp_path), "--max", "0"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Total markers: 0" in output


def test_cli_diff_lists_only_markers_added_since_ref(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)

    (repo / "pkg").mkdir()
    file_path = repo / "pkg" / "mod.py"
    file_path.write_text("# TODO: existing\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, capture_output=True, text=True)

    file_path.write_text("# TODO: existing\n# FIXME: newly added\n", encoding="utf-8")

    exit_code = cli(["diff", "HEAD", str(repo), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == [
        {
            "tag": "FIXME",
            "text": "newly added",
            "file": "pkg/mod.py",
            "line": 2,
            "count": 1,
            "locations": [{"file": "pkg/mod.py", "line": 2}],
        }
    ]
