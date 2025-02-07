# EarnORM Base Database Module

This module provides the core database functionality for EarnORM, including database adapters, query building, and transaction management.

## Overview

The base database module consists of four main components:

1. Database Adapter
2. Query System
3. Transaction System
4. Database Backends

### Database Adapter

The adapter system provides a unified interface for database operations:

```python
from earnorm.base.database import DatabaseAdapter

# Create adapter instance
adapter = MongoAdapter(client)

# Basic query
users = await adapter.query(User).filter(
    age__gt=18,
    status="active"
).all()

# Aggregate query
stats = await adapter.query(User, "aggregate")\
    .group_by("status")\
    .count("total")\
    .execute()

# Join query
results = await adapter.query(User, "join")\
    .join(Post)\
    .on(User.id == Post.user_id)\
    .execute()
```

### Query System

The query system supports:

1. Basic Queries
- Filtering
- Sorting
- Limiting/Offsetting
- Field selection

2. Aggregate Queries
- Group by operations
- Aggregation functions (count, sum, avg, etc.)
- Having clauses

3. Join Queries
- Inner/outer joins
- Multiple join conditions
- Join-specific field selection

Example:
```python
# Complex query example
users = await adapter.query(User)\
    .filter(age__gt=18)\
    .order_by("-created_at")\
    .limit(10)\
    .offset(20)\
    .select("id", "name", "email")\
    .all()

# Aggregate example
stats = await adapter.query(Order, "aggregate")\
    .group_by("status", "category")\
    .count("total_orders")\
    .sum("amount", "total_amount")\
    .having(total_orders__gt=10)\
    .execute()
```

### Transaction System

The transaction system provides:

1. ACID Properties
- Atomicity
- Consistency
- Isolation
- Durability

2. Transaction Management
- Begin/commit/rollback
- Savepoints
- Nested transactions
- Error handling

Example:
```python
async with adapter.transaction() as txn:
    # Create user
    user = await txn.create(User, {
        "name": "John Doe",
        "email": "john@example.com"
    })
    
    # Create related order
    order = await txn.create(Order, {
        "user_id": user.id,
        "amount": 100.00
    })
    
    # All operations will be committed if successful
    # or rolled back if any error occurs
```

## Directory Structure

```
earnorm/base/database/
├── adapter.py          # Base adapter interface
├── adapters/           # Database-specific adapters
│   ├── mongo.py       # MongoDB adapter
│   └── ...
├── query/             # Query building system
│   ├── core/          # Core query functionality
│   ├── backends/      # Backend-specific query implementations
│   └── interfaces/    # Query interfaces
└── transaction/       # Transaction management
    ├── base.py        # Base transaction interface
    └── backends/      # Backend-specific transaction implementations
```

## Features

1. Database Operations
- CRUD operations
- Bulk operations
- Complex queries
- Aggregations
- Joins

2. Query Building
- Intuitive query API
- Type-safe queries
- Query optimization
- Result caching

3. Transaction Support
- ACID compliance
- Nested transactions
- Savepoints
- Automatic rollback

4. Type Safety
- Type hints
- Runtime type checking
- Validation
- Error handling

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
