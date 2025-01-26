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
)

from earnorm.base.env import Environment
from earnorm.base.model.meta import BaseModel
from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField

# Type variables with constraints
M_co = TypeVar("M_co", bound=BaseModel, covariant=True)
M = TypeVar("M", bound=BaseModel)

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


class ModelProtocol(Protocol[M_co]):
    """Protocol for model interface."""

    env: Environment
    id: str

    @classmethod
    async def get(cls, env: Environment, _id: str) -> "ModelProtocol[M_co]":
        """Get model by ID."""
        ...


class ModelList(BaseModel, Generic[M]):
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
        super().__init__()
        self.items = items


class RelationField(BaseField[M]):
    """Base class for relation fields.

    This class provides common functionality for relation fields:
    - Model references and lazy loading
    - Back references and cascade operations
    - Domain filtering and context
    - Validation and type checking

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
        model_ref: Union[str, Type[M]],
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
        self._model_class: Optional[Type[M]] = None
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
            env = Environment.get_instance()
            self._model_class = cast(Type[M], env.get_model(self.model_ref))
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

    def _create_back_reference(self) -> "RelationField[Any]":
        """Create back reference field.

        This method should be overridden by subclasses to create the appropriate
        back reference field type.

        Returns:
            RelationField: Back reference field instance

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _create_back_reference()")

    def get_model_class(self) -> Type[M]:
        """Get referenced model class.

        Returns:
            Type[M]: Model class

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

    async def validate(self, value: Optional[M]) -> Optional[M]:
        """Validate field value.

        Args:
            value: Value to validate

        Returns:
            Optional[M]: Validated value

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

    async def _check_domain(self, value: M) -> bool:
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

    def copy(self) -> "RelationField[M]":
        """Create copy of field.

        Returns:
            RelationField[M]: New field instance with same configuration
        """
        return cast(RelationField[M], super().copy())


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
        model_ref: Union[str, Type[ModelList[M]]],
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
