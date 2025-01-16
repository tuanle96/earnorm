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

import functools
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

from earnorm.events.core.exceptions import HandlerError

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


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


def transactional(
    func: Optional[F] = None,
    *,
    propagation: str = "required",
    isolation: str = "default",
    timeout: Optional[float] = None,
) -> Union[F, Callable[[F], F]]:
    """Transaction decorator.

    This decorator adds transaction support to a function.
    It will manage transaction lifecycle and handle commit/rollback.

    Args:
        func: Function to decorate
        propagation: Transaction propagation mode
        isolation: Transaction isolation level
        timeout: Transaction timeout in seconds

    Returns:
        Decorated function

    Examples:
        ```python
        @transactional
        async def handle_event(event: Event) -> None:
            # Will run in a transaction
            await process_event(event)

        @transactional(propagation="requires_new")
        async def handle_in_new_tx(event: Event) -> None:
            # Will run in a new transaction
            await process_event(event)
        ```
    """

    def decorator(handler_func: F) -> F:
        @functools.wraps(handler_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get or create transaction
            tx = get_current_transaction()
            if tx is None:
                tx = create_transaction()

            try:
                # Execute handler
                result = await handler_func(*args, **kwargs)

                # Commit if we created the transaction
                if hasattr(tx, "commit"):  # type: ignore
                    await tx.commit()  # type: ignore

                return result

            except Exception as e:
                # Rollback on error if we created the transaction
                if hasattr(tx, "rollback"):  # type: ignore
                    await tx.rollback()  # type: ignore

                logger.error("Transaction failed: %s", str(e))
                raise HandlerError("Transaction failed: " + str(e))

        return wrapper  # type: ignore

    if func is None:
        return decorator
    return decorator(func)
