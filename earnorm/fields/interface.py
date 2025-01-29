"""Field interface types.

This module provides protocol classes and type definitions for fields.
It includes:
- FieldProtocol for field operations
- ModelInterface for model operations
- Common field value types
- Database conversion methods

Examples:
    >>> from earnorm.fields.interface import FieldProtocol, ModelInterface
    >>> from typing import runtime_checkable, Protocol
    >>>
    >>> @runtime_checkable
    ... class CustomField(FieldProtocol):
    ...     def validate(self, value: Any) -> None:
    ...         pass
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

from earnorm.fields.adapters.base import DatabaseAdapter
from earnorm.types.fields import DatabaseValue

# Type for field values (None or actual value)
FieldValue = Union[None, bool, int, float, str, Dict[str, Any], List[Any], Any]

# Database backend types
BackendOptions = Dict[str, Any]

# Type variable for field types
T = TypeVar("T")


@runtime_checkable
class FieldProtocol(Protocol[T]):
    """Protocol for field classes.

    This protocol defines the interface that all field classes must implement.
    It includes methods for:
    - Field setup and configuration
    - Validation and conversion
    - Database operations
    - Computed fields
    """

    name: str
    model_name: str
    required: bool
    readonly: bool
    store: bool
    index: bool
    help: str
    compute: Optional[str]
    depends: list[str]
    backend_options: Dict[str, Dict[str, Any]]
    adapters: Dict[str, DatabaseAdapter[T]]

    def setup(self, name: str, model_name: str) -> None:
        """Setup field.

        This method is called when field is added to model.
        It initializes field name and model name.

        Args:
            name: Field name
            model_name: Model name
        """
        ...

    async def validate(self, value: Any) -> None:
        """Validate field value.

        This method validates field value according to field type and options.
        It raises ValidationError if validation fails.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        ...

    async def convert(self, value: Any) -> Optional[T]:
        """Convert value to field type.

        This method converts value to field's Python type.
        It returns None if conversion fails.

        Args:
            value: Value to convert

        Returns:
            Converted value or None if conversion fails
        """
        ...

    async def to_db(self, value: Optional[T], backend: str) -> DatabaseValue:
        """Convert Python value to database format.

        This method uses the appropriate database adapter to convert the value.
        Each backend may have different format requirements.

        Args:
            value: Value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Database value

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return await self.adapters[backend].to_db_value(value)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[T]:
        """Convert database value to Python format.

        This method uses the appropriate database adapter to convert the value.
        Each backend may store values in different format.

        Args:
            value: Database value
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Python value

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return await self.adapters[backend].from_db_value(value)

    def get_backend_options(self, backend: str) -> BackendOptions:
        """Get database-specific options.

        This method returns options specific to database backend.
        Options may include:
        - Column type
        - Column constraints
        - Indexes
        - Validation rules

        Args:
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Backend-specific options

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return {
            "type": self.adapters[backend].get_field_type(),
            **self.adapters[backend].get_field_options(),
        }

    def register_adapter(self, adapter: DatabaseAdapter[T]) -> None:
        """Register database adapter.

        This method registers a new database adapter for a specific backend.
        It allows adding support for new database types.

        Args:
            adapter: Database adapter instance
        """
        self.adapters[adapter.backend_name] = adapter

    def setup_triggers(self) -> None:
        """Setup compute triggers.

        This method sets up triggers for computed fields.
        It is called when field is initialized.
        """
        ...

    def copy(self) -> "FieldProtocol[T]":
        """Create copy of field.

        This method creates deep copy of field.
        It is used for field inheritance.

        Returns:
            New field instance
        """
        ...


@runtime_checkable
class ModelInterface(Protocol):
    """Protocol defining model interface.

    This protocol defines the attributes and methods that all models must implement:
    - Model metadata (_name, _description, etc)
    - Model fields (_fields)
    - Model operations (validate, to_dict, etc)

    Attributes:
        _name: Model name
        _fields: Model fields
    """

    _name: str
    _fields: Dict[str, FieldProtocol[Any]]

    def validate(self) -> None:
        """Validate model."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        ...


# Type for field options
FieldOptions = Dict[str, Any]
