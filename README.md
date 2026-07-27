# todo-harvester

Scan a source tree for `TODO` / `FIXME` / `HACK` / `XXX` markers and produce a structured report.

## Install

### pipx (recommended)

```bash
pipx install .
```

After install:

```bash
todo-harvester --help
```

### Development install

```bash
python -m pip install -e .
```

## CLI overview

`todo-harvester` exposes two subcommands:

- `scan` — recursively scan files and extract marker comments.
- `diff` — compare current markers against a base git ref and report newly added markers.

Run help at any level:

```bash
todo-harvester --help
todo-harvester scan --help
todo-harvester diff --help
```

## `scan` subcommand

```bash
todo-harvester scan [root] [--exclude PATTERNS] [--absolute] [--tags TAGS] [--format {text,json,markdown}] [--no-dedup] [--blame] [--sort {path,age}] [--max N]
```

### Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `root` | positional path | `.` | Root directory to scan. |
| `--exclude` | comma-separated string | built-ins (`.git,node_modules,dist,build,__pycache__`) | Additional glob/path patterns to exclude. |
| `--absolute` | flag | `false` | Print absolute file paths instead of paths relative to `root`. |
| `--tags` | comma-separated string | `TODO,FIXME,HACK,XXX` | Restrict marker tags to match (case-insensitive). |
| `--format` | `text`, `json`, or `markdown` | `text` | Output format. |
| `--no-dedup` | flag | `false` | Disable duplicate collapsing (default behavior deduplicates markers with the same tag and normalized text). |
| `--blame` | flag | `false` | Add `author` + `date` metadata using `git blame --porcelain` for tracked files. |
| `--sort` | `path` or `age` | `path` | Sort by file/line (default) or by staleness (`age` = oldest blame date first). |
| `--max` | integer | unset | Exit with code `1` when total markers exceed `N` (useful for CI thresholds). |
| `-h`, `--help` | flag | n/a | Show command help and exit. |

## Examples

```bash
# Scan current directory, text output
todo-harvester scan

# Scan a specific folder
todo-harvester scan ./src

# Restrict tags
todo-harvester scan . --tags TODO,FIXME

# Exclude additional directories/files
todo-harvester scan . --exclude 'vendor,*.min.js,generated/*'

# Absolute paths
todo-harvester scan . --absolute

# JSON output
todo-harvester scan . --format json > markers.json

# Keep duplicate markers separate
todo-harvester scan . --format json --no-dedup

# Include git blame attribution (tracked files)
todo-harvester scan . --format json --blame

# Sort by staleness (oldest blamed lines first)
todo-harvester scan . --sort age --blame

# Fail CI if any marker exists
todo-harvester scan . --max 0

# Markdown report output
todo-harvester scan . --format markdown > marker-report.md

# Show markers newly introduced since origin/main
todo-harvester diff origin/main --format json
```

## `diff` subcommand

```bash
todo-harvester diff <ref> [root] [--exclude PATTERNS] [--absolute] [--tags TAGS] [--format {text,json,markdown}] [--no-dedup] [--blame] [--sort {path,age}]
```

`diff` scans the current working tree and compares it with marker output from the
same path at `<ref>`, then prints only markers that are newly introduced.

## Output formats

### Text (`--format text`)

Default text output is a grouped report:

- Header with total marker count
- Grouped sections by directory and file
- Stable marker line format (`path:line: TAG: message`) for grep/filters
- Duplicate markers (same tag + normalized text) are collapsed and include count/location metadata
- Summary footer with per-tag totals

Example:

```text
TODO Harvester Report

Total markers: 2

Grouped markers
[dir] src
[file] src/app.py
src/app.py:12: TODO: normalize user id
[file] src/db.py
src/db.py:8: FIXME: retry transaction

Summary by tag
FIXME: 1
TODO: 1
```

If marker text is empty, the line stays stable:

```text
path/to/file.py:12: TODO
```

### JSON (`--format json`)

Outputs a JSON array of marker objects.

#### Stable JSON schema

```json
[
  {
    "tag": "TODO",
    "text": "normalize user id",
    "file": "src/module/file.py",
    "line": 12,
    "count": 2,
    "locations": [
      {"file": "src/module/file.py", "line": 12},
      {"file": "src/module/other.py", "line": 44}
    ],
    "author": "Alice Example",
    "date": "2026-07-01"
  }
]
```

Field definitions:

- `tag` (`string`) — normalized uppercase marker tag.
- `text` (`string`) — marker text after the tag (may be empty).
- `file` (`string`) — representative file path (relative by default; absolute when `--absolute` is used).
- `line` (`integer`) — representative 1-based line number.
- `count` (`integer`) — number of occurrences represented by the record.
- `locations` (`array`) — all source occurrences as `{ "file": string, "line": integer }` entries.
- `author` (`string`, optional) — last commit author from `git blame` when `--blame` is enabled and the file is tracked.
- `date` (`string`, optional, `YYYY-MM-DD`) — blamed author date in UTC when `--blame` is available.

### Markdown (`--format markdown`)

Emits a headed digest suitable for docs/CI artifacts:

- Report title and total marker count
- Summary counts by tag
- Grouped marker list by file with line numbers

Example:

```markdown
# TODO Harvester Report

Total markers: **2**

## Summary by tag
- **FIXME**: 1
- **TODO**: 1

## Markers by file
### `pkg/a.py`
- L1 **TODO**: first
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Successful scan/diff output generation. |
| `1` | `scan --max N` threshold exceeded (marker count > `N`). |
| `2` | CLI usage/argument error, or git-ref resolution failure for `diff`. |

## Development

```bash
# Run tests
pytest -q
```

## Changelog

See [CHANGELOG.md](./CHANGELOG.md).
