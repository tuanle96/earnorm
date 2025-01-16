# Fields Module

## Overview
The Fields module provides a comprehensive set of field types for defining model schemas in EarnORM. It includes support for primitive types, complex types, and file storage using GridFS.

## Structure
```
fields/
├── base.py           # Base field implementation
├── types/            # Type definitions
├── primitive/        # Primitive field types
│   ├── boolean.py
│   ├── datetime.py
│   ├── decimal.py
│   ├── enum.py
│   ├── file.py
│   ├── number.py
│   ├── object_id.py
│   └── string.py
├── composite/        # Composite field types
│   ├── dict.py
│   ├── embedded.py
│   ├── list.py
│   ├── set.py
│   └── tuple.py
└── relation/         # Relation field types
    ├── base.py
    ├── many2many.py
    ├── many2one.py
    ├── one2many.py
    └── reference.py
```

## Field Types

### Primitive Types
- `StringField`: For text data
- `IntegerField`: For integer numbers
- `FloatField`: For floating point numbers
- `BooleanField`: For boolean values
- `DateTimeField`: For datetime values
- `ObjectIdField`: For MongoDB ObjectId values
- `DecimalField`: For precise decimal numbers
- `EnumField`: For enumerated values
- `FileField`: For file storage using GridFS

### 1. Primitive Fields
Basic fields for simple data types:

```python
from earnorm.fields import (
    BooleanField,
    DateField,
    DateTimeField,
    DecimalField,
    EnumField,
    FileField,
    FloatField,
    IntegerField,
    ObjectIdField,
    StringField
)

class User(Model):
    name = StringField(required=True)
    age = IntegerField(min_value=0)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
```

### 2. Composite Fields
Complex fields for structured data:

```python
from earnorm.fields import (
    DictField,
    EmbeddedField,
    ListField,
    SetField,
    TupleField
)

class Address(EmbeddedModel):
    street = StringField()
    city = StringField()
    country = StringField()

class User(Model):
    addresses = ListField(EmbeddedField(Address))
    metadata = DictField()
    tags = SetField(StringField())
    coordinates = TupleField(FloatField(), FloatField())
```

### 3. Relation Fields
Fields for model relationships:

```python
from earnorm.fields import (
    ReferenceField,
    Many2oneField,
    One2manyField,
    Many2manyField
)

class Author(Model):
    name = StringField()
    books = One2manyField('Book', field='author')

class Book(Model):
    title = StringField()
    author = Many2oneField(Author)
    categories = Many2manyField('Category')

class Category(Model):
    name = StringField()
    books = Many2manyField(Book)
```

## Common Features

### 1. Field Validation
All fields support validation:

```python
from earnorm.validators import MinLengthValidator, MaxLengthValidator

class User(Model):
    username = StringField(
        required=True,
        validators=[
            MinLengthValidator(3),
            MaxLengthValidator(50)
        ]
    )
```

### 2. Default Values
Fields can have default values:

```python
class Post(Model):
    title = StringField(required=True)
    status = StringField(default='draft')
    views = IntegerField(default=0)
```

### 3. File Handling
FileField supports file storage and management using GridFS:

```python
class Document(Model):
    title = StringField()
    file = FileField(
        allowed_types=['application/pdf'],
        max_size=10 * 1024 * 1024  # 10MB
    )

# Upload file
doc = Document(title="Report")
with open("report.pdf", "rb") as f:
    await doc.file.save(f, filename="report.pdf")

# Download file
with open("downloaded.pdf", "wb") as f:
    await doc.file.download(f)
```

## Best Practices

1. **Validation**
- Always define validation constraints when necessary
- Use built-in validators or create custom ones
- Validate data as early as possible
- Add descriptive error messages

2. **Relations**
- Choose the appropriate relationship type (One2many, Many2one, Many2many)
- Consider performance implications when designing relationships
- Use lazy loading for complex relationships
- Avoid deep nesting of relationships

3. **File Handling**
- Always specify allowed_types and max_size for FileField
- Handle file cleanup when deleting documents
- Use async context managers for file operations
- Implement proper error handling for file operations

