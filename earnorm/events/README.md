# Event System for EarnORM

EarnORM provides a powerful event system that allows asynchronous processing of model events and custom events.

## Features

- Asynchronous event processing
- Event handlers with decorators
- Model lifecycle events
- Batch event processing
- Delayed event execution
- Retry policies for failed events
- Event monitoring and management

## Installation

Events are built into EarnORM. No additional installation required.

## Usage

### Initialization

The event system is automatically initialized when initializing EarnORM:

```python
import earnorm

await earnorm.init(
    mongodb_uri="mongodb://localhost:27017",
    redis_uri="redis://localhost:6379/0",
    event_config={
        "queue_name": "my_app:events",
        "retry_policy": {
            "max_retries": 3,
            "interval_start": 60,  # seconds
            "interval_step": 60,   # seconds
            "interval_max": 3600,  # seconds
        }
    }
)
```

### Model Lifecycle Hooks

Model lifecycle hooks allow you to run code before or after model operations:

```python
from earnorm.base import BaseModel
from earnorm.fields import StringField, BooleanField, DateTimeField
from earnorm.events.decorators import (
    before_create, after_create,
    before_write, after_write,
    before_delete, after_delete
)

class User(BaseModel):
    _collection = "users"

    email = StringField(required=True)
    username = StringField(required=True)
    is_active = BooleanField(default=True)
    last_login = DateTimeField()

    @before_create
    async def validate_email(self):
        if not await self.is_valid_email():
            raise ValueError("Invalid email format")
        if await self.email_exists():
            raise ValueError("Email already exists")

    @after_write
    async def invalidate_cache(self):
        await self.env.cache.delete(f"user:{self.id}")
        await self.env.cache.delete_pattern("users:*")

    @before_delete
    async def check_dependencies(self):
        if await self.has_active_orders():
            raise ValueError("Cannot delete user with active orders")
        if await self.has_active_subscriptions():
            raise ValueError("Cannot delete user with active subscriptions")
```

### Custom Events with Event Data

You can define custom events with strongly typed data using Pydantic models:

```python
from earnorm.base import BaseModel
from earnorm.fields import (
    StringField, FloatField, ListField, DictField, 
    ObjectIdField, DateTimeField
)
from earnorm.events.core.types import EventData
from earnorm.events.decorators import event

class OrderItem(EventData):
    product_id: str
    name: str
    quantity: int
    price: float

class OrderCreatedEvent(EventData):
    order_id: str
    customer_id: str
    total: float
    items: list[OrderItem]
    shipping_address: dict
    created_at: str

class Order(BaseModel):
    _collection = "orders"

    customer_id = ObjectIdField(required=True)
    items = ListField(DictField(), required=True)
    total = FloatField(required=True)
    shipping_address = DictField(required=True)
    status = StringField(default="pending")
    created_at = DateTimeField(auto_now=True)

    async def create(self, **data):
        await super().create(**data)
        
        # Publish order created event
        await self.event_bus.publish(
            "order.created",
            OrderCreatedEvent(
                order_id=str(self.id),
                customer_id=str(self.customer_id),
                total=self.total,
                items=[OrderItem(**item) for item in self.items],
                shipping_address=self.shipping_address,
                created_at=self.created_at.isoformat()
            )
        )

    @event("order.created", data_class=OrderCreatedEvent)
    async def send_confirmation(self, data: OrderCreatedEvent):
        customer = await self.env.users.find_one([("_id", "=", data.customer_id)])
        if customer:
            await self.env.mail_service.send_order_confirmation(
                customer.email,
                order_id=data.order_id,
                total=data.total,
                items=data.items,
                shipping_address=data.shipping_address
            )
```

### Event Handlers

You can also create standalone event handlers:

