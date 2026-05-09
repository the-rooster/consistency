---
name: design-init
description: Initialize an existing project with the consistency framework (design_docs, drift checker, hooks, manifest). Use when the user asks to "set up the design framework", "add consistency framework to this project", or starts a fresh project intending to use the design-doc workflow.
---

# design-init

Bootstraps the consistency framework inside the current project.

## When to invoke

- User says: "set up the design framework", "init consistency",
  "add design docs to this repo", or similar.
- The project does not yet have `design_docs/` or `consistency.toml`.

If the project already has a `design_docs/` directory and a populated
`consistency.toml`, do not re-init. Tell the user it is already set
up and exit.

## What you produce

1. `design_docs/` directory.
2. `design_docs/codeql/` directory (placeholder for query files).
3. `consistency.toml` at the project root, populated from the user's
   answers to the questions below.
4. `scripts/consistency.py` copied from this skill's distribution
   (the framework keeps a vendored copy per project so projects can
   pin a checker version).
5. `scripts/hooks/pre-commit-consistency.sh` made executable.
6. `.pre-commit-config.yaml` updated (or created) with the
   consistency-drift-check entry.
7. `.claude/settings.json` updated with the Stop and PreToolUse hooks
   that run the drift checker.

## Procedure

1. **Detect project context.** Read the project root. Identify:
   - language(s) in use (Python, TS, Go, etc.)
   - existing test frameworks
   - whether a CodeQL CLI is on PATH (`which codeql` / `where codeql`)
   - whether a `.pre-commit-config.yaml` exists
   - whether `.claude/settings.json` exists

2. **Ask the user only what cannot be detected:**
   - Which BDD framework? (default: behave for Python, cucumber-js for
     TS/JS, godog for Go, specflow for C#)
   - Where to scan for `@design` annotations (default: `src/**/*` plus
     any directory containing source you detected)
   - Whether to enable CodeQL now or defer (default: enable, with a
     warning if the CLI is missing)

3. **Generate `consistency.toml`** from `templates/consistency.toml`,
   substituting the answers above. Set `[codeql].language` to the
   project's primary language.

4. **Vendor `scripts/consistency.py`** by copying the framework's
   checker into `scripts/`. Mark it executable.

5. **Wire pre-commit:**
   - If `.pre-commit-config.yaml` exists, append the
     `consistency-drift-check` hook from
     `templates/hooks/pre-commit-config.snippet.yaml`. Preserve all
     existing hooks. Do not duplicate if the entry is already present.
   - Otherwise, write the snippet as the entire file.

6. **Wire Claude Code hooks:**
   - If `.claude/settings.json` exists, merge the two hook entries
     from `templates/hooks/claude-settings.snippet.json` under the
     `hooks.Stop` and `hooks.PreToolUse` keys. Preserve existing
     hooks; never overwrite.
   - Otherwise, write a minimal `.claude/settings.json` containing
     just the snippet.

7. **Create `design_docs/README.md`** explaining the format briefly,
   pointing readers at the framework docs.

8. **Run the drift checker once** to confirm everything wires up:
   `python3 scripts/consistency.py --root .`. The output should be
   "0 error(s), 0 warning(s)" with an empty manifest.

9. **Report what you did.** List the files created/modified, surface
   any detection ambiguity (e.g. "I assumed Python; if not, edit
   `consistency.toml` and re-run the checker").

## Don'ts

- Do not commit on the user's behalf. Init creates files; the user
  decides when to commit them.
- Do not install pre-commit globally. If the user does not have
  `pre-commit` installed, mention it as a manual follow-up — do not
  pip-install on their machine.
- Do not write any design docs as part of init. Designs come from
  `design-propose`, not from init.