4. **Type Hints**
- Use type hints for fields
- Leverage IDE support with type hints
- Check type compatibility in CI/CD
- Document type constraints

5. **Performance**
- Use indexes for frequently queried fields
- Implement caching for expensive operations
- Use projection to fetch only required fields
- Batch operations when possible

## Common Issues & Solutions

1. **Circular Imports**
```python
# Use string references for circular imports
class Author(Model):
    books = One2manyField('Book', field='author')

class Book(Model):
    author = Many2oneField('Author')
```

2. **Complex Validation**
```python
from typing import Any

def validate_age(value: Any) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError("Age must be a positive integer")

class User(Model):
    age = IntegerField(validators=[validate_age])
```

3. **Custom Field Types**
```python
from earnorm.fields import Field

class EmailField(Field[str]):
    """Custom field for email validation.
    
    Examples:
        >>> class User(Model):
        ...     email = EmailField(required=True)
    """
    def validate(self, value: Any) -> None:
        super().validate(value)
        if '@' not in value:
            raise ValueError("Invalid email format")
```

4. **Handling Large Files**
```python
class LargeFile(Model):
    """Model for handling large file uploads with chunked processing.
    
    Examples:
        >>> file = LargeFile(name="large.zip")
        >>> async with file.file.chunk_writer() as writer:
        ...     while chunk := await stream.read(8192):
        ...         await writer.write(chunk)
    """
    name = StringField()
    file = FileField(
        max_size=1024 * 1024 * 1024,  # 1GB
        allowed_types=['application/zip']
    )
```

## Contributing

1. Follow code style and type hints
2. Add tests for new features
3. Update documentation
4. Add docstrings with code examples
5. Run linters and type checkers
6. Write clear commit messages

## Testing

1. **Unit Tests**
```python
async def test_email_field_validation():
    field = EmailField()
    
    # Valid email
    await field.validate("user@example.com")
    
    # Invalid email
    with pytest.raises(ValueError):
        await field.validate("invalid-email")
```

2. **Integration Tests**
```python
async def test_file_upload_download():
    doc = Document(title="Test")
    
    # Test upload
    data = b"test content"
    await doc.file.save(io.BytesIO(data), "test.txt")
    
    # Test download
    buffer = io.BytesIO()
    await doc.file.download(buffer)
    assert buffer.getvalue() == data
```

## Base Field Implementation

### Field Protocol
The base field functionality is defined by the `FieldProtocol`:

```python
class FieldProtocol(Protocol):
    """Protocol for field classes.
    
    This protocol defines the interface that all field classes must implement.
    It includes methods for validation, conversion, and serialization of field values.
    """
    name: str
    
    @property
    def metadata(self) -> Any:
        """Get field metadata."""
        pass
        
    def validate(self, value: Any) -> None:
        """Validate field value."""
        pass
        
    def convert(self, value: Any) -> Any:
        """Convert value to field type."""
        pass
        
    def to_dict(self, value: Any) -> Any:
        """Convert value to dict representation."""
        pass
```

### Base Field Class
The `Field` class implements the `FieldProtocol` and provides core functionality:

```python
class Field(FieldProtocol, Generic[T]):
    """Base field class.
    
    This class implements the FieldProtocol and provides the core functionality
    for all field types. It handles field validation, conversion between Python
    and MongoDB types, and serialization.
    
    Type Parameters:
        T: The Python type this field represents
        
    Attributes:
        name: Name of the field
        _metadata: Field metadata containing configuration
        _cache_manager: Cache manager for caching field operations
    """
    
    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        index: bool = False,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.
        
        Args:
            required: Whether the field is required
            unique: Whether the field value must be unique
            default: Default value for the field
            validators: List of validator functions
            index: Whether to create an index for this field
            description: Field description
            **kwargs: Additional field options
        """
        self.name: str = ""
        self._metadata = FieldMetadata(
            name=self.name,
            field_type=self._get_field_type(),
            required=required,
            unique=unique,
            default=default,
            validators=validators or [],
            index=index,
            description=description,
            options=kwargs,
        )
```

