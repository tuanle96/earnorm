"""Transaction decorator implementation.

This module provides decorators for transaction handling.
It adds transaction support to event handlers for atomic operations.

Features:
- Automatic transaction management
- Commit/rollback handling
- Error handling
- Transaction logging

Examples:
    ```python
    from earnorm.events.decorators.transaction import transactional
    from earnorm.events.core.event import Event

    @transactional
    async def handle_user_created(event: Event) -> None:
        # This handler will run in a transaction
        await create_user(event.data)
        await send_welcome_email(event.data)

    @transactional
    async def handle_with_rollback(event: Event) -> None:
        # Transaction will be rolled back on error
        await process_event(event)
    ```
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional, Protocol, TypeVar, runtime_checkable

from earnorm.events.core.event import Event

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])


@runtime_checkable
class Transaction(Protocol):
    """Transaction protocol."""

    timeout: float

    async def commit(self) -> None:
        """Commit transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback transaction."""
        ...


def get_current_transaction() -> Optional[Transaction]:
    """Get current transaction."""
    ...


def create_transaction() -> Transaction:
    """Create new transaction."""
    ...


def transactional(func: T) -> T:
    """Decorator to make event handler transactional.

    This decorator ensures that event handling is atomic - either all
    operations succeed or none do.

    Args:
        func: Event handler function to decorate

    Returns:
        Decorated function that runs in a transaction

    Examples:
        ```python
        @transactional
        async def handle_user_created(event):
            # All operations here will be in a transaction
            await create_profile(event.data)
            await send_welcome_email(event.data)
        ```
    """

    @wraps(func)
    async def wrapper(event: Event, *args: Any, **kwargs: Any) -> Any:
        """Wrap handler in transaction."""
        try:
            # Start transaction
            await event.env.db.begin()

            # Run handler
            result = await func(event, *args, **kwargs)

            # Commit transaction
            await event.env.db.commit()

            return result
        except Exception as e:
            # Rollback on error
            await event.env.db.rollback()
            raise e

    return wrapper  # type: ignore
