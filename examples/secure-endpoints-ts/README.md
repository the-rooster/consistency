# Worked example: secure-endpoints-ts

The same `secure-endpoints` design as `examples/secure-endpoints/`, but
built on Express + TypeScript + cucumber-js + a CodeQL JavaScript
query. Demonstrates that the framework is language-neutral and shows
the bits that *do* vary by language:

- `[codeql].language = "javascript"` (covers both JS and TS)
- `[bdd].command = "npx cucumber-js"`
- `[bdd].tag_arg_format = "--tags {tag}"` (cucumber-js convention,
  same as the default)
- The constraint declares both `semgrep` and `codeql` enforcement to
  illustrate the two options side-by-side. The Semgrep rule is
  ~25 lines of YAML; the CodeQL query is ~30 lines using the
  `python` import. For this property either is sufficient — Semgrep
  is the recommended default per the framework rubric, and CodeQL
  is shown for comparison.

## Project layout

```
secure-endpoints-ts/
├── consistency.toml
├── package.json
├── tsconfig.json
├── design_docs/
│   ├── secure-endpoints.md
│   └── codeql/secure-endpoints/auth-required.ql
├── features/
│   ├── secure-endpoints.feature
│   └── step_definitions/secure-endpoints.steps.ts
└── src/
    ├── auth.ts
    └── routes/
        ├── users.ts
        └── orders.ts
```

## Try it

From this directory:

```
python ../../scripts/consistency.py --root .
```

The checker parses the design, scans `src/**/*` for `@design`
annotations, regenerates `manifest.toml`, and (if CodeQL CLI and a
JavaScript database are available) runs the query.
