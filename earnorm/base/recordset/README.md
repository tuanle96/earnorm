# Recordset Module

## Overview
The Recordset module provides a fluent interface for querying and manipulating collections of records in EarnORM. It supports operations like filtering, sorting, pagination, and projection.

## Components

### 1. RecordSet
The core class for managing record collections:

```python
class RecordSet:
    """RecordSet for managing collections of records.
    
    Examples:
        >>> users = await User.search([("age", ">", 18)])
        >>> active_users = users.filter(status="active")
        >>> sorted_users = active_users.sort("name", "asc")
        >>> first_page = await sorted_users.paginate(page=1, per_page=10)
    """
    
    def __init__(self, model: Type[Model], domain: List[Any] = None):
        self.model = model
        self.domain = domain or []
        self._order = []
        self._limit = None
        self._offset = None
        self._fields = None
        
    async def all(self) -> List[Model]:
        """Get all records in the recordset."""
        return await self.model.find(self._build_query())
```

### 2. Query Builder
Builder for constructing MongoDB queries:

```python
class QueryBuilder:
    """Builder for constructing MongoDB queries.
    
    Examples:
        >>> builder = QueryBuilder()
        >>> query = (
        ...     builder
        ...     .filter([("age", ">", 18)])
        ...     .sort("name", "asc")
        ...     .limit(10)
        ...     .build()
        ... )
    """
    
    def filter(self, domain: List[Any]) -> "QueryBuilder":
        """Add filter conditions."""
        self._domain.extend(domain)
        return self
        
    def sort(self, field: str, direction: str = "asc") -> "QueryBuilder":
        """Add sort criteria."""
        self._order.append((field, 1 if direction == "asc" else -1))
        return self
```

### 3. Record Operations
Operations for manipulating records:

```python
class RecordOperations:
    """Operations for manipulating records.
    
    Examples:
        >>> records = await User.search([("age", ">", 18)])
        >>> await records.update({"status": "active"})
        >>> await records.delete()
    """
    
    async def update(self, values: Dict[str, Any]) -> None:
        """Update all records in the set."""
        await self.model.update_many(
            self._build_query(),
            {"$set": values}
        )
        
    async def delete(self) -> None:
        """Delete all records in the set."""
        await self.model.delete_many(self._build_query())
```

## Usage Examples

### 1. Basic Operations
```python
# Search and filter
users = await User.search([("age", ">", 18)])
active_users = users.filter([("status", "=", "active")])

# Sort and paginate
sorted_users = active_users.sort("name", "asc")
page = await sorted_users.paginate(page=1, per_page=10)

# Select specific fields
names_only = await users.select(["name", "email"]).all()
```

### 2. Complex Queries
```python
# Complex filtering
users = await User.search([
    ("age", ">", 18),
    "&",
    [
        ("role", "in", ["admin", "manager"]),
        "|",
        ("status", "=", "active")
    ]
])

# Multiple sort criteria
sorted_users = users.sort([
    ("role", "desc"),
    ("name", "asc")
])

# Aggregation
total_age = await users.sum("age")
avg_age = await users.avg("age")
```

### 3. Batch Operations
```python
# Update multiple records
users = await User.search([("status", "=", "inactive")])
await users.update({"status": "active"})

# Delete multiple records
old_users = await User.search([("last_login", "<", "2023-01-01")])
await old_users.delete()

# Batch create
new_users = await User.create_many([
    {"name": "John", "age": 25},
    {"name": "Jane", "age": 30}
])
```

## Best Practices

1. **Query Optimization**
- Use indexes for frequently queried fields
- Limit result set size
- Select only necessary fields
- Optimize complex queries

2. **Performance**
- Use batch operations when possible
- Avoid N+1 query problem
- Cache common queries
- Monitor query performance

3. **Data Integrity**
- Validate data before updates
- Use transactions when necessary
- Handle edge cases
- Backup data before bulk operations

4. **Code Organization**
- Separate business logic
- Use meaningful names
- Document complex queries
- Maintain test coverage

## Common Issues & Solutions

1. **Memory Management**
```python
class StreamingRecordSet(RecordSet):
    """RecordSet with streaming support."""
    
    async def stream(self, batch_size: int = 100) -> AsyncIterator[Model]:
        """Stream records in batches."""
        offset = 0
        while True:
            batch = await self.limit(batch_size).offset(offset).all()
            if not batch:
                break
            for record in batch:
                yield record
            offset += batch_size
```

2. **Complex Filtering**
```python
class AdvancedQueryBuilder(QueryBuilder):
    """Query builder with advanced filtering."""
    
    def filter_by_date_range(
        self,
        field: str,
        start_date: datetime,
        end_date: datetime
    ) -> "AdvancedQueryBuilder":
        """Filter by date range."""
        self._domain.extend([
            (field, ">=", start_date),
            (field, "<=", end_date)
        ])
        return self
```

3. **Bulk Operations**
```python
class BulkOperations:
    """Handler for bulk operations."""
    
    async def bulk_update(
        self,
        records: List[Model],
        values: Dict[str, Any]
    ) -> None:
        """Update multiple records efficiently."""
        operations = [
            UpdateOne(
                {"_id": record.id},
                {"$set": values}
            )
            for record in records
        ]
        await self.model.bulk_write(operations)
```

## Implementation Details

### 1. Query Execution
```python
class QueryExecutor:
    """Executor for database queries."""
    
    async def execute_find(
        self,
        query: Dict[str, Any],
        options: Dict[str, Any]
    ) -> List[Model]:
        """Execute find query."""
        cursor = self.collection.find(query)
        
        if options.get("sort"):
            cursor = cursor.sort(options["sort"])
            
        if options.get("limit"):
            cursor = cursor.limit(options["limit"])
            
        if options.get("skip"):
            cursor = cursor.skip(options["skip"])
            
        return await cursor.to_list(None)
```

### 2. Result Processing
```python
class ResultProcessor:
    """Processor for query results."""
    
    def process_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Model]:
        """Process raw query results."""
        return [
            self.model(**self._process_record(record))
            for record in results
        ]
        
    def _process_record(
        self,
        record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process individual record."""
        processed = {}
        for key, value in record.items():
            if isinstance(value, ObjectId):
                processed[key] = str(value)
            else:
                processed[key] = value
        return processed
```

## Contributing

1. Follow code style guidelines
2. Add comprehensive tests
3. Document new features
4. Update type hints
5. Benchmark performance impacts 
