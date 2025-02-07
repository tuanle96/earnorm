# Query System

This directory contains the query building and execution system for EarnORM.

## Overview

The query system provides a flexible and type-safe way to build and execute database queries. It supports:

1. Basic Queries
2. Aggregate Queries
3. Join Queries

## Directory Structure

```
query/
├── core/           # Core query functionality
├── backends/       # Backend-specific implementations
└── interfaces/     # Query interfaces and protocols
```

## Query Types

### Basic Queries

Basic queries support filtering, sorting, and pagination:

```python
# Simple filter
users = await User.query.filter(
    age__gt=18,
    status="active"
).all()

# Complex filter with operators
users = await User.query.filter(
    DomainBuilder()
    .field("age").greater_than(18)
    .and_()
    .field("status").equals("active")
    .or_()
    .field("role").in_(["admin", "moderator"])
    .build()
).all()

# Sorting and pagination
users = await User.query\
    .order_by("-created_at", "name")\
    .limit(10)\
    .offset(20)\
    .all()
```

### Aggregate Queries

Aggregate queries support grouping and aggregation functions:

```python
# Simple aggregation
total = await Order.query.aggregate().sum("amount")

# Complex aggregation
stats = await Order.query.aggregate()\
    .group_by("status", "category")\
    .count("total_orders")\
    .sum("amount", "total_amount")\
    .avg("amount", "avg_amount")\
    .having(total_orders__gt=10)\
    .execute()
```

### Join Queries

Join queries support different types of joins:

```python
# Inner join
results = await User.query.join(Post)\
    .on(User.id == Post.user_id)\
    .select("name", "posts.title")\
    .execute()

# Left join with conditions
results = await Order.query.join(
    User,
    join_type="left",
    on={"user_id": "id"},
    conditions={"status": "active"}
).execute()
```

## Query Building

The query building system uses a fluent interface:

```python
query = User.query\
    .filter(age__gt=18)\
    .exclude(status="inactive")\
    .order_by("-created_at")\
    .limit(10)\
    .select("id", "name", "email")
```

### Domain Builder

For complex filters, use the domain builder:

```python
domain = DomainBuilder()\
    .field("age").greater_than(18)\
    .and_()\
    .group(
        DomainBuilder()
        .field("role").equals("admin")
        .or_()
        .field("permissions").contains("manage_users")
    )\
    .build()

users = await User.query.filter(domain).all()
```

## Query Execution

Queries can be executed in different ways:

```python
# Get all results
results = await query.all()

# Get first result
result = await query.first()

# Get specific fields
data = await query.values("id", "name")

# Count results
count = await query.count()

# Check existence
exists = await query.exists()
```

## Backend Support

Each database backend must implement:

1. Query Translation
- Convert query objects to native queries
- Handle backend-specific operators
- Optimize query execution

2. Result Mapping
- Map database results to models
- Handle type conversion
- Support nested data

## Best Practices

1. Query Building
- Use type hints
- Validate query parameters
- Handle edge cases
- Support query optimization

2. Query Execution
- Use connection pooling
- Implement result caching
- Handle large result sets
- Monitor query performance

3. Error Handling
- Use custom exceptions
- Provide detailed error messages
- Implement logging
- Handle edge cases

## Contributing

To contribute:

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
