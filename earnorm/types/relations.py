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

from earnorm.types.models import ModelProtocol

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


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
    """Enum for relation field types."""

    ONE_TO_ONE = "one_to_one"
    MANY_TO_ONE = "many_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class RelationProtocol(Protocol[T]):
    """Protocol defining relation field interface.

    This protocol defines the core interface that all relation fields must implement.
    It includes:
    1. Basic attributes (model, type, etc)
    2. CRUD operations for related records
    3. Validation and conversion methods

    Examples:
        >>> class CustomRelation(RelationProtocol[User]):
        ...     @property
        ...     def model(self) -> Type[User]:
        ...         return User
        ...     relation_type = RelationType.ONE_TO_ONE
        ...
        ...     async def get_related(self) -> Optional[User]:
        ...         # Custom implementation
        ...         pass
    """

    @property
    def model(self) -> Type[T]:
        """Get the related model class.

        Returns:
            Type[T]: The related model class
        """
        ...

    relation_type: RelationType
    """Type of relation."""

    related_name: Optional[str]
    """Name of reverse relation field."""

    on_delete: str
    """Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')."""

    async def get_related(self, instance: Any) -> Union[Optional[T], List[T]]:
        """Get related record(s).

        Args:
            instance: Model instance to get related records for

        Returns:
            Single record for one-to-one/many-to-one
            List of records for one-to-many/many-to-many
        """
        ...

    async def set_related(
        self, instance: Any, value: Union[Optional[T], List[T]]
    ) -> None:
        """Set related record(s).

        Args:
            instance: Model instance to set related records for
            value: Related record(s) to set
        """
        ...

    async def delete_related(self, instance: Any) -> None:
        """Delete related record(s).

        Args:
            instance: Model instance to delete related records for
        """
        ...


class RelationOptions(Dict[str, Any]):
    """Type for relation field options.

    This type defines the structure of options passed to relation fields.
    It includes all configuration options like:
    - model: Related model class
    - relation_type: Type of relation
    - related_name: Name of reverse relation
    - on_delete: Delete behavior
    - through: Through model for many-to-many
    - through_fields: Field names in through model
    - index: Whether to create index
    """

    model: Type[ModelProtocol]
    """Related model class."""

    relation_type: RelationType
    """Type of relation."""

    related_name: Optional[str]
    """Name of reverse relation field."""

    on_delete: str
    """Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')."""

    through: Optional[Type[ModelProtocol]]
    """Through model for many-to-many relations."""

    through_fields: Optional[tuple[str, str]]
    """Field names in through model (local_field, foreign_field)."""

    index: bool
    """Whether to create index for foreign key."""
