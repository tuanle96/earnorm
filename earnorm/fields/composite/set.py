"""Set field implementation.

This module provides set field type for handling unique sequences of values.
It supports:
- Set validation
- Element validation
- Length validation
- Database type mapping
- Set comparison operations

Examples:
    >>> class User(Model):
    ...     roles = SetField(StringField())
    ...     permissions = SetField(
    ...         StringField(),
    ...         min_length=1,
    ...         max_length=10
    ...     )
    ...     tags = SetField(StringField())
    ...
    ...     # Query examples
    ...     admins = User.find(User.roles.contains("admin"))
    ...     has_perms = User.find(User.permissions.contains_all(["read", "write"]))
    ...     tagged = User.find(User.tags.is_not_empty())
"""

import json
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Protocol,
    Set,
    TypeVar,
    Union,
    cast,
)

from earnorm.database.mappers import get_mapper
from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin


class Comparable(Protocol):
    """Protocol for comparable types."""

    def __lt__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...


T = TypeVar("T", bound=Comparable)


class SetField(BaseField[Set[T]], FieldComparisonMixin, Generic[T]):
    """Field for set values.

    This field type handles unique sequences of values, with support for:
    - Set validation
    - Element validation
    - Length validation
    - Database type mapping
    - Set comparison operations

    Attributes:
        min_length: Minimum set length
        max_length: Maximum set length
        backend_options: Database backend options
    """

    min_length: Optional[int]
    max_length: Optional[int]
    backend_options: Dict[str, Any]

    def __init__(
        self,
        element_field: BaseField[T],
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        **options: Any,
    ) -> None:
        """Initialize set field.

        Args:
            element_field: Field type for set elements
            min_length: Minimum set length
            max_length: Maximum set length
            **options: Additional field options
        """
        super().__init__(**options)

        # Store as protected attribute to avoid type issues
        object.__setattr__(self, "_element_field", element_field)
        self.min_length = min_length
        self.max_length = max_length

        # Initialize backend options using mappers
        self.backend_options = {}
        for backend in ["mongodb", "postgres", "mysql"]:
            mapper = get_mapper(backend)
            self.backend_options[backend] = {
                "type": mapper.get_field_type(self),
                **mapper.get_field_options(self),
            }

    @property
    def element_field(self) -> BaseField[T]:
        """Get element field instance."""
        return object.__getattribute__(self, "_element_field")

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name
            model_name: Model name
        """
        await super().setup(name, model_name)
        await self.element_field.setup(f"{name}[]", model_name)

    async def validate(
        self, value: Any, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Set[T]]:
        """Validate set value.

        This method validates:
        - Value can be converted to set
        - Set length is within bounds
        - Elements are valid

        Args:
            value: Value to validate
            context: Validation context with following keys:
                    - model: Model instance
                    - env: Environment instance
                    - operation: Operation type (create/write/search...)
                    - values: Values being validated
                    - field_name: Name of field being validated

        Returns:
            Optional[Set[T]]: The validated set value

        Raises:
            FieldValidationError: If validation fails
        """
        value = await super().validate(value, context)

        if value is not None:
            # Convert to set if needed
            try:
                if not isinstance(value, set):
                    value = set(value)
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Cannot convert to set: {str(e)}",
                    field_name=self.name,
                    code="invalid_type",
                    context=context,
                )

            value_set: Set[Any] = cast(Set[Any], value)

            # Validate length
            if self.min_length is not None and len(value_set) < self.min_length:
                raise FieldValidationError(
                    message=f"Set must have at least {self.min_length} elements",
                    field_name=self.name,
                    code="min_length",
                    context=context,
                )

            if self.max_length is not None and len(value_set) > self.max_length:
                raise FieldValidationError(
                    message=f"Set must have at most {self.max_length} elements",
                    field_name=self.name,
                    code="max_length",
                    context=context,
                )

            # Create element context
            element_context = {
                **(context or {}),
                "parent_field": self,
                "parent_value": value_set,
                "validation_path": (
                    f"{context.get('validation_path', '')}.{self.name}"
                    if context
                    else self.name
                ),
            }

            # Validate elements
            validated_elements: Set[T] = set()
            for i, element in enumerate(value_set):
                try:
                    element_context["index"] = i
                    validated = await self.element_field.validate(
                        element, element_context
                    )
                    if validated is not None:
                        validated_elements.add(validated)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="invalid_element",
                        context=element_context,
                    ) from e

            return validated_elements

        return None

    async def convert(self, value: Any) -> Optional[Set[T]]:
        """Convert value to set.

        Args:
            value: Value to convert

        Returns:
            Converted set value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, str):
                # Try to parse as JSON array
                try:
                    value = json.loads(value)
                    if not isinstance(value, (list, set)):
                        raise FieldValidationError(
                            message="JSON value must be an array",
                            field_name=self.name,
                            code="invalid_json",
                        )
                except json.JSONDecodeError as e:
                    raise FieldValidationError(
                        message=f"Invalid JSON array: {str(e)}",
                        field_name=self.name,
                        code="invalid_json",
                    ) from e

            # Convert to set
            try:
                value = set(cast(Iterable[Any], value))
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Cannot convert to set: {str(e)}",
                    field_name=self.name,
                    code="conversion_error",
                ) from e

            # Convert elements
            result: Set[T] = set()
            for i, element in enumerate(value):
                try:
                    converted = await self.element_field.convert(element)
                    if converted is not None:
                        result.add(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result

        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert to set: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[Set[T]], backend: str) -> DatabaseValue:
        """Convert set to database format.

        Args:
            value: Set value to convert
            backend: Database backend type

        Returns:
            Converted set value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            result: List[DatabaseValue] = []
            # Convert to list and sort
            elements: List[T] = list(value)
            elements.sort()  # Sort in-place since T is Comparable
            for element in elements:
                db_value = await self.element_field.to_db(element, backend)
                result.append(db_value)
            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert set to database format: {str(e)}",
                field_name=self.name,
                code="db_conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[Set[T]]:
        """Convert database value to set.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted set value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        if not isinstance(value, (list, set)):
            raise FieldValidationError(
                message=f"Database value must be a list or set, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_db_type",
            )

        try:
            result: Set[T] = set()
            for i, element in enumerate(value):
                try:
                    converted = await self.element_field.from_db(element, backend)
                    if converted is not None:
                        result.add(converted)
                except Exception as e:
                    raise FieldValidationError(
                        message=f"Cannot convert database value at index {i}: {str(e)}",
                        field_name=self.name,
                        code="db_conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to set: {str(e)}",
                field_name=self.name,
                code="db_conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare set value for comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared set value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, (list, set)):
                # Convert to list and sort
                elements: List[T] = list(cast(Iterable[T], value))
                elements.sort()  # Sort in-place since T is Comparable
                return [
                    getattr(self.element_field, "_prepare_value")(x) for x in elements
                ]
            return [getattr(self.element_field, "_prepare_value")(value)]
        except (TypeError, ValueError, AttributeError):
            return None

    def contains(self, value: T) -> ComparisonOperator:
        """Check if set contains value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "contains", self._prepare_value(value))

    def not_contains(self, value: T) -> ComparisonOperator:
        """Check if set does not contain value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "not_contains", self._prepare_value(value))

    def contains_all(self, values: Union[List[T], Set[T]]) -> ComparisonOperator:
        """Check if set contains all values.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(
            self.name, "contains_all", self._prepare_value(values)
        )

    def contains_any(self, values: Union[List[T], Set[T]]) -> ComparisonOperator:
        """Check if set contains any value.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(
            self.name, "contains_any", self._prepare_value(values)
        )

    def is_subset(self, values: Union[List[T], Set[T]]) -> ComparisonOperator:
        """Check if set is subset of values.

        Args:
            values: Values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(self.name, "is_subset", self._prepare_value(values))

    def is_superset(self, values: Union[List[T], Set[T]]) -> ComparisonOperator:
        """Check if set is superset of values.

        Args:
            values: Values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(self.name, "is_superset", self._prepare_value(values))

    def length_equals(self, length: int) -> ComparisonOperator:
        """Check if set length equals value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_eq", length)

    def length_greater_than(self, length: int) -> ComparisonOperator:
        """Check if set length is greater than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_gt", length)

    def length_less_than(self, length: int) -> ComparisonOperator:
        """Check if set length is less than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_lt", length)

    def is_empty(self) -> ComparisonOperator:
        """Check if set is empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if set is not empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_empty", None)
