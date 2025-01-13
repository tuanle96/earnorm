# EarnORM

[![Project Status: Prototype](https://img.shields.io/badge/Project%20Status-Prototype-yellow.svg)]()
[![License: CC BY-NC](https://img.shields.io/badge/License-CC%20BY--NC-lightgrey.svg)]()
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)]()

[![PyPI version](https://badge.fury.io/py/earnorm.svg)](https://badge.fury.io/py/earnorm)
[![Downloads](https://pepy.tech/badge/earnorm)](https://pepy.tech/project/earnorm)
[![Documentation Status](https://readthedocs.org/projects/earnorm/badge/?version=latest)](https://earnorm.readthedocs.io/en/latest/?badge=latest)

[![Tests](https://github.com/earnorm/earnorm/workflows/Tests/badge.svg)](https://github.com/earnorm/earnorm/actions)
[![codecov](https://codecov.io/gh/earnorm/earnorm/branch/main/graph/badge.svg)](https://codecov.io/gh/earnorm/earnorm)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[![GitHub contributors](https://img.shields.io/github/contributors/earnorm/earnorm.svg)](https://github.com/earnorm/earnorm/graphs/contributors)
[![GitHub issues](https://img.shields.io/github/issues/earnorm/earnorm.svg)](https://github.com/earnorm/earnorm/issues)
[![GitHub stars](https://img.shields.io/github/stars/earnorm/earnorm.svg)](https://github.com/earnorm/earnorm/stargazers)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/earnorm)](https://github.com/sponsors/earnorm)

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
- **Connection Pooling**: Smart connection management for optimal resource utilization
- **Query Optimization**: Automatic query analysis and index suggestions
- **Multi-level Caching**: In-memory and Redis caching with intelligent invalidation
- **Batch Operations**: Efficient bulk create, update, and delete operations
- **Lazy Loading**: Load related documents only when needed

### 🛡 Core Features
- **Type Safety**: Full type hints and runtime validation with Pydantic
- **Schema Management**: Automatic collection and index management
- **Security System**: Comprehensive ACL, RBAC, and Record Rules
- **Change Tracking**: Audit logging and version control
- **Event System**: Rich set of lifecycle hooks and event handlers
- **Plugin System**: Extensible architecture with plugin support

### 🔧 Development Tools
- **Async CLI**: Schema management and development tools
- **Testing Suite**: Async test utilities and fixtures
- **Dev Server**: Development server with hot reload
- **Documentation**: Auto-generated API documentation
- **Monitoring**: Performance metrics and health checks
- **DevContainer**: Ready-to-use development environment

### Field Types and Relationships
```python
from earnorm import BaseModel, Field
from typing import List, Optional

class Category(BaseModel):
    _collection = "categories"
    name: str = Field(min_length=2)
    description: Optional[str] = None

class Product(BaseModel):
    _collection = "products"
    name: str = Field(min_length=3)
    price: float = Field(gt=0)
    
    # One-to-many relationship with lazy loading
    category = Many2oneField(Category, lazy=True)
    
    # Many-to-many relationship
    tags = Many2manyField("Tag", lazy=True)
    
    async def get_category(self):
        # Lazy loading in sync mode
        category = self.category.convert()
        
        # Full loading in async mode
        category = await self.category.async_convert()
        return category

class Tag(BaseModel):
    _collection = "tags"
    name: str = Field(unique=True)
    products = One2manyField(Product, inverse_field="tags")

## 🚀 Quickstart

### Installation
```bash
pip install earnorm
```

### Define Models
```python
from earnorm import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class User(BaseModel):
    _collection = "users"
    _indexes = [
        {"keys": [("email", 1)], "unique": True}
    ]
    
    username: str = Field(min_length=3)
    email: str = Field(regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    async def orders(self) -> List["Order"]:
        return await self.env["orders"].find({"user_id": self.id})

class Order(BaseModel):
    _collection = "orders"
    _abstract = False
    
    user_id: str
    items: List[str]
    total: float
    status: str = "pending"
    
    @property
    async def user(self) -> Optional[User]:
        return await self.env["users"].find_one({"_id": self.user_id})
```

### Use Async/Await
```python
import asyncio
from earnorm import init_orm

async def main():
    # Initialize ORM
    await init_orm(
        uri="mongodb://localhost:27017",
        database="myapp",
        redis_uri="redis://localhost:6379"
    )
    
    # Create user
    user = User(username="john", email="john@example.com")
    await user.save()
    
    # Create order with validation
    order = Order(user_id=user.id, items=["item1", "item2"], total=29.99)
    await order.save()
    
    # Efficient querying with async
    orders = await Order.find(
        {"total": {"$gt": 20}},
        sort=[("created_at", -1)],
        limit=10
    ).to_list()
    
    # Access related documents
    for order in orders:
        user = await order.user  # Lazy loading
        print(f"Order {order.id} by {user.username}")

if __name__ == "__main__":
    asyncio.run(main())

### Schema Management
```bash
# Create/update collections and indexes
earnorm schema upgrade --database mydb

# View schema information
earnorm schema info --database mydb
```

### Security
```python
# Define groups
@groups.define
class UserGroups:
    ADMIN = "admin"
    USER = "user"

# Define model with security
class Order(BaseModel):
    _collection = "orders"
    _acl = {
        "create": ["admin"],
        "read": ["admin", "user"],
        "write": ["admin"],
        "delete": ["admin"]
    }
    _audit = {
        "create": True,
        "write": ["status", "total"]
    }
```

## 🏗 Project Status

The project is currently in prototype stage with basic functionality:

✅ Implemented:

🚧 In Progress:

- Base Model with Pydantic integration
- Schema Management (collections, indexes)
- Security System (ACL, RBAC, Record Rules)
- Audit Logging
- CLI Tools
- Caching System
- Query Builder
- Testing Utilities
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
