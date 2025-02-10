"""One-to-many relation field implementation.

This module provides the OneToManyField class for defining one-to-many relations in EarnORM.
It allows one record in the source model to reference multiple records in the target model.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields.relations import OneToManyField

    >>> class Department(BaseModel):
    ...     _name = 'department'
    ...     employees = OneToManyField(
    ...         'Employee',  # Using string reference
    ...         related_name='department',
    ...         on_delete='CASCADE'
    ...     )

    >>> class Employee(BaseModel):
    ...     _name = 'employee'
    ...     department = ManyToOneField(
    ...         'Department',
    ...         related_name='employees'
    ...     )

    >>> # Create related records
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
    >>> employees = await dept.employees  # Returns recordset
    >>> for emp in employees:
    ...     print(await emp.name)
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, TypeVar, cast

from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationType

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


class OneToManyField(RelationField[T], Generic[T]):
    """Field for one-to-many relations.

    This field allows one record in the source model to reference multiple records
    in the target model. It automatically creates a reverse many-to-one relation field
    on the target model.

    Args:
        model: Related model class or string reference
        related_name: Name of reverse relation field
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        required: Whether relation is required
        help: Help text for the field
        **options: Additional field options

    Examples:
        >>> class Department(BaseModel):
        ...     _name = 'department'
        ...     employees = OneToManyField(
        ...         'Employee',
        ...         related_name='department',
        ...         on_delete='CASCADE'
        ...     )

        >>> # Create related records
        >>> dept = await Department.create({'name': 'IT'})
        >>> emp = await Employee.create({
        ...     'name': 'John',
        ...     'department': dept
        ... })

        >>> # Access related records
        >>> employees = await dept.employees  # Returns recordset
        >>> for emp in employees:
        ...     print(await emp.name)
    """

    field_type = "one2many"
    logger = logging.getLogger(__name__)

    def __init__(
        self,
        model: ModelType[T],
        *,
        related_name: Optional[str] = None,
        on_delete: str = "CASCADE",
        required: bool = False,
        help: Optional[str] = None,
        **options: Dict[str, Any],
    ) -> None:
        """Initialize one-to-many field.

        Args:
            model: Related model class or string reference
            related_name: Name of reverse relation field
            on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
            required: Whether relation is required
            help: Help text for the field
            **options: Additional field options
        """
        if not related_name:
            raise ValueError("related_name is required for OneToManyField")

        super().__init__(
            model,
            RelationType.ONE_TO_MANY,
            related_name=related_name,
            on_delete=on_delete,
            required=required,
            help=help,
            lazy=True,
            **options,
        )

    async def __get__(self, instance: Optional[Any], owner: Optional[type] = None) -> T:
        """Get related records.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Recordset containing related records (may be empty)
        """
        self.logger.info(f"OneToManyField.__get__ called for {self.name}")
        if instance is None:
            self.logger.info("Returning field descriptor (accessed from class)")
            return self  # type: ignore

        value = await super().__get__(instance, owner)
        self.logger.info(f"Got value from super().__get__: {value}")

        if value is None:  # type: ignore
            # Return empty recordset instead of None
            model = await self._resolve_model()
            self.logger.info(f"Returning empty recordset for model: {model}")
            return model._browse(model._env, [])  # type: ignore

        self.logger.info(f"Returning value: {value}")
        return cast(T, value)  # Cast to recordset type
