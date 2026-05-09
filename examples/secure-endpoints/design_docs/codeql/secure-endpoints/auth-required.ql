/**
 * @design secure-endpoints#auth-required
 *
 * Returns Flask route handlers that are not decorated with
 * `require_auth`. Empty result set means the constraint holds for
 * every route in the codebase.
 *
 * Approach: select every function that carries an `@app.route(...)`
 * decorator, then exclude those that also carry an
 * `@require_auth` decorator. Anything left is a violation.
 *
 * @kind problem
 * @problem.severity error
 * @id consistency/secure-endpoints/auth-required
 */

import python

predicate hasDecorator(Function f, string name) {
  exists(Decorator d |
    d = f.getADecorator() and
    (
      d.(Name).getId() = name
      or
      d.(Call).getFunc().(Name).getId() = name
      or
      d.(Attribute).getName() = name
    )
  )
}

from Function f
where
  hasDecorator(f, "route")
  and not hasDecorator(f, "require_auth")
select f, "Route handler `" + f.getName() + "` is not wrapped in require_auth."
