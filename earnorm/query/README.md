# Query Components

Query building and execution components for EarnORM.

## Purpose

The query module provides a fluent interface for building and executing MongoDB queries:
- Query builder with method chaining
- Filter operations
- Sort operations
- Pagination
- Aggregation pipeline
- Query optimization

## Concepts & Examples

### Basic Queries
```python
# Find all users
users = User.find()

# Find by criteria
active_users = User.find().filter(status="active")

# Sort and limit
recent_users = User.find().sort("-created_at").limit(10)

# Pagination
page_users = User.find().skip(20).limit(10)

# Count
total = User.find().filter(age__gte=18).count()
```

### Complex Queries
```python
# Multiple conditions
users = User.find().filter(
    age__gte=18,
    status="active",
    country__in=["US", "UK"]
)

# OR conditions
users = User.find().filter(
    {"$or": [
        {"age__gte": 18},
        {"vip": True}
    ]}
)

# Text search
users = User.find().text_search("john")
```

### Aggregation
```python
# Group by country
result = User.aggregate([
    {"$group": {
        "_id": "$country",
        "count": {"$sum": 1},
        "avg_age": {"$avg": "$age"}
    }}
])

# Complex pipeline
result = User.aggregate([
    {"$match": {"age__gte": 18}},
    {"$group": {"_id": "$country"}},
    {"$sort": {"count": -1}},
    {"$limit": 5}
])
```

## Best Practices

1. **Query Design**
- Use appropriate filters
- Optimize sort operations
- Implement pagination
- Leverage indexes
- Monitor query performance

2. **Query Building**
- Keep queries readable
- Use method chaining
- Handle edge cases
- Validate input data
- Document complex queries

3. **Aggregation**
- Plan pipeline stages
- Optimize memory usage
- Use appropriate operators
- Consider performance
- Test with large datasets

4. **Performance**
- Use indexes effectively
- Limit result sets
- Optimize sort operations
- Monitor query times
- Profile slow queries

## Future Features

1. **Query Builder**
- [ ] Advanced filtering
- [ ] Nested queries
- [ ] Query templates
- [ ] Query caching
- [ ] Query logging

2. **Aggregation**
- [ ] Pipeline builder
- [ ] Stage templates
- [ ] Memory optimization
- [ ] Result caching
- [ ] Pipeline validation

3. **Performance**
- [ ] Query optimization
- [ ] Index suggestions
- [ ] Query profiling
- [ ] Execution stats
- [ ] Performance alerts

4. **Integration**
- [ ] Query hooks
- [ ] Custom operators
- [ ] Query middleware
- [ ] Result transformers
- [ ] Query events 