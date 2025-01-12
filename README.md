# EarnORM

[![Project Status: Prototype](https://img.shields.io/badge/Project%20Status-Prototype-yellow.svg)]()
[![License: CC BY-NC](https://img.shields.io/badge/License-CC%20BY--NC-lightgrey.svg)]()
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)]()

A modern, async-first MongoDB ORM for Python built on top of Pydantic and Motor. Currently in prototype stage.

## 🌟 Features

### Core Features
- Async-first design with full async/await support
- Type safety and validation with Pydantic
- Automatic schema and index management
- Comprehensive security system (ACL, RBAC, Record Rules)
- Multi-level caching (memory and Redis)
- Audit logging and change tracking

### Development Tools
- CLI tools for schema management
- Testing utilities and fixtures
- Development server
- Documentation generator

## 🚀 Quickstart

### Installation
```bash
pip install earnorm
```

### Define Models
```python
from earnorm import BaseModel
from datetime import datetime

class User(BaseModel):
    _collection = "users"
    _indexes = [
        {
            "keys": [("email", 1)],
            "unique": True
        }
    ]
    
    username: str
    email: str
    created_at: datetime = datetime.utcnow()

class Product(BaseModel):
    _collection = "products"
    _abstract = False  # Create collection
    
    name: str
    price: float
```

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