```python
from earnorm.events.decorators import event_handler
from earnorm.events.core.types import EventData
from datetime import datetime

class PaymentEvent(EventData):
    payment_id: str
    order_id: str
    amount: float
    status: str
    error_code: str = None
    error_message: str = None
    timestamp: str

@event_handler("payment.failed")
async def notify_admin(data: PaymentEvent):
    if data.amount > 1000:
        await env.slack.send_message(
            channel="#payments-alerts",
            text=(
                f"🚨 High value payment failed!\n"
                f"Payment ID: {data.payment_id}\n"
                f"Order ID: {data.order_id}\n"
                f"Amount: ${data.amount:,.2f}\n"
                f"Error: [{data.error_code}] {data.error_message}\n"
                f"Time: {data.timestamp}"
            )
        )
```

### Model Event Handlers

To handle events for a specific model:

```python
from earnorm.events.decorators import model_event_handler
from earnorm.base import BaseModel
from earnorm.fields import StringField, DateTimeField, DictField
from datetime import datetime

class SecurityLog(BaseModel):
    _collection = "security_logs"

    event_type = StringField(required=True)
    user_id = StringField(required=True)
    metadata = DictField(default_factory=dict)
    created_at = DateTimeField(auto_now=True)

@model_event_handler(SecurityLog, "user.password_changed")
async def log_password_change(data: dict):
    await SecurityLog.create(
        event_type="password_changed",
        user_id=data["user_id"],
        metadata={
            "ip_address": data["ip_address"],
            "user_agent": data["user_agent"],
            "location": data["location"]
        }
    )
```

### Publishing Events from Models

Each model instance has access to `event_bus` for publishing events:

```python
from earnorm.base import BaseModel
from earnorm.fields import (
    StringField, FloatField, DateTimeField, 
    ObjectIdField, BooleanField
)
from earnorm.events.core.types import EventData
from datetime import datetime, timedelta

class SubscriptionEvent(EventData):
    subscription_id: str
    user_id: str
    plan: str
    expires_at: str
    is_trial: bool = False

class Subscription(BaseModel):
    _collection = "subscriptions"

    user_id = ObjectIdField(required=True)
    plan = StringField(required=True)
    is_trial = BooleanField(default=False)
    expires_at = DateTimeField(required=True)
    created_at = DateTimeField(auto_now=True)

    async def create(self, **data):
        await super().create(**data)
        
        # Schedule renewal reminder 7 days before expiry
        reminder_date = self.expires_at - timedelta(days=7)
        
        await self.event_bus.publish(
            "subscription.renewal_reminder",
            SubscriptionEvent(
                subscription_id=str(self.id),
                user_id=str(self.user_id),
                plan=self.plan,
                expires_at=self.expires_at.isoformat(),
                is_trial=self.is_trial
            ),
            delay=(reminder_date - datetime.utcnow()).total_seconds()
        )

    @event("subscription.renewal_reminder", data_class=SubscriptionEvent)
    async def send_reminder(self, data: SubscriptionEvent):
        user = await self.env.users.find_one([("_id", "=", data.user_id)])
        if user:
            await self.env.mail_service.send_renewal_reminder(
                email=user.email,
                subscription_id=data.subscription_id,
                plan=data.plan,
                expires_at=data.expires_at,
                is_trial=data.is_trial
            )
```

## Best Practices

### Event Naming

- Use lowercase with dots for namespacing (e.g. `user.created`, `order.payment.failed`)
- Be descriptive and specific
- Use past tense for lifecycle events
- Use present tense for commands/actions

### Data Handling

- Define event data classes using Pydantic models
- Include all necessary data in the event
- Keep event data serializable
- Validate data at both publish and handle time

### Error Handling

- Use retry policies for transient failures
- Log failed events for debugging
- Consider fallback handlers for critical events
- Validate event data before processing

### Performance

- Keep event handlers lightweight
- Use batch processing for high volume events
- Consider event priorities
- Monitor queue size and processing time

### Monitoring

- Log event processing metrics
- Set up alerts for failed events
- Monitor queue length and processing time
- Track retry attempts and failures 
