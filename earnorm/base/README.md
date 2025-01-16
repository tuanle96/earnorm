# Base Module

## Overview
The Base module is the core foundation of EarnORM, providing essential components for model definition, data manipulation, and database operations. It consists of several submodules that work together to provide a complete ORM solution.

## Structure
```
base/
├── domain/         # Domain expressions and query building
├── fields/         # Field types and validation
├── recordset/      # Record collection management
├── registry/       # Model and database registration
├── relationships/  # Model relationships management
└── types.py        # Common type definitions
```

## Submodules

### 1. Domain
The Domain submodule provides a powerful expression language for building complex queries:

```python
from earnorm.base.domain import DomainExpression, DomainBuilder

# Using domain builder
builder = DomainBuilder()
domain = (
    builder
    .field("age").greater_than(18)
    .and_()
    .field("status").equals("active")
    .build()
)

# Using domain expression
expr = DomainExpression([
    ["age", ">", 18],
    "AND",
    ["status", "=", "active"]
])
```

[Read more about Domain](./domain/README.md)

### 2. Fields
The Fields submodule defines various field types and their behaviors:

```python
from earnorm.base.fields import StringField, IntegerField, DateTimeField

class User(Model):
    name = StringField(required=True)
    age = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

[Read more about Fields](./fields/README.md)

### 3. RecordSet
The RecordSet submodule provides a fluent interface for querying and manipulating collections of records:

```python
from earnorm.base.recordset import RecordSet

# Query and filter records
users = await User.search([("age", ">", 18)])
active_users = users.filter(status="active")

# Sort and paginate
sorted_users = active_users.sort("name", "asc")
page = await sorted_users.paginate(page=1, per_page=10)
```

[Read more about RecordSet](./recordset/README.md)

### 4. Registry
The Registry submodule manages model registration and database connections:

```python
from earnorm.base.registry import ModelRegistry, DatabaseRegistry

# Register models
registry = ModelRegistry()
registry.register(User)
registry.register(Post)

# Setup database
db_registry = DatabaseRegistry()
await db_registry.initialize(
    uri="mongodb://localhost:27017",
    database="earnbase"
)
```

[Read more about Registry](./registry/README.md)

### 5. Relationships
The Relationships submodule provides tools for defining and managing relationships between models:

```python
from earnorm.base.relationships import OneToOne, OneToMany, ManyToMany

class User(Model):
    profile = OneToOne("Profile", "user_id")
    posts = OneToMany("Post", "author_id")
    groups = ManyToMany("Group", "UserGroup")
```

[Read more about Relationships](./relationships/README.md)

## Usage Examples

### 1. Model Definition
```python
from earnorm.base import Model
from earnorm.base.fields import StringField, IntegerField
from earnorm.base.relationships import OneToMany

class User(Model):
    _collection = "users"
    _indexes = [
        {"fields": [("email", 1)], "unique": True}
    ]
    
    name = StringField(required=True)
    email = StringField(required=True, unique=True)
    age = IntegerField(default=0)
    posts = OneToMany("Post", "author_id")
```

### 2. Basic Operations
```python
# Create record
user = await User.create({
    "name": "John",
    "email": "john@example.com",
    "age": 25
})

# Query records
adult_users = await User.search([
    ("age", ">=", 18),
    ("status", "=", "active")
])

# Update records
await adult_users.update({"status": "verified"})

# Delete records
await User.delete([("status", "=", "inactive")])
```

### 3. Advanced Queries
```python
# Complex filtering with domain expressions
domain = (
    DomainBuilder()
    .field("age").greater_than(18)
    .and_()
    .open_group()
        .field("role").in_(["admin", "manager"])
        .or_()
        .field("permissions").contains("super_user")
    .close_group()
    .build()
)

users = await User.search(domain)

# Relationship queries
user = await User.get(user_id)
user_posts = await user.posts.filter(status="published").sort("created_at", "desc").all()
```

## Best Practices

1. **Model Design**
- Use meaningful collection names
- Define appropriate indexes
- Validate field constraints
- Document model relationships

2. **Query Optimization**
- Use appropriate field types
- Create necessary indexes
- Optimize complex queries
- Monitor query performance

3. **Data Integrity**
- Validate data before operations
- Use transactions when needed
- Handle relationship cascades
- Maintain referential integrity

4. **Code Organization**
- Group related models
- Follow naming conventions
- Document complex logic
- Write comprehensive tests

## Contributing

1. Follow code style guidelines
2. Add comprehensive tests
3. Document new features
4. Update type hints
5. Benchmark performance impacts 
