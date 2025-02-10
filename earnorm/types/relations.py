"""Types and protocols for relation fields.

This module defines the core types and protocols used by relation fields in EarnORM.
It provides:
1. Relation type enums
2. Relation protocols
3. Type definitions for relation options

Examples:
    >>> from earnorm.types.relations import RelationType, RelationProtocol
    >>> from earnorm.base.model import BaseModel

    >>> class User(BaseModel):
    ...     _name = 'res.user'

    >>> class Profile(BaseModel):
    ...     _name = 'res.profile'
    ...     user = OneToOneField(User, related_name='profile')
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from earnorm.types.models import ModelProtocol

# Covariant type variable for relation fields
T_co = TypeVar("T_co", covariant=True)
ModelT = TypeVar("ModelT", bound="ModelProtocol")


class RelationFieldOptions(TypedDict, total=False):
    """Type for relation field options."""

    store: bool  # Whether to store the field in database
    index: bool  # Whether to create an index
    help: str  # Help text for the field
    compute: Any  # Compute method
    depends: List[str]  # Dependencies for compute method
    validators: List[Any]  # Field validators
    lazy: bool  # Whether to use lazy loading


class RelationType(str, Enum):
    """Relation type enum.

    Attributes:
        ONE_TO_ONE: One-to-one relation
        ONE_TO_MANY: One-to-many relation
        MANY_TO_ONE: Many-to-one relation
        MANY_TO_MANY: Many-to-many relation
    """

    ONE_TO_ONE = "one2one"
    ONE_TO_MANY = "one2many"
    MANY_TO_ONE = "many2one"
    MANY_TO_MANY = "many2many"


@dataclass
class RelationOptions:
    """Options for relation fields.

    Attributes:
        model: Related model class or string reference
        related_name: Name of reverse relation field
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        through: Through model for many-to-many relations
        through_fields: Field names for through model
        lazy: Whether to load related records lazily
        required: Whether relation is required
        help: Help text for the field

    Examples:
        >>> options = RelationOptions(
        ...     model='Employee',
        ...     related_name='department',
        ...     on_delete='CASCADE',
        ...     lazy=True
        ... )
    """

    model: Union[Type[ModelProtocol], str]
    related_name: str
    on_delete: str = "CASCADE"
    through: Optional[Dict[str, Any]] = None
    through_fields: Optional[Dict[str, Any]] = None
    lazy: bool = True
    required: bool = False
    help: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate options after initialization."""
        if not self.related_name:
            raise ValueError("related_name is required")

        if self.on_delete not in ("CASCADE", "SET_NULL", "PROTECT"):
            raise ValueError(
                f"Invalid on_delete value: {self.on_delete}. "
                "Must be one of: CASCADE, SET_NULL, PROTECT"
            )


class RelationProtocol(Protocol[T_co]):
    """Protocol for relation fields.

    This protocol defines the interface that all relation fields must implement.
    It ensures type safety and proper handling of related records.

    Type Parameters:
        T_co: Covariant type of related model

    Examples:
        >>> class OneToManyField(RelationField[T], Generic[T]):
        ...     def __init__(self, model: ModelType[T], **options):
        ...         super().__init__(model, RelationType.ONE_TO_MANY, **options)
    """

    async def get_related(self, instance: Any) -> Optional[Union[T_co, List[T_co]]]:
        """Get related record(s).

        Args:
            instance: Model instance

        Returns:
            Single record for one-to-one/many-to-one
            List of records for one-to-many/many-to-many
        """
        ...

    async def set_related(self, instance: Any, value: Any) -> None:
        """Set related record(s).

        Args:
            instance: Model instance
            value: Related record(s) to set
        """
        ...

    async def delete_related(self, instance: Any) -> None:
        """Delete related record(s).

        Args:
            instance: Model instance
        """
        ...
