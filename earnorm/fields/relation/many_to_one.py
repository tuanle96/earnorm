"""Many-to-one relationship field implementation.

This module provides many-to-one relationship field types.
It supports:
- Forward and reverse relationships
- Lazy loading of related models
- Cascade deletion
- Database foreign key constraints
- Validation of related models
- Domain filtering and context

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

from typing import Any, Final, Literal, Optional, Type, TypeVar, Union, cast

from earnorm.base.env import Environment
from earnorm.base.model.meta import BaseModel
from earnorm.exceptions import FieldValidationError
from earnorm.fields.relation.base import Context, Domain, RelationField
from earnorm.fields.relation.one_to_many import OneToManyField

M = TypeVar("M", bound=BaseModel)

# Constants
OnDeleteAction = Literal["cascade", "set null", "restrict"]
DEFAULT_ONDELETE: Final[OnDeleteAction] = "set null"
DEFAULT_CONTEXT: Final[Context] = {}


class ManyToOneField(RelationField[M]):
    """Field for many-to-one relationships.

    This field type handles many-to-one relationships, with support for:
    - Back references
    - Cascade operations
    - Lazy loading
    - Validation
    - On delete actions
    - Domain filtering
    - Context

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
        model_ref: Union[str, Type[M]],
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

    def _create_back_reference(self) -> OneToManyField[M]:
        """Create back reference field.

        Returns:
            OneToManyField: Back reference field instance
        """
        return OneToManyField(
            self.model_name,  # type: ignore
            back_populates=self.name,
            cascade=self.cascade,
            lazy_load=self.lazy_load,
            domain=self.domain,
            context=self.context,
        )

    async def convert(self, value: Any) -> Optional[M]:
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
                return value  # type: ignore
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
                    env = Environment.get_instance()
                    instance = await model_class.get(env, value)  # type: ignore
                    return cast(M, instance)
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

    async def validate(self, value: Optional[M]) -> Optional[M]:
        """Validate field value.

        Args:
            value: Value to validate

        Returns:
            Optional[M]: Validated value

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
        if self.domain and not await self._check_domain(value):  # type: ignore
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

    async def to_db(self, value: Optional[M], backend: str) -> Optional[str]:
        """Convert model instance to database format.

        Args:
            value: Model instance
            backend: Database backend type

        Returns:
            Database value or None

        Raises:
            FieldValidationError: If conversion fails
        """
        if value is None:
            return None

        if not hasattr(value, "id"):
            raise FieldValidationError(
                message=f"Model instance {value} has no id attribute",
                field_name=self.name,
            )
        return str(value.id)  # type: ignore

    async def from_db(self, value: Any, backend: str) -> Optional[M]:
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

        if not hasattr(self, "model"):
            raise FieldValidationError(
                message=(
                    f"Cannot load related model for field {self.name} "
                    "without parent model"
                ),
                field_name=self.name,
            )

        try:
            env = Environment.get_instance()
            if self.lazy_load:
                # Create model instance without loading
                instance = model_class(env)  # type: ignore
                instance.id = value  # type: ignore
                return instance  # type: ignore
            else:
                # Load and validate model instance
                instance = await model_class.get(env, value)  # type: ignore
                await instance.validate()  # type: ignore
                return instance  # type: ignore
        except Exception as e:
            raise FieldValidationError(
                message=f"Failed to load {model_class.__name__} with id {value}: {e}",
                field_name=self.name,
            ) from e
