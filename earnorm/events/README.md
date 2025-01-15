# Event System

The event system in EarnORM provides a robust way to handle asynchronous events and implement event-driven architectures. It supports model lifecycle events, custom event handlers, and asynchronous event processing using Redis as the message broker.

## Features

- Model lifecycle events (before/after save, before/after delete)
- Custom event handlers with pattern matching
- Asynchronous event processing
- Event retries with configurable delay
- Event batching for improved performance
- Multiple worker support
- Redis-based message broker

## Usage

### Basic Setup

```python
from redis.asyncio import Redis
from earnorm.events import EventBus

# Initialize Redis client
redis = Redis(host="localhost", port=6379)

# Create event bus
event_bus = EventBus(
    redis=redis,
    queue_name="myapp:events",
    batch_size=100,
    poll_interval=1.0,
    max_retries=3,
    retry_delay=5.0,
    num_workers=2
)

# Start event bus
await event_bus.start()

# Stop event bus when done
await event_bus.stop()

# Or use context manager
async with event_bus:
    # Event bus is started automatically
    pass  # Do work here
    # Event bus is stopped automatically
```

### Model Lifecycle Events

```python
from earnorm.events import before_save, after_save, before_delete, after_delete
from earnorm.base import BaseModel

class User(BaseModel):
    name: str
    email: str

    @before_save()
    async def validate_email(self):
        # Validate email before saving
        if not is_valid_email(self.email):
            raise ValueError("Invalid email")

    @after_save()
    async def send_welcome_email(self):
        # Send welcome email after saving
        await send_email(self.email, "Welcome!")

    @before_delete()
    async def backup_data(self):
        # Backup user data before deletion
        await backup_user(self.to_dict())

    @after_delete()
    async def cleanup_resources(self):
        # Clean up user resources after deletion
        await cleanup_user_files(self.id)
```

### Custom Event Handlers

```python
from earnorm.events import Event

# Define event handler
async def handle_user_created(event: Event):
    user_data = event.data
    await send_notification(f"New user created: {user_data['name']}")

# Subscribe to event
event_bus.subscribe("user.created", handle_user_created)

# Publish event
event = Event(
    name="user.created",
    data={"name": "John Doe", "email": "john@example.com"},
    metadata={"source": "api"}
)
await event_bus.publish(event)

# Publish event with delay
await event_bus.publish(event, delay=60.0)  # Delay 60 seconds
```

### Error Handling

```python
async def handle_payment(event: Event):
    try:
        await process_payment(event.data)
    except Exception as e:
        # Event will be retried up to max_retries times
        raise

# Failed events are moved to failed queue after max retries
# They can be inspected and requeued if needed
```

## Configuration

The event system can be configured through the `EventBus` constructor:

- `queue_name`: Name of the Redis queue (default: "earnorm:events")
- `batch_size`: Number of events to process in batch (default: 100)
- `poll_interval`: Interval between queue polls in seconds (default: 1.0)
- `max_retries`: Maximum number of retries for failed events (default: 3)
- `retry_delay`: Delay between retries in seconds (default: 5.0)
- `num_workers`: Number of worker tasks (default: 1)

## Best Practices

1. **Event Design**
   - Keep events small and focused
   - Include only necessary data
   - Use clear and consistent naming
   - Add relevant metadata

2. **Event Handlers**
   - Keep handlers simple and single-purpose
   - Handle errors gracefully
   - Avoid long-running operations
   - Use async/await properly

3. **Performance**
   - Adjust batch size based on load
   - Monitor queue length
   - Scale workers as needed
   - Use appropriate retry delays

4. **Maintenance**
   - Monitor failed events
   - Set up logging
   - Implement error tracking
   - Regular queue cleanup

## Future Features

- [ ] Scheduled events
- [ ] Event patterns (pub/sub)
- [ ] Event persistence
- [ ] Event replay
- [ ] Event filtering
- [ ] Event metrics
- [ ] Event monitoring
- [ ] Event debugging tools 
