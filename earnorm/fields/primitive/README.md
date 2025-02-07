# Primitive Fields

This module provides primitive field types for the EarnORM framework.

## Overview

The primitive fields module includes basic data type fields:

1. String Fields (`string.py`)
2. Number Fields (`number.py`)
3. Boolean Fields (`boolean.py`)
4. DateTime Fields (`datetime.py`)

## Field Types

### String Fields
```python
from earnorm.fields.primitive import StringField, TextField, CharField

class User(BaseModel):
    # Fixed length string
    code = CharField(length=10)
    
    # Variable length string
    name = StringField(min_length=2, max_length=100)
    
    # Long text
    description = TextField()
```

### Number Fields
```python
from earnorm.fields.primitive import IntegerField, FloatField, DecimalField

class Product(BaseModel):
    # Integer
    quantity = IntegerField(min_value=0)
    
    # Float
    weight = FloatField(precision=2)
    
    # Decimal (for currency)
    price = DecimalField(precision=10, scale=2)
```

### Boolean Fields
```python
from earnorm.fields.primitive import BooleanField

class User(BaseModel):
    is_active = BooleanField(default=True)
    is_admin = BooleanField(default=False)
```

### DateTime Fields
```python
from earnorm.fields.primitive import DateTimeField, DateField, TimeField

class Event(BaseModel):
    # Date and time
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    # Date only
    event_date = DateField()
    
    # Time only
    start_time = TimeField()
```

## Features

1. String Fields
   - Fixed/variable length
   - Pattern matching
   - Case sensitivity
   - Strip whitespace
   - Format validation

2. Number Fields
   - Integer/float/decimal
   - Range validation
   - Precision control
   - Currency handling
   - Unit conversion

3. Boolean Fields
   - True/false values
   - Null handling
   - Default values
   - Conversion rules

4. DateTime Fields
   - Date/time handling
   - Timezone support
   - Auto timestamps
   - Format conversion
   - Range validation

## Implementation Guide

### 1. String Fields

1. Basic usage:
```python
# Fixed length
code = CharField(length=10)

# Variable length
name = StringField(max_length=100)

# Text field
content = TextField()
```

2. Validation options:
```python
# Pattern matching
username = StringField(pattern=r'^[a-zA-Z0-9_]+$')

# Case options
email = StringField(case_sensitive=False)

# Strip options
title = StringField(strip=True)
```

### 2. Number Fields

1. Basic usage:
```python
# Integer
count = IntegerField()

# Float
price = FloatField()

# Decimal
amount = DecimalField()
```

2. Validation options:
```python
# Range validation
age = IntegerField(min_value=0, max_value=150)

# Precision
weight = FloatField(precision=2)

# Currency
price = DecimalField(precision=10, scale=2)
```

### 3. Boolean Fields

1. Basic usage:
```python
# Simple boolean
is_active = BooleanField()

# With default
is_admin = BooleanField(default=False)
```

2. Options:
```python
# Null handling
has_accepted = BooleanField(null=True)

# Custom values
status = BooleanField(true_value=1, false_value=0)
```

### 4. DateTime Fields

1. Basic usage:
```python
# Date and time
created_at = DateTimeField()

# Date only
birth_date = DateField()

# Time only
start_time = TimeField()
```

2. Options:
```python
# Auto timestamps
updated_at = DateTimeField(auto_now=True)

# Timezone
meeting_time = DateTimeField(use_tz=True)

# Format
date_str = DateField(format="%Y-%m-%d")
```

## Best Practices

1. String Fields
   - Set appropriate length limits
   - Use proper validation patterns
   - Handle case sensitivity
   - Consider storage impact

2. Number Fields
   - Choose appropriate type
   - Set value constraints
   - Handle precision
   - Consider performance

3. Boolean Fields
   - Use clear field names
   - Set sensible defaults
   - Handle null values
   - Document true/false meaning

4. DateTime Fields
   - Handle timezones properly
   - Use auto fields appropriately
   - Set format standards
   - Consider storage format

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
