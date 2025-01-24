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

# Type for field values (None or actual value)
FieldValue = Union[None, bool, int, float, str, Dict[str, Any], List[Any], Any]

# Database backend types
DatabaseValue = Any
BackendOptions = Dict[str, Any]

# Type variable for field types
T = TypeVar("T")


@runtime_checkable
class FieldProtocol(Protocol):
    """Protocol defining field interface.

    This protocol defines the attributes and methods that all fields must implement:
    - Field metadata (name, model_name, help, etc)
    - Field options (required, readonly, store, etc)
    - Field operations (validate, convert, etc)
    - Database operations (to_db, from_db, etc)
    - Compute methods (compute, depends, etc)

    Attributes:
        name: Field name
        model_name: Model name
        required: Whether field is required
        readonly: Whether field is readonly
        store: Whether field is stored
        index: Whether field is indexed
        help: Help text
        compute: Compute method name
        depends: Field dependencies
        backend_options: Backend-specific options
    """

    name: str
    model_name: str
    required: bool
    readonly: bool
    store: bool
    index: bool
    help: str
    compute: Optional[str]
    depends: List[str]
    backend_options: Dict[str, Dict[str, Any]]

    def setup(self, name: str, model_name: str) -> None:
        """Setup field.

        This method is called when field is added to model.
        It initializes field name and model name.

        Args:
            name: Field name
            model_name: Model name
        """
        ...

    def validate(self, value: Any) -> None:
        """Validate field value.

        This method validates field value according to field type and options.
        It raises ValidationError if validation fails.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        ...

    def convert(self, value: Any) -> FieldValue:
        """Convert value to field type.

        This method converts value to field's Python type.
        It returns None if conversion fails.

        Args:
            value: Value to convert

        Returns:
            Converted value or None if conversion fails
        """
        ...

    def to_db(self, value: Any, backend: str) -> DatabaseValue:
        """Convert Python value to database format.

        This method converts Python value to format suitable for database.
        Each backend may have different format requirements.

        Args:
            value: Value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Database value
        """
        ...

    def from_db(self, value: DatabaseValue, backend: str) -> FieldValue:
        """Convert database value to Python format.

        This method converts database value back to Python type.
        Each backend may store values in different format.

        Args:
            value: Database value
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Python value
        """
        ...

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
        """
        ...

    def setup_triggers(self) -> None:
        """Setup compute triggers.

        This method sets up triggers for computed fields.
        It is called when field is initialized.
        """
        ...

    def copy(self) -> "FieldProtocol":
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
    _fields: Dict[str, FieldProtocol]

    def validate(self) -> None:
        """Validate model."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        ...


# Type for field options
FieldOptions = Dict[str, Any]
