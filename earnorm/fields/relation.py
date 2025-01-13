"""Relation field types for EarnORM."""

from typing import Any, List, Optional, Type, Union

from bson import ObjectId

from ..base.model import BaseModel
from .base import Field


class Many2one(Field):
    """Many-to-one relation field."""

    def __init__(
        self,
        *,
        string: str,
        relation_model: Union[str, Type[BaseModel]],
        required: bool = False,
        ondelete: str = "set null",
        **kwargs: Any,
    ) -> None:
        """Initialize many-to-one field.

        Args:
            string: Field label
            relation_model: Related model class or name
            required: Whether relation is required
            ondelete: What to do when related record is deleted
            **kwargs: Additional field options
        """
        self.relation_model = relation_model
        self.ondelete = ondelete
        super().__init__(string=string, required=required, **kwargs)

    def validate(self, value: Any) -> Optional[str]:
        """Validate relation value.

        Args:
            value: Value to validate

        Returns:
            Optional[str]: Validated relation ID

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            if self.required:
                raise ValueError(f"{self.string} is required")
            return None

        if isinstance(value, str):
            try:
                ObjectId(value)
                return value
            except Exception:
                raise ValueError(f"{self.string} must be a valid ObjectId")

        if isinstance(value, dict) and "_id" in value:
            return str(value["_id"])

        raise ValueError(f"{self.string} must be a relation ID or document")

    def to_mongo(self, value: Optional[str]) -> Optional[ObjectId]:
        """Convert value to MongoDB format.

        Args:
            value: Value to convert

        Returns:
            Optional[ObjectId]: MongoDB ObjectId
        """
        return ObjectId(value) if value else None

    def from_mongo(self, value: Optional[ObjectId]) -> Optional[str]:
        """Convert value from MongoDB format.

        Args:
            value: Value to convert

        Returns:
            Optional[str]: String ID
        """
        return str(value) if value else None


class One2many(Field):
    """One-to-many relation field."""

    def __init__(
        self,
        *,
        string: str,
        relation_model: Union[str, Type[BaseModel]],
        inverse_field: str,
        **kwargs: Any,
    ) -> None:
        """Initialize one-to-many field.

        Args:
            string: Field label
            relation_model: Related model class or name
            inverse_field: Name of inverse Many2one field
            **kwargs: Additional field options
        """
        self.relation_model = relation_model
        self.inverse_field = inverse_field
        super().__init__(string=string, **kwargs)

    def validate(self, value: Any) -> List[str]:
        """Validate relation value.

        Args:
            value: Value to validate

        Returns:
            List[str]: List of relation IDs

        Raises:
            ValueError: If validation fails
        """
        if not value:
            return []

        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{self.string} must be a list of IDs")

        ids = []
        for item in value:
            if isinstance(item, str):
                try:
                    ObjectId(item)
                    ids.append(item)
                except Exception:
                    raise ValueError(f"{self.string} contains invalid ID: {item}")
            elif isinstance(item, dict) and "_id" in item:
                ids.append(str(item["_id"]))
            else:
                raise ValueError(f"{self.string} contains invalid item: {item}")

        return ids


class Many2many(Field):
    """Many-to-many relation field."""

    def __init__(
        self,
        *,
        string: str,
        relation_model: Union[str, Type[BaseModel]],
        relation_table: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize many-to-many field.

        Args:
            string: Field label
            relation_model: Related model class or name
            relation_table: Optional custom relation table name
            **kwargs: Additional field options
        """
        self.relation_model = relation_model
        self.relation_table = relation_table
        super().__init__(string=string, **kwargs)

    def validate(self, value: Any) -> List[str]:
        """Validate relation value.

        Args:
            value: Value to validate

        Returns:
            List[str]: List of relation IDs

        Raises:
            ValueError: If validation fails
        """
        if not value:
            return []

        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{self.string} must be a list of IDs")

        ids = []
        for item in value:
            if isinstance(item, str):
                try:
                    ObjectId(item)
                    ids.append(item)
                except Exception:
                    raise ValueError(f"{self.string} contains invalid ID: {item}")
            elif isinstance(item, dict) and "_id" in item:
                ids.append(str(item["_id"]))
            else:
                raise ValueError(f"{self.string} contains invalid item: {item}")

        return ids

    def get_relation_table(self, model_name: str) -> str:
        """Get name of relation table.

        Args:
            model_name: Name of model containing this field

        Returns:
            str: Relation table name
        """
        if self.relation_table:
            return self.relation_table

        names = sorted([model_name, self.relation_model])
        return f"{names[0]}_{names[1]}_rel"
