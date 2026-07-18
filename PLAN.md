# PLAN — todo-harvester

## Scope

A single self-contained CLI that:
- Recursively walks a directory tree (respecting ignore patterns).
- Extracts marker comments (`TODO`, `FIXME`, `HACK`, `XXX`, plus user-defined tags).
- Records file path, line number, tag, and the marker text.
- Optionally attributes each marker to an author + date via `git blame`.
- Deduplicates near-identical markers.
- Emits reports in plain text, Markdown, and JSON.
- Provides CI affordances: a `--max` threshold and a `diff` subcommand against a base ref.

## Tech approach

- **Language:** Python 3 (stdlib-first; no heavy deps for the core scanner).
- **Scanning:** `os.walk` + per-line regex. Language-agnostic comment detection covering
  `#`, `//`, `/* */`, `--`, and `<!-- -->` styles.
- **Ignore rules:** honor a `--exclude` glob list; optionally parse `.gitignore`.
- **Blame:** shell out to `git blame --porcelain` only for files under version control.
- **Dedup:** normalize whitespace/case and hash the marker body; collapse duplicates with
  a count and a list of locations.
- **Output:** pluggable formatter interface (text / markdown / json).
- **Packaging:** installable via `pipx`, single `todo-harvester` entry point.

## Milestones

1. **M1 — Core scan:** walker + regex + text report. Tag and exclude filters.
2. **M2 — Formatters:** Markdown and JSON output; stable schema.
3. **M3 — Attribution:** `--blame` author/date, `--sort age`.
4. **M4 — Dedup:** near-identical collapsing with location lists.
5. **M5 — CI mode:** `--max` threshold exit codes and `diff <ref>` subcommand.
6. **M6 — Polish:** tests, docs, packaging, example config.

## Non-goals

- Not a full static-analysis or linting framework.
- Not a bidirectional sync with GitHub/Jira issues (report-only for v1).
- No IDE plugins or editor integrations in the initial scope.
- No attempt to *fix* the flagged code — discovery and reporting only.
