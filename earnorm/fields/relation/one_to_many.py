"""One-to-many relationship field implementation.

This module provides one-to-many relationship field types.
It supports:
- Forward and reverse relationships
- Lazy loading of related models
- Cascade deletion
- Database foreign key constraints
- Validation of related models

Examples:
    >>> class Department(Model):
    ...     name = StringField(required=True)
    ...     employees = OneToManyField(
    ...         "User",
    ...         back_populates="department",
    ...         cascade=True
    ...     )
    ...
    >>> class User(Model):
    ...     name = StringField(required=True)
    ...     department = ManyToOneField(
    ...         Department,
    ...         back_populates="employees"
    ...     )
"""

from typing import Any, Final, List, Optional, Type, TypeVar, Union, cast

from earnorm.base.env import Environment
from earnorm.base.model.meta import BaseModel
from earnorm.exceptions import FieldValidationError
from earnorm.fields.relation.base import Domain, ModelList, OneToManyRelationField

M = TypeVar("M", bound=BaseModel)

# Constants
DEFAULT_CASCADE: Final[bool] = True


class OneToManyField(OneToManyRelationField[M]):
    """Field for one-to-many relationships.

    This field type handles one-to-many relationships, with support for:
    - Back references
    - Cascade operations
    - Lazy loading
    - Validation
    - Bulk operations

    Attributes:
        model_ref: Referenced model class or name
        back_populates: Name of back reference field
        cascade: Whether to cascade operations
        lazy_load: Whether to load related models lazily
    """

    model: Any  # Parent model instance

    def __init__(
        self,
        model_ref: Union[str, Type[M]],
        *,
        back_populates: Optional[str] = None,
        cascade: bool = DEFAULT_CASCADE,
        lazy_load: bool = True,
        domain: Optional[Domain] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize one-to-many field.

        Args:
            model_ref: Referenced model class or name
            back_populates: Name of back reference field
            cascade: Whether to cascade operations
            lazy_load: Whether to load related models lazily
            domain: Domain for filtering related records
            **kwargs: Additional field options
        """
        super().__init__(
            cast(Union[str, Type[ModelList[M]]], model_ref),
            back_populates=back_populates,
            cascade=cascade,
            lazy_load=lazy_load,
            domain=domain,
            **kwargs,
        )

    async def convert(self, value: Any) -> Optional[ModelList[M]]:
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
        result: List[M] = []

        try:
            env = Environment.get_instance()
            for item in cast(List[Union[M, str]], value):
                if isinstance(item, model_class):
                    result.append(cast(M, item))
                elif isinstance(item, str):
                    # Try to load by ID
                    try:
                        instance = await model_class.get(env, item)  # type: ignore
                        result.append(cast(M, instance))
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
        self, value: Optional[ModelList[M]], backend: str
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

    async def from_db(self, value: Any, backend: str) -> Optional[ModelList[M]]:
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
        result: List[M] = []

        try:
            env = Environment.get_instance()
            for item_id in cast(List[str], value):
                if self.lazy_load:
                    # Create model instance without loading
                    instance = model_class(env)  # type: ignore
                    instance.id = item_id  # type: ignore
                    result.append(cast(M, instance))
                else:
                    # Load and validate model instance
                    instance = await model_class.get(env, item_id)  # type: ignore
                    await instance.validate()  # type: ignore
                    result.append(cast(M, instance))
        except Exception as e:
            raise FieldValidationError(
                message=f"Failed to load {model_class.__name__} instances: {e}",
                field_name=self.name,
            ) from e

        return ModelList(items=result)
