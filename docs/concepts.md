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
| `semgrep` | A Semgrep rule in `design_docs/semgrep/<design-id>/<constraint-id>.yml` whose results identify violating code locations. Lightweight AST pattern matching across many languages. |
| `codeql` | A CodeQL query in `design_docs/codeql/<design-id>/<constraint-id>.ql` returning violating locations. Use when you need dataflow or taint analysis. |
| `linter` | A textual or existing-linter check (regex, eslint rule, ruff rule). Use for simple single-file textual properties only. |
| `pre-commit` | A pre-commit hook that fails commits violating the property. |
| `claude-hook` | A Claude Code `PreToolUse` or `PostToolUse` hook that prevents the agent from making a change that would violate the property. |
| `manual` | Explicit escape hatch. The constraint is enforced by review only. Drift checker emits a warning, not an error. |

A constraint with no enforcement is rejected by the drift checker —
the framework's whole point is that every constraint binds to a check.

### Choosing among `linter`, `semgrep`, and `codeql`

The three static-enforcement options form a capability ladder.
Use the cheapest tool that can express the property.

| Property shape | Enforcement |
|---|---|
| Filenames, imports, single-line textual rules | `linter` |
| AST patterns: "every X function is decorated with Y", "every X call passes Y as arg N", "no constructor in this directory uses pattern Z" | `semgrep` |
| Dataflow / taint / cross-procedural: "user input never reaches a raw SQL exec without `parameterize`", "every secret read flows through `redact` before any log call" | `codeql` |

**Semgrep** is the recommended default for structural enforcement.
Its rules are short YAML, multi-language out of the box, and the CLI
installs via `pip install semgrep` with no database build step.
A typical rule fits in a screen.

**CodeQL** is reserved for properties that genuinely need dataflow
or taint analysis. Its queries are more expressive but longer and
harder to write; the database build step adds friction. Reach for
it only when Semgrep cannot express the property — typically when
the predicate involves "value flows from X to Y" rather than
"this AST shape exists."

**Linter** is for genuinely textual rules where AST awareness adds
nothing — filename checks, import bans, simple regexes against
known files.

Why the bias against ad-hoc regex `linter` rules for structural
properties: they over- or under-match as the codebase evolves and
the agent has to keep tweaking them. Semgrep and CodeQL hold as
long as the structure does.

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
