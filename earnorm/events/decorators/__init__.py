"""Event decorators."""

from .event import event, event_handler, model_event_handler
from .model import (
    after_create,
    after_delete,
    after_update,
    after_write,
    before_create,
    before_delete,
    before_update,
    before_write,
)

__all__ = [
    # Lifecycle hooks
    "before_create",
    "after_create",
    "before_write",
    "after_write",
    "before_update",
    "after_update",
    "before_delete",
    "after_delete",
    # Event handlers
    "event",
    "event_handler",
    "model_event_handler",
]
