"""Django example views."""

import json
from typing import Any, Dict

from bson import ObjectId
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from models import Post, User

from earnorm import init


@method_decorator(csrf_exempt, name="dispatch")
class UserView(View):
    """User view."""

    async def post(self, request: Any) -> JsonResponse:
        """Create a new user."""
        try:
            data = json.loads(request.body)

            # Check if email exists
            existing = await User.find_one({"email": data["email"]})
            if existing:
                return JsonResponse({"error": "Email already registered"}, status=400)

            # Create user
            user = User.from_dict(data)
            await user.save()

            return JsonResponse(user.to_dict(), status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    async def get(self, request: Any, user_id: str = None) -> JsonResponse:
        """Get user(s)."""
        try:
            if user_id:
                # Get specific user
                user = await User.find_one({"_id": ObjectId(user_id)})
                if not user:
                    return JsonResponse({"error": "User not found"}, status=404)
                return JsonResponse(user.to_dict())

            # List all users
            users = await User.find({})
            return JsonResponse([user.to_dict() for user in users], safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class PostView(View):
    """Post view."""

    async def post(self, request: Any) -> JsonResponse:
        """Create a new post."""
        try:
            data = json.loads(request.body)

            # Check if author exists
            author = await User.find_one({"_id": ObjectId(data["author_id"])})
            if not author:
                return JsonResponse({"error": "Author not found"}, status=404)

            # Create post
            post = Post.from_dict(data, author)
            await post.save()

            return JsonResponse(post.to_dict(), status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    async def get(self, request: Any, post_id: str = None) -> JsonResponse:
        """Get post(s)."""
        try:
            if post_id:
                # Get specific post
                post = await Post.find_one({"_id": ObjectId(post_id)})
                if not post:
                    return JsonResponse({"error": "Post not found"}, status=404)
                return JsonResponse(post.to_dict())

            # List all posts
            posts = await Post.find({})
            return JsonResponse([post.to_dict() for post in posts], safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class UserPostView(View):
    """User posts view."""

    async def get(self, request: Any, user_id: str) -> JsonResponse:
        """Get posts by user."""
        try:
            # Check if user exists
            user = await User.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Get user's posts
            posts = await user.posts
            return JsonResponse([post.to_dict() for post in posts], safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
