"""Model decorators.

This module provides decorators for model methods:
- @multi: Mark method as operating on multiple records
- @model: Mark method as class method
- @depends: Mark method as depending on fields

Examples:
    >>> from earnorm.base.model.decorators import multi, model, depends
    >>>
    >>> class Partner(BaseModel):
    ...     name = StringField()
    ...     age = IntegerField()
    ...
    ...     @multi
    ...     def send_email(self):
    ...         # Send email to multiple partners
    ...         pass
    ...
    ...     @model
    ...     def find_by_name(cls, name):
    ...         # Find partners by name
    ...         return cls.search([("name", "=", name)])
    ...
    ...     @depends("age")
    ...     def _compute_is_adult(self) -> bool:
    ...         # Compute is_adult based on age
    ...         return self.age >= 18
"""

from typing import Any, Callable, TypeVar

from earnorm.types import FieldName

T = TypeVar("T", bound=Callable[..., Any])


def multi(method: T) -> T:
    """Mark method as operating on multiple records.

    This decorator marks a method as capable of handling multiple records.
    The method will receive a recordset as self.

    Args:
        method: Method to decorate

    Returns:
        Decorated method

    Examples:
        >>> @multi
        ... def archive(self):
        ...     # Archive multiple records
        ...     self.write({"active": False})
    """
    method._multi = True  # type: ignore
    return method


def model(method: T) -> T:
    """Mark method as class method.

    This decorator converts a method to a class method.
    The method will receive the model class as cls.

    Args:
        method: Method to decorate

    Returns:
        Decorated method

    Examples:
        >>> @model
        ... def default_get(cls, fields_list):
        ...     # Get default values for fields
        ...     return {field: None for field in fields_list}
    """
    method._model = True  # type: ignore
    return classmethod(method)  # type: ignore


def depends(*fields: FieldName) -> Callable[[T], T]:
    """Mark method as depending on fields.

    This decorator marks a compute method as depending on fields.
    The method will be called when any of the fields change.

    Args:
        *fields: Field names that method depends on

    Returns:
        Decorator function

    Examples:
        >>> @depends("first_name", "last_name")
        ... def _compute_full_name(self):
        ...     # Compute full_name from first_name and last_name
        ...     self.full_name = f"{self.first_name} {self.last_name}"
    """

    def decorator(method: T) -> T:
        method._depends = fields  # type: ignore
        return method

    return decorator
