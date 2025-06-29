# EarnORM Codebase Structure

**Last Updated**: 2025-01-28  
**Version**: 0.1.4 (Alpha)  
**Status**: Active Development - Async-first ORM Framework

## 📁 **Project Root Structure**

```
earnorm/                           # Project root
├── .augment-guidelines            # Project-specific development guidelines
├── .devcontainer/                 # Development container configuration
├── .github/                       # GitHub configuration
│   ├── FUNDING.yml               # GitHub funding configuration
│   └── topics.yml                # Repository topics
├── examples/                      # Usage examples and demos
│   └── simple/                   # Simple usage example
│       ├── config.yaml           # Example configuration
│       └── main.py               # Example implementation
├── earnorm/                       # Core ORM package
├── CODE_OF_CONDUCT.md            # Community guidelines
├── CONTRIBUTING.md               # Development contribution guide
├── CONTRIBUTORS.md               # Project contributors
├── LICENSE                       # MIT License
├── MANIFEST.in                   # Package manifest
├── README.md                     # Project overview and documentation
├── poetry.lock                   # Locked dependency versions
├── pyproject.toml               # Project configuration and dependencies
├── setup.cfg                    # Legacy configuration (linting, testing)
└── todo.md                      # Planned features and improvements
```

## 🏗️ **Core Package Structure (`earnorm/`)**

```
earnorm/
├── __init__.py                   # Package initialization and main entry point
├── README.md                     # Core package documentation
├── api.py                        # API decorators (@model, @multi, @one)
├── constants.py                  # Global constants and field mappings
├── exceptions.py                 # Exception hierarchy and error handling
├── registry.py                   # Model and service registration system
│
├── base/                         # Core ORM functionality
│   ├── __init__.py              # Base module exports
│   ├── README.md                # Base module documentation
│   ├── env.py                   # Environment management and DI integration
│   ├── database/                # Database abstraction layer
│   └── model/                   # Base model system
│
├── config/                       # Configuration management
│   ├── __init__.py              # Config module exports
│   ├── README.md                # Configuration documentation
│   ├── data.py                  # Configuration data models and loading
│   └── model.py                 # Configuration model definitions
│
├── database/                     # Database utilities and type mapping
│   ├── __init__.py              # Database module exports
│   ├── README.md                # Database module documentation
│   ├── mappers.py               # Data type mappers
│   └── type_mapping.py          # Type conversion utilities
│
├── di/                          # Dependency injection system
│   ├── __init__.py              # DI module exports
│   ├── README.md                # DI documentation
│   ├── container/               # DI container implementation
│   ├── lifecycle/               # Object lifecycle management
│   └── resolver/                # Dependency resolution
│
├── fields/                      # Field type system
│   ├── __init__.py              # Field module exports
│   ├── README.md                # Field system documentation
│   ├── base.py                  # Base field implementation
│   ├── interface.py             # Field interfaces and protocols
│   ├── types.py                 # Field type definitions
│   ├── composite/               # Complex field types
│   ├── primitive/               # Basic field types
│   ├── relations/               # Relationship fields
│   └── validators/              # Field validation system
│
├── pool/                        # Connection pooling system
│   ├── __init__.py              # Pool module exports
│   ├── README.md                # Connection pooling documentation
│   ├── constants.py             # Pool-related constants
│   ├── factory.py               # Pool factory implementation
│   ├── registry.py              # Pool registry management
│   ├── types.py                 # Pool type definitions
│   ├── backends/                # Database-specific pool implementations
│   ├── core/                    # Core pooling functionality
│   ├── protocols/               # Pool interfaces and protocols
│   └── utils/                   # Pool utility functions
│
├── types/                       # Type definitions and protocols
│   ├── __init__.py              # Types module exports
│   ├── README.md                # Type system documentation
│   ├── base.py                  # Base types and JSON types
│   ├── database.py              # Database-related types
│   ├── fields.py                # Field-related types
│   ├── models.py                # Model-related types
│   └── relations.py             # Relationship types
│
└── validators/                  # Validation system
    ├── __init__.py              # Validators module exports
    ├── README.md                # Validation documentation
    ├── base.py                  # Base validator classes
    ├── fields/                  # Field-specific validators
    └── models/                  # Model-specific validators
```

## 🔧 **Module Details**

### **1. Base Module (`earnorm/base/`)**

**Purpose**: Core ORM functionality including models, database abstraction, and environment management.

```
base/
├── __init__.py                  # Exports: BaseModel, Environment, DatabaseAdapter, etc.
├── README.md                    # Architecture documentation
├── env.py                       # Environment: DI integration, model registry, lifecycle
├── database/                    # Database abstraction layer
│   ├── __init__.py             # Database exports
│   ├── README.md               # Database documentation
│   ├── adapter.py              # DatabaseAdapter abstract base class
│   ├── adapters/               # Database-specific implementations
│   │   ├── __init__.py        # Adapter exports
│   │   ├── README.md          # Adapter documentation
│   │   └── mongo.py           # MongoDB adapter implementation
│   ├── query/                  # Query building system
│   │   ├── __init__.py        # Query exports
│   │   ├── README.md          # Query documentation
│   │   ├── backends/          # Database-specific query builders
│   │   ├── core/              # Core query functionality
│   │   └── interfaces/        # Query interfaces and protocols
│   └── transaction/            # Transaction management
│       ├── __init__.py        # Transaction exports
│       ├── README.md          # Transaction documentation
│       ├── base.py            # Base transaction classes
│       └── backends/          # Database-specific transactions
└── model/                      # Base model system
    ├── __init__.py             # Model exports
    ├── README.md               # Model documentation
    ├── base.py                 # BaseModel class implementation
    ├── descriptors.py          # Field descriptors and property management
    └── meta.py                 # Model metaclass and metadata
```

