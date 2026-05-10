---
name: design-scaffold
description: Generate the BDD scenarios, Semgrep rules, CodeQL queries, linter rules, pre-commit hooks, and Claude Code hooks declared by an approved design's constraints. Use after the user approves a design (status=approved) and before any feature implementation work. Defaults to Semgrep for structural properties; reserves CodeQL for predicates that need dataflow or taint analysis.
---

# design-scaffold

Turns an `approved` design into the mechanical checks that will keep
its constraints honest. Runs *before* the feature is implemented so
that those checks are red-green indicators of progress.

## When to invoke

- A design exists at status `approved`.
- The user just approved the design (use right after `design-propose`).
- The user says "scaffold the tests for X", "set up the checks for X",
  or similar.

## When NOT to invoke

- Design is still `draft` — the user has not signed off on what to
  enforce.
- Design is already `scaffolded` — re-scaffolding overwrites work the
  user may have edited; ask first.

## Procedure

### 1. Load the design

Parse `design_docs/<id>.md`. Verify status is `approved`. If not,
stop and explain.

### 2. For each constraint, generate enforcement artifacts

Process constraints in declaration order. For each, produce the
artifacts named by `enforcement`:

#### `bdd`

Write a Gherkin scenario in the project's BDD framework. Tag the
scenario with the constraint's `bdd_tag` (default
`@<design-id>--<constraint-id>`) so the drift checker can scope
runs to it.

Source the scenario from the design's "Acceptance criteria" section
where possible. Do not invent behavior not implied by the design;
if the design is silent on an edge case, ask before adding it.

Use the project's existing `features/` (or equivalent) directory.
Create a new file per design (`features/<design-id>.feature`) so
constraints from one design stay together.

Scenarios fail (red) at this point — that is correct. They will go
green during `design-implement`.

#### `semgrep`

The framework's preferred enforcement for AST-pattern structural
properties — most "every X is wrapped/decorated/passes Y"
properties belong here, not in CodeQL.

1. Write a Semgrep YAML rule whose `pattern` (or `patterns:` block)
   matches *violating* code, not compliant code. Empty result =
   property holds.
2. Use `pattern-not` to subtract the compliant cases. Typical shape:
   `pattern: <broad match>` then `pattern-not: <broad match where Y
   is also present>`.
3. Set `languages:` based on the project. Semgrep auto-detects most
   files but the rule needs to declare which languages it applies to.
4. Set `severity: ERROR` and a `message` that explains the
   constraint (the agent that violates the rule reads this; make it
   instructive).
5. Write the rule to
   `design_docs/semgrep/<design-id>/<constraint-id>.yml`.
6. Run `semgrep scan --config <rule-path> --error <source-globs>`
   once. It should currently report violations (no implementation
   yet) or zero violations (property happens to hold). Both are
   acceptable starting states.
7. Add a comment at the top of the rule pointing back at the design:

   ```yaml
   # @design <design-id>#<constraint-id>
   # See design_docs/<design-id>.md for context.
   ```

Reach for `codeql` instead of `semgrep` only if the property
genuinely needs taint flow or cross-procedural dataflow. If you
catch yourself writing a chain of `pattern-inside` / `pattern-not`
that approximates dataflow, that is the cue to switch to CodeQL.

#### `codeql`

The framework's preferred enforcement for *dataflow* properties.
For pure AST patterns prefer `semgrep`. Take time to write a *good*
query.

1. Determine the database language from `consistency.toml`'s
   `[codeql]` block. If polyglot, write one query per language.
2. Write a query that returns the *violating* code locations, not the
   compliant ones. Empty result = property holds. This makes the
   drift checker's "no-violations" status mean what it says.
3. The query should encode the constraint's predicate as directly as
   possible. Examples:

   - "Every HTTP route handler is wrapped in `require_auth`":
     query selects route-handler functions whose call graph from the
     entry point does not pass through `require_auth`.
   - "No SQL string is built from user input without going through
     `parameterize`": query is a taint-tracking configuration with
     user input as source, raw SQL execution as sink, and
     `parameterize` as a sanitizer.
   - "Every `unwrap` is in test code or guarded by `is_ok`": query
     selects `unwrap` call sites outside test directories whose AST
     ancestor chain does not contain a guarding `if is_ok(...)`.

4. Write the query to
   `design_docs/codeql/<design-id>/<constraint-id>.ql`.
5. Run it once against the current database. It should currently
   report violations (the feature is not yet implemented), or zero
   violations (the property already happens to hold). Both are
   acceptable starting states.
6. Add a brief comment block at the top of the query explaining what
   property it encodes and pointing back to the design:

   ```ql
   /**
    * @design secure-endpoints#auth-required
    * Selects route handlers whose call graph does not flow through
    * the require_auth middleware.
    */
   ```

If you are not confident the query expresses the property correctly,
say so to the user. A wrong CodeQL query is worse than no query — it
gives false confidence.

#### `linter`

Use the project's existing linter where possible (ruff, eslint,
golangci-lint). Add a rule with the ID declared in the constraint's
`linter_rule` field. If the property is structural, push back: it
probably belongs in `codeql`.

Add an entry under `[linter]` in `consistency.toml` mapping the rule
id to a command the drift checker can run.

#### `pre-commit`

Write a script under `scripts/hooks/<hook-id>.sh` that exits non-zero
on violation. Append an entry referencing it to
`.pre-commit-config.yaml`.

#### `claude-hook`

Write a script under `.claude/hooks/<hook-id>.sh`. Add a `PreToolUse`
or `PostToolUse` entry under `hooks` in `.claude/settings.json`.
Choose the trigger so the hook fires *when the agent tries to do the
thing the constraint forbids* — `Bash` for shell commands, `Edit` /
`Write` for file mutations, etc.

#### `manual`

Add a TODO note in the design's body explaining what the human
reviewer must check. The drift checker will surface a warning each
run as a reminder.

### 3. Run the drift checker

`python3 scripts/consistency.py --root . --design <id>`

Expected outcome: the checker reports the design's constraints as
*not yet satisfied* (because no implementation exists yet), but no
*orphan* findings — every enforcement mechanism the design declares
is wired up. If you see orphan-annotation, missing-field, or other
shape errors, fix them before stopping.

### 4. Stop and ask

Tell the user explicitly what you scaffolded and ask them to review:

> "I've scaffolded the following for `<id>`:
> - `features/<id>.feature` with N scenarios (currently failing — will
>   pass after implementation)
> - `design_docs/codeql/<id>/<constraint>.ql` (currently reporting M
>   violations — will report zero after implementation)
> - [other artifacts]
>
> Please read these. They are the contract: when they all turn green,
> the feature is correctly implemented. If they over- or under-specify,
> tell me now — they are much cheaper to fix at this stage than after
> the feature lands."

Wait for explicit approval. On approval, flip the design's status to
`scaffolded` and update `updated` date.

## Don'ts

- Do not write any feature implementation code in this step.
- Do not lower the severity of a constraint just to make the checker
  pass.
- Do not skip CodeQL because "it would be hard to write the query".
  If the constraint is genuinely too complex for CodeQL, raise it
  with the user; downgrading it to `linter` silently is dishonest.
- Do not commit. The user controls when to commit.
