"""Many-to-many relation field implementation.

This module provides the ManyToManyField class for defining many-to-many relations in EarnORM.
It allows multiple records in the source model to reference multiple records in the target model.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields.relations import ManyToManyField

    >>> class Tag(BaseModel):
    ...     _name = 'res.tag'
    ...     name = StringField()
    ...     users = ManyToManyField(
    ...         'res.user',     # _name của User model
    ...         relation='res.user_tag_rel',
    ...         relation_column1='tag_id',
    ...         relation_column2='user_id'
    ...     )

    >>> class User(BaseModel):
    ...     _name = 'res.user'  # Model name được reference
    ...     name = StringField()
"""

from typing import TYPE_CHECKING, Any, List, Optional, TypeVar, Union

from earnorm.fields.primitive.datetime import DateTimeField
from earnorm.fields.primitive.string import StringField
from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.fields import DatabaseValue
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationType

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


class ManyToManyField(RelationField[T]):
    """Field for many-to-many relations.

    This field allows multiple records in the source model to reference multiple records
    in the target model through a relation table.

    Args:
        model: Related model's _name (string) or model class
        relation: Name of relation table/collection
        relation_column1: Name of source ID column
        relation_column2: Name of target ID column
        help: Help text for the field
        **options: Additional field options

    Raises:
        ValueError: If required parameters are missing or invalid

    Attributes:
        relation: Name of relation table/collection
        relation_column1: Name of source ID column
        relation_column2: Name of target ID column
    """

    def __init__(
        self,
        model: ModelType[T],
        *,
        relation: str,
        relation_column1: str,
        relation_column2: str,
        help: Optional[str] = None,
        **options: Any,
    ) -> None:
        """Initialize many-to-many field.

        Args:
            model: Related model's _name (string) or model class
            relation: Name of relation table/collection
            relation_column1: Name of source ID column
            relation_column2: Name of target ID column
            help: Help text for the field
            **options: Additional field options

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not relation:
            raise ValueError("relation parameter is required")
        if not relation_column1:
            raise ValueError("relation_column1 parameter is required")
        if not relation_column2:
            raise ValueError("relation_column2 parameter is required")

        # Store relation configuration
        self._relation = relation
        self._relation_column1 = relation_column1
        self._relation_column2 = relation_column2
        self._relation_model = None

        super().__init__(
            model,
            RelationType.MANY_TO_MANY,
            related_name=None,
            on_delete="CASCADE",
            required=False,
            lazy=True,
            help=help,
            **options,
        )

    async def setup(self, name: str, model_name: str) -> None:
        """Setup many-to-many field và relation model."""
        await super().setup(name, model_name)

        # Define relation model fields
        fields = {
            self._relation_column1: StringField(
                required=True, index=True, help=f"ID of {model_name} record"
            ),
            self._relation_column2: StringField(
                required=True, index=True, help=f"ID of {self.model_ref} record"
            ),
            "created_at": DateTimeField(auto_now_add=True),
            "updated_at": DateTimeField(auto_now=True),
        }

        # Create relation model dynamically
        relation_model = type(
            self._relation.replace(".", "_"),
            (BaseModel,),
            {
                "_name": self._relation,
                "_description": f"Relation model for {model_name}.{name}",
                **fields,
            },
        )

        # Store relation model reference
        self._relation_model = relation_model

    async def to_db(self, value: Optional[T], backend: str) -> DatabaseValue:
        """Convert model instance/recordset to database value.

        Args:
            value: Model instance/recordset
            backend: Database backend type

        Returns:
            Database ID value

        Raises:
            ValueError: If value is invalid or missing ID
        """
        if value is None:
            return None

        # Validate recordset
        if not hasattr(value, "id"):
            raise ValueError(f"Invalid recordset for {self.name}: {value}")

        if value.id is None:  # type: ignore
            raise ValueError(f"Recordset {value} has no ID")

        # Convert based on backend
        return str(value.id)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[T]:
        """Convert database value to model instance/recordset.

        Args:
            value: Database ID value
            backend: Database backend type

        Returns:
            Model instance/recordset

        Raises:
            RuntimeError: If model resolution fails
            ValueError: If database value is invalid
        """
        if value is None:
            return None

        try:
            # Resolve model class
            model = await self._resolve_model()

            # Convert based on backend
            if backend == "mongodb":
                if not isinstance(value, str):
                    raise ValueError(f"Invalid MongoDB ID: {value}")
                return await model.browse(value)
            elif backend == "postgresql":
                # Handle both integer and UUID IDs
                if isinstance(value, (int, str)):
                    return await model.browse(str(value))
                raise ValueError(f"Invalid PostgreSQL ID: {value}")
            else:
                # Default handling
                return await model.browse(str(value))

        except Exception as e:
            raise RuntimeError(f"Failed to convert database value: {str(e)}") from e

    async def get_related(self, source_instance: Any) -> List[T]:
        """Get related records through relation model.

        Args:
            source_instance: Source model instance

        Returns:
            List of related model instances/recordsets
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        try:
            # Get relation records
            relation_records = await self._get_relation_records(source_instance)

            # Convert to recordsets
            records: List[T] = []
            for record in relation_records:
                related = await self.from_db(
                    getattr(record, self._relation_column2),
                    self.env.adapter.backend_type,
                )
                if related:
                    records.append(related)

            return records

        except Exception as e:
            raise RuntimeError(f"Failed to get related records: {str(e)}") from e

    async def _get_relation_records(self, instance: Any) -> List[Any]:
        """Get records from relation model."""
        if not self._relation_model:
            raise RuntimeError("Relation model not initialized")

        records = await self._relation_model.search(
            [(self._relation_column1, "=", instance.id)]
        )
        return list(records)

    async def set_related(
        self, source_instance: Any, value: Union[Optional[T], List[T]]
    ) -> None:
        """Set related records.

        Args:
            source_instance: Model instance to set related records for
            value: Related records to set

        Raises:
            RuntimeError: If environment is not set
            ValueError: If value is invalid
            ValidationError: If validation fails
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        await self.validate(value)

        if not isinstance(value, list):
            raise ValueError("ManyToManyField requires a list of records")

        try:
            # Clear existing relations
            await self._clear_relations(source_instance)

            # Create new relations
            for record in value:
                await self._create_relation(source_instance, record)

        except Exception as e:
            raise RuntimeError(f"Failed to set related records: {str(e)}") from e

    async def _clear_relations(self, instance: Any) -> None:
        """Clear all relations for instance."""
        if not self._relation_model:
            raise RuntimeError("Relation model not initialized")

        records = await self._relation_model.search(
            [(self._relation_column1, "=", instance.id)]
        )
        await records.unlink()

    async def _create_relation(self, source: Any, target: T) -> None:
        """Create relation record."""
        if not self._relation_model:
            raise RuntimeError("Relation model not initialized")

        await self._relation_model.create(
            {self._relation_column1: source.id, self._relation_column2: target.id}
        )

    async def delete_related(self, source_instance: Any) -> None:
        """Handle deletion based on on_delete policy.

        Args:
            source_instance: Model instance to delete related records for

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            if self.on_delete == "CASCADE":
                # Delete related records
                related = await self.get_related(source_instance)
                for record in related:
                    await record.unlink()
            elif self.on_delete == "SET_NULL":
                # Just clear relations
                await self._clear_relations(source_instance)
            # PROTECT is handled by database constraint

        except Exception as e:
            raise RuntimeError(f"Failed to delete related records: {str(e)}") from e
