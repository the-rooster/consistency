# consistency

An experimental framework for building applications with LLM coding agents
where designs, tests, and implementations stay aligned automatically.

## The problem

LLM-assisted codebases drift. Each new feature can be implemented in a
slightly different shape, and properties that should hold globally —
"every endpoint requires auth", "every external call is retried",
"every handler emits a structured log" — silently stop holding. Code
review catches some of it; most of it slips through.

## The idea

Make designs first-class artifacts and bind them to mechanical checks:

1. Every project has a `design_docs/` folder. Each design is a Markdown
   file with TOML frontmatter declaring an `id`, status, and a list of
   constraints.
2. A constraint declares a property the design requires, plus *how* it
   should be enforced — a BDD scenario, a linter rule, a pre-commit
   check, a Claude Code hook.
3. Code that implements a design carries an `@design: <id>` annotation.
   A manifest aggregates these into bidirectional links so you can
   navigate from design → code and back.
4. A drift checker, run pre-commit and inside the agent's own hooks,
   verifies: every design has a matching test, every annotation points
   to a real design, and every constraint's enforcement mechanism is
   wired up.

## The pipeline

The framework defines a five-step workflow that the bundled Claude
skills drive:

1. **Propose.** User describes a feature. Agent drafts a design doc,
   stops for approval.
2. **Iterate.** User accepts or sends back. Loop until approved.
3. **Scaffold tests and hooks.** Agent generates BDD tests and the
   linters / pre-commit / Claude hooks the design's constraints
   require. Stops for approval.
4. **Implement.** Agent writes the feature, adds `@design` annotations,
   and proves the new tests pass.
5. **Verify.** Drift checker runs end-to-end; report attached to the
   commit.

The constraint that *tests and hooks land before the implementation*
is intentional: it forces the agent to commit to mechanically-checkable
acceptance criteria before writing any feature code.

## Skills

Distributed as Claude skills you can install per-project or globally.

| Skill | Purpose |
|-------|---------|
| `design-init` | Initialize an existing project with the framework: directory, manifest, hooks, drift checker. |
| `design-propose` | Draft a design doc from a user feature request. Stops for approval. |
| `design-scaffold` | Generate BDD tests, linter rules, and hooks declared by an approved design. Stops for approval. |
| `design-implement` | Implement an approved, scaffolded design end-to-end and prove the constraints hold. |
| `design-verify` | Run the drift checker and report orphan annotations, unimplemented designs, and missing enforcement. |

## Status

Experimental. Format and skill contracts will change.
