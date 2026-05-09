from flask import Flask, request, jsonify
from ..auth import require_auth

app = Flask(__name__)


# @design: secure-endpoints#auth-required
@app.route("/orders/<int:order_id>")
@require_auth
def get_order(order_id):
    return jsonify({"id": order_id, "viewer": request.user})
