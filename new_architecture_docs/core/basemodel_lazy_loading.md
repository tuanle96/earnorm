# BaseModel Lazy Loading

## Overview
Odoo implement lazy loading trực tiếp trong BaseModel thay vì tạo một RecordSet class riêng. Điều này cho phép truy cập trực tiếp các fields và methods của model.

## 1. Core Implementation

### BaseModel Structure
```python
class BaseModel(metaclass=MetaModel):
    """Base class for all models"""
    
    def __init__(self, env, ids, prefetch_ids=None):
        self.env = env
        self._ids = ids
        self._prefetch_ids = prefetch_ids or set(ids)
        
    def __getattr__(self, name):
        """Lazy loading through attribute access"""
        field = self._fields.get(name)
        if field:
            # Check cache first
            if self.env.cache.contains(field, self._ids):
                return self.env.cache.get(field, self._ids)
            # Load from database
            self._load_field(field)
            return self.env.cache.get(field, self._ids)
        raise AttributeError(f"Field {name} does not exist")
```

### Browse Method
```python
@classmethod
def browse(cls, env, ids):
    """Create model instance for given ids"""
    if not ids:
        ids = ()
    elif isinstance(ids, int):
        ids = (ids,)
        
    # Return new instance of the same class
    return cls(env, ids)
```

## 2. Loading Mechanisms

### Field Loading
```python
def _load_field(self, field):
    """Load field values from database"""
    # Check if already loaded
    if self.env.cache.contains(field, self._ids):
        return
        
    # Determine fields to load (include dependencies)
    to_load = self._get_load_fields(field)
    
    # Load from database
    self._read(to_load)

def _read(self, fields):
    """Read field values from database"""
    # Build SQL query
    query = self._build_read_query(fields)
    self.env.cr.execute(query)
    
    # Process results and update cache
    for row in self.env.cr.dictfetchall():
        for field in fields:
            self.env.cache.set(field, row['id'], row[field.name])
```

### Prefetch Management
```python
def _prefetch_field(self, field):
    """Setup prefetching for field"""
    if field.prefetch and self._prefetch_ids:
        # Add to prefetch queue
        self.env.add_to_prefetch(self._name, self._prefetch_ids)
        
        # Setup related fields prefetch
        if field.relational:
            self._prefetch_related(field)

def _prefetch_related(self, field):
    """Setup prefetching for related fields"""
    comodel = self.env[field.comodel_name]
    
    # Get related record ids
    related_ids = set()
    for record_id in self._prefetch_ids:
        value = self.env.cache.get(field, record_id)
        if value:
            related_ids.update(value if isinstance(value, tuple) else [value])
    
    # Add to prefetch queue
    if related_ids:
        comodel.browse(related_ids)._prefetch_field(field)
```

## 3. Cache Integration

### Cache Management
```python
def _cache_field(self, field):
    """Manage field caching"""
    
    def compute_value(record_id):
        """Compute value for record"""
        if field.compute:
            # Handle computed fields
            record = self.browse(record_id)
            field.compute(record)
        else:
            # Load from database
            self._read([field])
    
    # Process records
    for record_id in self._ids:
        if not self.env.cache.contains(field, record_id):
            compute_value(record_id)
```

### Cache Invalidation
```python
def _invalidate_cache(self, fnames=None):
    """Invalidate cache for specified fields"""
    if fnames is None:
        # Invalidate all fields
        return self.env.cache.invalidate([(f, self._ids) for f in self._fields.values()])
        
    # Invalidate specific fields
    fields = [self._fields[fname] for fname in fnames]
    self.env.cache.invalidate([(f, self._ids) for f in fields])
```

## 4. Performance Optimizations

### Batch Loading
```python
def _read_batch(self, fields, records):
    """Load multiple records in batch"""
    result = []
    
    # Split records into batches
    for sub_ids in split_every(1000, records._ids):
        # Read batch from database
        query = self._build_read_query(fields, sub_ids)
        self.env.cr.execute(query)
        result.extend(self.env.cr.dictfetchall())
        
    return result
```

### Smart Prefetching
```python
def _setup_prefetch(self, field):
    """Setup smart prefetching"""
    # Add commonly accessed fields
    if field.relational:
        common_fields = self._get_common_fields(field.comodel_name)
        self.env.add_to_prefetch(field.comodel_name, common_fields)
        
    # Add dependent fields
    for dependent in field.depends:
        self._prefetch_field(self._fields[dependent])
```

## 5. Usage Examples

### Basic Record Access
```python
# Creates BaseModel instance
partner = env['res.partner'].browse(1)

# Triggers lazy loading of name field
name = partner.name

# Subsequent access uses cached value
name_again = partner.name  # Uses cache
```

### Batch Processing
```python
# Creates single BaseModel instance for multiple records
partners = env['res.partner'].browse([1, 2, 3])

# Loads all names in one query
for partner in partners:
    print(partner.name)
```

### Related Fields
```python
# Loads order and related customer efficiently
order = env['sale.order'].browse(1)
customer_name = order.partner_id.name  # Uses prefetching
```

### Computed Fields
```python
class Product(models.Model):
    _name = 'product.product'
    
    list_price = fields.Float()
    discount = fields.Float()
    
    @api.depends('list_price', 'discount')
    def _compute_final_price(self):
        for record in self:
            # Computed on first access
            record.final_price = record.list_price * (1 - record.discount)
``` 