# Core ORM Mechanisms

## Overview
Phân tích chi tiết về các cơ chế cốt lõi của ORM bao gồm Base Model, Meta Model, RecordSet, Prefetching và Environment.

## 1. Meta Model

### Concept
MetaModel là một metaclass đặc biệt được sử dụng để đăng ký và xây dựng các model classes trong ORM.

```python
class MetaModel(type):
    """Metaclass for Odoo Models"""
    
    def __new__(meta, name, bases, attrs):
        """Create and register new model class"""
        # Create new class
        cls = super(MetaModel, meta).__new__(meta, name, bases, attrs)
        
        # Skip registration for abstract models
        if attrs.get('_register', True) is False:
            return cls
            
        # Register model in registry
        registry = Registry.get_instance()
        registry.add_model(cls._name, cls)
        
        return cls
```

### Features
1. **Model Registration**: Tự động đăng ký model vào registry
2. **Inheritance Handling**: Xử lý kế thừa giữa các models
3. **Attribute Processing**: Xử lý các thuộc tính đặc biệt như _name, _inherit
4. **Field Setup**: Thiết lập các fields và dependencies

## 2. Base Model

### Architecture
```python
class BaseModel(metaclass=MetaModel):
    _name = None
    _table = None
    _sequence = None
    _inherit = None
    _inherits = {}
    
    def __init__(self, pool, cr):
        self.pool = pool
        self._cr = cr
        self._context = {}
        self._ids = []
        self._prefetch_ids = set()
```

### Core Components
1. **Model Properties**
   - `_name`: Technical name của model
   - `_table`: Database table name
   - `_inherit`: Parent models để kế thừa
   - `_inherits`: Dictionary của delegated inheritance

2. **Instance Attributes**
   - `pool`: Registry instance
   - `_cr`: Database cursor
   - `_context`: Execution context
   - `_ids`: List of record IDs
   - `_prefetch_ids`: Set of IDs to prefetch

## 3. RecordSet

### Structure
```python
class RecordSet:
    """Collection of records of a Model"""
    
    def __init__(self, model, ids, prefetch_ids=None):
        self._model = model
        self._ids = ids
        self._prefetch_ids = prefetch_ids or set(ids)
        self._cache = {}
```

### Key Features
1. **Record Management**
   - Quản lý collection của records
   - Lazy loading của records
   - Caching của field values

2. **Method Delegation**
   - Chuyển các method calls tới model class
   - Xử lý recordset operations

3. **Iteration Support**
   - Hỗ trợ Python iteration protocol
   - Lazy fetching khi iterate

## 4. Prefetching Mechanism

### Implementation
```python
class PrefetchManager:
    """Manage prefetching of records"""
    
    def __init__(self, model):
        self.model = model
        self.to_fetch = set()
        self.fetched = set()
        self.fields = set()
    
    def prefetch_records(self, records, fields):
        """Prefetch records for specified fields"""
        # Calculate records to fetch
        to_fetch = records._prefetch_ids - self.fetched
        if not to_fetch:
            return
            
        # Fetch records in batch
        records = self.model.browse(to_fetch)
        values = records.read(fields)
        
        # Update cache
        for value in values:
            record_id = value['id']
            for field in fields:
                self.model.env.cache.set(
                    self.model._fields[field],
                    record_id,
                    value[field]
                )
```

### Process Flow
1. **Initialization**
   - Set up prefetch sets khi tạo recordset
   - Track fields cần prefetch

2. **Batch Loading**
   - Load nhiều records cùng lúc
   - Optimize database queries
   - Cache kết quả

3. **Cache Management**
   - Store prefetched values trong cache
   - Invalidate cache khi cần
   - Handle cache dependencies

## 5. Environment

### Structure
```python
class Environment:
    """Execution environment"""
    
    def __init__(self, cr, uid, context):
        self.cr = cr
        self.uid = uid
        self.context = context
        self.registry = Registry(cr.dbname)
        self.cache = Cache()
        self.protected = set()
        
    def __getitem__(self, model_name):
        """Get model by name"""
        return self.registry[model_name]
```

### Components
1. **Database Access**
   - Cursor management
   - Transaction control
   - Query execution

2. **Context Management**
   - User context
   - Language
   - Timezone
   - Company

3. **Cache Control**
   - Record cache
   - Field cache
   - Prefetch cache

## Interaction Flow

### 1. Model Creation
```python
# MetaModel creates model class
class Partner(models.Model):
    _name = 'res.partner'
    
    # Fields are processed by MetaModel
    name = fields.Char()
    
# Model is registered in registry
registry['res.partner'] = Partner
```

### 2. Record Access
```python
# Create recordset
partners = env['res.partner'].browse([1, 2, 3])

# Prefetching is triggered
partners._prefetch_ids.update([1, 2, 3])

# Access triggers cache/prefetch
for partner in partners:
    print(partner.name)  # Uses cache if available
```

### 3. Field Operations
```python
# Write operation
partner.write({'name': 'New Name'})
# 1. Updates database
# 2. Invalidates cache
# 3. Updates recordset cache

# Read operation
partner.name
# 1. Checks cache
# 2. Fetches from database if needed
# 3. Updates cache
```

## Best Practices

### 1. Prefetching
- Use `prefetch_related` for related fields
- Group similar operations
- Monitor prefetch size

### 2. Caching
- Clear cache when needed
- Use appropriate cache invalidation
- Monitor cache size

### 3. Environment
- Use context managers
- Handle transactions properly
- Clean up resources

## Common Issues & Solutions

### 1. Memory Management
```python
# Control prefetch size
def process_partners(self):
    partners = self.search([])
    for batch in partners.split_every(1000):
        batch.invalidate_cache()
        batch.prefetch_related('company_id')
```

### 2. Performance Optimization
```python
# Optimize reads
def get_partners(self):
    return self.search([]).prefetch_related(
        'company_id',
        'category_id',
        'bank_ids'
    )
```

### 3. Cache Consistency
```python
# Handle cache invalidation
@api.model
def complex_write(self, vals):
    self.clear_caches()
    return super().write(vals)
``` 