"""Events module for EarnORM.

This module provides event handling system for model lifecycle events:
- Event registration and dispatching for model operations
- Synchronous event handlers for model validation and hooks
- Event bus implementation for model events

Examples:
    ```python
    from earnorm.base import BaseModel
    from earnorm.base.events import ModelEvents

    class User(BaseModel):
        @events.on("before_create")
        async def validate_email(self):
            if not is_valid_email(self.email):
                raise ValidationError("Invalid email")
    ```
"""

from typing import List

from earnorm.base.events.model import EventError, ModelEvents

__all__: List[str] = ["ModelEvents", "EventError"]
