# Event System

Event system for EarnORM, using Celery as the message broker. Events are processed asynchronously and can be delayed, retried, and monitored.

## Installation

Event system is built into EarnORM. To use it, you need:
1. Redis server for message broker
2. Celery worker for processing events

## Initialization

Event system is automatically initialized when you initialize EarnORM with Redis URI:

```python
from earnorm import init

await init(
    mongo_uri="mongodb://localhost:27017",
    database="earnbase",
    redis_uri="redis://localhost:6379/0",
    event_config={
        "queue_name": "my_app:events",
        "retry_policy": {
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.2,
            "interval_max": 0.5,
        }
    }
)
```

## Basic Usage

### Define Event Handler

```python
from earnorm.events import event_handler

@event_handler("user.created")
async def handle_user_created(event):
    print(f"User created: {event.data}")
```

### Publish Event

```python
from earnorm import event_bus
from earnorm.events import Event

await event_bus.publish(
    Event(
        name="user.created",
        data={"id": "123", "email": "user@example.com"}
    )
)

# Publish with delay
await event_bus.publish(
    Event(
        name="user.welcome_email",
        data={"email": "user@example.com"}
    ),
    delay=60  # delay 60 seconds
)
```

## Model Events

### Model Lifecycle Hooks

EarnORM provides simple decorators for model lifecycle hooks:

```python
from datetime import datetime
from earnorm.base import BaseModel
from earnorm.events.decorators import before_create, after_write, before_delete

class User(BaseModel):
    """User model with lifecycle hooks."""
    
    _collection = "users"
    
    username: str
    email: str
    status: str = "inactive"
    created_at: datetime
    updated_at: datetime

    @before_create
    async def _before_create(self):
        """Validate and prepare data before creating user."""
        self.created_at = datetime.utcnow()
        await self.validate_email()
    
    @after_write
    async def _after_write(self):
        """Update cache and search index after any write operation."""
        await self.invalidate_cache()
        await self.index_search()
    
    @before_delete
    async def _before_delete(self):
        """Check if user can be deleted."""
        if self.has_active_orders():
            raise ValueError("Cannot delete user with active orders")

    async def validate_email(self):
        """Validate email format and uniqueness."""
        if not is_valid_email(self.email):
            raise ValueError("Invalid email format")
        
        # Check uniqueness
        existing = await User.find_one({"email": self.email})
        if existing and existing.id != self.id:
            raise ValueError("Email already exists")

    async def invalidate_cache(self):
        """Invalidate user cache."""
        cache_key = f"user:{self.id}"
        await self._env.cache.delete(cache_key)

    async def index_search(self):
        """Update search index."""
        await self._env.search.index_document(
            "users",
            self.id,
            {
                "username": self.username,
                "email": self.email,
                "status": self.status
            }
        )

    def has_active_orders(self) -> bool:
        """Check if user has any active orders."""
        return Order.count({"user_id": self.id, "status": "active"}) > 0

### Available Lifecycle Hooks

1. **Create Hooks**
   - `@before_create`: Called before creating a new record
   - `@after_create`: Called after successful creation

2. **Write Hooks**
   - `@before_write`: Called before any write operation (create/update)
   - `@after_write`: Called after any write operation

3. **Update Hooks**
   - `@before_update`: Called before updating an existing record
   - `@after_update`: Called after successful update

4. **Delete Hooks**
   - `@before_delete`: Called before deleting a record
   - `@after_delete`: Called after successful deletion

### Best Practices for Lifecycle Hooks

1. **Naming Convention**
   - Prefix internal hooks with underscore (e.g. `_before_create`)
   - Use descriptive names for business logic methods

2. **Validation**
   - Use `before_create` and `before_write` for data validation
   - Raise clear validation errors with meaningful messages

3. **Side Effects**
   - Use `after_write` for cache invalidation
   - Use `after_write` for search indexing
   - Use `after_delete` for cleanup tasks

4. **Error Handling**
   - Handle errors gracefully in hooks
   - Rollback changes if needed
   - Log errors for debugging

5. **Performance**
   - Keep hooks lightweight
   - Use async operations when possible
   - Batch operations when dealing with multiple records

## Configuration

Event system can be configured through `event_config` in `earnorm.init()`:

```python
event_config = {
    # Queue name for events
    "queue_name": "my_app:events",

    # Retry policy for failed events
    "retry_policy": {
        # Maximum number of retries
        "max_retries": 3,
        # Initial delay in seconds
        "interval_start": 0,
        # Delay increment in seconds
        "interval_step": 0.2,
        # Maximum delay in seconds
        "interval_max": 0.5,
    }
}
```

## Best Practices

### Event Naming

- Use lowercase and dots for namespace separation
- Format: `<namespace>.<resource>.<action>`
- Examples: `user.created`, `order.payment.completed`

### Event Data

- Include only necessary data for event handlers
- Use IDs instead of entire objects
- Add metadata like timestamp, version when needed

### Error Handling

- Always have retry policies for critical events
- Log errors with full context
- Have fallback plans for failed events

### Performance

- Use batch events when possible
- Consider delays for non-critical events
- Monitor queue size and processing time

### Monitoring

- Monitor failed jobs through `event_bus.get_failed_jobs()`
- Retry failed jobs with `event_bus.retry_job(job_id)`
- Remove stuck jobs with `event_bus.remove_job(job_id)`

## Event System for EarnORM

Event system provides asynchronous event processing capabilities for EarnORM models.

### Features
- Asynchronous event processing
- Event handlers with decorators
- Model lifecycle events
- Batch event processing
- Delayed event execution
- Retry policies for failed events
- Event monitoring and management

### Installation

Events are included in EarnORM by default. No additional installation required.

### Usage

#### Initialize Event System

```python
from earnorm import init

