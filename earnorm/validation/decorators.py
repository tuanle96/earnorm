"""Validation decorators."""

from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterator,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
)

from ..metrics.prometheus import metrics_manager
from .validators import AsyncValidator, ValidationError

T = TypeVar("T")
ValidatorType = Union[Callable[..., None], Callable[..., Awaitable[None]]]
ChainType = Union[Iterator[AsyncValidator], Awaitable[Iterator[AsyncValidator]]]


def validates(func: ValidatorType) -> ValidatorType:
    """Decorator for model validation methods."""

    @wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
        """Wrap validation method."""
        try:
            result = func(self, *args, **kwargs)
            if isinstance(result, Awaitable):
                await result
            await metrics_manager.track_validation(
                model=self.__class__.__name__,
                field=func.__name__.replace("validate_", ""),
                validator="custom",
                value=str(args[0]) if args else "",
                success=True,
            )
        except ValidationError as e:
            if not e.field:
                e.field = func.__name__.replace("validate_", "")
            await metrics_manager.track_validation(
                model=self.__class__.__name__,
                field=e.field,
                validator="custom",
                value=str(args[0]) if args else "",
                success=False,
                error=str(e),
            )
            raise e

    return cast(ValidatorType, wrapper)


def validates_fields(*field_names: str) -> Callable[[ValidatorType], ValidatorType]:
    """Decorator for field validation methods."""

    def decorator(func: ValidatorType) -> ValidatorType:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            """Wrap validation method."""
            field_values: List[Any] = []
            try:
                # Get field values
                field_values = [getattr(self, name) for name in field_names]

                # Call validation function
                result = func(self, *field_values, *args, **kwargs)
                if isinstance(result, Awaitable):
                    await result

                # Track validation success
                for name, value in zip(field_names, field_values):
                    await metrics_manager.track_validation(
                        model=self.__class__.__name__,
                        field=name,
                        validator="custom",
                        value=str(value),
                        success=True,
                    )
            except ValidationError as e:
                if not e.field:
                    e.field = field_names[0]
                await metrics_manager.track_validation(
                    model=self.__class__.__name__,
                    field=e.field,
                    validator="custom",
                    value=str(field_values[0]) if field_values else "",
                    success=False,
                    error=str(e),
                )
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
            validators: Optional[Iterator[AsyncValidator]] = None

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
                            await validator(
                                value,
                                model=self.__class__.__name__,
                                field=name,
                            )
                        else:
                            validator(value)
                    except ValidationError as e:
                        if not e.field:
                            e.field = name
                        raise e

        return cast(ValidatorType, wrapper)

    return decorator
