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

        Examples:
            >>> field = ReferenceField(User)
            >>> field.convert("507f1f77bcf86cd799439011")
            ObjectId('507f1f77bcf86cd799439011')
            >>> field.convert(None)
            None
        """
        if value is None:
            return cast(M, None)
        if isinstance(value, ObjectId):
            return cast(M, value)
        if isinstance(value, self.model):
            return cast(M, value.id)
        return cast(M, ObjectId(str(value)))

    def to_dict(self, value: Optional[M]) -> Optional[str]:
        """Convert ObjectId to string.

        Args:
            value: ObjectId to convert

        Returns:
            String representation of ObjectId or None if value is None

        Examples:
            >>> field = ReferenceField(User)
            >>> field.to_dict(ObjectId("507f1f77bcf86cd799439011"))
            '507f1f77bcf86cd799439011'
            >>> field.to_dict(None)
            None
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, self.model):
            return str(value.id)
        return str(value)

    def to_mongo(self, value: Optional[M]) -> Optional[ObjectId]:
        """Convert Python ObjectId to MongoDB ObjectId.

        Args:
            value: ObjectId to convert

        Returns:
            MongoDB ObjectId or None if value is None

        Examples:
            >>> field = ReferenceField(User)
            >>> field.to_mongo("507f1f77bcf86cd799439011")
            ObjectId('507f1f77bcf86cd799439011')
            >>> field.to_mongo(None)
            None
        """
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return value
        if isinstance(value, self.model):
            return ObjectId(value.id)
        return ObjectId(str(value))

    def from_mongo(self, value: Any) -> M:
        """Convert MongoDB ObjectId to Python ObjectId.

        Args:
            value: MongoDB value to convert

        Returns:
            Python ObjectId wrapped in a model instance

        Raises:
            ValueError: If value cannot be converted to ObjectId

        Examples:
            >>> field = ReferenceField(User)
            >>> field.from_mongo(ObjectId("507f1f77bcf86cd799439011"))
            ObjectId('507f1f77bcf86cd799439011')
            >>> field.from_mongo(None)
            None
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

        Examples:
            >>> field = ReferenceField(User)
            >>> user = await field.async_convert("507f1f77bcf86cd799439011")
            >>> print(user.name)
            'John'
        """
        if value is None:
            return None
        if isinstance(value, self.model):
            return value
        if isinstance(value, ObjectId):
            result = await self.model.find_by_id(str(value))
            return cast(M, result)
        result = await self.model.find_by_id(str(ObjectId(str(value))))
        return cast(M, result)

    async def async_to_dict(self, value: Optional[M]) -> Optional[str]:
        """Convert model instance to dict representation asynchronously.

        Args:
            value: Model instance to convert

        Returns:
            String representation of model's ID or None if value is None

        Examples:
            >>> field = ReferenceField(User)
            >>> user = await User.find_by_id("507f1f77bcf86cd799439011")
            >>> await field.async_to_dict(user)
            '507f1f77bcf86cd799439011'
        """
        if value is None:
            return None
        return str(value.id)

    async def async_to_mongo(self, value: Optional[M]) -> Optional[ObjectId]:
        """Convert Python value to MongoDB value asynchronously.

        Args:
            value: Model instance to convert

        Returns:
            Model's ID as ObjectId or None if value is None

        Examples:
            >>> field = ReferenceField(User)
            >>> user = await User.find_by_id("507f1f77bcf86cd799439011")
            >>> await field.async_to_mongo(user)
            ObjectId('507f1f77bcf86cd799439011')
        """
        if value is None:
            return None
        return ObjectId(value.id)

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

        Examples:
            >>> field = ReferenceField(User)
            >>> user = await field.async_from_mongo(ObjectId("507f1f77bcf86cd799439011"))
            >>> print(user.name)
            'John'
        """
        if value is None:
            return None
        if isinstance(value, self.model):
            return value
        if isinstance(value, ObjectId):
            result = await self.model.find_by_id(str(value))
            return cast(M, result)
        result = await self.model.find_by_id(str(ObjectId(str(value))))
        return cast(M, result)
