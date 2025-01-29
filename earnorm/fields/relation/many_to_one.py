"""Many-to-one relationship field implementation.

This module provides many-to-one relationship field types.
It supports:
- Forward and reverse relationships
- Lazy loading of related models
- Cascade deletion
- Database foreign key constraints
- Validation of related models
- Domain filtering and context
- Comparison operations

Examples:
    >>> class User(Model):
    ...     department = ManyToOneField(
    ...         "Department",
    ...         ondelete="cascade",
    ...         domain=[("active", "=", True)],
    ...         context={"show_archived": False}
    ...     )
    ...     manager = ManyToOneField(
    ...         "User",
    ...         ondelete="set null",
    ...         required=False
    ...     )
"""

from typing import Any, Final, Literal, Optional, Type, Union, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.relation.base import Context, Domain, RelationField
from earnorm.fields.relation.one_to_many import OneToManyField
from earnorm.types.fields import ComparisonOperator

# Constants
OnDeleteAction = Literal["cascade", "set null", "restrict"]
DEFAULT_ONDELETE: Final[OnDeleteAction] = "set null"
DEFAULT_CONTEXT: Final[Context] = {}


class ManyToOneField(RelationField[Any]):
    """Field for many-to-one relationships.

    This field type handles many-to-one relationships, with support for:
    - Back references
    - Cascade operations
    - Lazy loading
    - Validation
    - On delete actions
    - Domain filtering
    - Context
    - Comparison operations

    Attributes:
        model_ref: Referenced model class or name
        ondelete: Action to take when referenced record is deleted
        back_populates: Name of back reference field
        cascade: Whether to cascade operations
        lazy_load: Whether to load related models lazily
        domain: Domain for filtering related records
        context: Context for related records
    """

    model: Any  # Parent model instance

    def __init__(
        self,
        model_ref: Union[str, Type[Any]],
        *,
        ondelete: OnDeleteAction = DEFAULT_ONDELETE,
        back_populates: Optional[str] = None,
        cascade: bool = False,
        lazy_load: bool = True,
        domain: Optional[Domain] = None,
        context: Optional[Context] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize many-to-one field.

        Args:
            model_ref: Referenced model class or name
            ondelete: Action to take when referenced record is deleted
            back_populates: Name of back reference field
            cascade: Whether to cascade operations
            lazy_load: Whether to load related models lazily
            domain: Domain for filtering related records
            context: Context for related records
            **kwargs: Additional field options
        """
        super().__init__(
            model_ref,
            back_populates=back_populates,
            cascade=cascade,
            lazy_load=lazy_load,
            domain=domain,
            context=context or DEFAULT_CONTEXT.copy(),
            **kwargs,
        )
        self.ondelete = ondelete

    def is_empty(self) -> ComparisonOperator:
        """Check if relation is empty (no related record).

        Returns:
            ComparisonOperator: Comparison operator for empty check
        """
        return ComparisonOperator(self.name, "is_null", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if relation is not empty (has related record).

        Returns:
            ComparisonOperator: Comparison operator for non-empty check
        """
        return ComparisonOperator(self.name, "is_not_null", None)

    def contains(self, value: Any) -> ComparisonOperator:
        """Check if relation points to a specific value.

        Args:
            value: Value to check for (model instance or ID)

        Returns:
            ComparisonOperator: Comparison operator for equality check
        """
        if hasattr(value, "id"):
            value = str(value.id)  # type: ignore
        return ComparisonOperator(self.name, "=", value)

    def size(self, operator: str, value: int) -> ComparisonOperator:
        """Not supported for many-to-one relations.

        Raises:
            NotImplementedError: Always raised as size comparison is not supported
        """
        raise NotImplementedError(
            "Size comparison not supported for many-to-one relations"
        )

    def any(self, field: str, operator: str, value: Any) -> ComparisonOperator:
        """Not supported for many-to-one relations.

        Raises:
            NotImplementedError: Always raised as any comparison is not supported
        """
        raise NotImplementedError(
            "Any comparison not supported for many-to-one relations"
        )

    def all(self, field: str, operator: str, value: Any) -> ComparisonOperator:
        """Not supported for many-to-one relations.

        Raises:
            NotImplementedError: Always raised as all comparison is not supported
        """
        raise NotImplementedError(
            "All comparison not supported for many-to-one relations"
        )

    def _create_back_reference(self) -> RelationField[Any]:
        """Create back reference field.

        Returns:
            RelationField: Back reference field instance
        """
        return cast(
            RelationField[Any],
            OneToManyField(
                self.model_name,  # type: ignore
                back_populates=self.name,
                cascade=self.cascade,
                lazy_load=self.lazy_load,
                domain=self.domain,
                context=self.context,
            ),
        )

    async def convert(self, value: Any) -> Optional[Any]:
        """Convert value to model instance.

        Args:
            value: Value to convert

        Returns:
            Model instance or None

        Raises:
            FieldValidationError: If conversion fails
        """
        if value is None:
            return None

        model_class = self.get_model_class()

        try:
            if isinstance(value, model_class):
                return value
            elif isinstance(value, str):
                # Try to load by ID
                if not hasattr(self, "model"):
                    raise FieldValidationError(
                        message=(
                            f"Cannot load related model for field {self.name} "
                            "without parent model"
                        ),
                        field_name=self.name,
                    )

                try:
                    from earnorm.base.env import Environment

                    env = Environment.get_instance()
                    instance = await model_class.get(env, value)  # type: ignore
                    return instance
                except Exception as e:
                    raise FieldValidationError(
                        message=f"Failed to load {model_class.__name__} with id {value}: {e}",
                        field_name=self.name,
                    ) from e
            else:
                raise FieldValidationError(
                    message=(
                        f"Cannot convert {type(value).__name__} to {model_class.__name__} "
                        f"for field {self.name}"
                    ),
                    field_name=self.name,
                )
        except Exception as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
            ) from e

    async def validate(self, value: Optional[Any]) -> Optional[Any]:
        """Validate field value.

        Args:
            value: Value to validate

        Returns:
            Optional[Any]: Validated value

        Raises:
            FieldValidationError: If validation fails
        """
        if value is None:
            return None

        model_class = self.get_model_class()
        if not isinstance(value, model_class):
            raise FieldValidationError(
                message=(
                    f"Expected {model_class.__name__} instance for field {self.name}, "
                    f"got {type(value).__name__}"
                ),
                field_name=self.name,
            )

        # Check domain if specified
        if self.domain and not await self._check_domain(value):
            constraints = [
                f"{field} {op} {expected}" for field, op, expected in self.domain
            ]
            raise FieldValidationError(
                message=(
                    f"Value does not match domain constraints for field {self.name}: "
                    f"{', '.join(constraints)}"
                ),
                field_name=self.name,
            )

        return value

    async def to_db(self, value: Optional[Any], backend: str) -> Optional[str]:
        """Convert value to database format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            Database value or None
        """
        if value is None:
            return None

        if not hasattr(value, "id"):
            raise FieldValidationError(
                message=f"Model instance {value} has no id attribute",
                field_name=self.name,
            )

        return str(value.id)  # type: ignore

    async def from_db(self, value: Any, backend: str) -> Optional[Any]:
        """Convert database value to model instance.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Model instance or None

        Raises:
            FieldValidationError: If conversion fails
        """
        if value is None:
            return None

        model_class = self.get_model_class()

        try:
            if self.lazy_load:
                # Create model instance without loading
                from earnorm.base.env import Environment

                env = Environment.get_instance()
                instance = model_class(env)  # type: ignore
                instance.id = value  # type: ignore
                return instance
            else:
                # Load and validate model instance
                from earnorm.base.env import Environment

                env = Environment.get_instance()
                instance = await model_class.get(env, value)  # type: ignore
                await instance.validate()  # type: ignore
                return instance
        except Exception as e:
            raise FieldValidationError(
                message=f"Failed to load {model_class.__name__} with id {value}: {e}",
                field_name=self.name,
            ) from e
