# Model Inheritance in Odoo

## Overview
Odoo cung cấp 3 cơ chế inheritance chính:
1. **Classical Inheritance** (Extension): Mở rộng model hiện có
2. **Prototype Inheritance** (Delegation): Tái sử dụng fields và methods thông qua delegation
3. **Delegation Inheritance** (_inherits): Tự động tạo related fields

## 1. Classical Inheritance (_inherit)

### Basic Implementation
```python
class BaseModel(metaclass=MetaModel):
    """Base class for all models"""
    _name = None
    _inherit = None
    
    @classmethod
    def _build_model(cls, pool):
        """Build model with inheritance"""
        # Get parent models
        parents = cls._get_parent_models(pool)
        
        # Inherit fields and methods
        for parent in parents:
            cls._inherit_fields(parent)
            cls._inherit_methods(parent)

def _get_parent_models(cls, pool):
    """Get parent models to inherit from"""
    parents = []
    if isinstance(cls._inherit, str):
        parents = [pool[cls._inherit]]
    elif isinstance(cls._inherit, (list, tuple)):
        parents = [pool[parent] for parent in cls._inherit]
    return parents
```

### Example Usage
```python
# Base model
class Partner(models.Model):
    _name = 'res.partner'
    
    name = fields.Char(required=True)
    email = fields.Char()

# Extended model
class Customer(models.Model):
    _inherit = 'res.partner'
    
    # Add new fields
    customer_code = fields.Char()
    
    # Override existing method
    def write(self, vals):
        # Add custom logic
        return super().write(vals)
```

## 2. Prototype Inheritance (_inherits)

### Implementation
```python
class ProtoInheritance:
    """Handle prototype inheritance"""
    
    def _setup_prototype(self):
        """Setup prototype inheritance"""
        if not self._inherits:
            return
            
        for parent, field in self._inherits.items():
            # Create delegation field
            self._add_delegation_field(parent, field)
            
            # Setup related fields
            self._setup_related_fields(parent)
            
    def _add_delegation_field(self, parent_model, field_name):
        """Add many2one field for delegation"""
        self._fields[field_name] = fields.Many2one(
            parent_model,
            required=True,
            ondelete='cascade',
            delegate=True
        )
        
    def _setup_related_fields(self, parent_model):
        """Setup related fields from parent"""
        parent = self.env[parent_model]
        for name, field in parent._fields.items():
            if name not in self._fields:
                # Create related field
                self._fields[name] = field.new(
                    related=f'{parent_model}.{name}',
                    inherited=True
                )
```

### Example Usage
```python
class Company(models.Model):
    _name = 'res.company'
    
    name = fields.Char(required=True)
    address = fields.Text()

class Partner(models.Model):
    _name = 'res.partner'
    _inherits = {'res.company': 'company_id'}
    
    # Automatically gets all fields from res.company
    company_id = fields.Many2one('res.company', required=True, ondelete='cascade')
    
    # Add partner-specific fields
    email = fields.Char()
```

## 3. Delegation Inheritance (_inherits)

### Implementation
```python
class DelegationInheritance:
    """Handle delegation inheritance"""
    
    def _setup_inheritance(self):
        """Setup delegation inheritance"""
        for parent, field in self._inherits.items():
            # Create delegation fields
            self._add_inherited_fields(parent, field)
            
    def _add_inherited_fields(self, parent_model, field_name):
        """Add inherited fields from parent"""
        parent = self.env[parent_model]
        for name, field in parent._fields.items():
            if name not in self._fields:
                # Create delegated field
                self._fields[name] = field.new(
                    inherited=True,
                    related=f'{field_name}.{name}'
                )
                
    def _inherits_check(self):
        """Check inheritance validity"""
        for parent in self._inherits:
            parent_model = self.env[parent]
            if parent_model._inherits:
                # Check for inheritance cycles
                self._check_inheritance_cycle(parent_model)
```

### Example Usage
```python
class User(models.Model):
    _name = 'res.users'
    _inherits = {'res.partner': 'partner_id'}
    
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    login = fields.Char(required=True)
    password = fields.Char()
    
    # Automatically gets all fields from res.partner
    # Can access partner fields directly: user.name, user.email
```

## 4. Inheritance Resolution

### Field Resolution
```python
def _setup_fields(self):
    """Setup model fields with inheritance"""
    # Get all inherited fields
    for parent in self._inherit:
        parent_model = self.env[parent]
        for name, field in parent_model._fields.items():
            if name not in self._fields:
                # Inherit field
                self._fields[name] = field.new(inherited=True)
            else:
                # Override field
                self._fields[name].update_attrs(
                    self._fields[name].get_description()
                )
```

### Method Resolution
```python
def _setup_methods(self):
    """Setup model methods with inheritance"""
    # Get all inherited methods
    for parent in self._inherit:
        parent_model = self.env[parent]
        for name, method in parent_model._methods.items():
            if name not in self._methods:
                # Inherit method
                setattr(self, name, method)
```

## 5. Best Practices

### 1. Inheritance Selection
```python
# Extension (add fields/methods)
class CustomerExtension(models.Model):
    _inherit = 'res.partner'
    
    customer_type = fields.Selection([
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale')
    ])

# New Model (complete inheritance)
class Customer(models.Model):
    _name = 'res.customer'
    _inherit = 'res.partner'
    
    # Complete new implementation
```

### 2. Multiple Inheritance
```python
class ComplexModel(models.Model):
    _name = 'complex.model'
    _inherit = ['res.partner', 'mail.thread']
    
    def _setup_inheritance(self):
        # Handle multiple inheritance
        super()._setup_inheritance()
        # Add custom logic for multiple parents
```

### 3. Delegation vs Extension
```python
# Use delegation when you want to reuse structure
class Employee(models.Model):
    _name = 'hr.employee'
    _inherits = {'res.partner': 'partner_id'}
    
    partner_id = fields.Many2one('res.partner', required=True)
    department_id = fields.Many2one('hr.department')

# Use extension when you want to modify behavior
class CustomerPartner(models.Model):
    _inherit = 'res.partner'
    
    def write(self, vals):
        # Add custom logic
        return super().write(vals)
```

## 6. Common Issues & Solutions

### 1. Inheritance Cycles
```python
def _check_inheritance_cycle(self):
    """Check for inheritance cycles"""
    visited = set()
    def check_cycle(model):
        if model._name in visited:
            raise ValidationError("Inheritance cycle detected")
        visited.add(model._name)
        for parent in model._inherit:
            check_cycle(self.env[parent])
    check_cycle(self)
```

### 2. Field Conflicts
```python
def _handle_field_conflicts(self):
    """Handle field naming conflicts"""
    for name, field in self._fields.items():
        if name in self._inherit_fields:
            # Check field compatibility
            inherited = self._inherit_fields[name]
            if field.type != inherited.type:
                raise ValidationError(
                    f"Field {name} type conflict"
                )
```

### 3. Method Override
```python
def _setup_method_override(self):
    """Handle method overrides properly"""
    for name, method in self._methods.items():
        if hasattr(method, '_super'):
            # Ensure proper super call chain
            original = getattr(super(), name, None)
            if original:
                method._super = original
``` 