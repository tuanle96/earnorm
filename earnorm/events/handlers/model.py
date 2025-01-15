"""Built-in event handlers for model lifecycle events."""

import logging
from typing import Any, Type

from earnorm.base import BaseModel
from earnorm.events.core import Event

logger = logging.getLogger(__name__)


class ModelEventHandler:
    """Base class for model event handlers."""

    def __init__(self, model_cls: Type[BaseModel]) -> None:
        """Initialize model event handler.

        Args:
            model_cls: Model class to handle events for
        """
        self.model_cls = model_cls

    async def handle_create(self, event: Event) -> None:
        """Handle model create event.

        Args:
            event: Create event containing model data
        """
        logger.debug(f"Handling create event for {self.model_cls.__name__}")
        data = event.data.get("data", {})

        # Create new model instance
        model = self.model_cls(**data)

        # Run before_create hooks
        if hasattr(model, "before_create"):
            await model.before_create()

        # Save model
        await model.save()

        # Run after_create hooks
        if hasattr(model, "after_create"):
            await model.after_create()

    async def handle_update(self, event: Event) -> None:
        """Handle model update event.

        Args:
            event: Update event containing model ID and data
        """
        logger.debug(f"Handling update event for {self.model_cls.__name__}")
        model_id = event.data.get("id")
        data = event.data.get("data", {})

        if not model_id:
            logger.error("Update event missing model ID")
            return

        # Find existing model
        result = await self.model_cls.find_one([model_id])
        if not result:
            logger.error(f"Model {model_id} not found")
            return

        model = result[0]

        # Run before_update hooks
        if hasattr(model, "before_update"):
            await model.before_update()

        # Update model
        await model.write(data)

        # Run after_update hooks
        if hasattr(model, "after_update"):
            await model.after_update()

    async def handle_delete(self, event: Event) -> None:
        """Handle model delete event.

        Args:
            event: Delete event containing model ID
        """
        logger.debug(f"Handling delete event for {self.model_cls.__name__}")
        model_id = event.data.get("id")

        if not model_id:
            logger.error("Delete event missing model ID")
            return

        # Find existing model
        result = await self.model_cls.find_one([model_id])
        if not result:
            logger.error(f"Model {model_id} not found")
            return

        model = result[0]

        # Run before_delete hooks
        if hasattr(model, "before_delete"):
            await model.before_delete()

        # Delete model
        await model.delete()

        # Run after_delete hooks
        if hasattr(model, "after_delete"):
            await model.after_delete()


def register_model_handlers(model_cls: Type[BaseModel], event_bus: Any) -> None:
    """Register model event handlers.

    Args:
        model_cls: Model class to register handlers for
        event_bus: Event bus instance
    """
    handler = ModelEventHandler(model_cls)

    # Register handlers for model events
    event_bus.subscribe(f"{model_cls.__name__}.create", handler.handle_create)
    event_bus.subscribe(f"{model_cls.__name__}.update", handler.handle_update)
    event_bus.subscribe(f"{model_cls.__name__}.delete", handler.handle_delete)
