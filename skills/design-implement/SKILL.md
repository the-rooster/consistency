---
name: design-implement
description: Implement a design that has been approved and scaffolded, adding @design annotations on every code site that contributes to a constraint, and proving every constraint passes (BDD green, CodeQL empty, linter clean) before declaring done. Use after design-scaffold has produced tests/queries the user has approved.
---

# design-implement

Writes the feature code for a design at status `scaffolded` and only
declares completion when the drift checker is green for that design.

## When to invoke

- A design is at status `scaffolded` and the user has reviewed and
  approved the scaffolded tests/queries.
- The user says "implement <design-id>", "build the feature for X",
  or similar.

## When NOT to invoke

- Design is still `draft` or `approved` — earlier pipeline steps must
  finish first.
- The scaffolded checks are stale — if the design has been edited
  since scaffolding, re-run `design-scaffold` first.

## Procedure

### 1. Re-read the design

Open `design_docs/<id>.md`. Re-read every constraint. The constraints
are the acceptance criteria — when they all pass, the feature is
done. If you find yourself wanting to do *more* than what they
require, that is scope creep; resist it. If you find yourself wanting
to do *less*, you have either misread the design or the design needs
amendment (in which case stop and raise it with the user).

### 2. Sketch the implementation

Before writing code, write yourself a short plan: which files change,
which symbols are introduced, how the new code attaches to the
existing system. Do not show this to the user unless they ask — it is
private scratchwork to keep you honest about scope.

### 3. Write the code

Implement the feature. As you go:

- Add `@design: <id>#<constraint-id>` annotations on every code site
  that contributes to a constraint. Annotations live in comments and
  should be on the line above the relevant function, class, or block.
- For multi-constraint designs, the constraint-level annotation form
  is required. The drift checker will warn on bare-design annotations
  in this case.
- Do not annotate trivial helpers. Annotate the *load-bearing* sites
  the constraint cares about. A single design can have 20 annotation
  sites or 1 — what matters is that every constraint is reachable
  from at least one annotation.

Example:

```python
# @design: secure-endpoints#auth-required
@app.route("/users/<id>")
@require_auth
def get_user(id):
    ...
```

### 4. Run the constraint checks iteratively

After each meaningful chunk of implementation, run:

```
python3 scripts/consistency.py --root . --design <id>
```

You will see the BDD scenarios go green and the CodeQL violation
counts drop. Use this as your progress signal. If a check that was
green goes red, stop and find out why before writing more code.

### 5. Resist the temptation to weaken checks

If a CodeQL query reports a violation you cannot make go away, do
*not* edit the query to ignore the violation. Either:

- The implementation is wrong — fix the implementation.
- The query is wrong — discuss with the user. Editing a query during
  implementation needs the same approval gate as scaffolding it.
- The constraint is wrong — discuss with the user. The design may
  need a new revision.

The same applies to BDD scenarios and linter rules. Every check is a
contract the user signed off on; you do not have unilateral authority
to renegotiate it.

### 6. Final verification

When you believe the design is done:

1. Run the full drift checker: `python3 scripts/consistency.py --root .`
2. Confirm: zero errors, zero warnings attributable to this design.
3. Confirm: every constraint has at least one annotation pointing at
   it.
4. Flip status to `implemented` in the design's frontmatter; update
   `updated` to today's date.
5. Run the drift checker once more after the status flip — the
   `implemented` status triggers stricter checks (e.g. "implemented
   designs must have annotations"), so this final run proves the
   tighter contract.

### 7. Report

Tell the user concisely:

> "<id> is implemented. Drift checker is green. Files touched: ...
> Annotations added: N at [list of files]. Status flipped to
> implemented. Manifest regenerated."

## Don'ts

- Do not weaken constraints to make the checker pass.
- Do not skip annotations. The drift checker will catch you, but more
  importantly the manifest will be wrong, which silently degrades
  every future review.
- Do not commit on the user's behalf. The user decides when.
- Do not refactor unrelated code while you are here. If you spot
  drift in another design, surface it; do not silently fix it as
  part of this commit.
