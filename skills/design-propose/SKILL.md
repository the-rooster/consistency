---
name: design-propose
description: Draft a design doc from a user feature request and stop for explicit approval before any implementation work begins. Use this skill at the start of any feature, refactor, or property-introducing change in a project that uses the consistency framework. Recognized triggers include "I want a feature that does X", "let's add Y", "make it so that every Z does Q", or any request that introduces new code patterns or invariants.
---

# design-propose

Translates a user feature request into a `design_docs/<id>.md` file at
status `draft` and stops for explicit user approval. This skill is the
first gate in the consistency pipeline; nothing else should run until
the user has approved the resulting design.

## When to invoke

- User describes a new feature or behavior in a project that has
  `design_docs/` and `consistency.toml`.
- User says "let's design X", "draft a doc for Y", "I want all Z to ...".
- User asks for a refactor that introduces a new cross-cutting pattern.

## When NOT to invoke

- Trivial bug fixes that do not introduce new patterns or invariants.
- Edits inside an already-implemented design (those go through a new
  design with `supersedes`, or a small inline edit if the existing
  constraints still apply).

## Procedure

### 1. Understand the request

Re-read the user's feature description. Identify:

- **Behavioral statements**: things the system must do.
- **Invariants**: things that must hold across the system (these
  become constraints).
- **Boundaries**: what the user did not say — the design's
  out-of-scope section is as load-bearing as its in-scope section.

If the request is ambiguous about an invariant ("all endpoints must
be secure" — which endpoints? which definition of secure?), ask the
user *before* drafting. The draft is cheaper to write once you know
what you are committing to.

### 2. Pick an ID

kebab-case, short (2-4 words), describes the property not the
mechanism: `secure-endpoints` not `auth-middleware`,
`webhook-retries` not `retry-loop`.

Check the design ID does not collide with an existing design (use the
manifest or list `design_docs/`).

### 3. Draft the file

Copy `templates/design_doc.md` to `design_docs/<id>.md`. Fill in:

- frontmatter (`status = "draft"`, today's date for `created` and `updated`)
- background section (one to three paragraphs)
- acceptance criteria (concrete, observable bullet points)
- out-of-scope section
- one `[[constraint]]` block per invariant the user stated or implied

### 4. Choose enforcement mechanisms thoughtfully

For each constraint, pick `enforcement` values. The framework
strongly prefers `codeql` for structural / cross-cutting properties.
Use this rubric:

| Property shape | First-choice enforcement |
|---|---|
| "every X is wrapped in Y" / "every X flows through Y" | `codeql` (+ `bdd` for representative scenarios) |
| "X never calls Y directly" / "no X without prior Y" | `codeql` |
| "user-facing behavior on the happy path" | `bdd` |
| "user-facing behavior on edge cases" | `bdd` |
| "filename/path/format constraint" | `linter` (regex is fine) |
| "process / workflow constraint" (e.g. "every PR has a label") | `pre-commit` or `claude-hook` |
| "no agent should edit file X without approval" | `claude-hook` |
| "expensive cross-cutting check that is hard to automate" | `manual` (rare; document why) |

If a constraint reasonably fits both `codeql` and `linter`, prefer
`codeql`. Regex linters drift; structural queries hold as long as the
structure holds.

If a constraint fits both `codeql` and `bdd`, list both. CodeQL
proves the static property; BDD proves the runtime behavior. They are
complementary, not redundant.

### 5. Sanity-check the draft

Before showing the user, walk through these checks yourself:

- Is every constraint mechanically checkable? If you cannot describe
  *what file* would prove violation, the constraint is too vague.
- Could a reasonable engineer implement this design two different
  ways? If yes, add or sharpen a constraint until the answer is no.
- Does any constraint depend on the implementation choice rather than
  on the user property? If yes, drop it — designs are about *what*,
  not *how*.

### 6. Stop and ask

Show the user the draft (or the file path) and ask explicitly:

> "I've drafted `design_docs/<id>.md` at status `draft`. Please read
> it and either approve or send back changes. Once you approve, I'll
> flip it to `approved` and we'll move on to scaffolding tests and
> hooks."

Do **not** start scaffolding. Do **not** flip status to `approved`
without an explicit user "approved" / "yes, ship it" / similar.

### 7. On approval

When the user approves, edit the frontmatter: `status = "approved"`,
update `updated` to today's date. Then tell the user that
`design-scaffold` is the next step.

### 8. On iteration

If the user sends back changes, apply them and ask again. Status
stays `draft` until explicit approval.

## Output the user expects

A single Markdown file under `design_docs/`, plus a clear stop-message
asking for approval. Nothing else.
