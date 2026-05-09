# Installing the skills

The consistency framework distributes as Claude skills you can install
either globally (available to every project on your machine) or
per-project (committed to a particular repo).

## Global install

Best when you want the skills available from any working directory.

```
# Linux / macOS
mkdir -p ~/.claude/skills
cp -R skills/* ~/.claude/skills/

# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills"
Copy-Item -Recurse skills\* "$env:USERPROFILE\.claude\skills\"
```

After installing, the five skills (`design-init`, `design-propose`,
`design-scaffold`, `design-implement`, `design-verify`) appear in
Claude Code's available skills.

## Per-project install

Best when you want the skill versions pinned to a particular project,
or when you want every collaborator to use the same version.

```
mkdir -p .claude/skills
cp -R /path/to/consistency/skills/* .claude/skills/
git add .claude/skills
```

Project-level skills override globally-installed ones with the same
name.

## Vendoring the drift checker

Whichever way you install the skills, the drift checker
(`scripts/consistency.py`) lives *inside the project being managed*
— `design-init` copies it there. The skills assume the path
`scripts/consistency.py`; if you keep it elsewhere, update the hook
templates and the skill files accordingly.

## Required external tools

| Tool | When | Install |
|------|------|---------|
| Python 3.11+ | always — the drift checker | https://python.org |
| CodeQL CLI | for `codeql` enforcement | https://github.com/github/codeql-cli-binaries |
| Your BDD framework | for `bdd` enforcement | per-language (e.g. `pip install behave`) |
| pre-commit | for the pre-commit hook | `pip install pre-commit` (optional but recommended) |

The drift checker degrades gracefully when CodeQL or the BDD framework
is unavailable: it reports the missing tool as an error rather than
silently skipping. This is intentional — silent skips are how
consistency frameworks die.
