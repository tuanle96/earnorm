"""Model lifecycle management."""

from typing import Any, Callable, Coroutine, Generic, List, TypeVar

from earnorm.base.types import ModelProtocol

M = TypeVar("M", bound=ModelProtocol)
ModelHook = Callable[[M], Coroutine[Any, Any, None]]


class Lifecycle(Generic[M]):
    """Model lifecycle manager.

    This class manages model lifecycle events:
    - Before/after save
    - Before/after delete

    Type Parameters:
        M: Type of model this lifecycle manager handles
    """

    def __init__(self) -> None:
        """Initialize lifecycle manager."""
        self._before_save_hooks: List[ModelHook[M]] = []
        self._after_save_hooks: List[ModelHook[M]] = []
        self._before_delete_hooks: List[ModelHook[M]] = []
        self._after_delete_hooks: List[ModelHook[M]] = []

    def add_before_save_hook(self, hook: ModelHook[M]) -> None:
        """Add before save hook.

        Args:
            hook: Hook function to call before saving

        Raises:
            TypeError: If hook is not a coroutine function
        """
        self._before_save_hooks.append(hook)

    def add_after_save_hook(self, hook: ModelHook[M]) -> None:
        """Add after save hook.

        Args:
            hook: Hook function to call after saving

        Raises:
            TypeError: If hook is not a coroutine function
        """
        self._after_save_hooks.append(hook)

    def add_before_delete_hook(self, hook: ModelHook[M]) -> None:
        """Add before delete hook.

        Args:
            hook: Hook function to call before deleting

        Raises:
            TypeError: If hook is not a coroutine function
        """
        self._before_delete_hooks.append(hook)

    def add_after_delete_hook(self, hook: ModelHook[M]) -> None:
        """Add after delete hook.

        Args:
            hook: Hook function to call after deleting

        Raises:
            TypeError: If hook is not a coroutine function
        """
        self._after_delete_hooks.append(hook)

    async def before_save(self, model: M) -> None:
        """Run before save hooks.

        Args:
            model: Model instance being saved
        """
        for hook in self._before_save_hooks:
            await hook(model)

    async def after_save(self, model: M) -> None:
        """Run after save hooks.

        Args:
            model: Model instance that was saved
        """
        for hook in self._after_save_hooks:
            await hook(model)

    async def before_delete(self, model: M) -> None:
        """Run before delete hooks.

        Args:
            model: Model instance being deleted
        """
        for hook in self._before_delete_hooks:
            await hook(model)

    async def after_delete(self, model: M) -> None:
        """Run after delete hooks.

        Args:
            model: Model instance that was deleted
        """
        for hook in self._after_delete_hooks:
            await hook(model)
