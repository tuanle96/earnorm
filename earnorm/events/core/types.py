"""Type definitions for event system."""

from datetime import datetime
from typing import Optional, TypeVar

from pydantic import BaseModel, Field


class EventMetadata(BaseModel):
    """Event metadata."""

    model: Optional[str] = None
    model_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    trace_id: Optional[str] = None
    user_id: Optional[str] = None


class EventData(BaseModel):
    """Base class for event data.

    All event data classes should inherit from this class.

    Example:
        ```python
        class OrderCreatedEvent(EventData):
            order_id: str
            total: float
            items: list[dict]

        @event("order_created", data_class=OrderCreatedEvent)
        async def handle_order(self, data: OrderCreatedEvent):
            print(f"Order {data.order_id} created with total {data.total}")
        ```
    """

    id: Optional[str] = None  # ID của model nếu cần

    class Config:
        """Pydantic config."""

        extra = "allow"  # Cho phép thêm fields không định nghĩa
        frozen = True  # Immutable data


class Event(BaseModel):
    """Event model."""

    name: str
    data: EventData
    metadata: EventMetadata = Field(default_factory=EventMetadata)

    class Config:
        """Pydantic config."""

        frozen = True  # Immutable event


# Type variable cho event data
EventDataT = TypeVar("EventDataT", bound=EventData)
