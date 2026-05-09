#!/usr/bin/env python3
"""
consistency: drift checker for the design-doc framework.

Run from a project root that has been initialized with the framework
(i.e. has a `consistency.toml` and a `design_docs/` directory).

Usage:
    consistency.py                  # full check + regenerate manifest
    consistency.py --design <id>    # scope to one design
    consistency.py --manifest-only  # skip enforcement, regenerate manifest only
    consistency.py --strict         # warnings become errors
    consistency.py --with-coverage  # also run the BDD coverage cross-check
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib  # type: ignore

# Severity exit codes are aggregated; any error means non-zero exit.
EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_USAGE = 2

VERSION = "0.1.0"

ANNOTATION_RE = re.compile(
    r"@design[:\s(]+\s*(?P<id>[a-z0-9][a-z0-9-]*)(?:#(?P<constraint>[a-z0-9][a-z0-9-]*))?\s*\)?"
)


# ---------- data model -------------------------------------------------------


@dataclasses.dataclass
class Constraint:
    id: str
    description: str
    enforcement: list[str]
    bdd_tag: str | None = None
    codeql_query: str | None = None
    linter_rule: str | None = None
    hook_id: str | None = None
    severity: str = "error"


@dataclasses.dataclass
class Design:
    id: str
    title: str
    status: str
    owner: str
    created: dt.date
    updated: dt.date
    file: Path
    tags: list[str] = dataclasses.field(default_factory=list)
    supersedes: list[str] = dataclasses.field(default_factory=list)
    constraints: list[Constraint] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Annotation:
    design_id: str
    constraint_id: str | None
    file: Path
    line: int


@dataclasses.dataclass
class Finding:
    severity: str  # "error" or "warning"
    code: str  # short slug for filtering
    message: str
    location: str | None = None


# ---------- parsing ----------------------------------------------------------


VALID_STATUSES = {"draft", "approved", "scaffolded", "implemented", "deprecated"}
VALID_ENFORCEMENT = {"bdd", "codeql", "linter", "pre-commit", "claude-hook", "manual"}


def parse_design_doc(path: Path) -> tuple[Design | None, list[Finding]]:
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("+++\n"):
        findings.append(Finding(
            "error", "missing-frontmatter",
            f"{path}: file does not start with `+++` TOML frontmatter delimiter",
            str(path),
        ))
        return None, findings
    end = text.find("\n+++", 4)
    if end == -1:
        findings.append(Finding(
            "error", "unterminated-frontmatter",
            f"{path}: closing `+++` delimiter not found",
            str(path),
        ))
        return None, findings
    frontmatter = text[4:end]
    try:
        data = tomllib.loads(frontmatter)
    except tomllib.TOMLDecodeError as e:
        findings.append(Finding(
            "error", "invalid-toml",
            f"{path}: invalid TOML in frontmatter: {e}",
            str(path),
        ))
        return None, findings

    required = ["id", "title", "status", "owner", "created", "updated"]
    for field in required:
        if field not in data:
            findings.append(Finding(
                "error", "missing-field",
                f"{path}: required field `{field}` missing",
                str(path),
            ))
            return None, findings

    status = data["status"]
    if status not in VALID_STATUSES:
        findings.append(Finding(
            "error", "bad-status",
            f"{path}: status `{status}` not one of {sorted(VALID_STATUSES)}",
            str(path),
        ))

    constraints: list[Constraint] = []
    for raw in data.get("constraint", []):
        if "id" not in raw or "description" not in raw or "enforcement" not in raw:
            findings.append(Finding(
                "error", "bad-constraint",
                f"{path}: constraint missing id/description/enforcement",
                str(path),
            ))
            continue
        bad = [e for e in raw["enforcement"] if e not in VALID_ENFORCEMENT]
        if bad:
            findings.append(Finding(
                "error", "bad-enforcement",
                f"{path}#{raw['id']}: unknown enforcement {bad}",
                str(path),
            ))
        if not raw["enforcement"]:
            findings.append(Finding(
                "error", "no-enforcement",
                f"{path}#{raw['id']}: constraint has empty enforcement; the framework requires at least one mechanism",
                str(path),
            ))
        c = Constraint(
            id=raw["id"],
            description=raw["description"],
            enforcement=list(raw["enforcement"]),
            bdd_tag=raw.get("bdd_tag"),
            codeql_query=raw.get("codeql_query"),
            linter_rule=raw.get("linter_rule"),
            hook_id=raw.get("hook_id"),
            severity=raw.get("severity", "error"),
        )
        if "bdd" in c.enforcement and not c.bdd_tag:
            c.bdd_tag = f"@{data['id']}--{c.id}"
        if "codeql" in c.enforcement and not c.codeql_query:
            c.codeql_query = f"design_docs/codeql/{data['id']}/{c.id}.ql"
        constraints.append(c)

    design = Design(
        id=data["id"],
        title=data["title"],
        status=status,
        owner=data["owner"],
        created=_as_date(data["created"]),
        updated=_as_date(data["updated"]),
        file=path,
        tags=list(data.get("tags", [])),
        supersedes=list(data.get("supersedes", [])),
        constraints=constraints,
    )
    return design, findings


def _as_date(v: Any) -> dt.date:
    if isinstance(v, dt.date) and not isinstance(v, dt.datetime):
        return v
    if isinstance(v, dt.datetime):
        return v.date()
    return dt.date.fromisoformat(str(v))


# ---------- annotation scanning ---------------------------------------------


def scan_annotations(roots: list[Path], excludes: list[re.Pattern]) -> list[Annotation]:
    found: list[Annotation] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(rx.search(str(p)) for rx in excludes):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                for m in ANNOTATION_RE.finditer(line):
                    found.append(Annotation(
                        design_id=m.group("id"),
                        constraint_id=m.group("constraint"),
                        file=p,
                        line=i,
                    ))
    return found


# ---------- enforcement runners ---------------------------------------------


def run_codeql(design: Design, c: Constraint, cfg: dict) -> tuple[str, int, str | None]:
    """Returns (status, violation_count, error_message)."""
    codeql_cfg = cfg.get("codeql", {})
    if not codeql_cfg.get("enabled", False):
        return ("skipped", 0, "codeql not enabled in consistency.toml")
    db = codeql_cfg.get("database_dir")
    if not db:
        return ("error", 0, "codeql.database_dir not set")
    query_path = Path(c.codeql_query)
    if not query_path.exists():
        return ("error", 0, f"codeql query file not found: {query_path}")
    try:
        proc = subprocess.run(
            ["codeql", "query", "run", "--database", db, str(query_path), "--output", "-"],
            capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError:
        return ("error", 0, "codeql CLI not on PATH; install from https://github.com/github/codeql-cli-binaries")
    except subprocess.TimeoutExpired:
        return ("error", 0, f"codeql query timed out: {query_path}")
    if proc.returncode != 0:
        return ("error", 0, f"codeql exit {proc.returncode}: {proc.stderr.strip()[:400]}")
    # CodeQL `query run` prints a results table. Empty body == no violations.
    # We treat any non-blank body row as a violation; the agent can refine
    # this once a richer output format (e.g. SARIF) is wired up.
    rows = [r for r in proc.stdout.splitlines() if r.strip() and not r.startswith("|")]
    return ("violations" if rows else "no-violations", len(rows), None)


def run_bdd(design: Design, c: Constraint, cfg: dict) -> tuple[str, str | None]:
    bdd_cfg = cfg.get("bdd", {})
    cmd = bdd_cfg.get("command")
    if not cmd:
        return ("skipped", "bdd.command not set in consistency.toml")
    # tag_arg_format lets each BDD framework express how a tag is passed
    # on its CLI. Tokens: {tag} = the constraint's tag (e.g. "@foo--bar"),
    # {tag_unprefixed} = the same without the leading "@". The default
    # works for behave, pytest-bdd, cucumber-js, godog.
    args = cmd.split() + _render_tag_args(c, bdd_cfg)
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        return ("error", f"bdd command not found: {cmd}")
    except subprocess.TimeoutExpired:
        return ("error", f"bdd command timed out: {cmd}")
    return (("passing" if proc.returncode == 0 else "failing"), None)


def _render_tag_args(c: Constraint, bdd_cfg: dict) -> list[str]:
    if not c.bdd_tag:
        return []
    fmt = bdd_cfg.get("tag_arg_format", "--tags {tag}")
    rendered = fmt.format(tag=c.bdd_tag, tag_unprefixed=c.bdd_tag.lstrip("@"))
    return rendered.split()


# ---------- coverage cross-check --------------------------------------------


def run_bdd_with_coverage(c: Constraint, cfg: dict, root: Path) -> tuple[dict[str, set[int]] | None, dict[str, float], str | None]:
    """Run the BDD command for one constraint under coverage.

    Returns (covered_lines_by_file, coverage_fraction_by_file, error).
    Files are keyed by repo-relative POSIX path. covered_lines_by_file
    maps file → set of executed source lines. coverage_fraction_by_file
    maps file → 0.0..1.0 of statements executed in that file by the
    scoped run.
    """
    bdd_cfg = cfg.get("bdd", {})
    cov_cfg = bdd_cfg.get("coverage", {})
    if not cov_cfg.get("enabled", False):
        return (None, {}, "coverage not enabled in consistency.toml")
    bdd_command = bdd_cfg.get("command")
    if not bdd_command:
        return (None, {}, "bdd.command not set")
    template = cov_cfg.get("command", "coverage run -m {bdd_command} {tag_args} && coverage json -o {report_path}")
    report_path = Path(cov_cfg.get("report_path", ".consistency/coverage.json"))
    abs_report = (root / report_path).resolve()
    abs_report.parent.mkdir(parents=True, exist_ok=True)
    if abs_report.exists():
        abs_report.unlink()
    tag_args = " ".join(_render_tag_args(c, bdd_cfg))
    rendered = template.format(
        bdd_command=bdd_command, tag_args=tag_args, report_path=str(abs_report),
    )
    try:
        # Coverage commands typically need a shell because of the && and the
        # bdd_command itself may include flags. Running through the system
        # shell is acceptable here — the command originates from the
        # project's own consistency.toml, not user input.
        subprocess.run(rendered, shell=True, cwd=root, timeout=900, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        return (None, {}, f"coverage command timed out: {rendered}")
    if not abs_report.exists():
        return (None, {}, f"coverage report not produced at {abs_report}")
    fmt = cov_cfg.get("format", "coverage.py")
    try:
        if fmt == "coverage.py":
            covered, fractions = _parse_coverage_py(abs_report, root)
        elif fmt == "istanbul":
            covered, fractions = _parse_istanbul(abs_report, root)
        else:
            return (None, {}, f"unknown coverage format: {fmt}")
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return (None, {}, f"failed to parse {abs_report}: {e}")
    return (covered, fractions, None)


def _parse_coverage_py(report: Path, root: Path) -> tuple[dict[str, set[int]], dict[str, float]]:
    data = json.loads(report.read_text(encoding="utf-8"))
    covered: dict[str, set[int]] = {}
    fractions: dict[str, float] = {}
    for filename, payload in (data.get("files") or {}).items():
        rel = _rel_to(filename, root)
        covered[rel] = set(payload.get("executed_lines", []))
        summary = payload.get("summary", {})
        n_total = summary.get("num_statements", 0) or 0
        n_covered = summary.get("covered_lines", 0) or 0
        fractions[rel] = (n_covered / n_total) if n_total else 0.0
    return covered, fractions


def _parse_istanbul(report: Path, root: Path) -> tuple[dict[str, set[int]], dict[str, float]]:
    data = json.loads(report.read_text(encoding="utf-8"))
    covered: dict[str, set[int]] = {}
    fractions: dict[str, float] = {}
    for filename, payload in data.items():
        rel = _rel_to(filename, root)
        statement_map = payload.get("statementMap", {})
        statements = payload.get("s", {})
        executed_lines: set[int] = set()
        n_total = 0
        n_covered = 0
        for stmt_id, hits in statements.items():
            n_total += 1
            loc = statement_map.get(stmt_id, {}).get("start", {})
            line = loc.get("line")
            if hits and line is not None:
                executed_lines.add(line)
                n_covered += 1
        covered[rel] = executed_lines
        fractions[rel] = (n_covered / n_total) if n_total else 0.0
    return covered, fractions


def _rel_to(filename: str, root: Path) -> str:
    p = Path(filename)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return p.as_posix()


def cross_check_coverage(
    d: Design, c: Constraint, anns_for_constraint: list[Annotation],
    all_anns_for_design: list[Annotation],
    covered: dict[str, set[int]], fractions: dict[str, float],
    cfg: dict, root: Path,
) -> list[Finding]:
    """Compare annotations to coverage. Two findings:
       - annotation-uncovered: an annotation's ownership range is not exercised
       - covered-unannotated: a heavily-covered file has no annotation for this design
    """
    findings: list[Finding] = []

    # annotation-uncovered: per annotation, compute its ownership range
    # in the file (this annotation's line up to the next annotation in
    # the same file, or EOF), then check whether any line in that range
    # was executed.
    by_file: dict[Path, list[Annotation]] = {}
    for a in all_anns_for_design:
        by_file.setdefault(a.file, []).append(a)
    for f, alist in by_file.items():
        alist.sort(key=lambda a: a.line)
    for a in anns_for_constraint:
        rel = _rel(a.file, root)
        ranges_in_file = sorted({x.line for x in by_file.get(a.file, [])})
        try:
            idx = ranges_in_file.index(a.line)
            next_line = ranges_in_file[idx + 1] if idx + 1 < len(ranges_in_file) else None
        except ValueError:
            next_line = None
        upper = next_line if next_line is not None else 10**9
        executed = covered.get(rel, set())
        owned_executed = {ln for ln in executed if a.line <= ln < upper}
        if not owned_executed:
            findings.append(Finding(
                "warning", "annotation-uncovered",
                f"{rel}:{a.line}: @design {d.id}#{c.id} but no line in this annotation's range was executed by scenarios tagged {c.bdd_tag}",
                f"{rel}:{a.line}",
            ))

    # covered-unannotated: files heavily covered by this constraint's
    # scenarios that have no @design annotation for this design.
    threshold = float(cfg.get("bdd", {}).get("coverage", {}).get("heavy_coverage_threshold", 0.5))
    files_with_design_annotation = {_rel(a.file, root) for a in all_anns_for_design}
    for rel, frac in fractions.items():
        if frac < threshold:
            continue
        if rel in files_with_design_annotation:
            continue
        findings.append(Finding(
            "warning", "covered-unannotated",
            f"{rel}: {frac:.0%} of statements covered by scenarios for {d.id}#{c.id} but no @design annotation present",
            rel,
        ))

    return findings


# ---------- main check -------------------------------------------------------


def load_config(root: Path) -> dict:
    cfg_path = root / "consistency.toml"
    if not cfg_path.exists():
        return {}
    return tomllib.loads(cfg_path.read_text(encoding="utf-8"))


def collect_designs(root: Path) -> tuple[list[Design], list[Finding]]:
    findings: list[Finding] = []
    designs: list[Design] = []
    dd = root / "design_docs"
    if not dd.exists():
        findings.append(Finding(
            "error", "no-design-docs", f"{dd} does not exist; run design-init first", str(dd),
        ))
        return designs, findings
    for p in sorted(dd.glob("*.md")):
        if p.name == "manifest.toml":
            continue
        d, f = parse_design_doc(p)
        findings.extend(f)
        if d is not None:
            designs.append(d)
    return designs, findings


def check(root: Path, only_design: str | None, manifest_only: bool, strict: bool, with_coverage: bool = False) -> int:
    cfg = load_config(root)
    designs, findings = collect_designs(root)

    by_id: dict[str, Design] = {}
    for d in designs:
        if d.id in by_id:
            findings.append(Finding(
                "error", "duplicate-id",
                f"design id `{d.id}` defined in both {by_id[d.id].file} and {d.file}",
                str(d.file),
            ))
        by_id[d.id] = d

    proj = cfg.get("project", {})
    source_globs = proj.get("source_globs", ["src/**/*"])
    exclude_globs = proj.get("exclude_globs", [])
    excludes = [re.compile(_glob_to_re(g)) for g in exclude_globs]
    roots = [root / g.split("/**")[0] for g in source_globs]
    annotations = scan_annotations(roots, excludes)

    # Orphan annotations: design or constraint does not exist.
    annotations_by_design: dict[str, list[Annotation]] = {}
    for a in annotations:
        if a.design_id not in by_id:
            findings.append(Finding(
                "error", "orphan-annotation",
                f"{a.file}:{a.line}: @design points at unknown design `{a.design_id}`",
                f"{a.file}:{a.line}",
            ))
            continue
        d = by_id[a.design_id]
        if a.constraint_id and not any(c.id == a.constraint_id for c in d.constraints):
            findings.append(Finding(
                "error", "orphan-constraint",
                f"{a.file}:{a.line}: @design `{a.design_id}#{a.constraint_id}` constraint not found",
                f"{a.file}:{a.line}",
            ))
            continue
        annotations_by_design.setdefault(d.id, []).append(a)

    # Per-design checks.
    for d in designs:
        if only_design and d.id != only_design:
            continue
        ann = annotations_by_design.get(d.id, [])
        if d.status == "implemented" and not ann:
            findings.append(Finding(
                "error", "implemented-no-annotations",
                f"{d.file}: status=implemented but no @design annotations point here",
                str(d.file),
            ))
        if d.status == "deprecated" and ann:
            findings.append(Finding(
                "error", "deprecated-with-annotations",
                f"{d.file}: status=deprecated but {len(ann)} annotations still point here",
                str(d.file),
            ))
        if d.status in ("approved", "scaffolded") and ann:
            findings.append(Finding(
                "warning", "premature-annotations",
                f"{d.file}: status={d.status} but {len(ann)} annotations already exist",
                str(d.file),
            ))

        if not d.constraints:
            findings.append(Finding(
                "warning", "no-constraints",
                f"{d.file}: design has zero constraints; nothing is mechanically enforced",
                str(d.file),
            ))

        # If a multi-constraint design has bare-design annotations, warn.
        if len(d.constraints) > 1:
            bare = [a for a in ann if a.constraint_id is None]
            for a in bare:
                findings.append(Finding(
                    "warning", "ambiguous-annotation",
                    f"{a.file}:{a.line}: design `{d.id}` has multiple constraints; use `@design: {d.id}#<constraint-id>`",
                    f"{a.file}:{a.line}",
                ))

        if not manifest_only and d.status in ("scaffolded", "implemented"):
            for c in d.constraints:
                if d.status == "implemented":
                    constraint_ann = [a for a in ann if a.constraint_id == c.id]
                    if not constraint_ann and len(d.constraints) > 1:
                        findings.append(Finding(
                            c.severity, "constraint-no-annotations",
                            f"{d.file}#{c.id}: implemented but no annotations reference this constraint",
                            str(d.file),
                        ))

                if "codeql" in c.enforcement:
                    status, n, err = run_codeql(d, c, cfg)
                    if err:
                        findings.append(Finding(c.severity, "codeql-error", f"{d.id}#{c.id}: {err}", str(d.file)))
                    elif status == "violations":
                        findings.append(Finding(
                            c.severity, "codeql-violations",
                            f"{d.id}#{c.id}: codeql query reported {n} violation(s)",
                            str(d.file),
                        ))

                if "bdd" in c.enforcement and d.status == "implemented":
                    status, err = run_bdd(d, c, cfg)
                    if err:
                        findings.append(Finding(c.severity, "bdd-error", f"{d.id}#{c.id}: {err}", str(d.file)))
                    elif status == "failing":
                        findings.append(Finding(
                            c.severity, "bdd-failing",
                            f"{d.id}#{c.id}: bdd scenario tagged {c.bdd_tag} is failing",
                            str(d.file),
                        ))

                if with_coverage and "bdd" in c.enforcement and d.status == "implemented":
                    covered, fractions, cov_err = run_bdd_with_coverage(c, cfg, root)
                    if cov_err:
                        findings.append(Finding(
                            "warning", "coverage-error",
                            f"{d.id}#{c.id}: coverage cross-check skipped: {cov_err}",
                            str(d.file),
                        ))
                    elif covered is not None:
                        ann_for_c = [a for a in ann if a.constraint_id == c.id]
                        findings.extend(cross_check_coverage(
                            d, c, ann_for_c, ann, covered, fractions, cfg, root,
                        ))

    # Manifest regeneration.
    manifest_path = Path(cfg.get("checker", {}).get("manifest_path", "design_docs/manifest.toml"))
    write_manifest(root / manifest_path, designs, annotations_by_design, root)

    # Report.
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    for f in findings:
        prefix = "ERROR" if f.severity == "error" else "WARN "
        sys.stderr.write(f"{prefix} [{f.code}] {f.message}\n")
    sys.stderr.write(f"\n{len(errors)} error(s), {len(warnings)} warning(s)\n")
    if errors or (strict and warnings):
        return EXIT_DRIFT
    return EXIT_OK


def write_manifest(out: Path, designs: list[Design], anns: dict[str, list[Annotation]], root: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Generated by scripts/consistency.py — do not hand-edit.",
        f"generated_at = {dt.datetime.utcnow().isoformat(timespec='seconds')}Z",
        f'checker_version = "{VERSION}"',
        "",
    ]
    for d in designs:
        lines += [
            "[[design]]",
            f'id = "{d.id}"',
            f'title = {json.dumps(d.title)}',
            f'status = "{d.status}"',
            f'file = "{_rel(d.file, root)}"',
        ]
        for c in d.constraints:
            ca = [a for a in anns.get(d.id, []) if a.constraint_id == c.id]
            lines += [
                "  [[design.constraint]]",
                f'  id = "{c.id}"',
                f'  enforcement = {json.dumps(c.enforcement)}',
            ]
            if c.bdd_tag:
                lines.append(f'  bdd_tag = "{c.bdd_tag}"')
            if c.codeql_query:
                lines.append(f'  codeql_query = "{c.codeql_query}"')
            if ca:
                lines.append("  annotations = [")
                for a in ca:
                    lines.append(f'    "{_rel(a.file, root)}:{a.line}",')
                lines.append("  ]")
            else:
                lines.append("  annotations = []")
        lines.append("")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rel(p: Path, root: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def _glob_to_re(g: str) -> str:
    # Crude but good enough for the exclude-glob use case (matches substrings).
    return g.replace("**", ".*").replace("*", "[^/]*")


# ---------- CLI -------------------------------------------------------------


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="consistency", description=__doc__)
    p.add_argument("--design", help="Scope checks to a single design id")
    p.add_argument("--manifest-only", action="store_true",
                   help="Skip enforcement, regenerate manifest only")
    p.add_argument("--strict", action="store_true",
                   help="Treat warnings as errors")
    p.add_argument("--root", default=".", help="Project root (default: cwd)")
    p.add_argument("--with-coverage", action="store_true",
                   help="Also run the BDD coverage cross-check (heavy; CI use)")
    p.add_argument("--version", action="version", version=VERSION)
    args = p.parse_args(argv)
    return check(
        Path(args.root).resolve(), args.design, args.manifest_only,
        args.strict, args.with_coverage,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
