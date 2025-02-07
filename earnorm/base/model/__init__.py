"""Model package for EarnORM.

This package provides the core model functionality for EarnORM, including:

1. Base Models
   - BaseModel: Foundation class for all models
   - StoredModel: Base class for persistent models
   - AbstractModel: Base class for service/business logic models

2. Model Features
   - Field validation and type checking
   - CRUD operations (create, read, update, delete)
   - Multiple database support
   - Event system
   - Field caching with async descriptors

3. Model Decorators
   - @model: Register model with environment
   - @multi: Enable multiple record operations
   - @depends: Define model dependencies

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields import StringField, IntegerField

    >>> # Define a model
    >>> class User(BaseModel):
    ...     _name = 'data.user'  # Collection/table name
    ...     name = StringField(required=True)
    ...     age = IntegerField()
    ...
    ...     async def validate(self):
    ...         '''Custom validation logic'''
    ...         if self.age < 0:
    ...             raise ValueError("Age cannot be negative")

    >>> # Create a record
    >>> user = await User.create({
    ...     "name": "John Doe",
    ...     "age": 30
    ... })

    >>> # Search records
    >>> users = await User.search([
    ...     ("age", ">=", 18),
    ...     ("name", "like", "John%")
    ... ])

    >>> # Update records
    >>> await users.write({
    ...     "age": 31
    ... })

    >>> # Delete records
    >>> await users.unlink()

Features:
    1. Field Validation:
       - Type checking
       - Required fields
       - Field constraints
       - Custom validators

    2. CRUD Operations:
       - Async create/read/update/delete
       - Bulk operations
       - Search with domain expressions
       - Record cache management

    3. Database Support:
       - MongoDB integration
       - Transaction support
       - Multiple database connections
       - Cross-database operations

    4. Event System:
       - Pre/post create hooks
       - Pre/post write hooks
       - Pre/post unlink hooks
       - Custom event handlers

    5. Field Caching:
       - Async field access
       - Cache invalidation
       - Lazy loading
       - Memory optimization

See Also:
    - earnorm.fields: Field definitions
    - earnorm.database: Database adapters
    - earnorm.env: Environment management
"""

from .base import BaseModel

__all__ = [
    "BaseModel",
]
