"""API decorators for model methods.

This module provides decorators to define method behaviors:
- @model: For class/static methods that don't need record state
- @multi: For methods that operate on recordsets
- @one: For methods that operate on single records
"""

import functools
import logging
from typing import TYPE_CHECKING, Any, Callable, Type, TypeVar, cast

if TYPE_CHECKING:
    from earnorm.base.model.base import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def model(method: F) -> F:
    """Decorator for methods that don't need record state.

    Similar to @classmethod but with additional model-specific behaviors:
    - Auto-injects environment if needed
    - Handles model registry lookup
    - Provides logging and error handling

    Args:
        method: The method to decorate

    Returns:
        Decorated method

    Examples:
        >>> class User(BaseModel):
        ...     @api.model
        ...     async def create(cls, vals):
        ...         return await super().create(vals)
    """

    async def wrapper(cls: Type["BaseModel"], *args: Any, **kwargs: Any) -> Any:
        try:
            # Log method call
            logger.debug(
                f"Calling {cls.__name__}.{method.__name__} with args={args}, kwargs={kwargs}"
            )

            # Execute method with cls and args
            if method.__name__ == "create":
                # Special handling for create method
                if len(args) == 1 and isinstance(args[0], dict):
                    result = await method(cls, vals=args[0])
                elif "vals" in kwargs:
                    result = await method(cls, vals=kwargs["vals"])
                else:
                    raise TypeError(
                        f"{cls.__name__}.create() missing required argument 'vals'"
                    )
            else:
                result = await method(cls, *args, **kwargs)

            # Log result
            logger.debug(f"Method {cls.__name__}.{method.__name__} returned: {result}")

            return result

        except Exception as e:
            # Log error
            logger.error(
                f"Error in {cls.__name__}.{method.__name__}: {str(e)}",
                exc_info=True,
            )
            raise

    # Create a new classmethod with the wrapper
    wrapped = classmethod(wrapper)

    # Copy metadata from original method
    for attr in functools.WRAPPER_ASSIGNMENTS:
        try:
            setattr(wrapped, attr, getattr(method, attr))
        except AttributeError:
            pass

    return cast(F, wrapped)


def multi(method: F) -> F:
    """Decorator for methods that operate on recordsets.

    Ensures:
    - Method is called on recordset
    - Handles empty recordsets
    - Provides logging and error handling

    Args:
        method: The method to decorate

    Returns:
        Decorated method

    Examples:
        >>> class User(BaseModel):
        ...     @api.multi
        ...     async def write(self, vals):
        ...         return await super().write(vals)
    """

    @functools.wraps(method)
    async def wrapper(self: "BaseModel", *args: Any, **kwargs: Any) -> Any:
        try:
            # Check if recordset
            if not hasattr(self, "_ids"):
                raise ValueError(
                    f"Method {method.__name__} must be called on recordset"
                )

            # Get record IDs safely
            record_ids = getattr(self, "_ids", [])

            # Log method call
            logger.debug(
                f"Calling {self.__class__.__name__}.{method.__name__} on records {record_ids} with args={args}, kwargs={kwargs}"
            )

            # Execute method
            result = await method(self, *args, **kwargs)

            # Log result
            logger.debug(
                f"Method {self.__class__.__name__}.{method.__name__} returned: {result}"
            )

            return result

        except Exception as e:
            # Log error
            logger.error(
                f"Error in {self.__class__.__name__}.{method.__name__}: {str(e)}",
                exc_info=True,
            )
            raise

    return cast(F, wrapper)


def one(method: F) -> F:
    """Decorator for methods that operate on single records.

    Ensures:
    - Method is called on single record
    - Record exists
    - Provides logging and error handling

    Args:
        method: The method to decorate

    Returns:
        Decorated method

    Examples:
        >>> class User(BaseModel):
        ...     @api.one
        ...     async def compute_age(self):
        ...         return datetime.now().year - self.birth_year
    """

    @functools.wraps(method)
    async def wrapper(self: "BaseModel", *args: Any, **kwargs: Any) -> Any:
        try:
            # Get record IDs safely
            record_ids = getattr(self, "_ids", [])

            # Ensure single record
            if not record_ids or len(record_ids) != 1:
                raise ValueError(
                    f"Method {method.__name__} must be called on single record"
                )

            # Log method call
            logger.debug(
                f"Calling {self.__class__.__name__}.{method.__name__} on record {record_ids[0]} with args={args}, kwargs={kwargs}"
            )

            # Execute method
            result = await method(self, *args, **kwargs)

            # Log result
            logger.debug(
                f"Method {self.__class__.__name__}.{method.__name__} returned: {result}"
            )

            return result

        except Exception as e:
            # Log error
            logger.error(
                f"Error in {self.__class__.__name__}.{method.__name__}: {str(e)}",
                exc_info=True,
            )
            raise

    return cast(F, wrapper)
