"""Validation decorators."""

from functools import wraps
from typing import Any, Awaitable, Callable, Iterator, Optional, TypeVar, Union, cast

from .validators import AsyncValidator, ValidationError, Validator

T = TypeVar("T")
ValidatorType = Union[Callable[..., None], Callable[..., Awaitable[None]]]
ChainType = Union[Iterator[Validator], Awaitable[Iterator[Validator]]]


def validates(func: ValidatorType) -> ValidatorType:
    """Decorator for model validation methods."""

    @wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
        """Wrap validation method."""
        try:
            result = func(self, *args, **kwargs)
            if isinstance(result, Awaitable):
                await result
        except ValidationError as e:
            if not e.field:
                e.field = func.__name__.replace("validate_", "")
            raise e

    return cast(ValidatorType, wrapper)


def validates_fields(*field_names: str) -> Callable[[ValidatorType], ValidatorType]:
    """Decorator for field validation methods."""

    def decorator(func: ValidatorType) -> ValidatorType:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            """Wrap validation method."""
            try:
                # Get field values
                field_values = [getattr(self, name) for name in field_names]

                # Call validation function
                result = func(self, *field_values, *args, **kwargs)
                if isinstance(result, Awaitable):
                    await result
            except ValidationError as e:
                if not e.field:
                    e.field = field_names[0]
                raise e

        return cast(ValidatorType, wrapper)

    return decorator


def chain_validates(*field_names: str) -> Callable[[ValidatorType], ValidatorType]:
    """Decorator for validation chains."""

    def decorator(func: ValidatorType) -> ValidatorType:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            """Wrap validation chain."""
            # Get validators from generator
            result = func(self, *args, **kwargs)
            validators: Optional[Iterator[Validator]] = None

            if isinstance(result, Awaitable):
                validators = await result
            else:
                validators = result

            if validators is None:
                return

            # Run validators in sequence
            for validator in validators:
                for name in field_names:
                    try:
                        value = getattr(self, name)
                        if isinstance(validator, AsyncValidator):
                            await validator(value)
                        else:
                            validator(value)
                    except ValidationError as e:
                        if not e.field:
                            e.field = name
                        raise e

        return cast(ValidatorType, wrapper)

    return decorator
