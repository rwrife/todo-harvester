# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `scan --format json` output mode for machine-readable marker reports.
- README rewritten with full CLI usage, argument reference, examples, JSON schema, and exit codes.
- GitHub Actions CI workflow to run tests and verify `pipx` installation/entry point.

## [0.1.0] - 2026-07-20

### Added
- Recursive file walker with sensible default excludes.
- Marker extraction engine for TODO/FIXME/HACK/XXX and custom tags.
- `todo-harvester` CLI with `scan` subcommand and text output.
