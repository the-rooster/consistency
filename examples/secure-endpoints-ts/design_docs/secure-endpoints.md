+++
id = "secure-endpoints"
title = "All HTTP endpoints require authenticated callers"
status = "implemented"
owner = "andrew"
created = 2026-05-09
updated = 2026-05-09
tags = ["security", "http"]

[[constraint]]
id = "auth-required"
description = "Every Express route registration includes the `requireAuth` middleware in its argument list."
enforcement = ["semgrep", "codeql", "bdd"]
+++

## Background

Same property as the Python example: every HTTP endpoint must require
an authenticated caller. In Express, route handlers are registered by
calling `app.get(path, ...handlers)`. The `requireAuth` middleware
must appear in the handler chain for every such registration.

## Acceptance criteria

- Every call to `app.get | post | put | patch | delete(path, ...)`
  passes `requireAuth` somewhere in its handler chain.
- A request without a valid `Authorization: Bearer <token>` header
  returns 401.
- A valid token attaches the caller's identity to `req.user` for the
  next handler to read.

## Out of scope

- Role-based authorization (separate design).
- API key auth for service-to-service traffic (separate design).

## Notes

The CodeQL query encodes the structural property; the cucumber-js
scenario encodes the runtime behavior. Both must hold.
