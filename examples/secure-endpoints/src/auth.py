"""Auth middleware used by every route handler in src/routes/."""

from functools import wraps
from flask import request, abort


_TOKENS = {"tok-abc": "andrew"}


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        user = _TOKENS.get(token)
        if user is None:
            abort(401)
        request.user = user
        return view(*args, **kwargs)
    return wrapped
