"""Model lifecycle hooks."""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine, Dict, List, Literal

from earnorm.base.models.interfaces import ModelInterface

logger = logging.getLogger(__name__)

# Type aliases
Hook = Callable[[ModelInterface], Coroutine[Any, Any, None]]
EventType = Literal["before_save", "after_save", "before_delete", "after_delete"]


class Lifecycle:
    """Model lifecycle hooks.

    This class manages model lifecycle hooks:
    - Before/after save
    - Before/after delete

    Hooks are async functions that are called at specific points
    in the model lifecycle. They can be used to perform additional
    operations or validations.
    """

    def __init__(self) -> None:
        """Initialize lifecycle with empty hook lists."""
        self._hooks: Dict[EventType, List[Hook]] = {
            "before_save": [],
            "after_save": [],
            "before_delete": [],
            "after_delete": [],
        }

    def add_hook(self, event: EventType, hook: Hook) -> None:
        """Add lifecycle hook.

        Args:
            event: Event type
            hook: Async function to call

        Raises:
            ValueError: If event type is invalid
        """
        if event not in self._hooks:
            raise ValueError(f"Invalid event: {event}")
        self._hooks[event].append(hook)

    async def before_save(self, model: ModelInterface) -> None:
        """Run before save hooks.

        Args:
            model: Model instance

        Raises:
            Exception: If any hook fails
        """
        for hook in self._hooks["before_save"]:
            try:
                await hook(model)
            except Exception as e:
                logger.error("Before save hook failed: %s", str(e))
                raise

    async def after_save(self, model: ModelInterface) -> None:
        """Run after save hooks.

        Args:
            model: Model instance

        Raises:
            Exception: If any hook fails
        """
        for hook in self._hooks["after_save"]:
            try:
                await hook(model)
            except Exception as e:
                logger.error("After save hook failed: %s", str(e))
                raise

    async def before_delete(self, model: ModelInterface) -> None:
        """Run before delete hooks.

        Args:
            model: Model instance

        Raises:
            Exception: If any hook fails
        """
        for hook in self._hooks["before_delete"]:
            try:
                await hook(model)
            except Exception as e:
                logger.error("Before delete hook failed: %s", str(e))
                raise

    async def after_delete(self, model: ModelInterface) -> None:
        """Run after delete hooks.

        Args:
            model: Model instance

        Raises:
            Exception: If any hook fails
        """
        for hook in self._hooks["after_delete"]:
            try:
                await hook(model)
            except Exception as e:
                logger.error("After delete hook failed: %s", str(e))
                raise
