# Concepts

This document defines the vocabulary the framework uses. Skills, scripts,
and templates all assume these definitions.

## Design

A *design* is a single Markdown file in `design_docs/` describing a
discrete piece of intended behavior. A design is the unit of approval,
the unit of testing, and the unit that code annotations point to.

Designs have stable, kebab-case IDs (`secure-endpoints`,
`webhook-retries`). The ID lives in TOML frontmatter and is *never
renamed* — only deprecated. Renaming breaks every annotation that
references the design.

A design is at one of these statuses:

- `draft` — being written, not yet approved by the user
- `approved` — approved; tests and hooks may be scaffolded
- `scaffolded` — tests and hooks exist; implementation may begin
- `implemented` — implementation exists, all constraints pass
- `deprecated` — design is retired; new code may not annotate it

Drift checks treat each status differently. A design at `approved`
must have no implementation annotations yet. A design at `implemented`
must have at least one. A design at `deprecated` must have none.

## Constraint

A *constraint* is a single property the design requires, plus a
declaration of how it is enforced. Constraints are the bridge between
prose ("all endpoints require auth") and machine checks.

Each constraint has:

- `id` — kebab-case, unique within the design
- `description` — one-line prose statement of the property
- `enforcement` — a list of one or more mechanisms

Supported enforcement mechanisms:

| Mechanism | Meaning |
|-----------|---------|
| `bdd` | A Gherkin scenario (or set of scenarios) in the project's BDD framework. The drift checker requires a matching scenario tag and runs the framework with the configured `tag_arg_format` to scope the run. |
| `codeql` | A CodeQL query in `design_docs/codeql/<design-id>/<constraint-id>.ql` that returns *violating* code locations. Empty result = constraint holds. |
| `linter` | A static check (regex, AST visitor, or existing linter rule). Use for simple textual or single-file properties; for cross-cutting structural properties prefer `codeql`. |
| `pre-commit` | A pre-commit hook that fails commits violating the property. |
| `claude-hook` | A Claude Code `PreToolUse` or `PostToolUse` hook that prevents the agent from making a change that would violate the property. |
| `manual` | Explicit escape hatch. The constraint is enforced by review only. Drift checker emits a warning, not an error. |

A constraint with no enforcement is rejected by the drift checker —
the framework's whole point is that every constraint binds to a check.

### Preferring CodeQL for structural properties

The framework actively prefers `codeql` over `linter` whenever the
property is *structural* — i.e., describes a relationship between code
elements rather than a single textual pattern. Examples that should
use CodeQL:

- "Every HTTP route handler is wrapped in auth middleware"
- "Every external network call lives inside a retry helper"
- "No SQL string is built from user input without going through the
  parameterized-query helper"
- "Every `Result.unwrap` is guarded by a prior `is_ok` check or sits
  in a test file"

Examples that are fine as `linter`:

- "Filenames in `migrations/` match `^\d{4}_.*\.sql$`"
- "No file imports the deprecated `legacy_utils` module"

Why the preference: CodeQL queries are explicit dataflow / structural
predicates, so they generalize across the codebase. Regex linters
tend to either over- or under-match as the codebase evolves, and the
agent has to keep tweaking them. A CodeQL query, once written, keeps
holding as long as the structural property is true.

## Annotation

An *annotation* is an in-code marker that a piece of code implements a
design. Format:

```
@design: <design-id>
```

or, to point at a specific constraint:

```
@design: <design-id>#<constraint-id>
```

Annotations live in comments. The drift checker grep-scans the repo
for them; they survive moves and refactors as long as the comment
travels with the code.

The constraint-level form is required when the design has multiple
constraints — it lets the drift checker prove that every constraint
has at least one implementation site.

## Manifest

The *manifest* (`design_docs/manifest.toml`) is a generated file that
aggregates the current state of all designs and their links. The drift
checker writes it; humans read it. It is committed to the repo so PR
reviewers can see at a glance what designs a change touches.

The manifest is regenerated on every drift check. Hand-editing it has
no effect.

## Drift

*Drift* is any of:

- An annotation pointing to a non-existent design or constraint
- A design at status `implemented` with zero annotations
- A constraint at status `implemented` with zero annotations to it
- A design with no enforcement mechanism wired up
- A `bdd` constraint with no matching scenario tag
- An `implemented` design whose tests do not currently pass

The drift checker reports drift; the pre-commit hook blocks commits
that introduce it.

## Coverage cross-check (optional)

When a `bdd` constraint runs under coverage instrumentation, the
drift checker can verify that each `@design` annotation actually
*sits in code that the matching scenarios exercise*. This catches a
real failure mode of annotation-based linking: an annotation whose
function or block has been refactored away to a sibling file, or
that lies outright.

Two findings come out of the cross-check:

- **`annotation-uncovered`** — an annotation `@design: X#c` whose
  *ownership range* (from the annotation's line to the next
  annotation in the same file, or EOF) contains no line that was
  executed by scenarios tagged for constraint `c`. Either the
  annotation lies, the scenario is too narrow, or the code is dead.
- **`covered-unannotated`** — a file whose statements are heavily
  covered (over `heavy_coverage_threshold`) by a design's scenarios
  but that has no `@design` annotation for that design. Surfaced as
  a *suggestion* — the human decides whether the coverage is intent
  or incidental.

Both findings are warnings, not errors, because both can have
legitimate explanations. The cross-check is opt-in
(`--with-coverage` on the checker, off by default) because running
the BDD suite under coverage is heavy. Wire it into CI; keep
pre-commit fast.
