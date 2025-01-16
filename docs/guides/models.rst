Models
======

Models are the core component of EarnORM, representing MongoDB collections and providing an interface for data manipulation.

Defining Models
-------------

Basic Model
~~~~~~~~~~

.. code-block:: python

    from earnorm import Model, fields

    class User(Model):
        _collection = "users"  # MongoDB collection name

        name = fields.String(required=True)
        email = fields.Email(required=True, unique=True)
        age = fields.Integer(min_value=0)
        is_active = fields.Boolean(default=True)
        created_at = fields.DateTime(auto_now_add=True)
        updated_at = fields.DateTime(auto_now=True)

Model Configuration
~~~~~~~~~~~~~~~~

Models support various configuration options:

.. code-block:: python

    class Product(Model):
        _collection = "products"  # Collection name
        _indexes = [
            {"fields": ["name"], "unique": True},
            {"fields": [("price", -1)]}
        ]
        _validators = [
            validate_price_range,
            validate_stock_level
        ]
        _options = {
            "cache_enabled": True,
            "cache_ttl": 3600
        }

Available options:
- `_collection`: MongoDB collection name
- `_indexes`: List of indexes to create
- `_validators`: List of model-level validators
- `_options`: Additional model options

Model Inheritance
~~~~~~~~~~~~~~~

Models support inheritance for code reuse:

.. code-block:: python

    class BaseModel(Model):
        created_at = fields.DateTime(auto_now_add=True)
        updated_at = fields.DateTime(auto_now=True)
        is_active = fields.Boolean(default=True)

    class User(BaseModel):
        name = fields.String(required=True)
        email = fields.Email(required=True, unique=True)

    class Product(BaseModel):
        name = fields.String(required=True)
        price = fields.Decimal(required=True)

CRUD Operations
-------------

Creating Records
~~~~~~~~~~~~~

.. code-block:: python

    # Create a single record
    user = await User.create({
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    })

    # Create multiple records
    users = await User.create_many([
        {
            "name": "Alice",
            "email": "alice@example.com"
        },
        {
            "name": "Bob",
            "email": "bob@example.com"
        }
    ])

Reading Records
~~~~~~~~~~~~

.. code-block:: python

    # Get by ID
    user = await User.get(user_id)

    # Find one
    user = await User.find_one({
        "email": "john@example.com"
    })

    # Find many
    active_users = await User.search([
        ("is_active", "=", True),
        ("age", ">=", 18)
    ])

    # Get all records
    all_users = await User.all()

    # Count records
    count = await User.count([
        ("is_active", "=", True)
    ])

Updating Records
~~~~~~~~~~~~~

.. code-block:: python

    # Update a single record
    user = await User.get(user_id)
    await user.update({
        "age": 31,
        "is_active": False
    })

    # Update many records
    await User.update_many(
        [("age", "<", 18)],
        {"is_active": False}
    )

Deleting Records
~~~~~~~~~~~~~

.. code-block:: python

    # Delete a single record
    await user.delete()

    # Delete many records
    await User.delete_many([
        ("is_active", "=", False)
    ])

    # Soft delete (if configured)
    await user.soft_delete()

Validation
---------

Field Validation
~~~~~~~~~~~~~

Fields have built-in validation:

.. code-block:: python

    class User(Model):
        name = fields.String(
            required=True,
            min_length=2,
            max_length=100
        )
        age = fields.Integer(
            min_value=0,
            max_value=150
        )
        email = fields.Email(
            required=True,
            unique=True
        )

Custom Validators
~~~~~~~~~~~~~~

You can add custom validators:

.. code-block:: python

    def validate_age(value):
        if value < 18:
            raise ValueError("User must be 18 or older")

    class User(Model):
        age = fields.Integer(validators=[validate_age])

    # Or model-level validators
    def validate_user(user):
        if user.end_date < user.start_date:
            raise ValueError("End date must be after start date")

    class User(Model):
        _validators = [validate_user]

Lifecycle Hooks
-------------

Models support various lifecycle hooks:

.. code-block:: python

    class User(Model):
        async def before_save(self):
            # Called before saving
            self.updated_at = datetime.now()

        async def after_save(self):
            # Called after saving
            await self.notify_update()

        async def before_delete(self):
            # Called before deletion
            await self.cleanup_resources()

        async def after_delete(self):
            # Called after deletion
            await self.notify_deletion()

Available hooks:
- `before_save`/`after_save`
- `before_delete`/`after_delete`
- `before_validate`/`after_validate`
- `before_update`/`after_update`

Querying
-------

Simple Queries
~~~~~~~~~~~~

.. code-block:: python

    # Basic operators
    users = await User.search([
        ("age", ">=", 18),
        ("status", "=", "active"),
        ("email", "like", "@example.com")
    ])

    # Sorting and pagination
    users = await User.search(
        [("is_active", "=", True)],
        sort=[("name", 1)],
        skip=0,
        limit=10
    )

Complex Queries
~~~~~~~~~~~~~

.. code-block:: python

    from earnorm.domain import DomainBuilder

    # Using domain builder
    domain = (
        DomainBuilder()
        .field("age").greater_than(18)
        .and_()
        .open_group()
            .field("role").in_(["admin", "manager"])
            .or_()
            .field("status").equals("active")
        .close_group()
        .build()
    )

    users = await User.search(domain)

Aggregation
~~~~~~~~~~

.. code-block:: python

    # Simple aggregation
    result = await User.aggregate([
        {"$match": {"age": {"$gte": 18}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "avg_age": {"$avg": "$age"}
        }}
    ])

    # Complex aggregation
    pipeline = [
        {"$match": {"is_active": True}},
        {"$lookup": {
            "from": "orders",
            "localField": "_id",
            "foreignField": "user_id",
            "as": "orders"
        }},
        {"$project": {
            "name": 1,
            "total_orders": {"$size": "$orders"},
            "total_spent": {"$sum": "$orders.amount"}
        }}
    ]

    result = await User.aggregate(pipeline)

Best Practices
------------

1. **Model Design**
   - Keep models focused and cohesive
   - Use appropriate field types
   - Add proper validation
   - Document model behavior

2. **Performance**
   - Create appropriate indexes
   - Use projection to limit fields
   - Batch operations when possible
   - Monitor query performance

3. **Validation**
   - Validate at field level when possible
   - Add model-level validation for complex rules
   - Use custom validators for business logic
   - Handle validation errors gracefully

4. **Lifecycle Hooks**
   - Keep hooks focused
   - Avoid heavy operations in hooks
   - Handle errors properly
   - Document hook behavior

5. **Querying**
   - Use appropriate query methods
   - Leverage domain builder for complex queries
   - Implement proper error handling
   - Monitor and optimize slow queries

Next Steps
---------

- Learn about available :doc:`fields` types
- Understand :doc:`queries` in detail
- Work with :doc:`relationships`
- Explore :doc:`examples/basic` for practical examples
