"""Event system for EarnORM."""

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, TypeVar

from ..utils.singleton import Singleton

T = TypeVar("T")
EventHandler = Callable[..., Awaitable[None]]


class EventManager(metaclass=Singleton):
    """Manager for event handling."""

    def __init__(self) -> None:
        """Initialize event manager."""
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._running_tasks: Set[asyncio.Task[None]] = set()
        self._max_retries = 3
        self._retry_delay = 1.0  # seconds

    def on(self, event: str) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register event handler.

        Args:
            event: Event name

        Returns:
            Decorator function
        """

        def decorator(handler: EventHandler) -> EventHandler:
            self.add_handler(event, handler)
            return handler

        return decorator

    def add_handler(self, event: str, handler: EventHandler) -> None:
        """Add event handler.

        Args:
            event: Event name
            handler: Event handler function
        """
        self._handlers[event].append(handler)

    def remove_handler(self, event: str, handler: EventHandler) -> None:
        """Remove event handler.

        Args:
            event: Event name
            handler: Event handler function
        """
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    async def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit event.

        Args:
            event: Event name
            *args: Positional arguments for handlers
            **kwargs: Keyword arguments for handlers
        """
        if event not in self._handlers:
            return

        # Create tasks for handlers
        tasks: List[asyncio.Task[None]] = []
        for handler in self._handlers[event]:
            task = asyncio.create_task(self._run_handler(handler, *args, **kwargs))
            tasks.append(task)
            self._running_tasks.add(task)
            task.add_done_callback(self._running_tasks.discard)

        # Wait for all handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_handler(
        self, handler: EventHandler, *args: Any, **kwargs: Any
    ) -> None:
        """Run event handler with retry logic.

        Args:
            handler: Event handler function
            *args: Positional arguments for handler
            **kwargs: Keyword arguments for handler
        """
        retries = 0
        while True:
            try:
                await handler(*args, **kwargs)
                break
            except Exception as e:
                retries += 1
                if retries >= self._max_retries:
                    # TODO: Add logging
                    name = handler.__name__
                    msg = f"Handler {name} failed after {retries} retries: {str(e)}"
                    print(msg)
                    break
                await asyncio.sleep(self._retry_delay * retries)

    def clear_handlers(self, event: Optional[str] = None) -> None:
        """Clear event handlers.

        Args:
            event: Optional event name. If None, clear all handlers
        """
        if event is not None:
            self._handlers[event].clear()
        else:
            self._handlers.clear()

    async def wait_for(self, event: str, timeout: Optional[float] = None) -> None:
        """Wait for event to be emitted.

        Args:
            event: Event name
            timeout: Optional timeout in seconds

        Raises:
            TimeoutError: If timeout is reached
            asyncio.CancelledError: If wait is cancelled
        """
        future: asyncio.Future[None] = asyncio.Future()

        async def _handler(*args: Any, **kwargs: Any) -> None:
            if not future.done():
                future.set_result(None)

        self.add_handler(event, _handler)
        try:
            await asyncio.wait_for(future, timeout)
        finally:
            self.remove_handler(event, _handler)

    def get_handler_count(self, event: str) -> int:
        """Get number of handlers for event.

        Args:
            event: Event name

        Returns:
            int: Number of handlers
        """
        return len(self._handlers[event])

    def get_events(self) -> List[str]:
        """Get list of registered events.

        Returns:
            List[str]: List of event names
        """
        return list(self._handlers.keys())

    def set_retry_policy(self, max_retries: int, retry_delay: float) -> None:
        """Set retry policy for handlers.

        Args:
            max_retries: Maximum number of retries
            retry_delay: Base delay between retries in seconds
        """
        self._max_retries = max_retries
        self._retry_delay = retry_delay
