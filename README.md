# EarnORM 🚀

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/earnbase/earnorm)

> A powerful, async-first ORM framework for modern Python applications

## 📖 Description

EarnORM is a modern, async-first Object-Relational Mapping (ORM) framework designed to provide a flexible and type-safe interface for database operations in Python applications. Built with performance and developer experience in mind, it offers seamless integration with multiple databases and modern Python features.

## 🏗️ Project Status

Currently in **Alpha** stage. Core features are implemented and working, but the API may change as we gather feedback and improve the framework.

- [x] Core ORM functionality
- [x] MongoDB support
- [x] Connection pooling
- [x] Type safety
- [ ] PostgreSQL support (in progress)
- [ ] MySQL support (planned)
- [ ] Migration system (planned)
- [ ] Admin interface (planned)

## ✨ Key Highlights

- 🔄 **Async/Await First**: Built from the ground up for asynchronous operations
- 🔒 **Type Safety**: Full type hints support with runtime validation
- 🎯 **Multiple Database Support**: MongoDB, PostgreSQL (coming soon), MySQL (planned)
- 🌟 **Modern Python**: Leverages latest Python features and best practices
- 🛠️ **Developer Friendly**: Intuitive API with excellent IDE support

## 🎯 Features

### Core Features

- **Async Operations**
  - Non-blocking database operations
  - Async connection pooling
  - Event-driven architecture

- **Type System**
  - Runtime type checking
  - Custom type converters
  - Validation framework

- **Connection Management**
  - Smart connection pooling
  - Automatic recovery
  - Health monitoring

- **Model System**
  - Declarative models
  - Field validation
  - Relationship management
  - Event hooks

### Advanced Features

- **Query Building**
  - Type-safe queries
  - Complex filters
  - Aggregations
  - Joins

- **Transaction Support**
  - ACID compliance
  - Nested transactions
  - Savepoints
  - Automatic rollback

## 📚 Documentation

- [Getting Started](docs/getting-started.md)
- [User Guide](docs/user-guide.md)
- [API Reference](docs/api-reference.md)
- [Contributing Guide](CONTRIBUTING.md)

## 💡 Examples

### Basic Usage

```python
from earnorm.base import BaseModel
from earnorm.fields import StringField, IntegerField

class User(BaseModel):
    _name = 'data.user'
    name = StringField(required=True)
    age = IntegerField()

    async def validate(self):
        if self.age < 0:
            raise ValueError("Age cannot be negative")

# Create record
user = await User.create({
    "name": "John Doe",
    "age": 30
})

# Query records
users = await User.search([
    ("age", ">=", 18),
    ("name", "like", "John%")
])
```

### FastAPI Integration with Lifecycle

```python
from fastapi import FastAPI
from earnorm.config import SystemConfig
from earnorm.di import container

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Load config
    config = SystemConfig.load_env(".env")
    
    # Initialize container
    await container.init(config)
    
    # Register services
    container.register("config", config)

@app.on_event("shutdown")
async def shutdown():
    await container.destroy()

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    User = await container.get_model("data.user")
    return await User.read(user_id)
```

### Django Integration

```python
from django.apps import AppConfig
from earnorm.config import SystemConfig
from earnorm.di import container

class MyAppConfig(AppConfig):
    name = 'myapp'
    
    async def ready(self):
        # Initialize EarnORM
        config = SystemConfig.load_env(".env")
        await container.init(config)
```

### Flask Integration

```python
from flask import Flask
from earnorm.config import SystemConfig
from earnorm.di import container

app = Flask(__name__)

@app.before_first_request
async def init_earnorm():
    config = SystemConfig.load_env(".env")
    await container.init(config)

@app.teardown_appcontext
async def shutdown_earnorm(exception=None):
    await container.destroy()
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

- GitHub: [@earnbase](https://github.com/earnbaseio)
- Email: contact@earnbase.io
- Twitter: [@earnbase](https://twitter.com/earnbaseio)

## 🙏 Credits

EarnORM is built with inspiration from:
- [Motor](https://motor.readthedocs.io/)

Special thanks to all our [contributors](https://github.com/tuanle96/earnorm/graphs/contributors)!
