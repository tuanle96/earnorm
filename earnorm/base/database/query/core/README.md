# Core Query Implementation

This directory contains the core query building functionality for EarnORM.

## Overview

The core module provides:

1. Base Query Builder
2. Operation System
3. Query Execution

### Base Query Builder

The base query builder (`query.py`) implements:

```python
from earnorm.base.database.query import Query
from earnorm.types import DatabaseModel

# Create query
query = Query(User)

# Add filters
query.filter(age__gt=18, status="active")

# Add sorting
query.order_by("-created_at", "name")

# Set pagination
query.limit(10).offset(20)

# Execute query
results = await query.all()
```

### Operation System

The operation system (`operations/`) supports:

1. Basic Operations
- Filtering
- Sorting
- Pagination
- Field selection

2. Aggregate Operations
- Group by
- Aggregation functions
- Having clauses
- Pipeline stages

3. Join Operations
- Inner/outer joins
- Multiple conditions
- Field selection
- Cross-database joins

4. Window Operations
- Ranking functions
- Aggregate functions
- Frame specifications
- Partitioning

## Directory Structure

```
core/
├── __init__.py         # Package exports
├── query.py           # Base query implementation
└── operations/        # Operation implementations
    ├── __init__.py    # Operation exports
    ├── base.py       # Base operation class
    ├── aggregate.py  # Aggregate operations
    ├── join.py      # Join operations
    └── window.py    # Window operations
```

## Features

1. Query Building
- Fluent interface
- Type safety
- Method chaining
- Result validation

2. Operation Support
- Operation composition
- Result processing
- Custom operations
- Pipeline building

3. Query Execution
- Async execution
- Result mapping
- Error handling
- Performance optimization

## Usage Examples

### Basic Query
```python
# Filter and sort
users = await Query(User).filter(
    age__gt=18,
    status="active"
).order_by(
    "-created_at"
).all()

# Select fields
users = await Query(User).select(
    "id", "name", "email"
).all()
```

### Aggregate Query
```python
# Group by with aggregates
stats = await Query(Order).aggregate().group_by(
    "status"
).count(
    "total"
).sum(
    "amount", "total_amount"
).execute()
```

### Join Query
```python
# Join with conditions
results = await Query(User).join(
    Post
).on(
    User.id == Post.user_id
).select(
    "name", "posts.title"
).execute()
```

### Window Query
```python
# Ranking by department
ranked = await Query(Employee).window().over(
    partition_by=["department"],
    order_by=["-salary"]
).row_number(
    "rank"
).execute()
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
