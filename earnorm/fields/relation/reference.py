"""Reference field type."""

from typing import Any, Optional, TypeVar, cast

from bson import ObjectId

from earnorm.fields.relation.base import BaseRelationField
from earnorm.types import ModelInterface

M = TypeVar("M", bound=ModelInterface)


class ReferenceField(BaseRelationField[M]):
    """Reference field for storing references to other documents.

    This field stores a reference to another document using its ObjectId.
    The referenced document can be loaded asynchronously when needed.

    Examples:
        >>> class User(BaseModel):
        ...     name = StringField()
        ...
        >>> class Post(BaseModel):
        ...     title = StringField()
        ...     author = ReferenceField(User)
        ...
        >>> # Create user and post
        >>> user = await User.create(name="John")
        >>> post = Post(title="Hello", author=user)
        >>> await post.save()
        ...
        >>> # Load post and author
        >>> post = await Post.find_by_id(post.id)
        >>> author = await post.author.async_convert()
        >>> print(author.name)
        'John'
    """

    def convert(self, value: Any) -> M:
        """Convert value to ObjectId.

        Args:
            value: Value to convert (can be ObjectId, model instance, or string)

        Returns:
            Converted ObjectId wrapped in a model instance

        Raises:
            ValueError: If value cannot be converted to ObjectId
        """
        if value is None:
            return cast(M, None)
        if isinstance(value, ObjectId):
            return cast(M, value)
        if isinstance(value, self.model):
            return cast(M, value.id)  # type: ignore
        return cast(M, ObjectId(str(value)))

    def to_dict(self, value: Optional[M]) -> Optional[str]:
        """Convert ObjectId to string.

        Args:
            value: ObjectId to convert

        Returns:
            String representation of ObjectId or None if value is None
        """
        if value is None:
            return None
        return str(value)

    def to_mongo(self, value: Optional[M]) -> Optional[ObjectId]:
        """Convert Python ObjectId to MongoDB ObjectId.

        Args:
            value: ObjectId to convert

        Returns:
            MongoDB ObjectId or None if value is None
        """
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))

    def from_mongo(self, value: Any) -> M:
        """Convert MongoDB ObjectId to Python ObjectId.

        Args:
            value: MongoDB value to convert

        Returns:
            Python ObjectId wrapped in a model instance

        Raises:
            ValueError: If value cannot be converted to ObjectId
        """
        if value is None:
            return cast(M, None)
        if isinstance(value, ObjectId):
            return cast(M, value)
        return cast(M, ObjectId(str(value)))

    async def async_convert(self, value: Any) -> Optional[M]:
        """Convert value to model instance asynchronously.

        This method loads the referenced document from the database.

        Args:
            value: Value to convert (can be ObjectId, model instance, or string)

        Returns:
            Referenced model instance or None if value is None

        Raises:
            ValueError: If value cannot be converted to ObjectId
            DocumentNotFoundError: If referenced document is not found
        """
        if value is None:
            return None
        if isinstance(value, self.model):
            return value
        if isinstance(value, ObjectId):
            return await self.model.find_by_id(value)  # type: ignore
        return await self.model.find_by_id(ObjectId(str(value)))  # type: ignore

    async def async_to_dict(self, value: Optional[M]) -> Optional[str]:
        """Convert model instance to dict representation asynchronously.

        Args:
            value: Model instance to convert

        Returns:
            String representation of model's ID or None if value is None
        """
        if value is None:
            return None
        return str(value.id)  # type: ignore

    async def async_to_mongo(self, value: Optional[M]) -> Optional[ObjectId]:
        """Convert Python value to MongoDB value asynchronously.

        Args:
            value: Model instance to convert

        Returns:
            Model's ID as ObjectId or None if value is None
        """
        if value is None:
            return None
        return value.id  # type: ignore

    async def async_from_mongo(self, value: Any) -> Optional[M]:
        """Convert MongoDB value to Python value asynchronously.

        This method loads the referenced document from the database.

        Args:
            value: MongoDB value to convert

        Returns:
            Referenced model instance or None if value is None

        Raises:
            ValueError: If value cannot be converted to ObjectId
            DocumentNotFoundError: If referenced document is not found
        """
        if value is None:
            return None
        if isinstance(value, self.model):
            return value
        if isinstance(value, ObjectId):
            return await self.model.find_by_id(value)  # type: ignore
        return await self.model.find_by_id(ObjectId(str(value)))  # type: ignore
