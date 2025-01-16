"""One-to-many field type.

This module provides the One2manyField class for handling one-to-many relationships
between models in the EarnORM framework.
"""

from typing import Any, List, Optional, Sequence, TypeVar, cast

from bson import ObjectId

from earnorm.fields.relation.base import BaseRelationField
from earnorm.types import ModelInterface

M = TypeVar("M", bound=ModelInterface)


class One2manyField(BaseRelationField[M]):
    """One-to-many field for handling relationships where one record can have multiple related records.

    This field is used to establish a one-to-many relationship between two models. It stores
    a list of ObjectIds that reference the related model instances.

    Examples:
        ```python
        class Author(Model):
            name = StringField()
            books = One2manyField(Book, field="author")

        class Book(Model):
            title = StringField()
            author = Many2oneField(Author)
        ```

        In this example, an Author can have multiple Books, but each Book has only one Author.
        The `field` parameter in One2manyField specifies which field in the Book model references
        the Author model.
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
            books = One2manyField(Book, field="author", required=True)
            ```
        """
        super().__init__(
            model=model,
            required=required,
            **kwargs,
        )
        self.field = field

    def _get_model_from_id(self, id_value: Any) -> Optional[M]:
        """Get model instance from ID value.

        Args:
            id_value: ID value to convert to model instance

        Returns:
            Model instance or None if not found
        """
        try:
            obj_id = ObjectId(str(id_value))
            return cast(Optional[M], self.model.find_by_id(obj_id))  # type: ignore
        except Exception:
            return None

    def _convert_sequence(self, value: Sequence[Any]) -> List[M]:
        """Convert sequence of values to list of model instances.

        Args:
            value: Sequence of values to convert

        Returns:
            List of model instances
        """
        result: List[M] = []
        for item in value:
            if isinstance(item, self.model):
                result.append(item)
            else:
                model = self._get_model_from_id(item)
                if model is not None:
                    result.append(model)
        return result

    async def _convert_sequence_async(self, value: Sequence[Any]) -> List[M]:
        """Convert sequence of values to list of model instances asynchronously.

        Args:
            value: Sequence of values to convert

        Returns:
            List of model instances
        """
        result: List[M] = []
        for item in value:
            if isinstance(item, self.model):
                result.append(item)
            else:
                model = await self._get_model_from_id_async(item)
                if model is not None:
                    result.append(model)
        return result

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
        return cast(M, self._convert_sequence(cast(Sequence[Any], value)))

    def to_dict(self, value: Optional[M]) -> Optional[List[str]]:
        """Convert list of ObjectId to list of string for JSON serialization.

        Args:
            value: List of ObjectId instances or None

        Returns:
            List of string representations of ObjectIds, or None if input is None
        """
        if value is None:
            return None
        return [str(item.id) for item in cast(List[M], value)]  # type: ignore

    def to_mongo(self, value: Optional[M]) -> Optional[List[ObjectId]]:
        """Convert Python list of ObjectId to MongoDB array.

        Args:
            value: List of ObjectId instances or None

        Returns:
            List of ObjectId instances ready for MongoDB storage, or None if input is None
        """
        if value is None:
            return None
        return [item.id for item in cast(List[M], value)]  # type: ignore

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
        return cast(M, self._convert_sequence(cast(Sequence[Any], value)))

    async def _get_model_from_id_async(self, id_value: Any) -> Optional[M]:
        """Get model instance from ID value asynchronously.

        Args:
            id_value: ID value to convert to model instance

        Returns:
            Model instance or None if not found
        """
        try:
            obj_id = ObjectId(str(id_value))
            return cast(Optional[M], await self.model.find_by_id(obj_id))  # type: ignore
        except Exception:
            return None

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
        return cast(M, await self._convert_sequence_async(cast(Sequence[Any], value)))

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
        return cast(M, await self._convert_sequence_async(cast(Sequence[Any], value)))
