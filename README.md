# EarnORM

[![Project Status: Prototype](https://img.shields.io/badge/Project%20Status-Prototype-yellow.svg)]()
[![License: CC BY-NC](https://img.shields.io/badge/License-CC%20BY--NC-lightgrey.svg)]()
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)]()
[![PyPI version](https://badge.fury.io/py/earnorm.svg)](https://badge.fury.io/py/earnorm)

EarnORM is a high-performance, async-first MongoDB ORM for Python, designed to maximize throughput in I/O-bound applications. Built on top of Motor and Pydantic, it leverages the full power of async/await to handle thousands of database operations concurrently while maintaining type safety and data validation.

🚀 **Key Highlights**:

- **Async-First Design**: Native async/await support throughout the entire stack for maximum I/O performance
- **Optimized for Speed**: Connection pooling, query optimization, and multi-level caching (memory + Redis)
- **Type Safety**: Full type hints and runtime validation powered by Pydantic
- **Developer Experience**: Rich set of async tools, decorators, and CLI commands
- **Production Ready**: Comprehensive security, audit logging, and monitoring features

Currently in prototype stage, EarnORM aims to be the go-to choice for building high-performance, scalable Python applications with MongoDB.

## 🌟 Features

### ⚡️ Performance Features

- **Async Core**: Built from ground up with async/await for non-blocking I/O operations
- **Connection Pooling**: Smart connection management with Motor
- **Query Optimization**: Automatic index management and domain expressions
- **Batch Operations**: Efficient bulk create, update, and delete operations
- **Lazy Loading**: Load related documents only when needed

### 🛡 Core Features

- **Type Safety**: Full type hints and runtime validation
- **Schema Management**: Automatic collection and index management
- **Domain Expressions**: Powerful search domain syntax (=, !=, >, >=, <, <=, in, not in, like, ilike)
- **RecordSet Operations**: Filtering, sorting, mapping, and batch operations
- **Event System**: Validators and constraints hooks
- **Field Types**: Built-in field types with validation (String, Int, Email, etc.)

### 🔧 Development Tools

- **Type Hints**: Full IDE support with auto-completion
- **Field Validation**: Required fields, unique constraints, and custom validators
- **Error Handling**: Clear error messages and validation feedback
- **Documentation**: Comprehensive docstrings and type annotations
- **Example Code**: Ready-to-use example applications

## 🏗 Project Status

The project is currently in prototype stage with the following functionality:

✅ Implemented:

- Async Model Base with Motor integration
- Type-safe RecordSet operations
- Field types and validation
- Domain expressions for querying
- Collection and index management
- Validators and constraints
- Basic event system

🚧 In Progress:

- Relationship fields (One2many, Many2one)
- Caching system
- Security (ACL, RBAC)
- Audit logging
- CLI tools
- Testing utilities
- Documentation

## 📝 Documentation

Detailed documentation can be found at [earnorm.readthedocs.io](https://earnorm.readthedocs.io)

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

EarnORM is released under the Creative Commons Attribution-NonCommercial (CC BY-NC) license.

This means you are free to:

- Use, copy and distribute the code
- Modify and build upon the code

Under the following terms:

- You must give appropriate credit
- You may not use the code for commercial purposes
- Derivative works must be shared under the same license

## 📧 Contact

- Email: [contact@earnorm.dev](mailto:contact@earnorm.dev)
- GitHub Issues: [earnorm/issues](https://github.com/earnorm/earnorm/issues)

## ⭐️ Credits

EarnORM is developed by the EarnBase team and the open source community.

Special thanks to:

- Pydantic team
- Motor team
- MongoDB team

## Examples

EarnORM provides examples for integration with popular Python web frameworks:

### FastAPI Example
```python
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel as PydanticModel

import earnorm
from earnorm import BaseModel, Email, Int, String


class User(BaseModel):
    """User model."""
    _collection = "users"
    _name = "user"
    _indexes = [{"email": 1}]

    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)


class UserCreate(PydanticModel):
    """User creation schema."""
    name: str
    email: str
    age: int


class UserResponse(PydanticModel):
    """User response schema."""
    id: Optional[str] = None
    name: str
    email: str
    age: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize EarnORM on startup and cleanup on shutdown."""
    # Initialize EarnORM
    await earnorm.init(
        mongo_uri="mongodb://localhost:27017",
        database="earnorm_example",
    )
    yield
    # Cleanup on shutdown if needed
    await earnorm.close()


app = FastAPI(title="EarnORM FastAPI Example", lifespan=lifespan)


@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user."""
    try:
        user_obj = User(**user.model_dump())
        await user_obj.save()
        return UserResponse(
            id=user_obj.id,
            name=user_obj.name,
            email=user_obj.email,
            age=user_obj.age,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users/", response_model=List[UserResponse])
async def list_users(age_gt: Optional[int] = None):
    """List all users with optional age filter."""
    domain = [("age", ">", age_gt)] if age_gt else None
    users = await User.search(domain)
    return [
        UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            age=user.age,
        )
        for user in users
    ]


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get a user by ID."""
    user = await User.find_one([("_id", "=", user_id)])
    if not user.exists():
        raise HTTPException(status_code=404, detail="User not found")
    record = user.ensure_one()
    return UserResponse(
        id=record.id,
        name=record.name,
        email=record.email,
        age=record.age,
    )


@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Delete a user by ID."""
    user = await User.find_one([("_id", "=", user_id)])
    if not user.exists():
        raise HTTPException(status_code=404, detail="User not found")
    await user.unlink()
    return {"message": "User deleted"}

### Simple Example
```python
from earnorm import BaseModel, String, Email, Int

class User(BaseModel):
    _collection = "users"
    _name = "user" 
    _indexes = [{"email": 1}]

    name = String(required=True)
    email = Email(required=True, unique=True) 
    age = Int(required=True)

# Create user
user = User(name="John", email="john@example.com", age=25)
await user.save()

# Search users
users = await User.search([("age", ">", 20)])
for user in users:
    print(f"{user.name}: {user.age}")

# Find one user
user = await User.find_one([("email", "=", "john@example.com")])
if user.exists():
    record = user.ensure_one()
    print(f"Found user: {record.name}")
```

### Framework Integration Examples

The `examples` directory contains sample applications demonstrating EarnORM integration with:

- **FastAPI**: REST API with Pydantic models and dependency injection
- **Django**: Async views with Django 3.1+ and URL routing
- **Flask**: Class-based views with MethodView

See the respective example directories for complete implementations.

## Best Practices

### Model Definition

1. **Collection Names**: Use plural form for collection names
```python
class User(BaseModel):
    _collection = "users"  # Good
    _name = "user"        # Singular for model name
```

2. **Field Requirements**: Always specify field requirements explicitly
```python
class Product(BaseModel):
    name = String(required=True)           # Required field
    description = String(required=False)    # Optional field
    price = Float(required=True)
```

3. **Indexes**: Define indexes for frequently queried fields
```python
class Order(BaseModel):
    _indexes = [
        {"user_id": 1},              # Single field index
        {"created_at": -1},          # Descending index
        {"status": 1, "date": -1}    # Compound index
    ]
```

### Querying

1. **Domain Expressions**: Use domain expressions for complex queries
```python
# Good
users = await User.search([
    ("age", ">", 18),
    ("status", "=", "active")
])

# Avoid raw queries when possible
```

2. **RecordSet Operations**: Utilize RecordSet methods for data manipulation
```python
# Filter records
active_users = users.filtered_domain([("status", "=", "active")])

# Sort records
sorted_users = users.sorted("age", reverse=True)

# Ensure single record
user = users.ensure_one()
```

3. **Batch Operations**: Use batch methods for better performance
```python
# Create multiple records
users = await User.create([
    {"name": "John", "age": 25},
    {"name": "Jane", "age": 30}
])

# Delete multiple records
await users.unlink()
```

### Error Handling

1. **Validation Errors**: Always handle validation errors
```python
try:
    user = User(name="John", age="invalid")
    await user.save()
except ValueError as e:
    print(f"Validation error: {e}")
```

2. **Record Existence**: Check record existence before operations
```python
user = await User.find_one([("email", "=", "john@example.com")])
if not user.exists():
    raise ValueError("User not found")
```

### Performance

1. **Indexing**: Create indexes for frequently queried fields and sorting operations
2. **Batch Operations**: Use batch operations instead of individual operations when possible
3. **Field Selection**: Only select required fields in queries
4. **Pagination**: Implement pagination for large result sets

### Type Safety

1. **Type Hints**: Use type hints for better IDE support
```python
from typing import List, Optional

def get_users(age: int) -> List[User]:
    return User.search([("age", ">", age)])
```

2. **Field Types**: Use appropriate field types for data validation
```python
class User(BaseModel):
    age = Int(min_value=0, max_value=150)
    email = Email(unique=True)
    status = String(choices=["active", "inactive"])
```