### **2. Fields Module (`earnorm/fields/`)**

**Purpose**: Comprehensive field type system with validation and relationships.

```
fields/
├── __init__.py                 # Field exports (StringField, IntegerField, etc.)
├── README.md                   # Field system documentation
├── base.py                     # BaseField abstract class
├── interface.py                # Field interfaces and protocols
├── types.py                    # Field type definitions
├── composite/                  # Complex field types
│   ├── __init__.py            # Composite field exports
│   ├── README.md              # Composite field documentation
│   ├── dict.py                # DictField implementation
│   ├── embedded.py            # EmbeddedField for nested documents
│   ├── list.py                # ListField implementation
│   ├── set.py                 # SetField implementation
│   └── tuple.py               # TupleField implementation
├── primitive/                  # Basic field types
│   ├── __init__.py            # Primitive field exports
│   ├── README.md              # Primitive field documentation
│   ├── boolean.py             # BooleanField
│   ├── datetime.py            # DateTimeField, DateField, TimeField
│   ├── decimal.py             # DecimalField for precise numbers
│   ├── enum.py                # EnumField for enumeration values
│   ├── file.py                # FileField for file handling
│   ├── json.py                # JSONField for JSON data
│   ├── number.py              # IntegerField, FloatField
│   ├── object_id.py           # ObjectIdField for MongoDB
│   ├── string.py              # StringField with validation
│   └── uuid.py                # UUIDField implementation
├── relations/                  # Relationship fields
│   ├── __init__.py            # Relationship exports
│   ├── base.py                # Base relationship field
│   ├── many_to_many.py        # ManyToManyField
│   ├── many_to_one.py         # ManyToOneField (foreign key)
│   ├── one_to_many.py         # OneToManyField (reverse foreign key)
│   └── one_to_one.py          # OneToOneField
└── validators/                 # Field validation system
    ├── __init__.py            # Validator exports
    ├── README.md              # Validation documentation
    ├── base.py                # Base validator classes
    ├── common.py              # Common validation functions
    └── registry.py            # Validator registry system
```

### **3. Pool Module (`earnorm/pool/`)**

**Purpose**: Connection pooling system with circuit breaker patterns and health monitoring.

```
pool/
├── __init__.py                 # Pool exports
├── README.md                   # Connection pooling documentation
├── constants.py                # Pool-related constants
├── factory.py                  # Pool factory for creating pool instances
├── registry.py                 # Pool registry for managing multiple pools
├── types.py                    # Pool type definitions and protocols
├── backends/                   # Database-specific pool implementations
│   ├── __init__.py            # Backend exports
│   ├── mongo.py               # MongoDB connection pool
│   ├── postgres.py            # PostgreSQL connection pool (planned)
│   └── redis.py               # Redis connection pool
├── core/                       # Core pooling functionality
│   ├── __init__.py            # Core exports
│   ├── base.py                # Base pool implementation
│   ├── circuit_breaker.py     # Circuit breaker pattern
│   ├── health.py              # Health monitoring
│   └── retry.py               # Retry policies
├── protocols/                  # Pool interfaces and protocols
│   ├── __init__.py            # Protocol exports
│   ├── base.py                # Base pool protocols
│   └── health.py              # Health check protocols
└── utils/                      # Pool utility functions
    ├── __init__.py            # Utility exports
    ├── config.py              # Pool configuration utilities
    └── metrics.py             # Pool metrics and monitoring
```

### **4. DI Module (`earnorm/di/`)**

**Purpose**: Dependency injection system for service management and lifecycle control.

```
di/
├── __init__.py                 # DI exports (container, Container class)
├── README.md                   # Dependency injection documentation
├── container/                  # DI container implementation
│   ├── __init__.py            # Container exports
│   ├── base.py                # Base container functionality
│   ├── registry.py            # Service registry
│   └── resolver.py            # Dependency resolution logic
├── lifecycle/                  # Object lifecycle management
│   ├── __init__.py            # Lifecycle exports
│   ├── manager.py             # Lifecycle manager
│   ├── events.py              # Lifecycle events
│   └── hooks.py               # Lifecycle hooks
└── resolver/                   # Dependency resolution
    ├── __init__.py            # Resolver exports
    ├── base.py                # Base resolver
    ├── factory.py             # Factory resolver
    └── singleton.py           # Singleton resolver
```

### **5. Config Module (`earnorm/config/`)**

**Purpose**: Configuration management with environment variables and YAML support.

