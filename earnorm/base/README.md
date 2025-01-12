# Base Components

Core components for EarnORM.

## Purpose

The base module provides core functionality:
- Base model with async support
- Field types and validation
- API decorators
- Model lifecycle hooks
- Type safety
- Inheritance support
- Model registry and environment

## Concepts & Examples

### Base Model
```python
from earnorm import BaseModel, Field
from datetime import datetime

class User(BaseModel):
    _collection = "users"
    
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Lifecycle hooks
    @before_create
    async def _before_create(self):
        await self.validate_email()
    
    @after_write
    async def _after_write(self):
        await self.invalidate_cache()
    
    # Custom methods
    @classmethod
    async def find_by_email(cls, email: str):
        return await cls.find_one(email=email)
    
    async def change_password(self, new_password: str):
        self.password = await self.hash_password(new_password)
        await self.save()
```

### Field Types
```python
from earnorm.base.fields import StringField, IntegerField, ReferenceField

class Product(BaseModel):
    _collection = "products"
    
    name: str = StringField(min_length=3, max_length=100)
    price: float = Field(gt=0)
    stock: int = IntegerField(minimum=0)
    category: Category = ReferenceField("Category", lazy=True)
    
    # Computed fields
    @computed("total_value")
    def total_value(self) -> float:
        return self.price * self.stock
    
    # Validation
    @validates("price")
    def validate_price(self, value: float) -> float:
        if value <= 0:
            raise ValueError("Price must be positive")
        return value
```

### API Decorators
```python
from earnorm.api import model, multi, returns

class Order(BaseModel):
    _collection = "orders"
    
    # Model methods
    @classmethod
    @model
    @returns(List["Order"])
    async def find_pending(cls):
        return await cls.find(status="pending")
    
    # Instance methods
    @multi
    @requires_permission("write")
    async def process_orders(self):
        for order in self:
            await order.process()
    
    # Computed fields
    @computed("total", depends=["items.price", "items.quantity"])
    def total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)
```

### Model Registry & Environment
```python
# Models are automatically registered when defined
class User(BaseModel):
    _collection = "users"
    name: str
    email: str

class Order(BaseModel):
    _collection = "orders"
    user_id: ObjectId
    total: float
    
    async def get_user(self):
        # Access other models through env
        User = self.env["users"]
        return await User.find_one(id=self.user_id)

# Access models through registry
async def process_order(order_id: ObjectId):
    Order = registry["orders"]
    order = await Order.find_one(id=order_id)
    if order:
        user = await order.get_user()
        # Process order...
```

### Inheritance
```python
class Vehicle(BaseModel):
    _collection = "vehicles"
    
    brand: str
    model: str
    year: int
    
    @computed("age")
    def age(self) -> int:
        return datetime.now().year - self.year

class Car(Vehicle):
    _collection = "cars"
    
    doors: int
    fuel_type: str
    
    @validates("doors")
    def validate_doors(self, value: int) -> int:
        if value not in [2, 4]:
            raise ValueError("Cars must have 2 or 4 doors")
        return value
```

## Best Practices

1. **Model Design**
- Use type hints
- Add field validation
- Define clear methods
- Handle errors
- Document behavior
- Set collection names

2. **Field Usage**
- Choose right types
- Set constraints
- Add validation
- Use computed fields
- Handle relations

3. **API Design**
- Use decorators
- Add return types
- Handle permissions
- Validate inputs
- Document APIs

4. **Performance**
- Use async/await
- Optimize queries
- Cache results
- Batch operations
- Monitor usage

5. **Registry Usage**
- Register models properly
- Use env for model access
- Handle dependencies
- Manage lifecycle
- Monitor registry

## Future Features

1. **Model Features**
- [ ] Dynamic fields
- [ ] Field encryption
- [ ] Field versioning
- [ ] Field observers
- [ ] Field aggregation

2. **API Features**
- [ ] API versioning
- [ ] API documentation
- [ ] API validation
- [ ] API metrics
- [ ] API caching

3. **Validation Features**
- [ ] Custom validators
- [ ] Validation chains
- [ ] Error handling
- [ ] Validation rules
- [ ] Schema evolution

4. **Hook Features**
- [ ] Transaction hooks
- [ ] Rollback hooks
- [ ] Hook priorities
- [ ] Hook conditions
- [ ] Hook composition

5. **Registry Features**
- [ ] Model dependencies
- [ ] Lazy loading
- [ ] Registry events
- [ ] Registry plugins
- [ ] Registry metrics 