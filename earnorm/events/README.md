# Events Module

## Overview
The Events module cung cấp một hệ thống event handling mạnh mẽ cho EarnORM, hỗ trợ xử lý các sự kiện bất đồng bộ, quản lý vòng đời và tích hợp với môi trường.

## Components

### 1. Event Bus
Lớp core để quản lý và điều phối các events:

```python
class EventBus:
    """Event bus for managing event publishing and subscription.
    
    Examples:
        >>> bus = EventBus()
        >>> await bus.publish("user.created", {"id": "123", "name": "John"})
        >>> await bus.subscribe("user.created", handle_user_created)
    """
    
    async def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        handlers = self._subscribers.get(event_name, [])
        for handler in handlers:
            await handler(payload)
            
    async def subscribe(self, event_name: str, handler: Callable) -> None:
        """Subscribe to an event."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(handler)
```

### 2. Event Handler
Base class cho các event handlers:

```python
class EventHandler:
    """Base class for event handlers.
    
    Examples:
        >>> class UserCreatedHandler(EventHandler):
        ...     async def handle(self, payload: Dict[str, Any]) -> None:
        ...         user_id = payload["id"]
        ...         await self.send_welcome_email(user_id)
    """
    
    async def handle(self, payload: Dict[str, Any]) -> None:
        """Handle the event."""
        raise NotImplementedError()
        
    @classmethod
    def get_event_name(cls) -> str:
        """Get the event name this handler listens to."""
        return cls._event_name
```

### 3. Event Lifecycle Manager
Quản lý vòng đời của event system:

```python
class EventLifecycleManager:
    """Manage event system lifecycle.
    
    Examples:
        >>> manager = EventLifecycleManager()
        >>> await manager.initialize()
        >>> await manager.register_handler(UserCreatedHandler())
        >>> await manager.cleanup()
    """
    
    async def initialize(self) -> None:
        """Initialize the event system."""
        self._bus = EventBus()
        self._handlers = []
        
    async def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        event_name = handler.get_event_name()
        await self._bus.subscribe(event_name, handler.handle)
        self._handlers.append(handler)
```

## Usage Examples

### 1. Basic Event Handling
```python
# Define an event handler
class UserCreatedHandler(EventHandler):
    _event_name = "user.created"
    
    async def handle(self, payload: Dict[str, Any]) -> None:
        user_id = payload["id"]
        await self.send_welcome_email(user_id)
        
# Register and use
manager = EventLifecycleManager()
await manager.initialize()
await manager.register_handler(UserCreatedHandler())

# Publish an event
await manager.publish("user.created", {
    "id": "123",
    "name": "John",
    "email": "john@example.com"
})
```

### 2. Multiple Handlers
```python
# Multiple handlers for same event
class NotificationHandler(EventHandler):
    _event_name = "user.created"
    
    async def handle(self, payload: Dict[str, Any]) -> None:
        await self.send_notification(payload["id"])
        
class AnalyticsHandler(EventHandler):
    _event_name = "user.created"
    
    async def handle(self, payload: Dict[str, Any]) -> None:
        await self.track_user_creation(payload)

# Register multiple handlers
await manager.register_handler(UserCreatedHandler())
await manager.register_handler(NotificationHandler())
await manager.register_handler(AnalyticsHandler())
```

### 3. Error Handling
```python
class ResilientHandler(EventHandler):
    _event_name = "critical.event"
    
    async def handle(self, payload: Dict[str, Any]) -> None:
        try:
            await self.process_critical_event(payload)
        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            await self.notify_admin(payload, str(e))
```

## Best Practices

1. **Event Design**
- Sử dụng event names có ý nghĩa và nhất quán
- Thiết kế payload rõ ràng và đầy đủ thông tin
- Tách biệt logic xử lý event
- Xử lý lỗi một cách graceful

2. **Performance**
- Xử lý event bất đồng bộ khi có thể
- Tránh blocking operations trong handlers
- Monitor event processing time
- Implement retry mechanism cho critical events

3. **Reliability**
- Implement error handling
- Log event processing
- Backup critical event data
- Implement event versioning

4. **Testing**
- Unit test handlers
- Mock event bus trong tests
- Test error scenarios
- Verify event payload schema

## Common Issues & Solutions

1. **Event Order**
```python
class OrderedEventBus(EventBus):
    """Event bus with ordered event processing."""
    
    async def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        handlers = sorted(
            self._subscribers.get(event_name, []),
            key=lambda h: getattr(h, "priority", 0)
        )
        for handler in handlers:
            await handler(payload)
```

2. **Event Validation**
```python
class ValidatedEventHandler(EventHandler):
    """Handler with payload validation."""
    
    _schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "data": {"type": "object"}
        },
        "required": ["id", "timestamp", "data"]
    }
    
    async def handle(self, payload: Dict[str, Any]) -> None:
        validate(payload, self._schema)
        await self.process_validated_payload(payload)
```

3. **Retry Mechanism**
```python
class RetryableHandler(EventHandler):
    """Handler with retry mechanism."""
    
    async def handle(self, payload: Dict[str, Any]) -> None:
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await self.process_event(payload)
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    await self.handle_final_failure(payload, e)
                else:
                    await asyncio.sleep(2 ** retry_count)
```

## Implementation Details

### 1. Event Context
```python
class EventContext:
    """Context for event processing."""
    
    def __init__(self, event_name: str, payload: Dict[str, Any]):
        self.event_name = event_name
        self.payload = payload
        self.timestamp = datetime.utcnow()
        self.metadata = {}
```

### 2. Event Middleware
```python
class EventMiddleware:
    """Middleware for event processing."""
    
    async def before_handle(self, context: EventContext) -> None:
        """Called before event handling."""
        pass
        
    async def after_handle(self, context: EventContext) -> None:
        """Called after event handling."""
        pass
```

## Contributing

1. Follow code style guidelines
2. Add comprehensive tests
3. Document new features
4. Update type hints
5. Benchmark performance impacts
