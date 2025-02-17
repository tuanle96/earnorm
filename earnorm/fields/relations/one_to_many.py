"""One-to-many relation field implementation.

This module provides the OneToManyField class for defining one-to-many relations in EarnORM.
It allows one record in the source model to reference multiple records in the target model.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields.relations import OneToManyField, ManyToOneField

    >>> class Department(BaseModel):
    ...     _name = 'res.department'
    ...     name = StringField()
    ...     employees = OneToManyField(
    ...         'res.employee',  # _name của Employee model
    ...         inverse_field='department'  # Tên field trong Employee model
    ...     )

    >>> class Employee(BaseModel):
    ...     _name = 'res.employee'  # Model name được reference
    ...     name = StringField()
    ...     department = ManyToOneField(
    ...         'res.department',
    ...         inverse_field='employees'
    ...     )
"""

from typing import TYPE_CHECKING, Any, List, Optional, TypeVar, Union

from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.fields import DatabaseValue
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationType

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


class OneToManyField(RelationField[T]):
    """Field for one-to-many relations.

    This field allows one record in the source model to reference multiple records
    in the target model. It is typically used as the reverse relation of a ManyToOneField.

    Examples:
        >>> class Department(BaseModel):
        ...     _name = 'res.department'
        ...     employees = OneToManyField(
        ...         'res.employee',
        ...         inverse_field='department'
        ...     )

        >>> # Create records
        >>> dept = await Department.create({'name': 'IT'})
        >>> emp1 = await Employee.create({
        ...     'name': 'John',
        ...     'department': dept
        ... })
        >>> emp2 = await Employee.create({
        ...     'name': 'Jane',
        ...     'department': dept
        ... })

        >>> # Access related records
        >>> employees = await dept.employees  # Returns list of employees
        >>> for emp in employees:
        ...     print(await emp.name)
    """

    def __init__(
        self,
        model: ModelType[T],
        *,
        inverse_field: str,
        help: Optional[str] = None,
        **options: Any,
    ) -> None:
        """Initialize one-to-many field.

        Args:
            model: Related model's _name (string) or model class
            inverse_field: Name of reverse relation field (required)
            help: Help text for the field
            **options: Additional field options

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not inverse_field:
            raise ValueError("inverse_field parameter is required")

        super().__init__(
            model,
            RelationType.ONE_TO_MANY,
            related_name=inverse_field,
            on_delete="CASCADE",
            required=False,
            lazy=True,
            help=help,
            **options,
        )

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
        """Get related records."""
        if not self.env:
            raise RuntimeError("Environment not set")

        try:
            # Get target model
            model = await self._resolve_model()

            # Search for records with foreign key matching source ID
            if not self.related_name:
                raise RuntimeError("inverse_field is not set")

            records = await model.search(
                [
                    (
                        str(self.related_name),
                        "=",
                        source_instance.id,
                    )
                ]
            )
            return list(records)

        except Exception as e:
            raise RuntimeError(f"Failed to get related records: {str(e)}") from e

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

        Examples:
            >>> dept = Department()
            >>> employees = [emp1, emp2]
            >>> await dept.employees.set_related(dept, employees)
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        await self.validate(value)

        if not isinstance(value, list):
            raise ValueError("OneToManyField requires a list of records")

        try:
            # Clear existing relations
            await self.clear(source_instance)

            # Set new relations
            for record in value:
                await self.add(source_instance, record)

        except Exception as e:
            raise RuntimeError(f"Failed to set related records: {str(e)}") from e

    async def add(self, instance: Any, record: T) -> None:
        """Add a record to the relation."""
        if not self.env:
            raise RuntimeError("Environment not set")

        try:
            # Set foreign key on target record
            if not self.related_name:
                raise RuntimeError("inverse_field is not set")

            await record.write({str(self.related_name): instance.id})

        except Exception as e:
            raise RuntimeError(f"Failed to add record: {str(e)}") from e

    async def remove(self, instance: Any, record: T) -> None:
        """Remove a record from the relation."""
        if not self.env:
            raise RuntimeError("Environment not set")

        try:
            # Clear foreign key on target record
            if not self.related_name:
                raise RuntimeError("inverse_field is not set")

            await record.write({str(self.related_name): None})

        except Exception as e:
            raise RuntimeError(f"Failed to remove record: {str(e)}") from e

    async def clear(self, instance: Any) -> None:
        """Clear all relations.

        Args:
            instance: Source model instance

        Examples:
            >>> dept = Department()
            >>> await dept.employees.clear()
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        try:
            # Get all related records
            records = await self.get_related(instance)

            # Clear foreign key on all records
            for record in records:
                await self.remove(instance, record)

        except Exception as e:
            raise RuntimeError(f"Failed to clear relations: {str(e)}") from e

    async def delete_related(self, source_instance: Any) -> None:
        """Handle deletion based on on_delete policy.

        Args:
            source_instance: Model instance to delete related records for

        Raises:
            RuntimeError: If deletion fails

        Examples:
            >>> dept = Department()
            >>> await dept.employees.delete_related(dept)  # Handles based on on_delete
        """
        try:
            # Get all related records
            records = await self.get_related(source_instance)

            if self.on_delete == "CASCADE":
                # Delete all related records
                for record in records:
                    await record.unlink()
            elif self.on_delete == "SET_NULL":
                # Clear foreign key on all records
                await self.clear(source_instance)
            # PROTECT is handled by database constraint

        except Exception as e:
            raise RuntimeError(f"Failed to delete related records: {str(e)}") from e