```
config/
├── __init__.py                 # Config exports (SystemConfig, SystemConfigData)
├── README.md                   # Configuration documentation
├── data.py                     # SystemConfigData: field definitions and loading
└── model.py                    # SystemConfig: configuration model with validation
```

### **6. Database Module (`earnorm/database/`)**

**Purpose**: Database utilities, type mapping, and data conversion.

```
database/
├── __init__.py                 # Database utility exports
├── README.md                   # Database utilities documentation
├── mappers.py                  # Data type mappers for different databases
└── type_mapping.py             # Type conversion utilities
```

### **7. Types Module (`earnorm/types/`)**

**Purpose**: Type definitions, protocols, and type safety infrastructure.

```
types/
├── __init__.py                 # Type exports
├── README.md                   # Type system documentation
├── base.py                     # Base types (JSONValue, DomainOperator, etc.)
├── database.py                 # Database-related types and protocols
├── fields.py                   # Field-related types and protocols
├── models.py                   # Model-related types (ModelProtocol, etc.)
└── relations.py                # Relationship types and protocols
```

### **8. Validators Module (`earnorm/validators/`)**

**Purpose**: Validation system for models and fields.

```
validators/
├── __init__.py                 # Validator exports
├── README.md                   # Validation system documentation
├── base.py                     # Base validator classes
├── fields/                     # Field-specific validators
│   ├── __init__.py            # Field validator exports
│   ├── string.py              # String validation (email, URL, etc.)
│   ├── number.py              # Number validation (range, precision)
│   └── datetime.py            # DateTime validation
└── models/                     # Model-specific validators
    ├── __init__.py            # Model validator exports
    └── base.py                # Base model validators
```

## 🔗 **Key Files and Their Purposes**

### **Root Level Files**

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package entry point, initialization function | ✅ Implemented |
| `api.py` | API decorators (@model, @multi, @one) | ✅ Implemented |
| `constants.py` | Global constants and field mappings | ✅ Implemented |
| `exceptions.py` | Exception hierarchy and error handling | ✅ Implemented |
| `registry.py` | Model and service registration system | ✅ Implemented |

### **Core Implementation Files**

| File | Purpose | Status |
|------|---------|--------|
| `base/model/base.py` | BaseModel class - core ORM functionality | ✅ Implemented |
| `base/env.py` | Environment management and DI integration | ✅ Implemented |
| `base/database/adapter.py` | Database adapter abstract interface | ✅ Implemented |
| `base/database/adapters/mongo.py` | MongoDB adapter implementation | ✅ Implemented |
| `config/data.py` | Configuration data models and loading | ✅ Implemented |
| `config/model.py` | Configuration model with validation | ✅ Implemented |

### **Field System Files**

| File | Purpose | Status |
|------|---------|--------|
| `fields/base.py` | Base field implementation | ✅ Implemented |
| `fields/primitive/*.py` | Basic field types (String, Integer, etc.) | ✅ Implemented |
| `fields/composite/*.py` | Complex field types (List, Dict, etc.) | ✅ Implemented |
| `fields/relations/*.py` | Relationship fields (ManyToOne, etc.) | ✅ Implemented |

## 📊 **Architecture Patterns**

### **1. Async-First Design**
- All database operations use `async/await`
- Non-blocking connection pooling
- Async context managers for transactions
- Event-driven architecture

### **2. Type Safety**
- Comprehensive type hints throughout
- Runtime type validation with Pydantic
- Protocol-based interfaces
- Generic type support

### **3. Dependency Injection**
- Service container for loose coupling
- Lifecycle management for resources
- Factory patterns for object creation
- Environment-based configuration

### **4. Modular Architecture**
- Clear separation of concerns
- Plugin-based field system
- Adapter pattern for databases
- Registry pattern for services

### **5. Validation-First Approach**
- Field-level validation
- Model-level validation
- Custom validator support
- Error aggregation and reporting

## 🚧 **Current Implementation Status**

### **✅ Completed Modules**
- **Base Model System**: Full CRUD operations, async support
- **MongoDB Adapter**: Complete implementation with transactions
- **Field System**: All primitive and composite fields
- **Configuration**: YAML and environment variable support
- **Dependency Injection**: Full container implementation
- **Connection Pooling**: MongoDB pool with circuit breaker

### **🔄 In Progress**
- **Relationship Fields**: Basic implementation, needs testing
- **Query System**: Core functionality, needs optimization
- **Validation System**: Basic validators, needs expansion

### **❌ Missing/Planned**
- **Test Suite**: Critical priority - no tests currently exist
- **PostgreSQL Adapter**: Planned for future release
- **MySQL Adapter**: Planned for future release
- **Migration System**: Planned for future release
- **Admin Interface**: Planned for future release

## 🎯 **Critical Priorities**

1. **Implement comprehensive test suite** (CRITICAL)
2. **Complete relationship field testing**
3. **Optimize query performance**
4. **Add PostgreSQL adapter**
5. **Implement migration system**

---

**Note**: This document reflects the actual codebase structure as of 2025-01-28. It should be updated whenever significant structural changes are made to the project.
