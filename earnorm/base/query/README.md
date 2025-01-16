# Query Module

## Overview
The Query module provides tools for building and executing MongoDB queries in EarnORM.

## Components

### 1. Query Parser (`parser.py`)
- Parse and validate query parameters
- Convert query parameters to MongoDB format
- Normalize query values

```python
from earnorm.base.query import QueryParser

parser = QueryParser()
query = parser.parse({
    "filter": {"age": 18},
    "sort": [("created_at", -1)],
    "limit": 10,
    "offset": 0
})
```

### 2. Query Builder (`builder.py`)
- Fluent interface for building queries
- Method chaining
- Query validation

```python
from earnorm.base.query import QueryBuilder

query = (QueryBuilder()
    .filter(age=18)
    .sort("created_at", -1)
    .limit(10)
    .offset(0))
```

### 3. Query Executor (`executor.py`)
- Execute queries against MongoDB
- Handle results
- Error handling

```python
from earnorm.base.query import QueryExecutor

executor = QueryExecutor(collection)
results = await executor.execute(query)
```

### 4. Query Result (`result.py`)
- Query result wrapper
- Result iteration
- Result transformation

## Query Components

### 1. Filter Operations
```python
# Equality
query.filter(age=18)

# Comparison
query.filter(age__gt=18)
query.filter(age__lt=30)
query.filter(age__in=[18, 19, 20])

# Logical
query.filter(age__gt=18, status="active")  # AND
query.filter(Q(age__gt=18) | Q(status="premium"))  # OR
```

### 2. Sort Operations
```python
# Single field ascending
query.sort("created_at")

# Single field descending
query.sort("created_at", -1)

# Multiple fields
query.sort("priority", -1).sort("created_at", 1)
```

### 3. Pagination
```python
# Limit results
query.limit(10)

# Skip results
query.offset(20)

# Both
query.limit(10).offset(20)  # Page 3
```

### 4. Projection
```python
# Include fields
query.project(name=1, email=1)

# Exclude fields
query.project(_id=0, password=0)

# Computed fields
query.project(full_name={"$concat": ["$first_name", " ", "$last_name"]})
```

## Best Practices

1. **Query Building**
- Use method chaining
- Validate input data
- Handle edge cases

2. **Performance**
- Use appropriate indexes
- Limit result size
- Project only needed fields

3. **Security**
- Validate user input
- Escape special characters
- Use parameterized queries

4. **Error Handling**
- Handle MongoDB errors
- Validate query parameters
- Return meaningful errors

## Common Issues & Solutions

1. **Performance**
- Index fields used in queries
- Limit result size
- Use projection

2. **Memory Usage**
- Stream large results
- Paginate results
- Clean up resources

3. **Type Safety**
- Validate input types
- Handle None values
- Use type hints

## Contributing

1. Add docstrings for all classes and methods
2. Implement unit tests
3. Follow type hints
4. Update documentation 
