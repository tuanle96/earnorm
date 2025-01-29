"""Base class for relation fields.

This module provides the base field class that all relation field types inherit from.
It handles:
- Model references and lazy loading
- Back references and cascade operations
- Domain filtering and context
- Validation and type checking

Examples:
    ```python
    class User(Model):
        department = ManyToOneField(
            "Department",
            ondelete="cascade",
            domain=[("active", "=", True)],
            context={"show_archived": False}
        )
    ```
"""

from typing import (
    Any,
    Dict,
    Final,
    FrozenSet,
    Generic,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator

# Type variables with constraints
M_co = TypeVar("M_co", covariant=True)  # Covariant type variable for model protocol
M = TypeVar("M")  # Invariant type variable for model types
V = TypeVar("V")  # Invariant type variable for field value types

# Type aliases with better type hints
DomainOperator = Literal["=", "!=", ">", ">=", "<", "<=", "in", "not in"]
DomainTuple = Tuple[str, DomainOperator, Any]
Domain = List[DomainTuple]
Context = Dict[str, Any]

# Constants
DEFAULT_CONTEXT: Final[Dict[str, Any]] = {}
VALID_OPERATORS: Final[FrozenSet[DomainOperator]] = frozenset(
    {"=", "!=", ">", ">=", "<", "<=", "in", "not in"}
)


@runtime_checkable
class RelationComparisonMixin(Protocol):
    """Mixin class for relation-specific comparison operations.

    This class provides default implementations for comparison operations
    specific to relation fields. Each relation type can override these
    methods to provide type-specific comparison behavior.
    """

    name: str  # Field name for error messages

    def is_empty(self) -> ComparisonOperator:
        """Check if relation is empty (no related records).

        Returns:
            ComparisonOperator: Comparison operator for empty check
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if relation is not empty (has related records).

        Returns:
            ComparisonOperator: Comparison operator for non-empty check
        """
        return ComparisonOperator(self.name, "is_not_empty", None)

    def contains(self, value: Any) -> ComparisonOperator:
        """Check if relation contains a specific value.

        Args:
            value: Value to check for (model instance or ID)

        Returns:
            ComparisonOperator: Comparison operator for contains check
        """
        if hasattr(value, "id"):
            value = str(value.id)  # type: ignore
        return ComparisonOperator(self.name, "contains", value)

    def size(self, operator: DomainOperator, value: int) -> ComparisonOperator:
        """Compare the size of the relation.

        Args:
            operator: Comparison operator (=, !=, >, >=, <, <=)
            value: Size to compare against

        Returns:
            ComparisonOperator: Comparison operator for size check

        Raises:
            ValueError: If operator is not valid for size comparison
        """
        if operator not in {"=", "!=", ">", ">=", "<", "<="}:
            raise ValueError(f"Invalid operator for size comparison: {operator}")
        return ComparisonOperator(self.name, f"size_{operator}", value)

    def any(
        self, field: str, operator: DomainOperator, value: Any
    ) -> ComparisonOperator:
        """Check if any related record matches a condition.

        Args:
            field: Field name to check
            operator: Comparison operator
            value: Value to compare against

        Returns:
            ComparisonOperator: Comparison operator for any check
        """
        return ComparisonOperator(self.name, "any", (field, operator, value))

    def all(
        self, field: str, operator: DomainOperator, value: Any
    ) -> ComparisonOperator:
        """Check if all related records match a condition.

        Args:
            field: Field name to check
            operator: Comparison operator
            value: Value to compare against

        Returns:
            ComparisonOperator: Comparison operator for all check
        """
        return ComparisonOperator(self.name, "all", (field, operator, value))


class ModelProtocol(Protocol[M_co]):
    """Protocol for model interface."""

    env: Any  # Type will be Environment
    id: str

    @classmethod
    async def get(cls, env: Any, _id: str) -> "ModelProtocol[M_co]":
        """Get model by ID."""
        ...


class ModelList(Generic[M]):
    """Container for list of model instances.

    This class wraps a list of model instances to make it compatible
    with the BaseModel type system.

    Attributes:
        items: List of model instances
    """

    items: List[M]

    def __init__(self, items: List[M]) -> None:
        """Initialize model list.

        Args:
            items: List of model instances
        """
        self.items = items


class RelationField(BaseField[V], RelationComparisonMixin, Generic[V]):
    """Base class for relation fields.

    This class provides common functionality for relation fields:
    - Model references and lazy loading
    - Back references and cascade operations
    - Domain filtering and context
    - Validation and type checking
    - Comparison operations

    Args:
        model_ref: Referenced model name or class
        back_populates: Name of field on other model for back reference
        cascade: Enable cascade operations (default: False)
        lazy_load: Enable lazy loading (default: True)
        domain: Domain for filtering related records
        context: Context for related records
        **kwargs: Additional field options
    """

    def __init__(
        self,
        model_ref: Union[str, Type[Any]],
        *,
        back_populates: Optional[str] = None,
        cascade: bool = False,
        lazy_load: bool = True,
        domain: Optional[Domain] = None,
        context: Optional[Context] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize relation field."""
        super().__init__(**kwargs)
        self.model_ref = model_ref
        self.back_populates = back_populates
        self.cascade = cascade
        self.lazy_load = lazy_load
        self.domain = domain or []
        self.context = context or DEFAULT_CONTEXT.copy()

        # Internal state
        self._model_class: Optional[Type[Any]] = None
        self._resolved_model = False

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name
            model_name: Model name
        """
        await super().setup(name, model_name)

        # Resolve model reference if string
        if isinstance(self.model_ref, str):
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            self._model_class = cast(Type[Any], await env.get_model(self.model_ref))
            self._resolved_model = True

        # Set up back reference if needed
        if self.back_populates:
            await self._setup_back_reference()

    async def _setup_back_reference(self) -> None:
        """Set up back reference on related model."""
        if not self._resolved_model or not self.back_populates:
            return

        # Get related model class
        model_class = self.get_model_class()

        # Create back reference field
        back_field = self._create_back_reference()

        # Add field to related model
        setattr(model_class, self.back_populates, back_field)

        # Set up back reference field
        await back_field.setup(self.back_populates, model_class.__name__)

    def _create_back_reference(self) -> "RelationField[V]":
        """Create back reference field.

        This method should be overridden by subclasses to create the appropriate
        back reference field type.

        Returns:
            RelationField: Back reference field instance

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _create_back_reference()")

    def get_model_class(self) -> Type[Any]:
        """Get referenced model class.

        Returns:
            Type[Any]: Model class

        Raises:
            RuntimeError: If model reference is not resolved
        """
        if not self._resolved_model:
            raise RuntimeError(
                f"Model reference not resolved for field {self.name}. "
                "Did you forget to call setup()?"
            )
        if not self._model_class:
            raise RuntimeError(
                f"Model class not found for field {self.name}. "
                f"Model reference: {self.model_ref}"
            )
        return self._model_class

    async def validate(self, value: Optional[V]) -> Optional[V]:
        """Validate field value.

        Args:
            value: Value to validate

        Returns:
            Optional[V]: Validated value

        Raises:
            FieldValidationError: If validation fails
        """
        # Run base validation
        value = await super().validate(value)

        if value is not None:
            # Check value is instance of model class
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

    async def _check_domain(self, value: V) -> bool:
        """Check if value matches domain constraints.

        Args:
            value: Value to check

        Returns:
            bool: True if value matches domain
        """
        for field, operator, expected in self.domain:
            # Get actual value
            actual = getattr(value, field)

            # Compare values based on operator
            if operator == "=":
                if actual != expected:
                    return False
            elif operator == "!=":
                if actual == expected:
                    return False
            elif operator == ">":
                if actual <= expected:
                    return False
            elif operator == ">=":
                if actual < expected:
                    return False
            elif operator == "<":
                if actual >= expected:
                    return False
            elif operator == "<=":
                if actual > expected:
                    return False
            elif operator == "in":
                if actual not in expected:
                    return False
            elif operator == "not in":
                if actual in expected:
                    return False

        return True

    def copy(self) -> "RelationField[V]":
        """Create copy of field.

        Returns:
            RelationField: New field instance with same configuration
        """
        return cast("RelationField[V]", super().copy())


class OneToManyRelationField(RelationField[ModelList[M]]):
    """Base class for one-to-many relation fields.

    This class provides common functionality for one-to-many relation fields:
    - Model references and lazy loading
    - Back references and cascade operations
    - Domain filtering and context
    - Validation and type checking
    - List operations

    Args:
        model_ref: Referenced model name or class
        back_populates: Name of field on other model for back reference
        cascade: Enable cascade operations (default: True)
        lazy_load: Enable lazy loading (default: True)
        domain: Domain for filtering related records
        context: Context for related records
        **kwargs: Additional field options
    """

    def __init__(
        self,
        model_ref: Union[str, Type[M]],
        *,
        back_populates: Optional[str] = None,
        cascade: bool = True,
        lazy_load: bool = True,
        domain: Optional[Domain] = None,
        context: Optional[Context] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize one-to-many relation field."""
        super().__init__(
            model_ref,
            back_populates=back_populates,
            cascade=cascade,
            lazy_load=lazy_load,
            domain=domain,
            context=context,
            **kwargs,
        )

    def _create_back_reference(self) -> "RelationField[ModelList[M]]":
        """Create back reference field.

        Returns:
            RelationField: Back reference field instance
        """
        return self.__class__(
            self.model_name,
            back_populates=self.name,
            cascade=self.cascade,
            lazy_load=self.lazy_load,
        )

    async def validate(self, value: Optional[ModelList[M]]) -> Optional[ModelList[M]]:
        """Validate field value.

        Args:
            value: Value to validate

        Returns:
            Optional[ModelList[M]]: Validated value

        Raises:
            FieldValidationError: If validation fails
        """
        if value is None:
            return None

        # Check each item in list
        model_class = self.get_model_class()
        for item in value.items:
            if not isinstance(item, model_class):
                raise FieldValidationError(
                    message=(
                        f"Expected {model_class.__name__} instance in list for field {self.name}, "
                        f"got {type(item).__name__}"
                    ),
                    field_name=self.name,
                )

            # Check domain if specified
            if self.domain and not await self._check_domain(item):  # type: ignore
                constraints = [
                    f"{field} {op} {expected}" for field, op, expected in self.domain
                ]
                raise FieldValidationError(
                    message=(
                        f"Item does not match domain constraints for field {self.name}: "
                        f"{', '.join(constraints)}"
                    ),
                    field_name=self.name,
                )

        return value
