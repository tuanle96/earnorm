# Query System

## Overview
The Query System provides a powerful and flexible way to build, optimize, and execute database queries with support for complex search domains, sorting, and pagination.

## Components

### 1. Query Builder
```python
class Query:
    def __init__(self, model):
        self.model = model
        self.tables = []  # FROM tables
        self.where_clause = []  # WHERE conditions
        self.where_params = []  # WHERE parameters
        self.joins = []  # JOIN clauses
        self.order = None  # ORDER BY
        self.limit = None  # LIMIT
        self.offset = None  # OFFSET
```

### 2. Domain Builder
```python
class Domain:
    def __init__(self, domain):
        self.domain = domain or []
        
    def normalize(self):
        """Normalize domain operators"""
        return normalize_domain(self.domain)
        
    def combine(self, operator, other):
        """Combine with another domain"""
        return Domain(['&' if operator == 'AND' else '|'] + self.domain + other.domain)
```

### 3. Expression Builder
```python
class Expression:
    def __init__(self, model):
        self.model = model
        self._tables = {}  # Joined tables
        self._joins = []  # JOIN expressions
```

## Features

### 1. Query Building
- Table selection
- Join handling
- Where conditions
- Order by clauses
- Limit and offset

### 2. Domain Operations
- Leaf conditions
- Logical operators
- Domain normalization
- Domain combination

### 3. Search Optimization
- Index usage
- Join optimization
- Query planning
- Result caching

## Implementation Details

### 1. Query Construction
```python
def _where_calc(self, domain):
    """Build WHERE clause from domain"""
    # Create query
    query = Query(self.model)
    
    # Add domain conditions
    for leaf in domain:
        field, operator, value = leaf
        query.add_where(field, operator, value)
        
    return query

def add_where(self, field, operator, value):
    """Add WHERE condition"""
    if field in self.model._fields:
        column = self.model._fields[field].column
        where, params = column.generate_where(operator, value)
        self.where_clause.append(where)
        self.where_params.extend(params)
```

### 2. Domain Processing
```python
def normalize_domain(domain):
    """Normalize domain expression"""
    if not domain:
        return []
        
    # Handle implicit '&' operators
    result = []
    for leaf in domain:
        if is_leaf(leaf):
            result.extend(['&', leaf])
        else:
            result.append(leaf)
            
    return result[1:]  # Remove first '&'
```

### 3. Query Execution
```python
def _search(self, query, offset=0, limit=None, order=None):
    """Execute search query"""
    # Build query
    query_str, params = query.select()
    
    # Add order, limit, offset
    if order:
        query_str += ' ORDER BY ' + order
    if limit:
        query_str += ' LIMIT %s'
        params.append(limit)
    if offset:
        query_str += ' OFFSET %s'
        params.append(offset)
        
    # Execute
    self.env.cr.execute(query_str, params)
    return [row[0] for row in self.env.cr.fetchall()]
```

## Usage Examples

### 1. Basic Search
```python
# Simple domain search
partners = env['res.partner'].search([
    ('name', 'like', 'Test'),
    ('active', '=', True)
])

# Search with order and limit
products = env['product.product'].search(
    [('type', '=', 'product')],
    order='name ASC',
    limit=10
)
```

### 2. Complex Domains
```python
# Combined conditions
domain = [
    '|',
    ('state', '=', 'draft'),
    '&',
    ('state', '=', 'open'),
    ('amount', '>', 1000.0)
]

# Search with domain
invoices = env['account.invoice'].search(domain)
```

### 3. Custom Queries
```python
# Raw SQL query
env.cr.execute("""
    SELECT p.id, p.name
    FROM res_partner p
    JOIN sale_order s ON s.partner_id = p.id
    WHERE s.state = 'done'
    GROUP BY p.id, p.name
    HAVING COUNT(s.id) > 5
""")

# Process results
partners = env['res.partner'].browse([r[0] for r in env.cr.fetchall()])
```

## Best Practices

1. **Query Building**
- Use appropriate operators
- Consider index usage
- Optimize joins
- Handle parameters safely

2. **Domain Construction**
- Keep domains simple
- Use proper operators
- Normalize domains
- Document complex domains

3. **Performance**
- Use indexes wisely
- Limit result sets
- Cache when appropriate
- Monitor query plans

## Common Issues & Solutions

1. **Performance Issues**
```python
# Optimize search with index
class Partner(models.Model):
    _name = 'res.partner'
    
    email = fields.Char(index=True)
    
    def _search_by_email(self, operator, value):
        return [('email', operator, value)]
```

2. **Complex Queries**
```python
# Break down complex queries
def search_partners(self, criteria):
    domain = []
    if criteria.get('customer'):
        domain.append(('customer_rank', '>', 0))
    if criteria.get('supplier'):
        domain.append(('supplier_rank', '>', 0))
    return self.search(domain)
```

3. **Join Optimization**
```python
# Optimize joins with prefetching
def get_orders(self):
    return self.env['sale.order'].search([
        ('partner_id', 'in', self.ids)
    ])._prefetch_field('order_line')
``` 