### Field Metadata
Field metadata stores configuration and validation rules:

```python
@dataclass
class FieldMetadata:
    """Field metadata.
    
    Attributes:
        name: Field name
        field_type: Python type for the field
        required: Whether field is required
        unique: Whether field value must be unique
        index: Whether to create database index
        default: Default field value
        description: Field description
        validators: List of validator functions
        options: Additional field options
    """
    name: str
    field_type: Type[Any]
    required: bool = False
    unique: bool = False
    index: bool = False
    default: Any = None
    description: Optional[str] = None
    validators: List[ValidatorFunc] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
```

### Validation
The base validation system:

```python
class BaseValidator(ABC):
    """Base validator class.
    
    Examples:
        ```python
        class EmailValidator(BaseValidator):
            def __call__(self, value: Any) -> None:
                if not isinstance(value, str):
                    raise ValidationError("Value must be a string")
                if "@" not in value:
                    raise ValidationError("Invalid email address")
        ```
    """
    
    def __init__(self, message: Optional[str] = None):
        self.message = message
        
    @abstractmethod
    def __call__(self, value: Any) -> ValidationResult:
        """Validate value."""
        pass
```

### Type Conversion
Base field type conversion methods:

```python
def convert(self, value: Any) -> T:
    """Convert value to field type."""
    if value is None:
        return self._metadata.default
    return value

def to_mongo(self, value: Optional[T]) -> Any:
    """Convert Python value to MongoDB format."""
    return value
    
def from_mongo(self, value: Any) -> T:
    """Convert MongoDB value to Python type."""
    return self.convert(value)
```

### Best Practices for Custom Fields

1. **Type Safety**
```python
class CustomField(Field[CustomType]):
    def _get_field_type(self) -> Type[Any]:
        return CustomType
        
    def convert(self, value: Any) -> CustomType:
        if not isinstance(value, CustomType):
            raise ValueError(f"Expected {CustomType.__name__}, got {type(value)}")
        return value
```

2. **Validation**
```python
class PositiveIntegerField(Field[int]):
    def validate(self, value: Any) -> None:
        super().validate(value)
        if value < 0:
            raise ValidationError("Value must be positive")
```

3. **Custom Conversion**
```python
class JsonField(Field[Dict[str, Any]]):
    def to_mongo(self, value: Optional[Dict[str, Any]]) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)
        
    def from_mongo(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        return json.loads(value)
``` 

## GridFS Support

EarnORM provides built-in support for storing and managing files using MongoDB's GridFS through the `FileField` type.

### FileField Features
- File upload/download with streaming support
- Automatic content type detection
- File size validation
- MIME type validation
- Metadata management
- Async operations

### Example Usage

```python
from earnorm import BaseModel
from earnorm.fields import StringField, FileField

class Document(BaseModel):
    title = StringField(required=True)
    attachment = FileField(
        allowed_types=["application/pdf", "image/jpeg"],
        max_size=10 * 1024 * 1024  # 10MB
    )

# Upload file
doc = Document(title="Report")
with open("report.pdf", "rb") as f:
    await doc.attachment.save(f, filename="report.pdf")

# Download file
with open("downloaded.pdf", "wb") as f:
    await doc.attachment.download(f)

# Get file info
info = await doc.attachment.get_info()
print(f"Filename: {info['filename']}")
print(f"Size: {info['length']} bytes")
print(f"Upload date: {info['uploadDate']}")

# Delete file
await doc.attachment.delete()
```

### FileField Options
- `allowed_types`: List of allowed MIME types
- `max_size`: Maximum file size in bytes
- `required`: Whether the field is required
- `unique`: Whether the field value must be unique

### Best Practices
1. **File Size Limits**
   - Always set appropriate `max_size` to prevent large file uploads
   - Consider your MongoDB storage capacity

2. **Content Type Validation**
   - Use `allowed_types` to restrict file types
   - Helps prevent security issues

3. **Error Handling**
   - Handle `GridFSError` for file operations
   - Validate files before upload

4. **Resource Management**
   - Delete unused files to free up storage
   - Use streaming for large files
``` 
