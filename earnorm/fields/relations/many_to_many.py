"""Many-to-many relation field implementation.

This module provides the ManyToManyField class for defining many-to-many relations in EarnORM.
It allows multiple records in the source model to reference multiple records in the target model.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields.relations import ManyToManyField

    >>> class User(BaseModel):
    ...     _name = 'res.user'
    ...     roles = ManyToManyField(
    ...         'res.role',  # Using string reference
    ...         related_name='users',
    ...         through='UserRole'
    ...     )

    >>> class Role(BaseModel):
    ...     _name = 'res.role'

    >>> class UserRole(BaseModel):
    ...     _name = 'res.user.role'
    ...     user = ManyToOneField('res.user')
    ...     role = ManyToOneField('res.role')
    ...     assigned_at = DateTimeField()

    >>> # Create related records
    >>> user = await User.create({'name': 'John'})
    >>> admin = await Role.create({'name': 'Admin'})
    >>> editor = await Role.create({'name': 'Editor'})

    >>> # Add roles to user
    >>> await user.roles.add(admin)
    >>> await user.roles.add(editor)

    >>> # Access related records
    >>> roles = await user.roles
    >>> users = await admin.users
"""

from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, Type, TypeVar, cast

from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationType

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


class ManyToManyField(RelationField[T], Generic[T]):
    """Field for many-to-many relations.

    This field allows multiple records in the source model to reference multiple records
    in the target model. It automatically creates a reverse many-to-many relation field
    on the target model.

    Args:
        model: Related model class or string reference
        related_name: Name of reverse relation field
        through: Through model for custom fields
        through_fields: Field names in through model (local_field, foreign_field)
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        required: Whether relation is required
        help: Help text for the field
        **options: Additional field options

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.user'
        ...     roles = ManyToManyField(
        ...         'res.role',  # Using string reference
        ...         related_name='users',
        ...         through='UserRole'
        ...     )

        >>> # Create related records
        >>> user = await User.create({'name': 'John'})
        >>> admin = await Role.create({'name': 'Admin'})
        >>> editor = await Role.create({'name': 'Editor'})

        >>> # Add roles to user
        >>> await user.roles.add(admin)
        >>> await user.roles.add(editor)

        >>> # Access related records
        >>> roles = await user.roles
        >>> users = await admin.users
    """

    field_type = "many2many"

    def __init__(
        self,
        model: ModelType[T],
        *,
        related_name: Optional[str] = None,
        through: Optional[Type[ModelProtocol]] = None,
        through_fields: Optional[tuple[str, str]] = None,
        on_delete: str = "CASCADE",
        required: bool = False,
        help: Optional[str] = None,
        **options: Dict[str, Any],
    ) -> None:
        """Initialize many-to-many field.

        Args:
            model: Related model class or string reference
            related_name: Name of reverse relation field
            through: Through model for custom fields
            through_fields: Field names in through model (local_field, foreign_field)
            on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
            required: Whether relation is required
            help: Help text for the field
            **options: Additional field options
        """
        field_options = {**options}
        if through is not None:
            field_options["through"] = cast(Dict[str, Any], {"model": through})
        if through_fields is not None:
            field_options["through_fields"] = cast(
                Dict[str, Any], {"fields": through_fields}
            )

        super().__init__(
            model,
            RelationType.MANY_TO_MANY,
            related_name=related_name,
            on_delete=on_delete,
            required=required,
            help=help,
            lazy=True,
            **field_options,
        )
