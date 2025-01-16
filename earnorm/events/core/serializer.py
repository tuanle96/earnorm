"""Event serializer implementation.

This module provides serialization and deserialization of events.
It supports JSON serialization with custom encoders and decoders.

Features:
- Event serialization to JSON
- Event deserialization from JSON
- Custom type encoders/decoders
- Validation
- Error handling

Examples:
    ```python
    from earnorm.events.core.serializer import EventSerializer
    from earnorm.events.core.event import Event
    from datetime import datetime

    # Create serializer
    serializer = EventSerializer()

    # Register custom encoder
    serializer.register_encoder(datetime, lambda dt: dt.isoformat())
    serializer.register_decoder(datetime, datetime.fromisoformat)

    # Serialize event
    event = Event(
        name="user.created",
        data={"id": "123", "created_at": datetime.now()}
    )
    json_str = serializer.serialize(event)

    # Deserialize event
    event = serializer.deserialize(json_str)
    ```
"""

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Type, TypeVar, cast

from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import SerializationError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EventSerializer:
    """Event serializer.

    This class handles serialization and deserialization of events.
    It supports JSON serialization with custom type encoders/decoders.

    Features:
    - Event serialization to JSON
    - Event deserialization from JSON
    - Custom type encoders/decoders
    - Validation
    - Error handling

    Attributes:
        _encoders: Dict mapping types to encoder functions
        _decoders: Dict mapping types to decoder functions
    """

    def __init__(self) -> None:
        """Initialize event serializer."""
        self._encoders: Dict[Type[Any], Callable[[Any], Any]] = {}
        self._decoders: Dict[Type[Any], Callable[[Any], Any]] = {}

        # Register default encoders/decoders
        self.register_encoder(datetime, lambda dt: dt.isoformat())
        self.register_decoder(datetime, datetime.fromisoformat)

    def register_encoder(self, type_: Type[T], encoder: Callable[[T], Any]) -> None:
        """Register type encoder.

        This method registers an encoder function for a type.
        The encoder should convert the type to a JSON-serializable value.

        Args:
            type_: Type to encode
            encoder: Encoder function

        Examples:
            ```python
            # Register datetime encoder
            serializer.register_encoder(
                datetime,
                lambda dt: dt.isoformat()
            )

            # Register custom type encoder
            class User:
                def __init__(self, id: str):
                    self.id = id

            serializer.register_encoder(
                User,
                lambda u: {"id": u.id}
            )
            ```
        """
        self._encoders[type_] = encoder
        logger.debug("Registered encoder for type %s", type_.__name__)

    def register_decoder(self, type_: Type[T], decoder: Callable[[Any], T]) -> None:
        """Register type decoder.

        This method registers a decoder function for a type.
        The decoder should convert a JSON value back to the type.

        Args:
            type_: Type to decode
            decoder: Decoder function

        Examples:
            ```python
            # Register datetime decoder
            serializer.register_decoder(
                datetime,
                datetime.fromisoformat
            )

            # Register custom type decoder
            class User:
                def __init__(self, id: str):
                    self.id = id

            serializer.register_decoder(
                User,
                lambda d: User(d["id"])
            )
            ```
        """
        self._decoders[type_] = decoder
        logger.debug("Registered decoder for type %s", type_.__name__)

    def serialize(self, event: Event) -> str:
        """Serialize event to JSON string.

        This method serializes an event to a JSON string.
        It uses registered encoders to handle custom types.

        Args:
            event: Event to serialize

        Returns:
            str: JSON string

        Raises:
            SerializationError: If serialization fails

        Examples:
            ```python
            event = Event(
                name="user.created",
                data={"id": "123", "created_at": datetime.now()}
            )
            json_str = serializer.serialize(event)
            ```
        """
        try:
            # Convert event to dict
            event_dict = {
                "name": event.name,
                "data": self._encode_value(event.data),
                "created_at": event.created_at.isoformat(),
            }

            # Serialize to JSON
            return json.dumps(event_dict)
        except Exception as e:
            logger.error("Failed to serialize event %s: %s", event.name, str(e))
            raise SerializationError("Failed to serialize event: %s" % str(e))

    def deserialize(self, json_str: str) -> Event:
        """Deserialize event from JSON string.

        This method deserializes an event from a JSON string.
        It uses registered decoders to handle custom types.

        Args:
            json_str: JSON string

        Returns:
            Event: Deserialized event

        Raises:
            SerializationError: If deserialization fails

        Examples:
            ```python
            json_str = '{"name": "user.created", "data": {"id": "123"}}'
            event = serializer.deserialize(json_str)
            ```
        """
        try:
            # Parse JSON
            event_dict = json.loads(json_str)

            # Create event
            return Event(
                name=event_dict["name"],
                data=self._decode_value(event_dict["data"]),
                created_at=datetime.fromisoformat(event_dict["created_at"]),
            )
        except Exception as e:
            logger.error("Failed to deserialize event: %s", str(e))
            raise SerializationError("Failed to deserialize event: %s" % str(e))

    def _encode_value(self, value: Any) -> Any:
        """Encode value using registered encoders.

        This method recursively encodes a value using registered encoders.
        It handles nested dicts, lists and custom types.

        Args:
            value: Value to encode

        Returns:
            Encoded value
        """
        if value is None:
            return None

        # Handle containers directly
        if isinstance(value, dict):
            return {
                str(k): self._encode_value(v) for k, v in value.items()  # type: ignore
            }
        if isinstance(value, (list, tuple)):
            return [self._encode_value(v) for v in value]  # type: ignore

        # Get value type for other cases
        value_type = cast(Type[Any], type(value))

        # Check for registered encoder
        if value_type in self._encoders:
            return self._encoders[value_type](value)

        # Return as is if JSON serializable
        return value

    def _decode_value(self, value: Any) -> Any:
        """Decode value using registered decoders.

        This method recursively decodes a value using registered decoders.
        It handles nested dicts, lists and custom types.

        Args:
            value: Value to decode

        Returns:
            Decoded value
        """
        if value is None:
            return None

        # Handle containers
        if isinstance(value, dict):
            return {
                str(k): self._decode_value(v) for k, v in value.items()  # type: ignore
            }
        if isinstance(value, (list, tuple)):
            return [self._decode_value(v) for v in value]  # type: ignore

        # Return as is if no decoder
        return value
