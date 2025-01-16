Core Concepts
=============

This guide explains the core concepts of EarnORM and how they work together.

Overview
--------

EarnORM is an async-first Object-Relational Mapping (ORM) library for MongoDB, designed with the following principles:

1. **Async-First**: Built from the ground up for asynchronous operations
2. **Type Safety**: Strong typing with runtime validation
3. **Developer Experience**: Intuitive API and comprehensive tooling
4. **Performance**: Optimized for high-throughput applications

Key Components
-------------

Models
~~~~~~

Models are Python classes that represent MongoDB collections:

.. code-block:: python

    from earnorm import Model, fields

    class User(Model):
        _collection = "users"  # MongoDB collection name

        name = fields.String(required=True)
        email = fields.Email(unique=True)

Models provide:
- Schema definition with fields
- Data validation
- CRUD operations
- Query interface
- Relationship management

Fields
~~~~~~

Fields define the structure and validation rules for model attributes:

.. code-block:: python

    class Product(Model):
        name = fields.String(required=True, min_length=3)
        price = fields.Decimal(min_value=0)
        tags = fields.List(fields.String())
        created_at = fields.DateTime(auto_now_add=True)

Features:
- Type conversion
- Validation rules
- Default values
- Automatic values (e.g., timestamps)
- Custom validation

Queries
~~~~~~~

EarnORM provides a powerful query system:

.. code-block:: python

    # Simple queries
    users = await User.search([
        ("age", ">=", 18),
        ("status", "=", "active")
    ])

    # Complex queries with domain builder
    from earnorm.domain import DomainBuilder

    domain = (
        DomainBuilder()
        .field("age").greater_than(18)
        .and_()
        .field("status").equals("active")
        .build()
    )

Features:
- Fluent query builder
- Complex conditions
- Sorting and pagination
- Aggregation pipeline
- Query optimization

Relationships
~~~~~~~~~~~~

Models can define relationships with other models:

.. code-block:: python

    class Author(Model):
        name = fields.String()
        books = fields.One2many("Book", "author")

    class Book(Model):
        title = fields.String()
        author = fields.Many2one(Author)
        categories = fields.Many2many("Category")

Types:
- One-to-One
- One-to-Many
- Many-to-One
- Many-to-Many

Features:
- Lazy loading
- Eager loading
- Cascade operations
- Reverse relationships

Lifecycle Management
------------------

EarnORM manages the lifecycle of objects and connections:

1. **Connection Management**
   - Connection pooling
   - Automatic reconnection
   - Multiple database support

2. **Model Lifecycle**
   - Pre/post save hooks
   - Pre/post delete hooks
   - Validation hooks
   - Custom hooks

3. **Transaction Management**
   - Atomic operations
   - Multi-document transactions
   - Rollback support

Example:

.. code-block:: python

    class User(Model):
        def before_save(self):
            # Called before saving
            self.updated_at = datetime.now()

        def after_save(self):
            # Called after saving
            await self.notify_update()

Dependency Injection
------------------

EarnORM uses dependency injection for:

1. **Service Management**
   - Database connections
   - Caching services
   - Event bus
   - Custom services

2. **Configuration**
   - Environment-based config
   - Service configuration
   - Feature flags

Example:

.. code-block:: python

    from earnorm import init, container

    # Initialize with services
    await init(
        mongo_uri="mongodb://localhost:27017",
        database="mydb",
        services={
            "cache": RedisCache(),
            "event_bus": EventBus()
        }
    )

    # Use services in models
    class User(Model):
        async def after_save(self):
            event_bus = await container.get("event_bus")
            await event_bus.publish("user.updated", self)

Best Practices
------------

1. **Model Design**
   - Keep models focused and cohesive
   - Use appropriate field types
   - Define clear relationships
   - Add proper validation

2. **Query Optimization**
   - Use indexes effectively
   - Limit returned fields
   - Batch operations when possible
   - Monitor query performance

3. **Resource Management**
   - Close connections properly
   - Use connection pooling
   - Implement proper error handling
   - Clean up resources

4. **Type Safety**
   - Use type hints consistently
   - Validate input data
   - Handle edge cases
   - Test type conversions

Next Steps
---------

- Learn about :doc:`models` in detail
- Explore available :doc:`fields` types
- Understand :doc:`queries` system
- Work with :doc:`relationships`
- Check :doc:`examples/basic` for practical examples
