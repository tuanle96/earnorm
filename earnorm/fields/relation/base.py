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
            "department",  # String reference to avoid circular imports
            field="department_id",
            ondelete="cascade",
            domain=[("active", "=", True)],
            context={"show_archived": False}
        )
    ```
"""

from __future__ import annotations

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

from earnorm.exceptions import (
    FieldValidationError,
    RelationBackReferenceError,
    RelationConstraintError,
    RelationLoadError,
    RelationModelResolutionError,
)
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator

# Type variables with constraints
M_co = TypeVar(
    "M_co", bound=Any, contravariant=True
)  # Contravariant type variable for model protocol
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
VALID_ONDELETE: Final[FrozenSet[str]] = frozenset({"cascade", "set null", "restrict"})


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


@runtime_checkable
class RelatedModelProtocol(Protocol[M_co]):
    """Protocol for related model interface.

    This protocol defines the minimal interface required for related models in relationships.
    It is a simplified version of ModelProtocol that only includes the essential
    methods and attributes needed for relationship handling.
    """

    env: Any  # Type will be Environment
    id: str

    @classmethod
    async def get(cls, env: Any, _id: str) -> "RelatedModelProtocol[M_co]":
        """Get model by ID."""
        ...

    @classmethod
    async def browse(cls, _id: str) -> Optional["RelatedModelProtocol[M_co]"]:
        """Browse model by ID."""
        ...

    @classmethod
    async def search(
        cls, domain: Domain, **kwargs: Any
    ) -> List["RelatedModelProtocol[M_co]"]:
        """Search models by domain."""
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

    def __len__(self) -> int:
        """Get number of items."""
        return len(self.items)

    def __iter__(self):
        """Iterate over items."""
        return iter(self.items)

    def __getitem__(self, index: int) -> M:
        """Get item by index."""
        return self.items[index]


class RelationField(BaseField[V], RelationComparisonMixin, Generic[V]):
    """Base class for relation fields.

    This class provides common functionality for relation fields:
    - Model references and lazy loading
    - Back references and cascade operations
    - Domain filtering and context
    - Validation and type checking
    - Comparison operations

    Args:
        model_ref: Referenced model name (_name attribute, not class name)
        field: Field name for the foreign key
        ondelete: Delete behavior ("cascade", "set null", "restrict")
        back_populates: Name of field on other model for back reference
        cascade_validation: Whether to cascade validation to related records
        lazy_load: Enable lazy loading (default: True)
        domain: Domain for filtering related records
        context: Context for related records
        cascade: Enable cascade operations (default: False)
        **kwargs: Additional field options

    Examples:
        >>> class User(Model):
        ...     department = ManyToOneField(
        ...         "department",  # Use _name of model, not class name
        ...         field="department_id",
        ...         ondelete="cascade",
        ...         domain=[("active", "=", True)],
        ...         context={"show_archived": False}
        ...     )
    """

    def __init__(
        self,
        model_ref: str,
        field: str,
        *,
        ondelete: str = "set null",
        back_populates: Optional[str] = None,
        cascade_validation: bool = True,
        lazy_load: bool = True,
        domain: Optional[Domain] = None,
        context: Optional[Context] = None,
        cascade: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize relation field."""
        super().__init__(**kwargs)

        # Validate ondelete option
        if ondelete not in VALID_ONDELETE:
            raise ValueError(
                f"Invalid ondelete value: {ondelete}. "
                f"Must be one of: {', '.join(VALID_ONDELETE)}"
            )

        self.model_ref = model_ref
        self.field = field
        self.ondelete = ondelete
        self.back_populates = back_populates
        self.cascade_validation = cascade_validation
        self.lazy_load = lazy_load
        self.domain = domain or []
        self.context = context or DEFAULT_CONTEXT.copy()
        self.cascade = cascade

        # Internal state
        self._model_class: Optional[Type[RelatedModelProtocol[Any]]] = None
        self._resolved_model: bool = False

    async def resolve_model_reference(self) -> None:
        """Resolve model reference to actual model class.

        This method is called during model setup to resolve string references
        to actual model classes.

        Raises:
            RelationModelResolutionError: If referenced model cannot be resolved
            ValueError: If model_ref is not _name of model
        """
        try:
            if not self._resolved_model:
                from earnorm.base.env import Environment

                env = Environment.get_instance()
                try:
                    model = await env.get_model(self.model_ref)
                    if model._name != self.model_ref:  # type: ignore
                        raise ValueError(
                            f"model_ref must be _name of model, got class name '{self.model_ref}'"
                        )
                    self._model_class = cast(Type[RelatedModelProtocol[Any]], model)
                    self._resolved_model = True
                except Exception as e:
                    raise RelationModelResolutionError(
                        f"Failed to resolve model reference: {str(e)}",
                        field_name=self.name,
                    )

        except Exception as e:
            raise RelationModelResolutionError(
                f"Failed to resolve model reference: {str(e)}", field_name=self.name
            )

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name
            model_name: Model name

        Raises:
            RelationBackReferenceError: If back reference setup fails
        """
        await super().setup(name, model_name)
        await self.resolve_model_reference()

        # Set up back reference if needed
        if self.back_populates and self._model_class:
            # Get back reference field
            back_field = getattr(self._model_class, self.back_populates, None)
            if back_field is None:
                raise RelationBackReferenceError(
                    f"Back reference field '{self.back_populates}' not found on model '{self.model_ref}'",
                    field_name=self.name,
                )

            # Set back reference
            back_field.back_populates = self.name

    async def _validate_related_record(self, value: Any, context: Any) -> None:
        """Validate the related record.

        Args:
            value: Related record to validate
            context: Validation context

        Raises:
            FieldValidationError: If validation fails
        """
        try:
            # Get validation method if exists
            validate_method = getattr(value, "validate", None)
            if validate_method and callable(validate_method):
                await validate_method()
        except Exception as e:
            raise FieldValidationError(
                message=f"Validation failed for related {self.model_ref}: {str(e)}",
                field_name=self.name,
                code="validation_failed",
            )

    async def convert_to_db(self, value: Any) -> Any:
        """Convert value for database storage.

        Args:
            value: Value to convert

        Returns:
            Any: Converted value for database
        """
        if value is None:
            return None

        # Ensure value is proper model instance
        if self._model_class is None:
            raise FieldValidationError(
                message=f"Model class not resolved for field {self.name}",
                field_name=self.name,
                code="model_not_resolved",
            )

        if not isinstance(value, self._model_class):
            raise FieldValidationError(
                message=f"Expected {self._model_class.__name__} instance for field {self.name}, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

        # Store ID reference
        return str(value.id)

    async def convert_from_db(self, value: Any) -> Optional[V]:
        """Convert database value to model instance.

        Args:
            value: Database value

        Returns:
            Optional[V]: Model instance or None

        Raises:
            RelationLoadError: If related record cannot be loaded
        """
        if value is None:
            return None

        # Ensure model class is resolved
        if not self._resolved_model:
            await self.resolve_model_reference()

        if not self._model_class:
            raise FieldValidationError(
                message=f"Model class not resolved for field {self.name}",
                field_name=self.name,
                code="model_not_resolved",
            )

        # Load related record
        try:
            record = await self._model_class.browse(value)
            return cast(V, record)
        except Exception as e:
            raise RelationLoadError(
                message=f"Failed to load related {self.model_ref}: {str(e)}",
                field_name=self.name,
            )

    async def pre_delete(self, record: Any) -> None:
        """Handle pre-delete operations.

        Args:
            record: Record being deleted

        Raises:
            RelationConstraintError: If delete is restricted
        """
        # Get related record
        related = await getattr(record, self.name)
        if not related:
            return

        if self.ondelete == "restrict":
            raise RelationConstraintError(
                f"Cannot delete {record} because it is referenced by {related}",
                field_name=self.name,
            )
        elif self.ondelete == "cascade":
            await related.unlink()
        # "set null" is handled automatically by the database

    def _check_model_class(self) -> Type[RelatedModelProtocol[Any]]:
        """Check if model class is resolved and return it.

        Returns:
            Type[RelatedModelProtocol[Any]]: Resolved model class

        Raises:
            FieldValidationError: If model class is not resolved
        """
        if not self._resolved_model:
            raise FieldValidationError(
                message=f"Model reference not resolved for field {self.name}",
                field_name=self.name,
                code="model_not_resolved",
            )

        if self._model_class is None:
            raise FieldValidationError(
                message=f"Model class not resolved for field {self.name}",
                field_name=self.name,
                code="model_not_resolved",
            )

        # Type assertion to help type checker
        assert isinstance(self._model_class, type), "Model class must be a type"
        return self._model_class

    async def __get__(
        self, instance: Optional[Any] = None, owner: Optional[Any] = None
    ) -> Union[V, "RelationField[V]"]:
        """Descriptor get implementation.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Union[V, RelationField[V]]: Field value or field instance

        Raises:
            FieldValidationError: If model class is not resolved
        """
        if instance is None:
            return self

        # Get raw value
        value = instance.__dict__.get(self.name)

        # Ensure model is resolved
        if not self._resolved_model:
            try:
                await self.resolve_model_reference()
            except Exception as e:
                raise FieldValidationError(
                    message=str(e),
                    field_name=self.name,
                    code="model_resolution_failed",
                )

        model_class = self._check_model_class()
        assert isinstance(model_class, type), "Model class must be a type"

        # Return value if already loaded
        if value is not None and isinstance(value, model_class):
            return cast(V, value)
        elif value is not None and isinstance(value, ModelList):
            return cast(V, value)

        # Return None if no value
        if value is None:
            return cast(V, None)

        # Load related record if lazy loading enabled
        if self.lazy_load:
            try:
                from earnorm.base.env import Environment

                env = Environment.get_instance()
                instance = await model_class.get(env, str(value))  # type: ignore
                return cast(V, instance)
            except Exception as e:
                raise FieldValidationError(
                    message=f"Failed to load related record: {str(e)}",
                    field_name=self.name,
                    code="load_failed",
                )

        return cast(V, value)

    def __set__(self, instance: Any, value: Any) -> None:
        """Descriptor set implementation.

        Args:
            instance: Model instance
            value: Value to set

        Raises:
            ValueError: If value is invalid
            FieldValidationError: If model class is not resolved
        """
        model_class = self._check_model_class()
        assert isinstance(model_class, type), "Model class must be a type"

        if value is not None:
            if not isinstance(value, model_class) and not isinstance(value, ModelList):
                raise ValueError(
                    f"{self.name} must be instance of {self.model_ref} or ModelList"
                )

        instance.__dict__[self.name] = value

    async def _check_domain(self, value: Any) -> bool:
        """Check if value matches domain constraints.

        Args:
            value: Value to check

        Returns:
            bool: True if value matches domain constraints
        """
        if not self.domain:
            return True

        for field, operator, expected in self.domain:
            field_value = getattr(value, field, None)
            if not await self._compare_values(field_value, operator, expected):
                return False

        return True

    async def _compare_values(
        self, value: Any, operator: DomainOperator, expected: Any
    ) -> bool:
        """Compare values using domain operator.

        Args:
            value: Value to compare
            operator: Comparison operator
            expected: Expected value

        Returns:
            bool: True if comparison matches
        """
        if operator == "=":
            return value == expected
        elif operator == "!=":
            return value != expected
        elif operator == ">":
            return value > expected
        elif operator == ">=":
            return value >= expected
        elif operator == "<":
            return value < expected
        elif operator == "<=":
            return value <= expected
        elif operator == "in":
            return value in expected
        elif operator == "not in":
            return value not in expected
        else:
            raise ValueError(f"Invalid operator: {operator}")

    async def validate(
        self, value: Any, context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Validate field value.

        Args:
            value: Value to validate
            context: Optional validation context

        Returns:
            Any: Validated value

        Raises:
            FieldValidationError: If validation fails
        """
        if value is None:
            if self.required:
                raise FieldValidationError(
                    message=f"Field {self.name} is required",
                    field_name=self.name,
                    code="required_field",
                )
            return None

        if not self._resolved_model:
            await self.resolve_model_reference()

        if self._model_class is None:
            raise FieldValidationError(
                message=f"Model class not resolved for field {self.name}",
                field_name=self.name,
                code="model_not_resolved",
            )

        if not isinstance(value, self._model_class):
            raise FieldValidationError(
                message=(
                    f"Expected {self._model_class.__name__} instance for field {self.name}, "
                    f"got {type(value).__name__}"
                ),
                field_name=self.name,
                code="invalid_type",
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
                code="domain_mismatch",
            )

        # Run validators if any
        if hasattr(self, "validators"):
            for validator in self.validators:
                try:
                    await validator(value, context or {})  # type: ignore
                except Exception as e:
                    raise FieldValidationError(
                        message=str(e),
                        field_name=self.name,
                        code="validation_failed",
                    ) from e

        return value  # type: ignore


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
            cast(str, model_ref if isinstance(model_ref, str) else model_ref.__name__),
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
