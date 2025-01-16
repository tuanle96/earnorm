# Event System

The Event System module provides a robust and flexible event handling system for EarnORM.
It enables asynchronous event processing, reliable message delivery, and extensible event handling.

## Features

- **Event Bus**: Central coordinator for event publishing and handling
- **Redis Backend**: Reliable message broker using Redis Pub/Sub
- **Event Handlers**: Flexible handlers for processing events
- **Transaction Support**: Atomic operations with automatic rollback
- **Retry Logic**: Configurable retry policies with exponential backoff
- **Health Checks**: System health monitoring and reporting
- **Metrics Collection**: Performance metrics and insights
- **Pattern Matching**: Glob-style event pattern matching
- **Event Filtering**: Flexible event filtering and routing
- **Event Batching**: Efficient batch processing of events

## Installation

The Event System is included with EarnORM. No additional installation is required.

## Quick Start

```python
from earnorm.events import Event, EventBus, event_handler

# Initialize event bus
bus = await EventBus.create(
    redis_uri="redis://localhost:6379/0",
    queue_name="myapp"
)

# Define event handler
@event_handler("user.created")
async def handle_user_created(event: Event) -> None:
    user = event.data
    await send_welcome_email(user)

# Register handler
await bus.register_handler(handle_user_created)

# Publish event
event = Event(
    name="user.created",
    data={"id": "123", "email": "user@example.com"}
)
await bus.publish(event)
```

## Components

### Event Bus

The Event Bus is the central coordinator for event processing:

```python
from earnorm.events import EventBus

# Create event bus
bus = await EventBus.create(
    redis_uri="redis://localhost:6379/0",
    queue_name="myapp",
    min_size=5,
    max_size=20
)

# Start processing
await bus.start()

# Stop processing
await bus.stop()
```

### Event Handlers

Event handlers process specific types of events:

```python
from earnorm.events import Event, event_handler

@event_handler("user.*")
async def handle_user_events(event: Event) -> None:
    if event.name == "user.created":
        await handle_user_created(event)
    elif event.name == "user.updated":
        await handle_user_updated(event)

@event_handler("order.created", retry=True)
async def handle_order_created(event: Event) -> None:
    order = event.data
    await process_order(order)
```

### Transaction Support

Wrap handlers in transactions for atomic operations:

```python
from earnorm.events import Event
from earnorm.events.decorators import transactional

@transactional
async def handle_user_created(event: Event) -> None:
    # All operations are atomic
    user = await create_user(event.data)
    await create_profile(user)
    await send_welcome_email(user)
```

### Retry Logic

Add retry logic to handlers for reliability:

```python
from earnorm.events import Event
from earnorm.events.decorators import retry

@retry(max_attempts=3, backoff=2.0)
async def handle_payment(event: Event) -> None:
    # Will retry up to 3 times with exponential backoff
    await process_payment(event.data)
```

### Health Checks

Monitor system health:

```python
from earnorm.events import EventBus
from earnorm.events.core.health import HealthChecker

# Create health checker
checker = HealthChecker(
    event_bus,
    check_interval=60.0,
    timeout=5.0
)

# Start health checks
await checker.start()

# Get health status
status = await checker.check()
print(f"System health: {status}")
```

### Metrics Collection

Track system metrics:

```python
from earnorm.events import EventBus
from earnorm.events.core.metrics import MetricsCollector

# Create metrics collector
collector = MetricsCollector(event_bus)

# Get metrics
metrics = await collector.get_metrics()
print(f"Success rate: {metrics.success_rate}")

# Get detailed report
report = await collector.get_report()
print(f"Metrics: {report}")
```

## Best Practices

1. **Event Names**:
   - Use dot notation for event names (e.g. "user.created")
   - Keep names descriptive and consistent
   - Use past tense for state changes

2. **Event Data**:
   - Include minimal necessary data
   - Use JSON-serializable types
   - Include event metadata when useful

3. **Event Handlers**:
   - Keep handlers focused and single-purpose
   - Use transactions for atomic operations
   - Add retry logic for reliability
   - Log errors and important state changes

4. **Error Handling**:
   - Handle expected errors gracefully
   - Use retry logic for transient failures
   - Log errors with context
   - Monitor error rates

5. **Performance**:
   - Use event batching for high volume
   - Monitor processing times
   - Scale connection pool as needed
   - Clean up resources properly

6. **Monitoring**:
   - Enable health checks
   - Collect metrics
   - Monitor error rates
   - Track processing times

## Configuration

The Event System can be configured through the following settings:

```python
# Event Bus settings
EVENT_BUS_CONFIG = {
    "redis_uri": "redis://localhost:6379/0",
    "queue_name": "myapp",
    "min_size": 5,
    "max_size": 20,
    "timeout": 30.0,
    "retry_policy": {
        "max_attempts": 3,
        "backoff": 2.0
    }
}

# Health check settings
HEALTH_CHECK_CONFIG = {
    "check_interval": 60.0,
    "timeout": 5.0
}

# Metrics settings
METRICS_CONFIG = {
    "max_samples": 1000
}
```

## Error Handling

The Event System provides several exception types:

- `EventError`: Base exception for all event errors
- `PublishError`: Error publishing an event
- `HandlerError`: Error in event handler
- `ValidationError`: Event validation error
- `ConnectionError`: Backend connection error

Example error handling:

```python
from earnorm.events.core.exceptions import EventError

try:
    await bus.publish(event)
except EventError as e:
    logger.error(f"Failed to publish event: {e}")
    # Handle error appropriately
```

## Testing

The Event System includes utilities for testing:

```python
from earnorm.events.utils.testing import MockBackend

# Create mock backend
backend = MockBackend()

# Create test bus
bus = await EventBus.create(backend=backend)

# Test event handling
event = Event("test.event", {"data": "test"})
await bus.publish(event)

# Verify event was processed
assert len(backend.published_events) == 1
assert backend.published_events[0].name == "test.event"
```

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to our repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
