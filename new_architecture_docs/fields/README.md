# Fields System

## Overview
The Fields System provides the foundation for defining and managing model attributes, with support for various field types, computed fields, and related fields.

## Components

### 1. Base Field Class
```python
class Field:
    type = None                # Field type
    relational = False         # Whether field is relational
    translate = False          # Whether field is translatable
    
    def __init__(self, string=None, **kwargs):
        self.string = string
        self.required = kwargs.get('required', False)
        self.readonly = kwargs.get('readonly', False)
        self.index = kwargs.get('index', False)
        self.default = kwargs.get('default', None)
        self.help = kwargs.get('help', None)
```

### 2. Field Types

#### Basic Fields
```python
class Char(Field):
    type = 'char'
    
class Integer(Field):
    type = 'integer'
    
class Float(Field):
    type = 'float'
    
class Boolean(Field):
    type = 'boolean'
    
class Date(Field):
    type = 'date'
```

#### Relational Fields
```python
class Many2one(Field):
    type = 'many2one'
    relational = True
    
class One2many(Field):
    type = 'one2many'
    relational = True
    
class Many2many(Field):
    type = 'many2many'
    relational = True
```

## Features

### 1. Field Attributes
- Required/Optional
- Readonly/Writable
- Indexed/Non-indexed
- Default values
- Help text
- Translations

### 2. Computed Fields
```python
class Field:
    def __init__(self, **kwargs):
        self.compute = kwargs.get('compute', None)
        self.inverse = kwargs.get('inverse', None)
        self.search = kwargs.get('search', None)
        self.store = kwargs.get('store', False)
```

### 3. Related Fields
```python
class Field:
    def __init__(self, **kwargs):
        self.related = kwargs.get('related', None)
        self.related_sudo = kwargs.get('related_sudo', False)
```

## Implementation Details

### 1. Field Definition
```python
def __set_name__(self, owner, name):
    """Set field name and attach to model"""
    self.name = name
    self.model_name = owner._name
    
def setup(self, model):
    """Setup field in model"""
    # Setup compute methods
    if self.compute:
        model._setup_compute_field(self)
    # Setup related fields
    if self.related:
        model._setup_related_field(self)
```

### 2. Value Conversion
```python
def convert_to_column(self, value, record):
    """Convert value to database format"""
    return value

def convert_to_cache(self, value, record, validate=True):
    """Convert value to cache format"""
    if validate:
        self._validate(value)
    return value

def convert_to_record(self, value, record):
    """Convert value to record format"""
    return value
```

### 3. Computed Fields
```python
def _compute_value(self, records):
    """Compute field value"""
    # Get compute method
    method = getattr(records, self.compute)
    # Compute values
    method()
    
def _inverse_value(self, records):
    """Inverse computed field"""
    if self.inverse:
        method = getattr(records, self.inverse)
        method()
```

## Usage Examples

### 1. Basic Fields
```python
class Partner(models.Model):
    _name = 'res.partner'
    
    name = fields.Char(string='Name', required=True)
    age = fields.Integer()
    active = fields.Boolean(default=True)
    birth_date = fields.Date()
```

### 2. Relational Fields
```python
class Order(models.Model):
    _name = 'sale.order'
    
    partner_id = fields.Many2one('res.partner', required=True)
    line_ids = fields.One2many('sale.order.line', 'order_id')
    tag_ids = fields.Many2many('sale.tag')
```

### 3. Computed Fields
```python
class Product(models.Model):
    _name = 'product.product'
    
    list_price = fields.Float()
    discount = fields.Float()
    
    final_price = fields.Float(
        compute='_compute_final_price',
        inverse='_inverse_final_price',
        store=True
    )
    
    @api.depends('list_price', 'discount')
    def _compute_final_price(self):
        for record in self:
            record.final_price = record.list_price * (1 - record.discount)
```

## Best Practices

1. **Field Naming**
- Use descriptive names
- Follow naming conventions
- Document field purpose

2. **Field Attributes**
- Set appropriate attributes
- Use required/readonly wisely
- Consider indexing needs

3. **Computed Fields**
- Minimize dependencies
- Store when appropriate
- Handle missing values

## Common Issues & Solutions

1. **Performance Issues**
```python
# Use store=True for frequently accessed computed fields
total = fields.Float(compute='_compute_total', store=True)

# Use index=True for search fields
code = fields.Char(index=True)
```

2. **Related Field Issues**
```python
# Use related_sudo for cross-company access
partner_name = fields.Char(
    related='partner_id.name',
    related_sudo=True
)
```

3. **Dependency Issues**
```python
@api.depends('line_ids.amount')
def _compute_total(self):
    # Handle missing records
    for record in self:
        record.total = sum(line.amount or 0.0 for line in record.line_ids)
``` 