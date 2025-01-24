# RecordSet trong Odoo

## 1. Tổng quan

RecordSet là một collection của các records trong Odoo, được implement thông qua BaseModel. Một recordset có các đặc điểm:
- Immutable collection của records
- Có environment context
- Hỗ trợ lazy loading
- Cache aware
- Method delegation

## 2. Implementation

### 2.1 BaseModel Structure

```python
class BaseModel(metaclass=MetaModel):
    """Base class for all Odoo models"""
    
    _name = None
    _table = None
    _sequence = None
    _inherit = None
    _inherits = {}
    
    def __init__(self, pool, cr):
        self.pool = pool      # model registry
        self._cr = cr        # database cursor
        self._ids = []       # record ids
        self._prefetch = {}  # prefetch ids by model
        
    @property
    def ids(self):
        """Return immutable list of record ids"""
        return tuple(self._ids)
```

### 2.2 Record Management

```python
class BaseModel:
    def browse(self, ids=None):
        """Create a recordset for given ids"""
        if ids is None:
            ids = []
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        # Create new recordset with ids
        records = self.new()
        records._ids = ids
        return records
        
    def new(self, values=None):
        """Create a new record without saving to database"""
        records = self.browse([])
        if values:
            records._update_cache(values)
        return records
        
    def create(self, values):
        """Create a new record in database"""
        # Validate values
        self._validate_create(values)
        
        # Create record
        record_id = self._create(values)
        return self.browse(record_id)
```

### 2.3 Recordset Operations

```python
class BaseModel:
    def filtered(self, func):
        """Filter records with function"""
        if isinstance(func, str):
            name = func
            func = lambda rec: any(rec.mapped(name))
        return self.browse([rec.id for rec in self if func(rec)])
        
    def mapped(self, func):
        """Apply function to all records"""
        if isinstance(func, str):
            recs = self
            for name in func.split('.'):
                recs = recs._mapped_field(name)
            return recs
        return [func(rec) for rec in self]
        
    def sorted(self, key=None, reverse=False):
        """Sort records with key function"""
        return self.browse(
            [rec.id for rec in sorted(self, key=key, reverse=reverse)]
        )
```

## 3. Lazy Loading

### 3.1 Field Loading

```python
class BaseModel:
    def __getattr__(self, name):
        """Lazy load field values"""
        field = self._fields.get(name)
        if field:
            # Check cache
            if self.env.cache.contains(self, field):
                return self.env.cache.get(self, field)
                
            # Load from database
            self._read([field.name])
            return self.env.cache.get(self, field)
            
        return super().__getattr__(name)
        
    def _read(self, fields):
        """Read field values from database"""
        # Optimize query for multiple records
        result = self._read_group(fields)
        
        # Update cache
        for record in self:
            for field in fields:
                self.env.cache.set(record, field, result[record.id][field])
```

### 3.2 Prefetching

```python
class BaseModel:
    def _prefetch_field(self, field):
        """Prefetch field for recordset"""
        if field.prefetch and self._ids:
            # Get records to prefetch
            records = self.browse(self._prefetch[self._name])
            
            # Read field values
            records._read([field.name])
            
    def _add_prefetch(self, model, ids):
        """Add records to prefetch set"""
        self._prefetch.setdefault(model, set()).update(ids)
```

## 4. Method Delegation

### 4.1 Basic Implementation

```python
class BaseModel:
    def __getattr__(self, name):
        """Delegate method calls to records"""
        # Check if method exists
        if name in self._methods:
            method = self._methods[name]
            
            # Return bound method
            return partial(method, self)
            
        return super().__getattr__(name)
        
    def ensure_one(self):
        """Ensure recordset contains single record"""
        if len(self) != 1:
            raise ValueError(
                'Expected singleton: %s' % self
            )
        return self
```

### 4.2 Multi-Record Methods

```python
def multi(method):
    """Decorator for methods supporting multiple records"""
    method._multi = True
    return method
    
class BaseModel:
    @multi
    def write(self, values):
        """Update multiple records"""
        for record in self:
            record._write(values)
        return True
        
    def _write(self, values):
        """Update single record"""
        # Update database
        self.env.cr.execute(
            "UPDATE %s SET %s WHERE id=%%s" % (
                self._table,
                ",".join("%s=%%s" % f for f in values),
            ),
            [values[f] for f in values] + [self.id]
        )
```

