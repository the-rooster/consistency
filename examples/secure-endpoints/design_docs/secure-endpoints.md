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
description = "Every Flask route handler is decorated with @require_auth and reads the caller identity from the request context."
enforcement = ["codeql", "bdd"]
+++

## Background

The application exposes HTTP endpoints under `src/routes/`. Several
incidents in the past year traced back to a developer adding a new
endpoint and forgetting to decorate it with the auth middleware. Two
of these endpoints leaked customer data before the omission was
caught. Code review caught some, but not all — by the time a missing
decorator gets to review, the reviewer is already pattern-matching
against neighboring code, so the omission is invisible in the diff.

We want this to be a structural property, enforced by tooling, not a
discipline maintained by reviewers.

## Acceptance criteria

- Every function bound to an HTTP route via `@app.route(...)` is
  decorated with `@require_auth`.
- A request to any route without a valid session token returns 401.
- A request with a valid token attaches the caller's identity to
  `request.user` for the handler to read.

## Out of scope

- Authorization / RBAC beyond "authenticated yes/no". A separate
  design will add role checks; this design only ensures *some* auth
  check happens.
- API key auth for service-to-service traffic. Same — separate design.

## Notes

The CodeQL query encodes the structural property; the BDD scenario
encodes the runtime behavior. Both must hold.
