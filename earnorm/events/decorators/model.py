"""Model lifecycle decorators."""

import functools
from typing import Any, Callable, TypeVar, cast

T = TypeVar("T", bound=Callable[..., Any])


def before_create(func: T) -> T:
    """Decorator for before create hook.

    Called before creating a new record.
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    # Mark as lifecycle hook
    setattr(wrapper, "_is_lifecycle_hook", True)
    setattr(wrapper, "_hook_type", "before_create")
    return cast(T, wrapper)


def after_create(func: T) -> T:
    """Decorator for after create hook.

    Called after successful creation.
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    setattr(wrapper, "_is_lifecycle_hook", True)
    setattr(wrapper, "_hook_type", "after_create")
    return cast(T, wrapper)


def before_write(func: T) -> T:
    """Decorator for before write hook.

    Called before any write operation (create/update).
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    setattr(wrapper, "_is_lifecycle_hook", True)
    setattr(wrapper, "_hook_type", "before_write")
    return cast(T, wrapper)


def after_write(func: T) -> T:
    """Decorator for after write hook.

    Called after any write operation.
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    setattr(wrapper, "_is_lifecycle_hook", True)
    setattr(wrapper, "_hook_type", "after_write")
    return cast(T, wrapper)


def before_update(func: T) -> T:
    """Decorator for before update hook.

    Called before updating an existing record.
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    setattr(wrapper, "_is_lifecycle_hook", True)
    setattr(wrapper, "_hook_type", "before_update")
    return cast(T, wrapper)


def after_update(func: T) -> T:
    """Decorator for after update hook.

    Called after successful update.
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    setattr(wrapper, "_is_lifecycle_hook", True)
    setattr(wrapper, "_hook_type", "after_update")
    return cast(T, wrapper)


def before_delete(func: T) -> T:
    """Decorator for before delete hook.

    Called before deleting a record.
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    setattr(wrapper, "_is_lifecycle_hook", True)
    setattr(wrapper, "_hook_type", "before_delete")
    return cast(T, wrapper)


def after_delete(func: T) -> T:
    """Decorator for after delete hook.

    Called after successful deletion.
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    setattr(wrapper, "_is_lifecycle_hook", True)
    setattr(wrapper, "_hook_type", "after_delete")
    return cast(T, wrapper)
