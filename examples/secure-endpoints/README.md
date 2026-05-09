# Worked example: secure-endpoints

A miniature Flask-style project showing how a single design flows
through the framework. The project here is illustrative — not meant
to run as-is — and shows the artifacts each pipeline step produces.

## Project layout

```
secure-endpoints/
├── consistency.toml
├── design_docs/
│   ├── secure-endpoints.md
│   ├── manifest.toml
│   └── codeql/
│       └── secure-endpoints/
│           └── auth-required.ql
├── features/
│   └── secure-endpoints.feature
└── src/
    ├── auth.py
    └── routes/
        ├── users.py
        └── orders.py
```

## What each file shows

- **`design_docs/secure-endpoints.md`** — the approved design, with
  a single `auth-required` constraint enforced by both `codeql` and
  `bdd`.
- **`design_docs/codeql/.../auth-required.ql`** — the CodeQL query
  that returns route handlers not wrapped in `require_auth`.
  Empty result set = constraint holds. The query header points back
  at the design.
- **`features/secure-endpoints.feature`** — a Gherkin scenario tagged
  `@secure-endpoints--auth-required` covering the runtime behavior.
- **`src/routes/*.py`** — handlers carrying the
  `@design: secure-endpoints#auth-required` annotation. Drift checker
  uses these to produce the design ↔ code map in `manifest.toml`.

## Try it

From this directory:

```
python3 ../../scripts/consistency.py --root .
```

The checker parses the design, scans the source for annotations,
regenerates `manifest.toml`, and (if `codeql` is available and a
database has been built) runs the query.