## 5. Cache Integration

### 5.1 Cache Operations

```python
class BaseModel:
    def _cache_key(self):
        """Get cache key for record"""
        return (self._name, self.id)
        
    def _update_cache(self, values):
        """Update cache with values"""
        for field, value in values.items():
            self.env.cache.set(self, self._fields[field], value)
            
    def invalidate_cache(self, fnames=None):
        """Invalidate cache for fields"""
        self.env.cache.invalidate([
            (self._name, fname, self.ids)
            for fname in (fnames or self._fields)
        ])
```

### 5.2 Cache Prefetching

```python
class BaseModel:
    def _prefetch_cache(self, fields):
        """Prefetch fields into cache"""
        # Get records to prefetch
        records = self.browse(self._prefetch[self._name])
        
        # Read fields in batch
        values = records._read_group(fields)
        
        # Update cache
        for record in records:
            record._update_cache(values[record.id])
```

## 6. Best Practices

### 6.1 Performance
1. Sử dụng prefetching cho related fields
2. Tránh N+1 queries bằng cách dùng prefetch
3. Cache invalidation có chọn lọc

### 6.2 Memory Usage
1. Tránh giữ large recordsets trong memory
2. Clear cache khi không cần thiết
3. Sử dụng iterator cho large datasets

### 6.3 Method Design
1. Sử dụng @api.multi cho multi-record methods
2. Sử dụng @api.model cho static methods
3. Validate recordset size với ensure_one()

## 7. Common Issues & Solutions

### 7.1 Performance Issues
1. **N+1 query problem**
   - Sử dụng prefetch_related
   - Batch load related records
   
2. **Memory leaks**
   - Clear recordset references
   - Implement cache cleanup
   - Use cursor pagination

### 7.2 Concurrency Issues
1. **Cache inconsistency**
   - Implement proper invalidation
   - Use optimistic locking
   - Handle concurrent updates

2. **Deadlocks**
   - Order operations consistently
   - Use shorter transactions
   - Implement retry logic

## 8. RecordSet Creation & Representation

### 8.1 RecordSet Creation Flow

```python
class BaseModel:
    def __new__(cls, *args, **kwargs):
        """Create new recordset instance"""
        # Create new instance
        instance = super(BaseModel, cls).__new__(cls)
        instance._ids = []
        
        # Set recordset type
        instance._RecordSet = type('RecordSet', (), {
            '_name': cls._name,
            '__repr__': lambda self: f"{cls._name}{instance._ids}"
        })
        
        return instance
        
    def __init__(self, pool, cr):
        """Initialize recordset"""
        self.pool = pool
        self._cr = cr
        self._env = None
        
    def browse(self, ids=None):
        """Create recordset from ids"""
        if ids is None:
            ids = []
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        # Create new recordset
        records = self.new()
        records._ids = ids
        
        # Return recordset instance
        return records
```

### 8.2 Custom String Representation

```python
class BaseModel:
    def __str__(self):
        """Custom string representation"""
        # Format: model_name([id1, id2, ...])
        return f"{self._name}{self._ids}"
        
    def __repr__(self):
        """Developer friendly representation"""
        # Format: recordset('model_name', [id1, id2, ...])
        return f"recordset('{self._name}', {self._ids})"
        
    def name_get(self):
        """Get display name for records"""
        return [(record.id, f"{self._description} #{record.id}") 
                for record in self]
```

### 8.3 Search Result Handling

```python
class BaseModel:
    def search(self, domain, *args, **kwargs):
        """Search records matching domain"""
        # Execute search query
        ids = self._search(domain, *args, **kwargs)
        
        # Return recordset instead of raw ids
        return self.browse(ids)
        
    def _search(self, domain, *args, **kwargs):
        """Execute actual search query"""
        query = self._where_calc(domain)
        self._apply_ir_rules(query)
        
        # Get record ids from query
        self._cr.execute(query)
        return [row[0] for row in self._cr.fetchall()]
```

### 8.4 RecordSet Type System

