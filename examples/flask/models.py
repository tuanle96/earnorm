"""Flask example models."""

from dataclasses import dataclass
from typing import List, Optional

from earnorm import BaseModel, Email, Int, Many2one, One2many, String


@dataclass
class UserDTO:
    """User data transfer object."""

    id: Optional[str] = None
    name: str = ""
    email: str = ""
    age: int = 0


@dataclass
class PostDTO:
    """Post data transfer object."""

    id: Optional[str] = None
    title: str = ""
    content: str = ""
    author_id: Optional[str] = None


class User(BaseModel):
    """User model."""

    _collection = "users"

    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)

    # Relations
    posts = One2many("Post", "author_id")

    def to_dto(self) -> UserDTO:
        """Convert to DTO."""
        return UserDTO(id=str(self.id), name=self.name, email=self.email, age=self.age)

    @classmethod
    def from_dto(cls, dto: UserDTO) -> "User":
        """Create from DTO."""
        return cls(name=dto.name, email=dto.email, age=dto.age)


class Post(BaseModel):
    """Post model."""

    _collection = "posts"

    title = String(required=True)
    content = String(required=True)

    # Relations
    author_id = Many2one("User", required=True)

    def to_dto(self) -> PostDTO:
        """Convert to DTO."""
        return PostDTO(
            id=str(self.id),
            title=self.title,
            content=self.content,
            author_id=str(self.author_id.id) if self.author_id else None,
        )

    @classmethod
    def from_dto(cls, dto: PostDTO, author: User) -> "Post":
        """Create from DTO."""
        return cls(title=dto.title, content=dto.content, author_id=author)
