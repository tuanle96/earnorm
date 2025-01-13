# Base Components

Core components for EarnORM.

## Purpose

The base module provides core functionality:

- Base model with MongoDB support
- Field types and validation
- Record Rules and Access Control
- Model lifecycle hooks
- Type safety with Pydantic
- Model registry and environment
- Recordset for batch operations
- Caching support

## Concepts & Examples

### Base Model

```python
from earnorm import BaseModel, Field
from datetime import datetime
from bson import ObjectId

class User(BaseModel):
    _collection = "users"
    _indexes = [
        {"keys": [("email", 1)], "unique": True}
    ]
    
    id: Optional[ObjectId] = None
    username: str = Field(min_length=3)
    email: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Lifecycle hooks
    @hook
    async def before_create(self):
        await self.validate_email()
    
    @hook
    async def after_save(self):
        await self.invalidate_cache()
    
    # Custom methods
    @classmethod
    async def find_by_email(cls, email: str):
        return await cls.find_one({"email": email})
    
    async def change_password(self, new_password: str):
        self.password = await self.hash_password(new_password)
        await self.save()
```

### Record Rules

```python
from earnorm.base import Rule, RuleManager

# Define rule
user_rule = Rule(
    name="user_access",
    model_cls=User,
    domain="{'company_id': user.company_id}",
    groups={"employee", "manager"},
    modes={"read", "write"}
)

# Register rule
rule_manager = RuleManager()
rule_manager.register_rule(
    collection="users",
    mode="read",
    domain={"active": True},
    groups=["employee"]
)

# Check access
can_access = await rule_manager.check_access(
    records=[user],
    mode="write",
    groups=user.groups
)
```

### RecordSet

```python
from earnorm import RecordSet

# Find users
users = await User.find({"active": True})
user_set = RecordSet(User, users)

# Batch operations
await user_set.write({"status": "active"})
await user_set.unlink()

# Iteration
async for user in user_set:
    print(user.email)

# Filtering
active_users = user_set.filtered(lambda u: u.active)
```

### Caching

```python
from earnorm.cache import cached

class User(BaseModel):
    @classmethod
    @cached(ttl=300)  # Cache for 5 minutes
    async def get_active_users(cls):
        return await cls.find({"active": True})
        
    @cached(ttl=300, key_pattern="user:{0.id}:stats")
    async def get_stats(self):
        return await self._compute_stats()
```

### Field Types and Relationships

```python
from earnorm.base.fields import (
    StringField, IntegerField, FloatField,
    BooleanField, DateTimeField, ObjectIdField,
    ListField, DictField, ReferenceField,
    Many2oneField, One2manyField, Many2manyField
)

class Category(BaseModel):
    _collection = "categories"
    
    name: str = StringField(min_length=2)
    description: str = StringField(required=False)
    
    # One-to-many relationship
    products = One2manyField("Product", inverse_field="category")

class Product(BaseModel):
    _collection = "products"
    
    name: str = StringField(min_length=3)
    price: float = FloatField(gt=0)
    stock: int = IntegerField(min_value=0)
    is_active: bool = BooleanField(default=True)
    created_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    metadata: dict = DictField(default_factory=dict)
    
    # Many-to-one relationship with lazy loading
    category = Many2oneField(
        Category,
        lazy=True,  # Enable lazy loading
        ondelete="set null",  # Behavior when parent is deleted
        index=True  # Create index on foreign key
    )
    
    # Many-to-many relationship
    tags = Many2manyField(
        "Tag",
        lazy=True,
        relation="product_tags",  # Custom relation collection name
        column1="product_id",     # Custom column names
        column2="tag_id"
    )
    
    # Relationship loading methods
    def get_category(self):
        # Sync mode - only returns lazy loaded instance
        return self.category.convert()
    
    async def load_category(self):
        # Async mode - fully loads from database
        return await self.category.async_convert()
    
    async def load_tags(self):
        # Load all related tags
        return await self.tags.async_convert()

class Tag(BaseModel):
    _collection = "tags"
    
    name: str = StringField(unique=True)
    color: str = StringField(pattern=r"^#[0-9a-fA-F]{6}$")
    
    # Inverse many-to-many relationship
    products = Many2manyField(
        Product,
        lazy=True,
        relation="product_tags",  # Must match related field
        column1="tag_id",
        column2="product_id"
    )
```

Key features of relationship fields:

1. **Many2oneField**:
   - Lazy loading support
   - Ondelete behavior ('set null', 'cascade')
   - Automatic indexing
   - Sync and async conversion methods

2. **One2manyField**:
   - Inverse relationship with Many2one
   - Batch loading of related records
   - Filtering and sorting capabilities
   - Automatic relationship maintenance

3. **Many2manyField**:
   - Custom relation collection
   - Custom column names
   - Bidirectional relationship
   - Efficient batch loading

4. **Common Features**:
   - Type safety with generics
   - Validation support
   - Automatic relationship syncing
   - Performance optimization with lazy loading
   - Full async/await support

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

- Use type hints with Pydantic models
- Add field validation and indexes
- Define clear lifecycle hooks
- Handle errors gracefully
- Document behavior
- Set collection names and indexes

2. **Security**

- Define record rules
- Set access control
- Use security groups
- Validate permissions
- Cache access checks

3. **Performance**

- Use recordsets for batch operations
- Cache frequent queries
- Optimize database access
- Monitor performance
- Handle large datasets

4. **Type Safety**

- Use Pydantic validation
- Add type hints
- Handle optional fields
- Validate input/output
- Test type conversions

5. **Caching Strategy**

- Cache frequent queries
- Set appropriate TTL
- Invalidate on changes
- Use key patterns
- Monitor cache usage

## Future Features

1. **Model Features**

- [ ] Computed fields
- [ ] Virtual fields
- [ ] Field encryption
- [ ] Field versioning
- [ ] Field observers

2. **Security Features**

- [ ] Row-level security
- [ ] Field-level security
- [ ] Audit logging
- [ ] Permission inheritance
- [ ] Security policies

3. **Performance Features**

- [ ] Query optimization
- [ ] Bulk operations
- [ ] Async iteration
- [ ] Connection pooling
- [ ] Query profiling

4. **Cache Features**

- [ ] Distributed caching
- [ ] Cache invalidation
- [ ] Cache warming
- [ ] Cache metrics
- [ ] Cache policies

5. **Type Features**

- [ ] Custom types
- [ ] Type conversion
- [ ] Type validation
- [ ] Generic types
- [ ] Type inference
