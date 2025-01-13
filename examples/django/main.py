"""Django integration example."""

import json
from typing import List

from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import earnorm
from earnorm import BaseModel, Email, Int, String


class User(BaseModel):
    """User model."""

    _collection = "users"
    _name = "user"
    _indexes = [{"email": 1}]

    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)


async def init_earnorm():
    """Initialize EarnORM."""
    await earnorm.init(
        mongo_uri="mongodb://localhost:27017",
        database="earnorm_example",
    )


@csrf_exempt
@require_http_methods(["POST"])
async def create_user(request):
    """Create a new user."""
    try:
        data = json.loads(request.body)
        user = User(
            name=data["name"],
            email=data["email"],
            age=data["age"],
        )
        await user.save()
        return JsonResponse(
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "age": user.age,
            }
        )
    except (KeyError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)


@require_http_methods(["GET"])
async def list_users(request):
    """List all users with optional age filter."""
    age_gt = request.GET.get("age_gt")
    domain = [("age", ">", int(age_gt))] if age_gt else None
    users = await User.search(domain)
    return JsonResponse(
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


@require_http_methods(["GET"])
async def get_user(request, user_id):
    """Get a user by ID."""
    user = await User.find_one([("_id", "=", user_id)])
    if not user.exists():
        return JsonResponse({"error": "User not found"}, status=404)
    record = user.ensure_one()
    return JsonResponse(
        {
            "id": record.id,
            "name": record.name,
            "email": record.email,
            "age": record.age,
        }
    )


@csrf_exempt
@require_http_methods(["DELETE"])
async def delete_user(request, user_id):
    """Delete a user by ID."""
    user = await User.find_one([("_id", "=", user_id)])
    if not user.exists():
        return JsonResponse({"error": "User not found"}, status=404)
    await user.unlink()
    return JsonResponse({"message": "User deleted"})


urlpatterns = [
    path("users/", create_user, name="create_user"),
    path("users/", list_users, name="list_users"),
    path("users/<str:user_id>/", get_user, name="get_user"),
    path("users/<str:user_id>/", delete_user, name="delete_user"),
]