```python
class MetaModel(type):
    """Metaclass for Odoo Models"""
    
    def __new__(meta, name, bases, attrs):
        """Create model class with recordset support"""
        # Create model class
        cls = super().__new__(meta, name, bases, attrs)
        
        # Create recordset class
        recordset_cls = type(f"{name}RecordSet", (), {
            '_name': attrs.get('_name'),
            '__repr__': lambda self: f"{self._name}{self._ids}",
            '__str__': lambda self: f"{self._name}{self._ids}"
        })
        
        # Attach recordset class to model
        cls._RecordSet = recordset_cls
        return cls
```

### 8.5 Examples

```python
# 1. Direct creation
users = env['res.users'].browse([1, 2, 3])
print(users)  # res.users[1, 2, 3]

# 2. Search result
users = env['res.users'].search([('login', '=', 'admin')])
print(users)  # res.users[1]

# 3. Related records
partner = env['res.partner'].browse(1)
users = partner.user_ids
print(users)  # res.users[1, 2]

# 4. Recordset operations
filtered = users.filtered(lambda u: u.login == 'admin')
print(filtered)  # res.users[1]

# 5. Type inspection
users = env['res.users'].browse([1, 2])
print(type(users))  # <class 'res.users'>
print(isinstance(users, BaseModel))  # True
print(users._name)  # 'res.users'
print(users.ids)  # [1, 2]
```

### 8.6 Implementation Details

1. **Model Class Creation**:
- MetaModel tạo model class với recordset support
- Mỗi model có một RecordSet class riêng
- RecordSet class kế thừa các thuộc tính của model

2. **Browse Method**:
- Entry point để tạo recordset
- Chuyển đổi single ID hoặc list IDs thành recordset
- Khởi tạo environment và cache

3. **Search Method**:
- Trả về recordset thay vì raw IDs
- Tự động wrap kết quả trong browse()
- Duy trì environment context

4. **String Representation**:
- Custom __str__ và __repr__ methods
- Format: model_name[ids]
- Developer-friendly debugging output

5. **Type System**:
- Mỗi model là một type riêng biệt
- RecordSet là instance của model type
- Hỗ trợ isinstance() và type() checks

### 8.7 Best Practices

1. **Type Checking**:
```python
# Recommended
if isinstance(record, models.Model):
    # Handle recordset
    
# Not recommended
if type(record).__name__ == 'RecordSet':
    # Brittle type check
```

2. **RecordSet Creation**:
```python
# Recommended
users = env['res.users'].browse([1, 2])

# Not recommended
users = env['res.users']([1, 2])  # Direct instantiation
```

3. **ID Management**:
```python
# Recommended
record_ids = records.ids  # Get immutable tuple
record_id = record.id    # Single record ID

# Not recommended
record_ids = records._ids  # Internal list
``` 

## 9. Internal Mechanisms

### 9.1 _ids Mechanism

```python
class BaseModel:
    def __init__(self, pool, cr):
        """Initialize model instance"""
        self._ids = []        # List of record IDs
        self._prefetch = {}   # Prefetch registry
        
    @property
    def ids(self):
        """Public access to record IDs"""
        # Return immutable tuple to prevent modification
        return tuple(self._ids)
        
    def _update_ids(self, ids):
        """Internal method to update record IDs"""
        if isinstance(ids, (int, long)):
            self._ids = [ids]
        else:
            self._ids = list(ids)
            
    def ensure_one(self):
        """Ensure single record"""
        if len(self._ids) != 1:
            raise ValueError(
                f'Expected singleton: {self._name}[{self._ids}]'
            )
        return self
```

### 9.2 _prefetch_ids Mechanism

```python
class BaseModel:
    def _prefetch_setup(self):
        """Setup prefetch registry"""
        # Initialize prefetch registry
        if not hasattr(self.env, '_prefetch'):
            self.env._prefetch = {
                self._name: set(self._ids)
            }
        else:
            self.env._prefetch.setdefault(
                self._name, set()
            ).update(self._ids)
            
    def _prefetch_field(self, field):
        """Prefetch specific field"""
        if not field.prefetch:
            return
            
        # Get records to prefetch
        ids_to_prefetch = self.env._prefetch[self._name]
        records = self.browse(ids_to_prefetch)
        
        # Prefetch field values
        records.read([field.name])
        
    def _add_prefetch_relations(self, record_ids):
        """Add related records to prefetch set"""
        self.env._prefetch.setdefault(
            self._name, set()
        ).update(record_ids)
        
    def clear_prefetch(self):
        """Clear prefetch registry"""
        if hasattr(self.env, '_prefetch'):
            self.env._prefetch.clear()
```

