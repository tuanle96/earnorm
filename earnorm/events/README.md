# Event Components

Event system components for EarnORM.

## Purpose

The events module provides a comprehensive event system:
- Model lifecycle events
- Pre/post operation hooks
- Custom event handlers
- Event propagation
- Event logging
- Async event handling

## Concepts & Examples

### Model Lifecycle Events
```python
class User(BaseModel):
    name = StringField()
    email = EmailField()
    
    @pre_save
    def before_save(self):
        self.updated_at = datetime.now()
        
    @post_save
    def after_save(self):
        notify_user_updated(self)
        
    @pre_delete
    def before_delete(self):
        archive_user(self)
        
    @post_delete
    def after_delete(self):
        cleanup_user_data(self)
```

### Custom Events
```python
class Order(BaseModel):
    status = StringField()
    
    @on_event('status_change')
    def handle_status_change(self, old_status, new_status):
        log_status_change(self, old_status, new_status)
        
    @on_event('payment_received')
    def handle_payment(self, payment):
        self.status = 'paid'
        self.paid_at = datetime.now()
        self.save()
```

### Event Handlers
```python
# Global event handler
@event_handler('user.created')
def handle_user_created(user):
    send_welcome_email(user)
    
# Model-specific handler
@User.on('password_changed')
def handle_password_change(user):
    send_password_change_notification(user)
    
# Multiple events handler
@event_handler(['user.login', 'user.logout'])
def log_user_activity(user, event):
    log_activity(user, event)
```

### Async Events
```python
class User(BaseModel):
    @post_save_async
    async def after_save(self):
        await notify_services(self)
        
    @on_event_async('profile_updated')
    async def handle_profile_update(self):
        await update_search_index(self)
        await notify_followers(self)

# Global async handler
@event_handler_async('order.completed')
async def handle_order_completed(order):
    await process_order_async(order)
    await notify_shipping_async(order)
```

## Best Practices

1. **Event Design**
- Keep events focused
- Use meaningful names
- Document event data
- Handle failures gracefully
- Consider event order

2. **Handler Implementation**
- Keep handlers simple
- Handle errors properly
- Avoid long operations
- Document side effects
- Consider async handlers

3. **Performance**
- Use async when appropriate
- Batch event processing
- Monitor event queues
- Handle backpressure
- Implement timeouts

4. **Maintenance**
- Log event failures
- Monitor event flow
- Track handler stats
- Clean up old handlers
- Document event flow

## Future Features

1. **Event Types**
- [ ] Scheduled events
- [ ] Conditional events
- [ ] Event patterns
- [ ] Event priorities
- [ ] Event versioning

2. **Handler Features**
- [ ] Handler groups
- [ ] Handler chains
- [ ] Handler timeouts
- [ ] Handler retries
- [ ] Handler metrics

3. **Event Management**
- [ ] Event monitoring
- [ ] Event replay
- [ ] Event sourcing
- [ ] Event store
- [ ] Event debugging

4. **Integration**
- [ ] Message queues
- [ ] Webhooks
- [ ] Event streaming
- [ ] External services
- [ ] Event plugins 