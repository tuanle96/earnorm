"""Django example models."""

from typing import Any, Dict, Optional

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse

from earnorm import BaseModel, Email, Int, Many2one, One2many, String


class User(BaseModel):
    """User model."""

    _collection = "users"

    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)

    # Relations
    posts = One2many("Post", "author_id")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON response."""
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "age": self.age,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create from dict."""
        return cls(name=data["name"], email=data["email"], age=data["age"])


class Post(BaseModel):
    """Post model."""

    _collection = "posts"

    title = String(required=True)
    content = String(required=True)

    # Relations
    author_id = Many2one("User", required=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON response."""
        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "author_id": str(self.author_id.id) if self.author_id else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], author: User) -> "Post":
        """Create from dict."""
        return cls(title=data["title"], content=data["content"], author_id=author)