### 9.3 MetaModel Implementation

```python
class MetaModel(type):
    """Metaclass for Odoo Models
    
    Responsible for:
    1. Model registration
    2. Inheritance processing
    3. Field setup
    4. Method decoration
    """
    
    _modules = {}        # mapping: model_name -> module_name
    _constraints = {}    # mapping: model_name -> constraints
    
    def __new__(meta, name, bases, attrs):
        """Create new model class"""
        # Skip registration for BaseModel
        if not attrs.get('_register', True):
            return super().__new__(meta, name, bases, attrs)
            
        # Setup model name
        name = attrs.get('_name', name)
        if not name:
            raise ValueError("Model must have _name")
            
        # Process inheritance
        inherit = attrs.get('_inherit', [])
        if isinstance(inherit, str):
            inherit = [inherit]
        for parent in inherit:
            # Merge attributes from parent
            parent_cls = meta._modules.get(parent)
            if parent_cls:
                for key, value in parent_cls.__dict__.items():
                    if not key.startswith('__'):
                        attrs.setdefault(key, value)
                        
        # Setup fields
        fields = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                fields[key] = value
                value.setup(key, meta)
        attrs['_fields'] = fields
        
        # Create model class
        cls = super().__new__(meta, name, bases, attrs)
        
        # Register model
        meta._modules[name] = cls
        return cls
        
    def __init__(cls, name, bases, attrs):
        """Initialize model class"""
        super().__init__(name, bases, attrs)
        
        # Setup constraints
        constraints = []
        for key, value in attrs.items():
            if hasattr(value, '_constrains'):
                constraints.append(value)
        cls._constraints = constraints
        
    @property
    def pool(cls):
        """Get model registry"""
        return cls.env.registry
```

### 9.4 Interaction Flow

```python
# 1. Model Definition
class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = ['res.partner']
    
    # MetaModel processes:
    # - Registers model in registry
    # - Sets up inheritance
    # - Processes fields
    # - Decorates methods

# 2. Record Access
users = env['res.users'].search([...])
# - Creates recordset
# - Sets _ids
# - Initializes _prefetch

# 3. Field Access
user = users[0]
partner = user.partner_id
# - Checks _prefetch_ids for partner_id
# - Prefetches related partner records
# - Updates cache
```

### 9.5 Key Points

1. **_ids Management**:
- Internal mutable list of record IDs
- Public immutable access via `ids` property
- Used for recordset operations
- Maintained during recordset transformations

2. **_prefetch_ids Mechanism**:
- Stored in environment to share across recordsets
- Grouped by model name
- Updated during record access
- Used for optimizing related record loading

3. **MetaModel Role**:
- Model registration and inheritance
- Field setup and validation
- Method decoration and API setup
- Constraint management
- Registry integration

### 9.6 Best Practices

1. **_ids Usage**:
```python
# Recommended
records.ids          # Public access
record.id           # Single record

# Not recommended
records._ids        # Internal list
len(records._ids)   # Use len(records)
```

2. **Prefetch Management**:
```python
# Recommended
records.read(['field1', 'field2'])  # Batch read
records.mapped('field')             # Automatic prefetch

# Not recommended
for record in records:              # N+1 queries
    record.field
```

3. **Model Definition**:
```python
# Recommended
class Model(models.Model):
    _name = 'model.name'
    _description = 'Model Description'
    
# Not recommended
class Model(models.Model):
    # Missing _name
    # Missing _description
``` 

## 10. Browse Mechanism

### 10.1 _browse Implementation

