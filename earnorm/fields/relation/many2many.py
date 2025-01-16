"""Many-to-many field type.

This module provides the Many2manyField class for handling many-to-many relationships
between models in the EarnORM framework.
"""

from typing import Any, List, Optional, TypeVar, Union, cast

from bson import ObjectId

from earnorm.fields.relation.base import BaseRelationField
from earnorm.types import ModelInterface

M = TypeVar("M", bound=ModelInterface)
ItemType = Union[ObjectId, ModelInterface, str]


class Many2manyField(BaseRelationField[M]):
    """Many-to-many field for storing references to multiple related documents.

    This field is used to establish a many-to-many relationship between two models.
    For example, a User can have multiple Groups, and a Group can have multiple Users.
    The field stores a list of ObjectIds that reference the related documents.

    Examples:
        ```python
        class User(Model):
            name = StringField()
            groups = Many2manyField(Group, field="members")

        class Group(Model):
            name = StringField()
            members = Many2manyField(User, field="groups")

        # Create users and groups
        user1 = await User.create(name="John")
        user2 = await User.create(name="Jane")

        group1 = await Group.create(name="Admins")
        group2 = await Group.create(name="Users")

        # Add users to groups
        await user1.groups.add(group1, group2)
        await user2.groups.add(group2)

        # Get all groups for a user
        user_groups = await user1.groups.async_convert()
        for group in user_groups:
            print(f"{user1.name} is in {group.name}")
            # Output:
            # John is in Admins
            # John is in Users

        # Get all members of a group
        group_members = await group2.members.async_convert()
        for member in group_members:
            print(f"{member.name} is a member of {group2.name}")
            # Output:
            # John is a member of Users
            # Jane is a member of Users
        ```

    Note:
        - The field stores a list of ObjectIds that reference the related documents
        - The related documents are loaded lazily when accessed
        - The field supports both synchronous and asynchronous access
        - The field can be used in queries to find related documents
        - Both sides of the relationship must be defined with Many2manyField
    """

    def __init__(
        self,
        model: type[M],
        field: str,
        *,
        required: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            model: Related model class that this field references
            field: Field name in the related model that references back to this model
            required: Whether this field is required
            **kwargs: Additional field options passed to the parent class

        Examples:
            ```python
            # Optional groups field
            groups = Many2manyField(Group, field="members")

            # Required roles field
            roles = Many2manyField(Role, field="users", required=True)
            ```
        """
        super().__init__(
            model=model,
            required=required,
            **kwargs,
        )
        self.field = field

    def convert(self, value: Any) -> M:
        """Convert value to list of ObjectId.

        Args:
            value: Value to convert, can be None, list of ObjectId, list of model instances,
                  or list of strings that can be converted to ObjectId

        Returns:
            List of ObjectId instances

        Raises:
            ValueError: If value is not None and not a list/tuple, or if any item cannot
                       be converted to ObjectId
        """
        if value is None:
            return cast(M, [])
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"Expected list or tuple, got {type(value)}")
        result: List[ObjectId] = []
        for item_value in cast(List[ItemType], value):
            if isinstance(item_value, ObjectId):
                result.append(item_value)
            elif isinstance(item_value, self.model):
                result.append(item_value.id)  # type: ignore
            else:
                result.append(ObjectId(str(item_value)))
        return cast(M, result)

    def to_dict(self, value: Optional[M]) -> Optional[List[str]]:
        """Convert list of ObjectId to list of string for JSON serialization.

        Args:
            value: List of ObjectId instances or None

        Returns:
            List of string representations of ObjectIds, or None if input is None
        """
        if value is None:
            return None
        return [str(item) for item in cast(List[ObjectId], value)]

    def to_mongo(self, value: Optional[M]) -> Optional[List[ObjectId]]:
        """Convert Python list of ObjectId to MongoDB array.

        Args:
            value: List of ObjectId instances or None

        Returns:
            List of ObjectId instances ready for MongoDB storage, or None if input is None
        """
        if value is None:
            return None
        return [
            item if isinstance(item, ObjectId) else ObjectId(str(item))
            for item in cast(List[Any], value)
        ]

    def from_mongo(self, value: Any) -> M:
        """Convert MongoDB array to Python list of ObjectId.

        Args:
            value: MongoDB array value or None

        Returns:
            List of ObjectId instances

        Raises:
            ValueError: If value is not None and not a list, or if any item cannot be
                       converted to ObjectId
        """
        if value is None:
            return cast(M, [])
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[ObjectId] = []
        for item_value in cast(List[ItemType], value):
            if isinstance(item_value, ObjectId):
                result.append(item_value)
            else:
                result.append(ObjectId(str(item_value)))
        return cast(M, result)

    async def async_convert(self, value: Any) -> M:
        """Convert value to list of model instances asynchronously.

        Args:
            value: Value to convert, can be None, list of ObjectId, list of model instances,
                  or list of strings that can be converted to ObjectId

        Returns:
            List of model instances

        Raises:
            ValueError: If value is not None and not a list/tuple
        """
        if value is None:
            return cast(M, [])
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"Expected list or tuple, got {type(value)}")
        result: List[M] = []
        for item_value in cast(List[ItemType], value):
            if isinstance(item_value, self.model):
                result.append(item_value)  # type: ignore
            elif isinstance(item_value, ObjectId):
                model = await self.model.find_by_id(item_value)  # type: ignore
                if model is not None:
                    result.append(model)  # type: ignore
            else:
                model = await self.model.find_by_id(ObjectId(str(item_value)))  # type: ignore
                if model is not None:
                    result.append(model)  # type: ignore
        return cast(M, result)

    async def async_to_dict(self, value: Optional[M]) -> Optional[List[str]]:
        """Convert list of model instances to list of string asynchronously.

        Args:
            value: List of model instances or None

        Returns:
            List of string representations of model IDs, or None if input is None
        """
        if value is None:
            return None
        return [str(item.id) for item in cast(List[M], value)]  # type: ignore

    async def async_to_mongo(self, value: Optional[M]) -> Optional[List[ObjectId]]:
        """Convert Python list of model instances to MongoDB array asynchronously.

        Args:
            value: List of model instances or None

        Returns:
            List of ObjectId instances ready for MongoDB storage, or None if input is None
        """
        if value is None:
            return None
        return [item.id for item in cast(List[M], value)]  # type: ignore

    async def async_from_mongo(self, value: Any) -> M:
        """Convert MongoDB array to Python list of model instances asynchronously.

        Args:
            value: MongoDB array value or None

        Returns:
            List of model instances

        Raises:
            ValueError: If value is not None and not a list
        """
        if value is None:
            return cast(M, [])
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[M] = []
        for item_value in cast(List[ItemType], value):
            if isinstance(item_value, self.model):
                result.append(item_value)  # type: ignore
            elif isinstance(item_value, ObjectId):
                model = await self.model.find_by_id(item_value)  # type: ignore
                if model is not None:
                    result.append(model)  # type: ignore
            else:
                model = await self.model.find_by_id(ObjectId(str(item_value)))  # type: ignore
                if model is not None:
                    result.append(model)  # type: ignore
        return cast(M, result)
