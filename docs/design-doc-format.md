# Design doc format

A design doc is a Markdown file in `design_docs/` with TOML frontmatter
delimited by `+++`. The frontmatter declares machine-readable metadata;
the body is prose for humans.

## File layout

```markdown
+++
id = "secure-endpoints"
title = "All HTTP endpoints require authenticated callers"
status = "approved"
owner = "andrew"
created = 2026-05-09
updated = 2026-05-09
tags = ["security", "http"]

[[constraint]]
id = "auth-required"
description = "Every HTTP route handler is wrapped in the `require_auth` middleware."
enforcement = ["codeql", "bdd"]

[[constraint]]
id = "no-bypass-flag"
description = "No code path sets `auth_bypass = true` outside of test files."
enforcement = ["codeql"]
+++

## Background

Prose explaining the motivation, the user problem, the alternatives
considered. The body is for humans; mechanical checks read only the
frontmatter and the constraint table.

## Acceptance criteria

Free-form. The `bdd` enforcement converts these into Gherkin scenarios
in step 3 of the pipeline.

## Out of scope

What this design intentionally does *not* cover.
```

## Frontmatter schema

### Document level

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | kebab-case, unique across the project, **never renamed** |
| `title` | string | yes | one-line human title |
| `status` | string | yes | one of `draft`, `approved`, `scaffolded`, `implemented`, `deprecated` |
| `owner` | string | yes | the human accountable for the design |
| `created` | date | yes | ISO date the design was first drafted |
| `updated` | date | yes | ISO date of last edit |
| `tags` | array<string> | no | free-form labels for grouping |
| `supersedes` | array<string> | no | IDs of designs this one replaces (those move to `deprecated`) |

### Constraint level (`[[constraint]]`, repeated)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | kebab-case, unique within the design |
| `description` | string | yes | one-line statement of the property |
| `enforcement` | array<string> | yes | one or more of `bdd`, `semgrep`, `codeql`, `linter`, `pre-commit`, `claude-hook`, `manual` |
| `bdd_tag` | string | when `bdd` ∈ enforcement | tag the BDD scenario must carry; defaults to `@<design-id>--<constraint-id>` |
| `semgrep_rule` | string | when `semgrep` ∈ enforcement | path to the semgrep YAML rule; defaults to `design_docs/semgrep/<design-id>/<constraint-id>.yml` |
| `codeql_query` | string | when `codeql` ∈ enforcement | path to the `.ql` file; defaults to `design_docs/codeql/<design-id>/<constraint-id>.ql` |
| `linter_rule` | string | when `linter` ∈ enforcement | identifier of the linter rule (project-defined) |
| `hook_id` | string | when `pre-commit` or `claude-hook` ∈ enforcement | identifier the hook config maps to a script |
| `severity` | string | no | `error` (default) or `warning` |

The drift checker reads the frontmatter to discover what to verify;
mismatches between declared enforcement and what is actually wired up
are themselves drift.

## Why TOML

YAML's whitespace sensitivity bites LLM-edited files often enough that
the cost outweighs its readability. TOML round-trips through edits
deterministically, supports typed dates natively, and is unambiguous
about array-of-tables (`[[constraint]]`), which is the most-edited part
of the schema.

## Linking to code

Code that implements a design carries an annotation in a comment:

```python
# @design: secure-endpoints#auth-required
def fetch_user(...):
    ...
```

Annotations are grep-discovered. The drift checker accepts any of:

- `@design: <id>`
- `@design: <id>#<constraint-id>`
- `@design(<id>)`
- `@design(<id>#<constraint-id>)`

If the design has more than one constraint, the constraint-level form
is required — the checker won't credit the bare-design form against
any specific constraint.