```python
class BaseModel:
    def _browse(self, env, ids):
        """Core method to create recordset
        
        Args:
            env: Environment instance
            ids: List of record IDs
            
        Returns:
            New recordset instance with given IDs
        """
        # Create new instance
        records = type(self).new(env)
        records._ids = ids
        
        # Setup prefetch
        if ids and env.prefetch:
            env.prefetch.setdefault(self._name, set()).update(ids)
            records._prefetch = env.prefetch
            
        return records
        
    def browse(self, ids=None):
        """Public interface for browsing records
        
        Args:
            ids: Single ID or list of IDs
            
        Returns:
            Recordset containing specified records
        """
        if ids is None:
            ids = []
        elif isinstance(ids, (int, long)):
            ids = [ids]
            
        # Create recordset via _browse
        return self._browse(self.env, ids)
        
    def new(self, values=None, ref=None):
        """Create new record without saving
        
        Args:
            values: Field values for new record
            ref: Reference key for cache
            
        Returns:
            New recordset instance
        """
        # Create empty recordset
        records = self._browse(self.env, [])
        
        if values:
            # Update cache with values
            records._update_cache(values, validate=False)
            
        if ref:
            # Add reference for prefetch
            records._prefetch_ref = ref
            
        return records
```

### 10.2 Browse Flow Analysis

1. **Entry Points**:
```python
# Direct browse
records = env['res.partner'].browse([1, 2, 3])

# Search result
records = env['res.partner'].search([...])  # Internally uses _browse

# Related records
user = env['res.users'].browse(1)
partner = user.partner_id  # Uses _browse for related record
```

2. **Internal Flow**:
```python
def _browse(self, env, ids):
    # 1. Create new instance
    records = type(self).new(env)
    
    # 2. Set record IDs
    records._ids = ids
    
    # 3. Setup prefetch if needed
    if ids and env.prefetch:
        # Add IDs to prefetch set
        env.prefetch[self._name].update(ids)
        # Link prefetch to recordset
        records._prefetch = env.prefetch
        
    return records
```

### 10.3 Key Components

1. **Instance Creation**:
- Tạo instance mới của model class
- Khởi tạo với environment
- Thiết lập các thuộc tính cơ bản

2. **ID Management**:
- Gán IDs cho recordset
- Chuyển đổi single ID thành list
- Validate ID format

3. **Prefetch Setup**:
- Thêm IDs vào prefetch set
- Link prefetch registry với recordset
- Enable prefetching cho related fields

### 10.4 Environment Integration

```python
class BaseModel:
    def with_env(self, env):
        """Switch environment of recordset"""
        # Create new recordset with new environment
        return self._browse(env, self._ids)
        
    def sudo(self, user=SUPERUSER_ID):
        """Switch user of recordset"""
        # Create new environment with new user
        env = self.env(user=user)
        # Create new recordset with new environment
        return self._browse(env, self._ids)
        
    def with_context(self, **overrides):
        """Switch context of recordset"""
        # Create new environment with updated context
        env = self.env(context=dict(self.env.context, **overrides))
        # Create new recordset with new environment
        return self._browse(env, self._ids)
```

### 10.5 Cache Integration

```python
class BaseModel:
    def _browse(self, env, ids):
        records = type(self).new(env)
        records._ids = ids
        
        # Setup cache for new recordset
        if ids:
            # Check existing cache
            for field in self._fields.values():
                # Get cached values
                values = env.cache.get_values(records, field)
                if values:
                    # Update cache for new recordset
                    env.cache.set_values(records, field, values)
                    
        return records
```

### 10.6 Best Practices

1. **Direct Usage**:
```python
# Recommended
records = model.browse([1, 2, 3])
record = model.browse(1)

# Not recommended
records = model._browse(env, [1, 2, 3])  # Internal method
```

2. **Environment Handling**:
```python
# Recommended
new_records = records.with_env(new_env)
sudo_records = records.sudo()

# Not recommended
new_records = records._browse(new_env, records._ids)
```

3. **Cache Management**:
```python
# Recommended
records.invalidate_cache()
records.modified(['field1', 'field2'])

# Not recommended
records.env.cache.invalidate()  # Too broad
```

### 10.7 Common Pitfalls

1. **Cache Inconsistency**:
```python
# Wrong: Creates independent cache
new_records = model._browse(env, records._ids)

# Correct: Maintains cache consistency
new_records = records.with_env(env)
```

2. **Prefetch Breaking**:
```python
# Wrong: Breaks prefetch chain
records = [model._browse(env, [id]) for id in ids]

# Correct: Maintains prefetch
records = model.browse(ids)
```

3. **Environment Isolation**:
```python
# Wrong: Mixes environments
records = model._browse(env1, ids)
records.env = env2  # Never modify env directly

# Correct: Creates new recordset
records = records.with_env(env2)
``` 
