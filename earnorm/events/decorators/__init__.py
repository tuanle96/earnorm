"""Event decorators.

This module provides decorators for event handling.
It includes decorators for event handlers, retry policies, and transactions.

Features:
- Event handler registration
- Retry policies
- Transaction management
- Error handling
- Metrics collection

Examples:
    ```python
    from earnorm.events.decorators import event_handler, retry, transactional

    @event_handler("user.created")
    async def handle_user_created(event: Event) -> None:
        print(f"User created: {event.data}")

    @retry(max_retries=3)
    async def handle_with_retry(event: Event) -> None:
        print(f"Handling event: {event.name}")

    @transactional
    async def handle_with_transaction(event: Event) -> None:
        print(f"Handling event in transaction: {event.name}")
    ```
"""

from .event import event_handler
from .retry import retry
from .transaction import transactional

__all__ = [
    "event_handler",
    "retry",
    "transactional",
]
