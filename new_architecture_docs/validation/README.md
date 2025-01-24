# Validation System

## Overview
The Validation System ensures data integrity through field validation, model constraints, and business logic validation at various levels.

## Components

### 1. Field Validator
```python
class FieldValidator:
    def __init__(self, field):
        self.field = field
        self.type = field.type
        self.required = field.required
        self.size = field.size
```

### 2. Model Constraints
```python
class ModelConstraints:
    def __init__(self, model):
        self.model = model
        self.sql_constraints = []
        self.constraints = []  # Python constraints
```

### 3. Business Rules
```python
class BusinessRules:
    def __init__(self):
        self.rules = []
        self.error_messages = {}
```

## Features

### 1. Field Validation
- Type checking
- Required fields
- Size limits
- Format validation
- Custom validators

### 2. Model Constraints
- SQL constraints
- Python constraints
- Unique constraints
- Check constraints

### 3. Business Rules
- Complex validations
- Cross-field validation
- Conditional validation
- Custom error messages

## Implementation Details

### 1. Field Validation
```python
def validate_field(self, value):
    """Validate field value"""
    if self.required and not value:
        raise ValidationError("Field is required")
        
    if self.size and len(value) > self.size:
        raise ValidationError(f"Value too long (max {self.size})")
        
    if not self._validate_type(value):
        raise ValidationError("Invalid type")
```

### 2. Model Constraints
```python
def _validate_constraints(self):
    """Validate model constraints"""
    # Check SQL constraints
    for constraint in self.sql_constraints:
        self._validate_sql_constraint(constraint)
        
    # Check Python constraints
    for constraint in self.constraints:
        if not constraint.check(self):
            raise ValidationError(constraint.message)
```

### 3. Business Rules
```python
def validate_business_rules(self, records):
    """Validate business rules"""
    for rule in self.rules:
        if not rule.condition(records):
            message = self.error_messages.get(rule.code, "Validation failed")
            raise ValidationError(message)
```

## Usage Examples

### 1. Field Validation
```python
class Partner(models.Model):
    _name = 'res.partner'
    
    email = fields.Char(required=True)
    phone = fields.Char(size=20)
    
    @api.constrains('email')
    def _check_email(self):
        for record in self:
            if record.email and '@' not in record.email:
                raise ValidationError('Invalid email format')
```

### 2. Model Constraints
```python
class Product(models.Model):
    _name = 'product.product'
    
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Code must be unique'),
        ('price_check', 'check(list_price >= 0)', 'Price must be positive')
    ]
    
    @api.constrains('stock_level', 'min_stock')
    def _check_stock(self):
        for record in self:
            if record.stock_level < record.min_stock:
                raise ValidationError('Stock below minimum level')
```

### 3. Business Rules
```python
class SaleOrder(models.Model):
    _name = 'sale.order'
    
    @api.constrains('line_ids', 'state')
    def _check_order_rules(self):
        for order in self:
            # Check credit limit
            if order.amount_total > order.partner_id.credit_limit:
                raise ValidationError('Credit limit exceeded')
                
            # Check stock availability
            for line in order.line_ids:
                if line.product_id.stock_level < line.quantity:
                    raise ValidationError('Insufficient stock')
```

## Best Practices

1. **Field Validation**
- Validate at field level
- Use appropriate constraints
- Handle edge cases
- Provide clear messages

2. **Model Constraints**
- Use SQL constraints when possible
- Keep constraints simple
- Document constraints
- Handle exceptions

3. **Business Rules**
- Separate business logic
- Use descriptive messages
- Handle dependencies
- Test thoroughly

## Common Issues & Solutions

1. **Performance Issues**
```python
# Optimize validation checks
@api.constrains('field1', 'field2')
def _check_fields(self):
    # Batch validation
    self.env.cr.execute("""
        SELECT id FROM table
        WHERE field1 > field2
    """)
    invalid_ids = [r[0] for r in self.env.cr.fetchall()]
    if invalid_ids:
        raise ValidationError('Validation failed')
```

2. **Complex Validations**
```python
# Break down complex validations
def _validate_order(self):
    self._validate_quantities()
    self._validate_prices()
    self._validate_dates()
    self._validate_stock()
```

3. **Circular Dependencies**
```python
# Handle circular references
@api.constrains('parent_id')
def _check_hierarchy(self):
    if not self._check_recursion():
        raise ValidationError('Recursive hierarchy detected')
``` 