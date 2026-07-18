# todo-harvester

Scan a codebase for `TODO` / `FIXME` / `HACK` / `XXX` comments and turn them into an
actionable, deduplicated backlog report.

## Project overview

`todo-harvester` is a small command-line tool that walks a source tree, extracts inline
"marker" comments (TODO, FIXME, HACK, XXX, and custom tags), and produces a clean,
grouped report of the work hiding in your code. It attributes each item to a file, line,
and (optionally) the author who last touched that line via `git blame`, then deduplicates
near-identical notes so a single recurring reminder doesn't drown the signal.

## Motivation

Every codebase accumulates inline promises — `# TODO: handle the empty case`,
`// FIXME: this leaks a handle`. They are invisible to issue trackers and easy to forget.
Grepping for `TODO` gives a noisy flat list with no grouping, no ownership, and no way to
tell a fresh note from a five-year-old one. `todo-harvester` closes that gap: it turns
scattered markers into a structured, prioritizable backlog you can actually act on.

## Use cases

- **Onboarding a new codebase** — get a fast map of known rough edges before you start.
- **Pre-release hygiene** — list every `FIXME` still standing before you cut a tag.
- **Tech-debt triage** — group markers by directory/owner and decide what to schedule.
- **CI gates** — fail a build if new `HACK`/`XXX` markers are introduced, or if the total
  count regresses beyond a threshold.
- **Weekly reports** — emit a Markdown or JSON digest of outstanding markers.

## How to use

Quickstart (planned interface):

```bash
# Scan the current directory, print a grouped report
todo-harvester scan .

# Only certain tags, output JSON
todo-harvester scan ./src --tags TODO,FIXME --format json > todos.json

# Attribute each marker to an author via git blame
todo-harvester scan . --blame

# Fail (exit non-zero) if there are more than 50 open markers — for CI
todo-harvester scan . --max 50
```

## Example commands or workflows

```bash
# Group by directory and show the 10 oldest FIXMEs
todo-harvester scan . --tags FIXME --sort age --limit 10

# Markdown digest for a weekly report, ignoring vendored code
todo-harvester scan . --format markdown --exclude 'node_modules,vendor,dist' > TODOS.md

# CI gate: no new markers allowed vs. the base branch
todo-harvester diff origin/main --tags TODO,FIXME,HACK
```

## Current status / next milestones

**Status:** bootstrapping. Scaffolding and backlog are in place; core scanner not yet built.

Next milestones:
1. Core file walker + marker regex engine with tag/exclude filters.
2. Report formatters: plain text, Markdown, JSON.
3. `--blame` git attribution and age sorting.
4. Deduplication of near-identical markers.
5. CI-friendly `--max` threshold and `diff` subcommand.

See [PLAN.md](./PLAN.md) for scope, approach, and non-goals.
