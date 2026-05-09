/**
 * @design secure-endpoints#auth-required
 *
 * Returns Express route registrations whose argument list does not
 * reference `requireAuth`. Empty result set means the constraint
 * holds for every route in the codebase.
 *
 * Approach: select call expressions whose callee is a method named
 * one of {get, post, put, patch, delete, all} on a value named
 * something like `app` or `router`. For each, require that at least
 * one argument is (or references) `requireAuth`. Anything failing
 * that requirement is a violation.
 *
 * Note: this is an approximation — it pattern-matches on the
 * receiver name rather than tracking the actual Express `Application`
 * type. For a stricter version, switch the receiver test to a type
 * predicate using the JavaScript framework models pack.
 *
 * @kind problem
 * @problem.severity error
 * @id consistency/secure-endpoints/auth-required
 */

import javascript

predicate isRouterReceiver(Expr e) {
  exists(string name | name = e.(VarAccess).getName() |
    name = "app" or name.matches("%router%") or name.matches("%Router%")
  )
}

predicate isRouteMethod(string m) {
  m in ["get", "post", "put", "patch", "delete", "all", "use"]
}

predicate referencesRequireAuth(Expr e) {
  e.(VarAccess).getName() = "requireAuth"
  or
  exists(VarAccess v | v.getName() = "requireAuth" and e.getAChildExpr*() = v)
}

from MethodCallExpr call
where
  isRouterReceiver(call.getReceiver())
  and isRouteMethod(call.getMethodName())
  and not exists(int i | i >= 1 and referencesRequireAuth(call.getArgument(i)))
select call,
  "Route registration `" + call.getMethodName()
  + "` does not include requireAuth in its handler chain."
