---
name: design-verify
description: Run the consistency drift checker on the project and report findings (orphan annotations, unimplemented designs, failing constraints, missing enforcement). Use when the user asks to "check designs", "verify consistency", "run the drift check", or wants a status snapshot of all designs.
---

# design-verify

Runs the project's drift checker and surfaces its findings as actionable
items. Also regenerates `design_docs/manifest.toml`.

## When to invoke

- User says: "check designs", "run drift", "verify consistency",
  "show me design status", or similar.
- After landing a non-trivial change, before opening a PR.
- Any time you suspect the repo is in an inconsistent state.

## Procedure

### 1. Run the checker

```
python3 scripts/consistency.py --root .
```

If `--strict` is appropriate (the user asked for a clean bill before
shipping), pass it.

If a single design is in question, scope to it: `--design <id>`.

### 2. Triage findings

The checker emits findings with codes; the most common and how to
respond:

| Code | What it means | Triage |
|------|---------------|--------|
| `orphan-annotation` | Code references a design that no longer exists | The design was deleted or renamed. Either remove the annotation or fix the reference. *Never* "fix" by renaming the design — IDs are stable. Create a new design with `supersedes` instead. |
| `orphan-constraint` | Code references a design's constraint that no longer exists | The constraint was renamed or removed. Same fix as above. |
| `implemented-no-annotations` | Design says `implemented` but no code claims it | Either the implementation was deleted (status should drop to `deprecated`), or annotations were never added (add them). |
| `deprecated-with-annotations` | Code still references a deprecated design | Migrate the code to the superseding design and update annotations. |
| `premature-annotations` | Code references a design that is not yet `implemented` | Usually a slip — annotations got added during scaffolding. Either remove them or, if implementation actually happened, advance the design's status. |
| `ambiguous-annotation` | Multi-constraint design referenced without a constraint id | Add `#<constraint-id>` to the annotation. |
| `codeql-violations` | A CodeQL query reported violating locations | Either fix the violations or, with user approval, refine the query if it is overmatching. |
| `codeql-error` | The CodeQL CLI failed | Likely the CLI is missing or the database is stale. Rebuild the database. |
| `bdd-failing` | A BDD scenario for an implemented constraint is red | Fix the implementation or, if the scenario is wrong, discuss with the user. |
| `no-enforcement` | A constraint has no enforcement mechanism | Reject — every constraint must bind to at least one mechanism. |
| `bad-status` / `missing-field` / `invalid-toml` | The design doc is malformed | Fix the frontmatter. |

### 3. Report

Group findings by design, by severity. Lead with errors. For each
finding, state the *code*, the *location*, and the *recommended next
step* (do not just regurgitate the checker output; the user wants to
know what to do).

Example:

> Drift report:
>
> **secure-endpoints** (status: implemented) — 1 error
> - `codeql-violations` at `design_docs/codeql/secure-endpoints/auth-required.ql`: 2 route handlers do not flow through `require_auth`. Locations: `src/routes/admin.py:14`, `src/routes/internal.py:9`. Likely fix: wrap both with the middleware.
>
> **webhook-retries** (status: scaffolded) — 0 errors, expected (not yet implemented).
>
> **legacy-tokens** (status: deprecated) — 1 error
> - `deprecated-with-annotations`: 3 sites still annotate this design (`src/auth/token.py:22`, ...). Migrate to `secure-endpoints` and update annotations.

### 4. Offer to fix

Mechanical fixes (orphan-annotation cleanup, ambiguous-annotation
disambiguation, manifest regeneration) you can offer to do
immediately. Substantive fixes (CodeQL violations, BDD failures,
deprecated-design migrations) require user direction — surface them
and stop.

## Don'ts

- Do not auto-fix CodeQL or BDD failures. They are user-facing
  contracts.
- Do not edit a design's status to clear a finding. Status is set by
  pipeline progression, not by the verifier.
- Do not silently rename design IDs to make orphan-annotation errors
  go away.
