"""FastAPI example models."""

from __future__ import annotations

from typing import TYPE_CHECKING, ForwardRef, Optional

from pydantic import BaseModel as PydanticModel

from earnorm import BaseModel, Email, Int, Many2one, One2many, String

if TYPE_CHECKING:
    from .models import Post

Post = ForwardRef("Post")


# Pydantic models for API
class UserCreate(PydanticModel):
    """User creation schema."""

    name: str
    email: str
    age: int


class UserResponse(PydanticModel):
    """User response schema."""

    id: str
    name: str
    email: str
    age: int


class PostCreate(PydanticModel):
    """Post creation schema."""

    title: str
    content: str
    author_id: str


class PostResponse(PydanticModel):
    """Post response schema."""

    id: str
    title: str
    content: str
    author_id: str


# EarnORM models
class User(BaseModel):
    """User model."""

    _name = "user"
    _indexes = [{"fields": [("email", 1)], "unique": True}]

    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)

    # Relations
    posts = One2many(Post, "author_id")

    def to_response(self) -> UserResponse:
        """Convert to response model."""

        for post in self.posts:
            post.to_response()

        return UserResponse(
            id=str(self.id), name=self.name, email=self.email, age=self.age
        )


class Post(BaseModel):
    """Post model."""

    _collection = "posts"

    title = String(required=True)
    content = String(required=True)

    # Relations
    author_id = Many2one("User", required=True)

    def to_response(self) -> PostResponse:
        """Convert to response model."""
        return PostResponse(
            id=str(self.id),
            title=self.title,
            content=self.content,
            author_id=str(self.author_id.id) if self.author_id else None,
        )
