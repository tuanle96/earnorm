# Validation Components

Validation system components for EarnORM.

## Purpose

The validation module provides comprehensive validation capabilities:
- Field-level validation
- Model-level validation
- Cross-field validation
- Custom validators
- Validation chains
- Async validation

## Concepts & Examples

### Field Validation
```python
# Basic field validation
name = StringField(required=True, min_length=2, max_length=50)
age = IntegerField(min_value=0, max_value=150)
email = EmailField(required=True, unique=True)

# Custom field validator
class PhoneField(StringField):
    def __init__(self, **kwargs):
        super().__init__(regex=r'^\+?1?\d{9,15}$', **kwargs)
        
    def validate(self, value):
        super().validate(value)
        if not value.startswith('+'):
            raise ValidationError("Phone number must start with '+'")
```

### Model Validation
```python
class User(BaseModel):
    name = StringField(required=True)
    email = EmailField(required=True)
    age = IntegerField()
    
    @validates
    def validate_age(self):
        if self.age < 18 and self.role == 'admin':
            raise ValidationError("Admin must be 18 or older")
            
    @validates_fields('password', 'confirm_password')
    def validate_passwords_match(self, password, confirm):
        if password != confirm:
            raise ValidationError("Passwords do not match")
```

### Validation Chain
```python
# Chain multiple validators
class Order(BaseModel):
    total = FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1000000),
            CustomValidator(lambda x: x % 0.01 == 0)
        ]
    )
    
    @chain_validates('status')
    def validate_status_transition(self):
        yield StatusExistsValidator()
        yield StatusTransitionValidator()
        yield StatusPermissionValidator()
```

### Async Validation
```python
class User(BaseModel):
    email = EmailField(required=True)
    
    @validates_async
    async def validate_email_exists(self):
        exists = await check_email_service(self.email)
        if not exists:
            raise ValidationError("Email does not exist")
            
    @validates_async_fields('username')
    async def validate_username_available(self, username):
        if await User.find(username=username).exists():
            raise ValidationError("Username already taken")
```

## Best Practices

1. **Field Validation**
- Use built-in validators when possible
- Create reusable custom validators
- Keep validation rules simple
- Document validation rules
- Handle edge cases

2. **Model Validation**
- Separate validation concerns
- Use appropriate decorators
- Handle validation dependencies
- Provide clear error messages
- Log validation failures

3. **Performance**
- Cache validation results
- Use async validation when appropriate
- Optimize validation chains
- Batch validations when possible
- Monitor validation times

4. **Error Handling**
- Use specific error types
- Provide detailed messages
- Include field context
- Handle nested validation
- Support i18n

## Future Features

1. **Validator Types**
- [ ] Complex validators
- [ ] Conditional validators
- [ ] Regex validators
- [ ] Format validators
- [ ] Custom error messages

2. **Validation Features**
- [ ] Validation groups
- [ ] Validation contexts
- [ ] Validation caching
- [ ] Validation events
- [ ] Validation rules DSL

3. **Async Features**
- [ ] Parallel validation
- [ ] Validation timeouts
- [ ] Batch validation
- [ ] Remote validation
- [ ] Validation queues

4. **Integration**
- [ ] Form validation
- [ ] API validation
- [ ] Schema validation
- [ ] Custom validators
- [ ] Validation plugins 