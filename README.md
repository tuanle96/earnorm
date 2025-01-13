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
