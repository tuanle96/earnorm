"""One-to-one relation field implementation.

This module provides the OneToOneField class for defining one-to-one relations in EarnORM.
It ensures that each record in the source model corresponds to exactly one record in the target model.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields.relations import OneToOneField

    >>> class User(BaseModel):
    ...     _name = 'res.user'

    >>> class Profile(BaseModel):
    ...     _name = 'res.profile'
    ...     user = OneToOneField(
    ...         'res.user',  # Using string reference
    ...         related_name='profile',
    ...         on_delete='CASCADE'
    ...     )

    >>> # Create related records
    >>> user = await User.create({'name': 'John'})
    >>> profile = await Profile.create({
    ...     'user': user,
    ...     'bio': 'Python developer'
    ... })

    >>> # Access related records
    >>> profile = await user.profile
    >>> user = await profile.user
"""

from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, TypeVar, cast

from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationType

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


class OneToOneField(RelationField[T], Generic[T]):
    """Field for one-to-one relations.

    This field ensures that each record in the source model corresponds to exactly one
    record in the target model, and vice versa. It automatically creates a reverse
    relation field on the target model.

    Args:
        model: Related model class or string reference
        related_name: Name of reverse relation field
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        required: Whether relation is required
        help: Help text for the field
        **options: Additional field options

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.user'
        ...     profile = OneToOneField(
        ...         'res.profile',  # Using string reference
        ...         related_name='user',
        ...         on_delete='CASCADE'
        ...     )

        >>> # Create related records
        >>> user = await User.create({'name': 'John'})
        >>> profile = await Profile.create({
        ...     'user': user,
        ...     'bio': 'Python developer'
        ... })

        >>> # Access related records
        >>> profile = await user.profile
        >>> user = await profile.user
    """

    field_type = "one2one"

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
        """Initialize one-to-one field.

        Args:
            model: Related model class or string reference
            related_name: Name of reverse relation field
            on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
            required: Whether relation is required
            help: Help text for the field
            **options: Additional field options
        """
        field_options = cast(
            Dict[str, Any],
            {
                **options,
                "unique": True,
                "index": True,
            },
        )  # One-to-one relations are always unique and indexed
        super().__init__(
            model,
            RelationType.ONE_TO_ONE,
            related_name=related_name,
            on_delete=on_delete,
            required=required,
            help=help,
            lazy=True,
            **field_options,
        )
