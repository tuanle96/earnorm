"""Flask integration example."""

from typing import Dict, List

from flask import Flask, jsonify, request
from flask.views import MethodView

import earnorm
from earnorm import BaseModel, Email, Int, String

app = Flask(__name__)


class User(BaseModel):
    """User model."""

    _collection = "users"
    _name = "user"
    _indexes = [{"email": 1}]

    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)


@app.before_first_request
async def init_earnorm():
    """Initialize EarnORM."""
    await earnorm.init(
        mongo_uri="mongodb://localhost:27017",
        database="earnorm_example",
    )


class UserAPI(MethodView):
    """User API endpoints."""

    async def post(self):
        """Create a new user."""
        try:
            data = request.get_json()
            user = User(
                name=data["name"],
                email=data["email"],
                age=data["age"],
            )
            await user.save()
            return jsonify(
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "age": user.age,
                }
            )
        except (KeyError, ValueError) as e:
            return jsonify({"error": str(e)}), 400

    async def get(self, user_id=None):
        """Get users or a specific user."""
        if user_id is None:
            # List users with optional age filter
            age_gt = request.args.get("age_gt")
            domain = [("age", ">", int(age_gt))] if age_gt else None
            users = await User.search(domain)
            return jsonify(
                {
                    "users": [
                        {
                            "id": user.id,
                            "name": user.name,
                            "email": user.email,
                            "age": user.age,
                        }
                        for user in users
                    ]
                }
            )
        else:
            # Get specific user
            user = await User.find_one([("_id", "=", user_id)])
            if not user.exists():
                return jsonify({"error": "User not found"}), 404
            record = user.ensure_one()
            return jsonify(
                {
                    "id": record.id,
                    "name": record.name,
                    "email": record.email,
                    "age": record.age,
                }
            )

    async def delete(self, user_id):
        """Delete a user by ID."""
        user = await User.find_one([("_id", "=", user_id)])
        if not user.exists():
            return jsonify({"error": "User not found"}), 404
        await user.unlink()
        return jsonify({"message": "User deleted"})


# Register API routes
user_view = UserAPI.as_view("user_api")
app.add_url_rule("/users/", view_func=user_view, methods=["GET", "POST"])
app.add_url_rule(
    "/users/<string:user_id>", view_func=user_view, methods=["GET", "DELETE"]
)


if __name__ == "__main__":
    app.run(debug=True)
