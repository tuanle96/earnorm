# Domain Module

## Overview
The Domain module provides a powerful expression language for building complex queries in EarnORM. It supports logical operators, comparison operators, and complex query building through a fluent interface.

## Components

### 1. Domain Expression
The core class for representing domain expressions:

```python
class DomainExpression:
    """Domain expression for building complex queries.
    
    Examples:
        >>> expr = DomainExpression([["age", ">", 18], DomainOperator.AND, ["active", "=", True]])
        >>> expr.to_list()
        [["age", ">", 18], "AND", ["active", "=", True]]
    """
    
    def and_(self, other: Union["DomainExpression", List[Any]]) -> "DomainExpression":
        """Combine with AND operator."""
        return DomainExpression(self._domain + [DomainOperator.AND] + other)
        
    def or_(self, other: Union["DomainExpression", List[Any]]) -> "DomainExpression":
        """Combine with OR operator."""
        return DomainExpression(self._domain + [DomainOperator.OR] + other)
        
    def not_(self) -> "DomainExpression":
        """Negate expression."""
        return DomainExpression([DomainOperator.NOT] + self._domain)
```

### 2. Domain Builder
Fluent interface for building domain expressions:

```python
class DomainBuilder:
    """Domain builder for constructing domain expressions.
    
    Examples:
        >>> builder = DomainBuilder()
        >>> domain = (
        ...     builder
        ...     .field("age").greater_than(18)
        ...     .and_()
        ...     .field("active").equals(True)
        ...     .build()
        ... )
    """
    
    def field(self, name: str) -> "DomainBuilder":
        """Set current field."""
        self._current_field = name
        return self
        
    def equals(self, value: Any) -> "DomainBuilder":
        """Add equals condition."""
        self._domain.append([self._current_field, "=", value])
        return self
```

### 3. Domain Parser
Converts domain expressions to MongoDB queries:

```python
class DomainParser:
    """Domain parser for converting domain expressions to MongoDB queries.
    
    Examples:
        >>> parser = DomainParser()
        >>> parser.parse(expr)
        {'$and': [{'age': {'$gt': 18}}, {'active': True}]}
    """
    
    def parse(self, expression: DomainExpression) -> MongoQuery:
        """Parse domain expression to MongoDB query."""
        domain = expression.to_list()
        return self._parse_domain(domain)
```

## Usage Examples

### 1. Basic Queries
```python
# Using domain builder
builder = DomainBuilder()
domain = (
    builder
    .field("age").greater_than(18)
    .and_()
    .field("status").equals("active")
    .build()
)

# Using domain expression
expr = DomainExpression([
    ["age", ">", 18],
    DomainOperator.AND,
    ["status", "=", "active"]
])
```

### 2. Complex Queries
```python
# Complex condition
domain = (
    builder
    .field("age").greater_than(18)
    .and_()
    .open_group()
        .field("role").in_(["admin", "manager"])
        .or_()
        .field("permissions").contains("super_user")
    .close_group()
    .build()
)

# With NOT operator
domain = (
    builder
    .not_()
    .open_group()
        .field("status").equals("deleted")
        .or_()
        .field("active").equals(False)
    .close_group()
    .build()
)
```

### 3. MongoDB Integration
```python
# Parse domain to MongoDB query
parser = DomainParser()
query = parser.parse(domain)

# Use in model
users = await User.search(query)
```

## Best Practices

1. **Query Building**
- Use builder pattern for complex queries
- Break down complex conditions
- Validate field names
- Handle edge cases

2. **Performance**
- Use appropriate indexes
- Optimize complex queries
- Monitor query performance
- Cache common queries

3. **Type Safety**
- Validate field types
- Check operator compatibility
- Handle None values
- Use type hints

4. **Error Handling**
- Validate domain expressions
- Handle parsing errors
- Provide clear error messages
- Log parsing failures

## Common Issues & Solutions

1. **Complex Conditions**
```python
# Break down complex conditions
domain = (
    builder
    .open_group()
        .field("status").equals("active")
        .and_()
        .field("role").equals("admin")
    .close_group()
    .or_()
    .open_group()
        .field("permissions").contains("super_user")
        .and_()
        .field("active").equals(True)
    .close_group()
    .build()
)
```

2. **Type Conversion**
```python
# Handle special types
class CustomDomainParser(DomainParser):
    def _convert_value(self, value: Any) -> Any:
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return value
```

3. **Query Optimization**
```python
# Use indexes for common queries
class User(Model):
    _indexes = [
        {"status": 1, "role": 1},
        {"permissions": 1},
        {"age": -1, "active": 1}
    ]
```

## Implementation Details

### 1. Domain Operators
```python
class DomainOperator(Enum):
    """Domain operators enum."""
    AND = auto()
    OR = auto()
    NOT = auto()
```

### 2. Query Building
```python
def _build_comparison(field: str, op: str, value: Any) -> Dict[str, Any]:
    """Build comparison expression."""
    if op == "=":
        return {field: value}
    if op == "in":
        return {field: {"$in": value}}
    return {field: {self._operator_map[op]: value}}
```

## Contributing

1. Follow code style guidelines
2. Add comprehensive tests
3. Document new features
4. Update type hints
5. Benchmark performance impacts 
