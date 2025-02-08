"""Many-to-many relationship field implementation.

This module provides many-to-many relationship field types for handling relationships between models.
It supports:
- Forward and reverse relationships
- Lazy loading of related models
- Cascade deletion
- Database foreign key constraints
- Validation of related models
- Filtering and ordering of related models
- Through models for additional relationship data
- Comparison operations

Examples:
    >>> class Student(Model):
    ...     name = StringField(required=True)
    ...     courses = ManyToManyField("course", back_populates="students")
    ...
    >>> class Course(Model):
    ...     name = StringField(required=True)
    ...     # students field will be added automatically with back_populates="students"
    ...
    >>> # With through model
    >>> class Enrollment(Model):
    ...     student = OneToOneField("student")
    ...     course = OneToOneField("course")
    ...     date = DateField(required=True)
    ...     grade = FloatField()
    ...
    >>> class Student(Model):
    ...     name = StringField(required=True)
    ...     courses = ManyToManyField(
    ...         "course",  # Use _name of model, not class name
    ...         through="enrollment",
    ...         back_populates="students"
    ...     )
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Final,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from earnorm.exceptions import FieldValidationError, ModelNotFoundError
from earnorm.fields.relation.base import Context, Domain, ModelList, RelationField
from earnorm.types.fields import ComparisonOperator

if TYPE_CHECKING:
    from earnorm.base.model.meta import BaseModel

    M = TypeVar("M", bound="BaseModel")  # Model type
else:
    M = TypeVar("M")  # Type variable for runtime

# Constants
DEFAULT_CASCADE: Final[bool] = True


class ManyToManyField(RelationField[ModelList[M]]):
    """Field for many-to-many relationships.

    This field type handles many-to-many relationships, with support for:
    - Back references
    - Cascade operations
    - Lazy loading
    - Validation
    - Through models
    - Bulk operations
    - Domain filtering
    - Context
    - Comparison operations

    Examples:
        >>> class Student(Model):
        ...     name = StringField(required=True)
        ...     courses = ManyToManyField("course", back_populates="students")
        ...
        >>> class Course(Model):
        ...     name = StringField(required=True)
        ...     # students field will be added automatically with back_populates="students"
        ...
        >>> # With through model
        >>> class Enrollment(Model):
        ...     student = OneToOneField("student")
        ...     course = OneToOneField("course")
        ...     date = DateField(required=True)
        ...     grade = FloatField()
        ...
        >>> class Student(Model):
        ...     name = StringField(required=True)
        ...     courses = ManyToManyField(
        ...         "course",  # Use _name of model, not class name
        ...         through="enrollment",
        ...         back_populates="students"
        ...     )
    """

    def __init__(
        self,
        model_ref: str,
        *,
        through: Optional[str] = None,
        back_populates: Optional[str] = None,
        cascade: bool = DEFAULT_CASCADE,
        lazy_load: bool = True,
        domain: Optional[Domain] = None,
        context: Optional[Context] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize many-to-many field.

        Args:
            model_ref: Referenced model name (_name attribute, not class name)
            through: Through model name (_name attribute, not class name)
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
            context=context,
            **kwargs,
        )
        self.through = through
        self._through_class: Optional[Type["BaseModel"]] = None

    def is_empty(self) -> ComparisonOperator:
        """Check if relation is empty (no related records).

        Returns:
            ComparisonOperator: Comparison operator for empty check
        """
        return ComparisonOperator(self.name, "size_=", 0)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if relation is not empty (has related records).

        Returns:
            ComparisonOperator: Comparison operator for non-empty check
        """
        return ComparisonOperator(self.name, "size_>", 0)

    def contains(self, value: Union[str, "BaseModel"]) -> ComparisonOperator:
        """Check if relation contains a specific value.

        Args:
            value: Value to check for (model instance or ID)

        Returns:
            ComparisonOperator: Comparison operator for contains check
        """
        if isinstance(value, str):
            return ComparisonOperator(self.name, "contains", value)
        return ComparisonOperator(self.name, "contains", str(value.id))

    def size(self, operator: str, value: int) -> ComparisonOperator:
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

    def any(self, field: str, operator: str, value: Any) -> ComparisonOperator:
        """Check if any related record matches a condition.

        Args:
            field: Field name to check
            operator: Comparison operator
            value: Value to compare against

        Returns:
            ComparisonOperator: Comparison operator for any check
        """
        return ComparisonOperator(self.name, "any", (field, operator, value))

    def all(self, field: str, operator: str, value: Any) -> ComparisonOperator:
        """Check if all related records match a condition.

        Args:
            field: Field name to check
            operator: Comparison operator
            value: Value to compare against

        Returns:
            ComparisonOperator: Comparison operator for all check
        """
        return ComparisonOperator(self.name, "all", (field, operator, value))

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name
            model_name: Model name
        """
        await super().setup(name, model_name)

        # Resolve through model reference if string
        if isinstance(self.through, str):
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            try:
                self._through_class = await env.get_model(self.through)  # type: ignore
            except ModelNotFoundError as e:
                raise FieldValidationError(
                    message=f"Through model {self.through} not found: {str(e)}",
                    field_name=self.name,
                    code="through_model_not_found",
                ) from e

    def _create_back_reference(self) -> "ManyToManyField[M]":
        """Create back reference field.

        Returns:
            ManyToManyField: Back reference field instance
        """
        return ManyToManyField(
            self.name,
            through=self.through,
            back_populates=self.name,
            cascade=self.cascade,
            lazy_load=self.lazy_load,
            domain=self.domain,
            context=self.context,
        )

    async def convert(self, value: Any) -> Optional[ModelList[M]]:
        """Convert value to list of model instances.

        Args:
            value: Value to convert

        Returns:
            Optional[ModelList[M]]: ModelList container or None

        Raises:
            FieldValidationError: If conversion fails
        """
        if value is None:
            return None

        if not isinstance(value, (list, tuple)):
            raise FieldValidationError(
                message=f"Expected list or tuple for field {self.name}, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

        if not self._resolved_model:
            await self.resolve_model_reference()

        if not self._model_class:
            raise FieldValidationError(
                message=f"Model class not resolved for field {self.name}",
                field_name=self.name,
                code="model_not_resolved",
            )

        result: List[M] = []

        try:
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            for item in cast(List[Union[M, str]], value):
                if isinstance(item, self._model_class):
                    result.append(cast(M, item))
                elif isinstance(item, str):
                    # Try to load by ID
                    try:
                        instance = await self._model_class.get(env, item)
                        result.append(cast(M, instance))
                    except Exception as e:
                        raise FieldValidationError(
                            message=f"Failed to load {self._model_class.__name__} with id {item}: {e}",
                            field_name=self.name,
                            code="load_failed",
                        ) from e
                else:
                    raise FieldValidationError(
                        message=(
                            f"Cannot convert {type(item).__name__} to {self._model_class.__name__} "
                            f"for field {self.name}"
                        ),
                        field_name=self.name,
                        code="invalid_type",
                    )
        except Exception as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="conversion_failed",
            ) from e

        return ModelList(items=result)

    async def validate(
        self, value: Optional[ModelList[M]], context: Optional[Dict[str, Any]] = None
    ) -> Optional[ModelList[M]]:
        """Validate field value.

        Args:
            value: Value to validate
            context: Optional validation context

        Returns:
            Optional[ModelList[M]]: Validated value

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

        if not self._model_class:
            raise FieldValidationError(
                message=f"Model class not resolved for field {self.name}",
                field_name=self.name,
                code="model_not_resolved",
            )

        # Check each item in list
        for item in value.items:
            if not isinstance(item, self._model_class):
                raise FieldValidationError(
                    message=(
                        f"Expected {self._model_class.__name__} instance in list for field {self.name}, "
                        f"got {type(item).__name__}"
                    ),
                    field_name=self.name,
                    code="invalid_type",
                )

            # Check domain if specified
            if self.domain and not await self._check_domain(item):
                constraints = [
                    f"{field} {op} {expected}" for field, op, expected in self.domain
                ]
                raise FieldValidationError(
                    message=(
                        f"Item does not match domain constraints for field {self.name}: "
                        f"{', '.join(constraints)}"
                    ),
                    field_name=self.name,
                    code="domain_mismatch",
                )

        return value

    async def to_db(
        self, value: Optional[ModelList[M]], backend: str
    ) -> Optional[List[str]]:
        """Convert list of model instances to database format.

        Args:
            value: ModelList container
            backend: Database backend type

        Returns:
            Optional[List[str]]: List of database values or None
        """
        if value is None:
            return None

        result: List[str] = []
        for item in value.items:
            if not hasattr(item, "id"):
                raise FieldValidationError(
                    message=f"Model instance {item} has no id attribute",
                    field_name=self.name,
                    code="missing_id",
                )
            result.append(str(item.id))  # type: ignore

        return result

    async def from_db(self, value: Any, backend: str) -> Optional[ModelList[M]]:
        """Convert database value to list of model instances.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Optional[ModelList[M]]: List of model instances or None
        """
        if value is None:
            return None

        if not self._resolved_model:
            await self.resolve_model_reference()

        if not self._model_class:
            raise FieldValidationError(
                message=f"Model class not resolved for field {self.name}",
                field_name=self.name,
                code="model_not_resolved",
            )

        if not isinstance(value, (list, tuple)):
            raise FieldValidationError(
                message=f"Expected list or tuple from database for field {self.name}, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

        result: List[M] = []
        try:
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            for item in cast(List[str], value):
                instance = await self._model_class.get(env, str(item))  # type: ignore
                result.append(cast(M, instance))
        except Exception as e:
            raise FieldValidationError(
                message=f"Failed to load related records: {str(e)}",
                field_name=self.name,
                code="load_failed",
            ) from e

        return ModelList(items=result)