await init(
    mongodb_uri="mongodb://localhost:27017",
    redis_uri="redis://localhost:6379/0",
    event_config={
        "queue_name": "my_app:events",
        "retry_policy": {
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.2,
            "interval_max": 0.5,
        }
    }
)
```

#### Using Events in Models

```python
from datetime import datetime
from typing import Optional

from earnorm.base import BaseModel
from earnorm.events.decorators import before_save, after_save, before_delete
from earnorm.events.utils import dispatch_model_event


class User(BaseModel):
    """User model with event handling."""
    
    _collection = "users"
    
    username: str
    email: str
    status: str = "inactive"
    last_login: Optional[datetime] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    @before_save("user.before_create")
    async def create(self) -> None:
        """Create a new user.
        
        Emits events:
        - user.before_create: Before user is created
        - user.created: After user is created
        - user.welcome_email: After user is created (delayed)
        """
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Save user
        await super().create()
        
        # Emit created event
        await dispatch_model_event(
            self._env.event_bus,
            User,
            "created",
            str(self.id),
            self
        )
        
        # Schedule welcome email
        await dispatch_model_event(
            self._env.event_bus,
            User,
            "welcome_email",
            str(self.id),
            self,
            delay=60  # Send after 60 seconds
        )

    @before_save("user.before_update")
    async def update_status(self, new_status: str) -> None:
        """Update user status.
        
        Emits events:
        - user.before_update: Before status is updated
        - user.status_changed: After status is changed
        """
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        await super().save()
        
        # Emit status changed event
        if old_status != new_status:
            await dispatch_model_event(
                self._env.event_bus,
                User,
                "status_changed",
                str(self.id),
                self
            )

    @after_save("user.login")
    async def record_login(self) -> None:
        """Record user login.
        
        Emits events:
        - user.login: After login is recorded
        """
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        await super().save()
```

#### Handle Model Events

```python
from earnorm.events import model_event_handler

@model_event_handler("User", "created")
async def handle_user_created(event):
    """Handle user created event."""
    user_data = event.data
    # Send welcome email
    await send_welcome_email(user_data["email"])

@model_event_handler("User", "status_changed")
async def handle_user_status_changed(event):
    """Handle user status changed event."""
    user_data = event.data
    # Update cache
    await update_user_cache(user_data["id"], user_data["status"])

@model_event_handler("User", "login")
async def handle_user_login(event):
    """Handle user login event."""
    user_data = event.data
    # Log login activity
    await log_user_login(user_data["id"], user_data["last_login"])
```

### Best Practices

1. **Event Naming**
- Use lowercase and dots for namespace separation
- Format: `<namespace>.<resource>.<action>`
- Examples: `user.created`, `user.status_changed`, `user.login`

2. **Event Data**
- Include only necessary data for event handlers
- Use IDs instead of entire objects when possible
- Add metadata like timestamp, version when needed

3. **Error Handling**
- Always have retry policies for critical events
- Log errors with full context
- Have fallback plans for failed events

4. **Performance**
- Use batch events for bulk operations
- Set appropriate retry intervals
- Monitor queue size and processing time

5. **Monitoring**
- Track failed events
- Monitor queue latency
- Set up alerts for critical failures
- Keep event logs for debugging 
