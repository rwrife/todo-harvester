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

`todo-harvester` currently exposes one subcommand:

- `scan` — recursively scan files and extract marker comments.

Run help at any level:

```bash
todo-harvester --help
todo-harvester scan --help
```

## `scan` subcommand

```bash
todo-harvester scan [root] [--exclude PATTERNS] [--absolute] [--tags TAGS] [--format {text,json,markdown}]
```

### Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `root` | positional path | `.` | Root directory to scan. |
| `--exclude` | comma-separated string | built-ins (`.git,node_modules,dist,build,__pycache__`) | Additional glob/path patterns to exclude. |
| `--absolute` | flag | `false` | Print absolute file paths instead of paths relative to `root`. |
| `--tags` | comma-separated string | `TODO,FIXME,HACK,XXX` | Restrict marker tags to match (case-insensitive). |
| `--format` | `text`, `json`, or `markdown` | `text` | Output format. |
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

# Markdown report output
todo-harvester scan . --format markdown > marker-report.md
```

## Output formats

### Text (`--format text`)

One marker per line:

```text
path/to/file.py:12: TODO: normalize user id
```

If marker text is empty:

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
    "count": 1
  }
]
```

Field definitions:

- `tag` (`string`) — normalized uppercase marker tag.
- `text` (`string`) — marker text after the tag (may be empty).
- `file` (`string`) — file path (relative by default; absolute when `--absolute` is used).
- `line` (`integer`) — 1-based line number.
- `count` (`integer`) — number of occurrences represented by the record (currently `1` per marker).

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
| `0` | Successful scan and output generation. |
| `2` | CLI usage/argument error (argparse). |

## Development

```bash
# Run tests
pytest -q
```

## Changelog

See [CHANGELOG.md](./CHANGELOG.md).
