"""Model event handlers."""

import inspect
from typing import Any, Dict, Optional, Type

from earnorm.base import BaseModel
from earnorm.events.core import Event


class ModelEventHandler:
    """Handler for model events."""

    def __init__(self) -> None:
        """Initialize model event handler."""
        self._models: Dict[str, Type[BaseModel]] = {}

    async def _run_hook(self, model: BaseModel, hook_name: str) -> None:
        """Run lifecycle hook on model.

        Args:
            model: Model instance
            hook_name: Name of hook to run
        """
        hook = getattr(model, hook_name, None)
        if hook and inspect.iscoroutinefunction(hook):
            await hook()

    async def _run_event_handler(
        self,
        model: BaseModel,
        handler: Any,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Run event handler on model.

        Args:
            model: Model instance
            handler: Event handler method
            event_data: Optional event data
        """
        # Get event data class if specified
        data_class = getattr(handler, "_event_data_class", None)

        # Validate and pass event data
        if data_class and event_data:
            data = data_class(**event_data)
            await handler(data)
        else:
            await handler(event_data)

    async def handle_create(self, model: BaseModel) -> None:
        """Handle model create event.

        Args:
            model: Model instance
        """
        await self._run_hook(model, "_before_create")
        await self._run_hook(model, "_after_create")

    async def handle_update(self, model: BaseModel, data: Dict[str, Any]) -> None:
        """Handle model update event.

        Args:
            model: Model instance
            data: Update data
        """
        await self._run_hook(model, "_before_update")
        await self._run_hook(model, "_after_update")

    async def handle_delete(self, model: BaseModel) -> None:
        """Handle model delete event.

        Args:
            model: Model instance
        """
        await self._run_hook(model, "_before_delete")
        await self._run_hook(model, "_after_delete")

    async def handle_event(self, event: Event) -> None:
        """Handle custom event.

        Args:
            event: Event instance
        """
        # Get model class and ID from event data
        model_id = event.data.get("id")
        model_name = event.data.get("model")

        if not model_id or not model_name:
            return

        # Get model class and instance
        model_cls = self._models.get(model_name)
        if not model_cls:
            return

        # Get model instance
        result = await model_cls.find_one([model_id])  # type: ignore
        if not result:
            return

        model = result[0]

        # Find and run event handler
        for _, method in inspect.getmembers(model):
            if (
                getattr(method, "_is_event_handler", False)
                and getattr(method, "_event_name", None) == event.name
            ):
                await self._run_event_handler(model, method, event.data)

    def register_model(self, model_cls: Type[BaseModel]) -> None:
        """Register model class.

        Args:
            model_cls: Model class to register
        """
        self._models[model_cls.__name__] = model_cls

    def register_model_handlers(self, event_bus: Any) -> None:
        """Register model event handlers.

        Args:
            event_bus: Event bus instance
        """
        # Register built-in handlers
        event_bus.subscribe("model.created", self.handle_create)
        event_bus.subscribe("model.updated", self.handle_update)
        event_bus.subscribe("model.deleted", self.handle_delete)

        # Register custom event handlers
        for model_cls in self._models.values():
            for _, method in inspect.getmembers(model_cls):
                if getattr(method, "_is_event_handler", False):
                    event_name = getattr(method, "_event_name")
                    event_bus.subscribe(event_name, self.handle_event)
