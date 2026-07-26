# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Marker deduplication by normalized text+tag with collapsed `count` and full `locations` metadata.
- `scan --no-dedup` flag to preserve one-record-per-marker behavior.
- `scan --format json` output mode for machine-readable marker reports.
- `scan --format markdown` output mode for headed, grouped report digests.
- Grouped plain-text report output with directory/file sections and per-tag summary footer.
- Stable JSON schema fields for machine output: `tag`, `text`, `file`, `line`, `count`, `locations`.
- README rewritten with full CLI usage, argument reference, examples, JSON schema, and exit codes.
- GitHub Actions CI workflow to run tests and verify `pipx` installation/entry point.

## [0.1.0] - 2026-07-20

### Added
- Recursive file walker with sensible default excludes.
- Marker extraction engine for TODO/FIXME/HACK/XXX and custom tags.
- `todo-harvester` CLI with `scan` subcommand and text output.
