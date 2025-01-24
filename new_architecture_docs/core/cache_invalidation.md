# Cache Invalidation Mechanism

## Overview
Cache invalidation là một cơ chế quan trọng trong ORM để đảm bảo tính nhất quán của dữ liệu. Cơ chế này xử lý việc xóa hoặc cập nhật cache khi dữ liệu thay đổi.

## Components

### 1. Cache Entry
```python
class CacheEntry:
    """Represents a cached value with metadata"""
    def __init__(self, value, timestamp):
        self.value = value
        self.timestamp = timestamp
        self.dirty = False
        self.dependencies = set()  # Related fields/records that affect this entry
```

### 2. Cache Manager
```python
class CacheManager:
    """Manages cache operations and invalidation"""
    def __init__(self):
        self._data = {}  # {field: {record_id: CacheEntry}}
        self._invalidation_queue = []
        self._dependencies = {}  # {field: set(dependent_fields)}
```

### 3. Dependency Tracker
```python
class DependencyTracker:
    """Tracks field dependencies for invalidation"""
    def __init__(self):
        self.field_dependencies = {}  # {field: set(dependent_fields)}
        self.computed_fields = {}  # {field: set(computed_fields)}
        self.related_fields = {}  # {field: set(related_fields)}
```

## Invalidation Types

### 1. Direct Invalidation
```python
def invalidate_direct(self, field, record_ids=None):
    """Invalidate specific field values"""
    if field not in self._data:
        return
        
    if record_ids is None:
        # Invalidate all records for this field
        del self._data[field]
    else:
        # Invalidate specific records
        field_cache = self._data[field]
        for record_id in record_ids:
            field_cache.pop(record_id, None)
```

### 2. Dependency-based Invalidation
```python
def invalidate_dependencies(self, field, record_ids):
    """Invalidate dependent fields"""
    dependencies = self._dependencies.get(field, set())
    for dependent_field in dependencies:
        self.invalidate_direct(dependent_field, record_ids)
        # Recursive invalidation for nested dependencies
        self.invalidate_dependencies(dependent_field, record_ids)
```

### 3. Computed Field Invalidation
```python
def invalidate_computed(self, field, record_ids):
    """Invalidate computed fields"""
    # Get all computed fields that depend on this field
    computed = self.computed_fields.get(field, set())
    for computed_field in computed:
        self.invalidate_direct(computed_field, record_ids)
        # Also invalidate fields that depend on computed fields
        self.invalidate_dependencies(computed_field, record_ids)
```

## Implementation Details

### 1. Write Operation Flow
```python
def write(self, vals):
    """Handle cache invalidation during write"""
    # Track modified fields
    modified_fields = set(vals.keys())
    
    # Perform write operation
    result = super().write(vals)
    
    # Invalidate cache for modified fields
    for field in modified_fields:
        self.env.cache.invalidate_direct(field, self.ids)
        self.env.cache.invalidate_dependencies(field, self.ids)
    
    return result
```

### 2. Computed Fields
```python
@api.depends('field1', 'field2')
def _compute_total(self):
    """Example of computed field with dependencies"""
    for record in self:
        # Computing triggers cache update
        record.total = record.field1 + record.field2
        
    # Dependencies are tracked through @api.depends
    # When field1 or field2 changes, total will be invalidated
```

### 3. Related Fields
```python
class Partner(models.Model):
    _name = 'res.partner'
    
    company_name = fields.Char(
        related='company_id.name',
        store=True
    )
    
    # When company_id.name changes:
    # 1. Invalidate company_name cache
    # 2. Recompute if stored
    # 3. Update cache with new value
```

## Cache Invalidation Strategies

### 1. Immediate Invalidation
```python
def immediate_invalidation(self):
    """Invalidate cache immediately"""
    self.env.cache.invalidate([
        (self._fields['name'], None),  # All records
        (self._fields['email'], self.ids),  # Specific records
    ])
```

### 2. Delayed Invalidation
```python
def delayed_invalidation(self):
    """Queue invalidation for later"""
    self.env.cache.queue_invalidation([
        (self._fields['name'], self.ids)
    ])
    # Invalidation will be processed at transaction commit
```

### 3. Selective Invalidation
```python
def selective_invalidation(self):
    """Invalidate only necessary cache entries"""
    # Check if cache entry is dirty
    if self.env.cache.is_dirty(self._fields['name'], self.id):
        self.env.cache.invalidate_direct(
            self._fields['name'],
            [self.id]
        )
```

## Performance Optimization

### 1. Batch Invalidation
```python
def batch_invalidate(self, records, fields):
    """Invalidate multiple records/fields at once"""
    invalidation_spec = []
    for field in fields:
        invalidation_spec.append((field, records.ids))
    
    # Single invalidation call
    self.env.cache.invalidate(invalidation_spec)
```

### 2. Smart Dependencies
```python
def setup_dependencies(self):
    """Setup smart dependency tracking"""
    # Group dependencies by model
    model_deps = defaultdict(set)
    for field in self._fields.values():
        if field.related:
            model_deps[field.related_field.model_name].add(field)
            
    # Setup efficient invalidation paths
    self._setup_invalidation_paths(model_deps)
```

### 3. Cache Pruning
```python
def prune_cache(self):
    """Remove old cache entries"""
    current_time = time.time()
    for field, record_dict in self._data.items():
        for record_id, entry in list(record_dict.items()):
            if current_time - entry.timestamp > self.MAX_CACHE_AGE:
                record_dict.pop(record_id, None)
```

## Best Practices

### 1. Dependency Management
- Minimize field dependencies
- Use appropriate store options
- Document dependencies clearly
- Handle circular dependencies

### 2. Invalidation Timing
- Choose appropriate invalidation strategy
- Group related invalidations
- Consider transaction boundaries
- Handle concurrent access

### 3. Performance Considerations
- Monitor cache size
- Use batch operations
- Implement pruning strategies
- Profile invalidation patterns

## Common Issues & Solutions

### 1. Memory Leaks
```python
# Implement cache cleanup
def cleanup_cache(self):
    """Periodic cache cleanup"""
    self.env.cache.clear_old_entries()
    gc.collect()  # Force garbage collection
```

### 2. Inconsistent State
```python
# Handle transaction rollback
@api.model
def safe_write(self, vals):
    """Write with safe cache handling"""
    try:
        with self.env.cr.savepoint():
            result = self.write(vals)
            return result
    except Exception:
        self.env.cache.clear()  # Clear cache on error
        raise
```

### 3. Performance Impact
```python
# Optimize invalidation
def optimize_invalidation(self):
    """Optimize cache invalidation"""
    # Group by model and field
    invalidation_groups = self._group_invalidation_spec()
    
    # Batch invalidate by group
    for group in invalidation_groups:
        self.env.cache.invalidate(group)
``` 