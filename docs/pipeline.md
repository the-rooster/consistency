# Pipeline

The framework's value is in the *gates* between steps, not the steps
themselves. Each gate forces the user to commit to something
mechanically-checkable before moving on.

## Step 1 — Propose

**Trigger:** user describes a feature, change, or property they want.

**Skill:** `design-propose`.

**Output:** a new file `design_docs/<id>.md` at status `draft` with:

- frontmatter populated except status (it is `draft`)
- a body sketching background, acceptance criteria, out-of-scope
- a constraint table where each constraint has at least one
  `enforcement` entry — the agent must propose *how* the property will
  be enforced, not just state the property

**Gate:** the agent stops and asks the user to read the design and
either approve or send it back. No implementation work happens before
this gate is passed.

## Step 2 — Iterate

**Trigger:** user requests changes to a draft design.

**Skill:** `design-propose` (continued).

**Output:** edits to the same file. Status stays `draft` until the
user explicitly says "approved" — at which point the agent flips
status to `approved` and updates the `updated` date.

**Gate:** explicit user approval. The pipeline does *not* progress on
"looks good" — the agent prompts for an explicit approve so the
state transition is deliberate.

## Step 3 — Scaffold tests and hooks

**Trigger:** a design at status `approved`.

**Skill:** `design-scaffold`.

**Output:**

- For each `bdd` constraint: a feature file or scenario carrying the
  constraint's `bdd_tag`, in the project's BDD framework. The
  scenario fails (red) until the implementation step.
- For each `codeql` constraint: a `.ql` query under
  `design_docs/codeql/<design-id>/<constraint-id>.ql` returning the
  *violating* locations. Empty result = constraint holds.
- For each `linter` constraint: the rule registered in whatever
  linter the project uses, plus a unit test for the rule itself.
- For each `pre-commit` constraint: a script under `scripts/hooks/`
  and a `.pre-commit-config.yaml` entry referencing it.
- For each `claude-hook` constraint: a JSON entry in the project's
  `.claude/settings.json` invoking a script under `.claude/hooks/`.
- The drift checker is run; it should pass for everything *except*
  the freshly-added `bdd` and `codeql` constraints, which fail (red)
  because the feature is not yet implemented.

**Gate:** user reviews the scaffolded tests/hooks and approves. The
agent flips status to `scaffolded`. This is the most important gate
in the pipeline — the user is approving "if these tests turn green,
the feature is correctly implemented", so the user must read them
critically.

## Step 4 — Implement

**Trigger:** a design at status `scaffolded`.

**Skill:** `design-implement`.

**Output:**

- Implementation code, with `@design: <id>#<constraint-id>` annotations
  on every code site that contributes to a constraint
- All BDD scenarios for this design pass
- All CodeQL queries for this design return empty
- All linter rules pass
- The drift checker reports zero drift attributable to this design
- Status flipped to `implemented`

**Gate:** the agent does not declare success until the drift checker
returns zero drift for this design.

## Step 5 — Verify

**Trigger:** any commit, plus on demand.

**Skill:** `design-verify` (also wired into pre-commit and Claude
hooks, so it runs automatically).

**Output:** the drift report. Pre-commit blocks the commit on errors;
warnings are reported but do not block.

The verify step is also where the manifest gets regenerated, so
reviewers see an up-to-date design ↔ code map in every PR.

## State diagram

```
draft ──user-approved──▶ approved
                              │
                       agent-scaffolds
                              │
                              ▼
                        scaffolded ──user-approved──▶ implementing
                                                          │
                                                  agent-implements
                                                          │
                                                          ▼
                                                    implemented
                                                          │
                                                  superseded-by
                                                          │
                                                          ▼
                                                    deprecated
```

Statuses move forward, not backward. If a design needs major rework,
create a new design with `supersedes = ["old-id"]` rather than
mutating the old one.
