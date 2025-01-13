"""Flask example application."""

from typing import Dict, List, Optional

from bson import ObjectId
from flask import Flask, jsonify, request
from models import Post, PostDTO, User, UserDTO

from earnorm import init

# Create Flask app
app = Flask(__name__)


@app.before_first_request
async def before_first_request():
    """Initialize EarnORM before first request."""
    await init(mongo_uri="mongodb://localhost:27017", database="earnorm_flask_example")


# User endpoints
@app.route("/users", methods=["POST"])
async def create_user():
    """Create a new user."""
    data = request.get_json()
    user_dto = UserDTO(**data)

    # Check if email exists
    existing = await User.find_one({"email": user_dto.email})
    if existing:
        return jsonify({"error": "Email already registered"}), 400

    # Create user
    user = User.from_dto(user_dto)
    await user.save()

    return jsonify(user.to_dto().__dict__), 201


@app.route("/users", methods=["GET"])
async def list_users():
    """List all users."""
    users = await User.find({})
    return jsonify([user.to_dto().__dict__ for user in users])


@app.route("/users/<user_id>", methods=["GET"])
async def get_user(user_id: str):
    """Get a specific user."""
    user = await User.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dto().__dict__)


# Post endpoints
@app.route("/posts", methods=["POST"])
async def create_post():
    """Create a new post."""
    data = request.get_json()
    post_dto = PostDTO(**data)

    # Check if author exists
    author = await User.find_one({"_id": ObjectId(post_dto.author_id)})
    if not author:
        return jsonify({"error": "Author not found"}), 404

    # Create post
    post = Post.from_dto(post_dto, author)
    await post.save()

    return jsonify(post.to_dto().__dict__), 201


@app.route("/posts", methods=["GET"])
async def list_posts():
    """List all posts."""
    posts = await Post.find({})
    return jsonify([post.to_dto().__dict__ for post in posts])


@app.route("/posts/<post_id>", methods=["GET"])
async def get_post(post_id: str):
    """Get a specific post."""
    post = await Post.find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"error": "Post not found"}), 404

    return jsonify(post.to_dto().__dict__)


@app.route("/users/<user_id>/posts", methods=["GET"])
async def get_user_posts(user_id: str):
    """Get all posts by a specific user."""
    user = await User.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    posts = await user.posts
    return jsonify([post.to_dto().__dict__ for post in posts])


if __name__ == "__main__":
    app.run(debug=True)
