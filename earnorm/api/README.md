# API Components

API decorator system for EarnORM.

## Purpose

The API module provides advanced decorator capabilities:
- Method decorators
- Field decorators
- Validation decorators
- Hook decorators
- Async decorators
- Caching decorators

## Concepts & Examples

### Method Decorators
```python
# Base model methods
@classmethod
@model
@returns(List["User"])
async def find_active(cls) -> List["User"]:
    return await cls.find(status="active")

# Instance methods
@multi
@requires_permission("write")
async def activate_users(self):
    await self.update({"status": "active"})

# Context methods
@with_context(tracking=True)
@with_env
async def process_order(self):
    await self._process()
    await self.env.commit()
```

### Field Decorators
```python
# Computed fields
class User(BaseModel):
    first_name: str
    last_name: str
    
    @computed("full_name", depends=["first_name", "last_name"])
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @computed("age", depends=["birth_date"], store=True)
    def age(self) -> int:
        return calculate_age(self.birth_date)

# Related fields
class Order(BaseModel):
    user: User
    
    @related("user.address", store=True)
    def shipping_address(self):
        return self.user.address
    
    @related("user.settings.currency")
    def currency(self):
        return self.user.settings.currency
```

### Validation Decorators
```python
# Field validation
class Product(BaseModel):
    price: float
    stock: int
    
    @constrains("price")
    def _check_price(self):
        if self.price < 0:
            raise ValueError("Price cannot be negative")
    
    @validates("stock")
    def _validate_stock(self, value):
        if value < 0:
            raise ValueError("Stock cannot be negative")
        return value

# Change tracking
class Order(BaseModel):
    status: str
    
    @onchange("status")
    async def _on_status_change(self):
        if self.status == "completed":
            await self.send_notification()
```

### Hook Decorators
```python
# Lifecycle hooks
class User(BaseModel):
    @before_create
    async def _before_create(self):
        self.created_at = datetime.utcnow()
        await self.validate_email()
    
    @after_write
    async def _after_write(self):
        await self.invalidate_cache()
        await self.index_search()
    
    @before_delete
    async def _before_delete(self):
        if self.has_active_orders():
            raise ValueError("Cannot delete user with active orders")
```

### Async Decorators
```python
# Async support
class UserService:
    @asynccontextmanager
    async def transaction(self):
        async with self.db.transaction():
            yield
    
    @asyncinit
    async def __init__(self):
        await self.initialize()
    
    @asyncproperty
    async def active_users(self):
        return await User.find(active=True)
```

### Caching Decorators
```python
# Cache management
class ProductService:
    @cached(ttl=3600)
    async def get_popular_products(self):
        return await Product.find(
            popular=True
        ).sort("-views").limit(10)
    
    @invalidates_cache("get_popular_products")
    async def update_product_views(self, product_id):
        await Product.increment(
            {"_id": product_id},
            {"views": 1}
        )
```

## Best Practices

1. **Decorator Design**
- Keep decorators focused
- Document behavior
- Handle errors gracefully
- Support async operations
- Maintain type hints

2. **Performance**
- Use caching wisely
- Optimize computations
- Minimize dependencies
- Batch operations
- Profile decorators

3. **Maintainability**
- Clear naming
- Consistent patterns
- Good documentation
- Easy testing
- Error handling

4. **Type Safety**
- Use type hints
- Validate inputs
- Check returns
- Handle edge cases
- Support generics

## Future Features

1. **Core Features**
- [ ] Async decorator factory
- [ ] Decorator composition
- [ ] Decorator registry
- [ ] Dynamic decorators
- [ ] Decorator metrics

2. **Field Features**
- [ ] Computed aggregations
- [ ] Virtual fields
- [ ] Field encryption
- [ ] Field versioning
- [ ] Field observers

3. **Validation Features**
- [ ] Async validation
- [ ] Custom validators
- [ ] Validation chains
- [ ] Error aggregation
- [ ] Validation rules

4. **Hook Features**
- [ ] Transaction hooks
- [ ] Rollback hooks
- [ ] Async hooks
- [ ] Hook priorities
- [ ] Hook conditions 