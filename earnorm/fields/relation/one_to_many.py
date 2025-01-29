"""One-to-many relationship field implementation.

This module provides one-to-many relationship field types.
It supports:
- Forward and reverse relationships
- Lazy loading of related models
- Cascade deletion
- Database foreign key constraints
- Validation of related models
- Domain filtering and context
- Comparison operations

Examples:
    >>> class Department(Model):
    ...     name = StringField(required=True)
    ...     employees = OneToManyField(
    ...         "User",
    ...         back_populates="department",
    ...         domain=[("active", "=", True)],
    ...         context={"show_archived": False}
    ...     )
"""

from typing import Any, Final, List, Optional, Type, Union, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.relation.base import Context, Domain, ModelList, RelationField
from earnorm.types.fields import ComparisonOperator

# Constants
DEFAULT_CASCADE: Final[bool] = True


class OneToManyField(RelationField[Any]):
    """Field for one-to-many relationships.

    This field type handles one-to-many relationships, with support for:
    - Back references
    - Cascade operations
    - Lazy loading
    - Validation
    - Domain filtering
    - Context
    - Comparison operations

    Attributes:
        model_ref: Referenced model class or name
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
        back_populates: Optional[str] = None,
        cascade: bool = DEFAULT_CASCADE,
        lazy_load: bool = True,
        domain: Optional[Domain] = None,
        context: Optional[Context] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize one-to-many field.

        Args:
            model_ref: Referenced model class or name
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

    async def convert(self, value: Any) -> Optional[ModelList[Any]]:
        """Convert value to list of model instances.

        Args:
            value: Value to convert

        Returns:
            ModelList container or None

        Raises:
            FieldValidationError: If conversion fails
        """
        if value is None:
            return None

        if not isinstance(value, (list, tuple)):
            raise FieldValidationError(
                message=f"Expected list or tuple for field {self.name}, got {type(value).__name__}",
                field_name=self.name,
            )

        model_class = self.get_model_class()
        result: List[Any] = []

        try:
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            for item in cast(List[Union[Any, str]], value):
                if isinstance(item, model_class):
                    result.append(item)
                elif isinstance(item, str):
                    # Try to load by ID
                    try:
                        instance = await model_class.get(env, item)  # type: ignore
                        result.append(instance)
                    except Exception as e:
                        raise FieldValidationError(
                            message=f"Failed to load {model_class.__name__} with id {item}: {e}",
                            field_name=self.name,
                        ) from e
                else:
                    raise FieldValidationError(
                        message=(
                            f"Cannot convert {type(item).__name__} to {model_class.__name__} "
                            f"for field {self.name}"
                        ),
                        field_name=self.name,
                    )
        except Exception as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
            ) from e

        return ModelList(items=result)

    async def to_db(
        self, value: Optional[ModelList[Any]], backend: str
    ) -> Optional[List[str]]:
        """Convert list of model instances to database format.

        Args:
            value: ModelList container
            backend: Database backend type

        Returns:
            List of database values or None

        Raises:
            FieldValidationError: If conversion fails
        """
        if value is None:
            return None

        result: List[str] = []
        for item in value.items:
            if not hasattr(item, "id"):
                raise FieldValidationError(
                    message=f"Model instance {item} has no id attribute",
                    field_name=self.name,
                )
            result.append(str(item.id))  # type: ignore

        return result

    async def from_db(self, value: Any, backend: str) -> Optional[ModelList[Any]]:
        """Convert database value to list of model instances.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            ModelList container or None

        Raises:
            FieldValidationError: If conversion fails
        """
        if value is None:
            return None

        if not isinstance(value, list):
            raise FieldValidationError(
                message=f"Expected list from database for field {self.name}, got {type(value).__name__}",
                field_name=self.name,
            )

        model_class = self.get_model_class()
        result: List[Any] = []

        try:
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            for item_id in cast(List[str], value):
                if self.lazy_load:
                    # Create model instance without loading
                    instance = model_class(env)  # type: ignore
                    instance.id = item_id  # type: ignore
                    result.append(instance)
                else:
                    # Load and validate model instance
                    instance = await model_class.get(env, item_id)  # type: ignore
                    await instance.validate()  # type: ignore
                    result.append(instance)
        except Exception as e:
            raise FieldValidationError(
                message=f"Failed to load {model_class.__name__} instances: {e}",
                field_name=self.name,
            ) from e

        return ModelList(items=result)

    def _create_back_reference(self) -> RelationField[Any]:
        """Create back reference field.

        Returns:
            RelationField: Back reference field instance
        """
        from earnorm.fields.relation.many_to_one import ManyToOneField

        return cast(
            RelationField[Any],
            ManyToOneField(
                self.model_name,  # type: ignore
                back_populates=self.name,
                cascade=self.cascade,
                lazy_load=self.lazy_load,
                domain=self.domain,
                context=self.context,
            ),
        )
