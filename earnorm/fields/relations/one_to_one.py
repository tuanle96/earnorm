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
    ...         inverse_field='profile',
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

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from earnorm.base.database.query.interfaces.domain import (
    DomainOperator,
    LogicalOperator,
)
from earnorm.exceptions import ValidationError
from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.fields import DatabaseValue
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
        inverse_field: Name of reverse relation field
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        required: Whether relation is required
        help: Help text for the field
        **options: Additional field options

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.user'
        ...     profile = OneToOneField(
        ...         'res.profile',  # Using string reference
        ...         inverse_field='user',
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
        inverse_field: Optional[str] = None,
        on_delete: str = "CASCADE",
        required: bool = False,
        help: Optional[str] = None,
        **options: Any,
    ) -> None:
        """Initialize one-to-one field.

        Args:
            model: Related model class or string reference
            inverse_field: Name of reverse relation field
            on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
            required: Whether relation is required
            help: Help text for the field
            **options: Additional field options

        Raises:
            ValueError: If on_delete value is invalid
        """
        if on_delete not in ("CASCADE", "SET_NULL", "PROTECT"):
            raise ValueError(
                f"Invalid on_delete value: {on_delete}. "
                "Must be one of: CASCADE, SET_NULL, PROTECT"
            )

        field_options = {
            **options,
            "unique": True,
            "index": True,
        }

        super().__init__(
            model,
            RelationType.ONE_TO_ONE,
            related_name=inverse_field,
            on_delete=on_delete,
            required=required,
            lazy=True,
            help=help,
            **field_options,
        )

    async def to_db(self, value: Optional[T], backend: str) -> DatabaseValue:
        """Convert model instance to database ID.

        Args:
            value: Model instance or None
            backend: Database backend type

        Returns:
            String ID or None

        Raises:
            ValueError: If value is invalid or missing ID

        Examples:
            >>> user = User(id="123")
            >>> await field.to_db(user, "mongodb")
            '123'
        """
        if value is None:
            return None

        if not hasattr(value, "id"):
            raise ValueError(f"Invalid value for {self.name}: {value}")

        if value.id is None:  # type: ignore[comparison-overlap]
            raise ValueError(f"Value {value} has no ID")

        return str(value.id)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[T]:
        """Convert database ID to model instance.

        Args:
            value: Database ID value
            backend: Database backend type

        Returns:
            Model instance or None

        Raises:
            RuntimeError: If model resolution fails
            ValueError: If database value is invalid

        Examples:
            >>> user = await field.from_db("123", "mongodb")
            >>> print(user.id)
            '123'
        """
        if value is None:
            return None

        if not isinstance(value, (str, int)):
            raise ValueError(f"Invalid database value for {self.name}: {value}")

        try:
            model = await self._resolve_model()
            return await model.browse(str(value))
        except Exception as e:
            raise RuntimeError(f"Failed to resolve model: {str(e)}") from e

    async def get_related(self, source_instance: Any) -> Optional[T]:
        """Get single related record.

        Args:
            source_instance: Model instance to get related record for

        Returns:
            Related record or None

        Raises:
            RuntimeError: If environment is not set
            ValueError: If source_instance is invalid

        Examples:
            >>> profile = Profile()
            >>> user = await profile.user  # Returns User instance
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        if not hasattr(source_instance, f"_{self.name}"):
            raise ValueError(f"Invalid instance for {self.name}: {source_instance}")

        db_value = getattr(source_instance, f"_{self.name}", None)
        value = await self.from_db(db_value, self.env.adapter.backend_type)
        return value

    async def _check_existing_relation(self, value: T) -> Optional[Any]:
        """Check if record already has a relation.

        Args:
            value: Record to check

        Returns:
            Existing related record or None

        Raises:
            RuntimeError: If check fails
        """
        try:
            model = await self._resolve_model()
            domain: List[Union[LogicalOperator, Tuple[str, DomainOperator, Any]]] = [  # type: ignore[valid-type]
                (self.name, "=", value.id)  # type: ignore[arg-type]
            ]
            records = await model.search(domain)  # type: ignore[arg-type]
            return records[0] if records else None
        except Exception as e:
            raise RuntimeError(f"Failed to check existing relation: {str(e)}") from e

    async def set_related(
        self, source_instance: Any, value: Union[Optional[T], List[T]]
    ) -> None:
        """Set single related record.

        Args:
            source_instance: Model instance to set related record for
            value: Related record or None

        Raises:
            RuntimeError: If environment is not set
            ValueError: If value is a list or invalid
            ValidationError: If validation fails or unique constraint violated

        Examples:
            >>> profile = Profile()
            >>> user = User()
            >>> await profile.user.set_related(profile, user)
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        await self.validate(value)

        if isinstance(value, list):
            raise ValueError("OneToOneField does not support multiple values")

        # Check unique constraint
        if value is not None:
            existing = await self._check_existing_relation(cast(T, value))
            if existing and existing != source_instance:
                raise ValidationError(
                    f"Record {value} is already related to another record",
                    field_name=self.name,
                    code="unique_constraint_violation",
                )

        db_value = await self.to_db(
            cast(Optional[T], value), self.env.adapter.backend_type
        )
        setattr(source_instance, f"_{self.name}", db_value)

    async def delete_related(self, source_instance: Any) -> None:
        """Handle deletion based on on_delete policy.

        Args:
            source_instance: Model instance to delete related record for

        Raises:
            RuntimeError: If deletion fails
            ValueError: If source_instance is invalid

        Examples:
            >>> profile = Profile()
            >>> await profile.user.delete_related(profile)  # Handles based on on_delete
        """
        try:
            value = await self.get_related(source_instance)
            if value is None:
                return

            if self.on_delete == "CASCADE":
                await value.unlink()
            elif self.on_delete == "SET_NULL":
                await self.set_related(source_instance, None)
            # PROTECT is handled by database constraint
        except Exception as e:
            raise RuntimeError(f"Failed to delete related record: {str(e)}") from e

    async def validate(
        self, value: Any, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Validate relation value.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If validation fails

        Examples:
            >>> field = OneToOneField(User)
            >>> await field.validate(user)  # OK
            >>> await field.validate([user1, user2])  # Raises ValidationError
        """
        if value is None:
            if self.required:
                raise ValidationError(
                    f"Field {self.name} is required",
                    field_name=self.name,
                    code="required",
                )
            return

        model = await self._resolve_model()

        if isinstance(value, list):
            raise ValidationError(
                f"Field {self.name} does not support multiple values",
                field_name=self.name,
                code="multiple_values_not_supported",
            )

        if not isinstance(value, model):
            raise ValidationError(
                f"Expected {model.__name__}, got {type(value)}",
                field_name=self.name,
                code="invalid_relation_type",
            )
