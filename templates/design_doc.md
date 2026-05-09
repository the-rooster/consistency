+++
id = "REPLACE-ME-kebab-case"
title = "REPLACE ME — one-line human title"
status = "draft"
owner = "REPLACE-ME"
created = 2026-01-01
updated = 2026-01-01
tags = []

# Repeat one [[constraint]] block per machine-checkable property.
# Pick enforcement values from: bdd, codeql, linter, pre-commit, claude-hook, manual.
# Prefer codeql over linter for structural / cross-cutting properties.

[[constraint]]
id = "REPLACE-ME-constraint-id"
description = "REPLACE ME — single declarative sentence stating what must hold."
enforcement = ["codeql", "bdd"]
# Optional, defaults shown:
# bdd_tag = "@<design-id>--<constraint-id>"
# codeql_query = "design_docs/codeql/<design-id>/<constraint-id>.ql"
# severity = "error"
+++

## Background

Why does this design exist? What user problem or invariant does it
encode? What alternatives were considered and rejected?

## Acceptance criteria

Concrete, observable statements. Each item here will become a BDD
scenario in step 3 of the pipeline if a `bdd` constraint applies.

- ...
- ...

## Out of scope

What this design does *not* cover, so reviewers don't expect it.

- ...

## Notes

Anything else useful to a reader: links to prior art, related designs,
external references.
