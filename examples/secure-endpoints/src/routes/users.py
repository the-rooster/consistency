from flask import Flask, request, jsonify
from ..auth import require_auth

app = Flask(__name__)


# @design: secure-endpoints#auth-required
@app.route("/users/<int:user_id>")
@require_auth
def get_user(user_id):
    return jsonify({"id": user_id, "viewer": request.user})
