Fields
======

Fields are the building blocks of models in EarnORM, defining the structure and validation rules for your data.

Field Types
----------

Primitive Fields
~~~~~~~~~~~~~

String Fields
^^^^^^^^^^^

.. code-block:: python

    class User(Model):
        # Basic string field
        name = fields.String(
            required=True,
            min_length=2,
            max_length=100
        )

        # Email field with validation
        email = fields.Email(
            required=True,
            unique=True
        )

        # Password field with hashing
        password = fields.Password(
            min_length=8,
            hash_algorithm="bcrypt"
        )

Numeric Fields
^^^^^^^^^^^

.. code-block:: python

    class Product(Model):
        # Integer field
        quantity = fields.Integer(
            required=True,
            min_value=0,
            max_value=1000
        )

        # Float field
        weight = fields.Float(
            min_value=0.1,
            max_value=100.0
        )

        # Decimal field for precise calculations
        price = fields.Decimal(
            required=True,
            min_value=0,
            precision=2
        )

Boolean and Date Fields
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    class Task(Model):
        # Boolean field
        is_completed = fields.Boolean(default=False)

        # Date field
        due_date = fields.Date(
            required=True,
            auto_now=False
        )

        # DateTime field
        created_at = fields.DateTime(
            auto_now_add=True
        )
        updated_at = fields.DateTime(
            auto_now=True
        )

ObjectId and Reference Fields
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    class Comment(Model):
        # ObjectId field
        id = fields.ObjectId(primary_key=True)

        # Reference to User model
        author = fields.Reference(
            "User",
            required=True,
            reverse_delete=CASCADE
        )

Composite Fields
~~~~~~~~~~~~~

List Fields
^^^^^^^^^

.. code-block:: python

    class Post(Model):
        # List of strings
        tags = fields.List(
            fields.String(),
            default=list
        )

        # List of embedded documents
        comments = fields.List(
            fields.EmbeddedModel(Comment)
        )

Dict Fields
^^^^^^^^

.. code-block:: python

    class User(Model):
        # Dictionary field
        settings = fields.Dict(
            key_field=fields.String(),
            value_field=fields.Any()
        )

        # JSON field
        metadata = fields.Json(
            default=dict
        )

Embedded Fields
^^^^^^^^^^^

.. code-block:: python

    class Address(EmbeddedModel):
        street = fields.String()
        city = fields.String()
        country = fields.String()

    class User(Model):
        # Single embedded document
        address = fields.Embedded(Address)

        # List of embedded documents
        addresses = fields.List(
            fields.Embedded(Address)
        )

File Fields
^^^^^^^^^

.. code-block:: python

    class Document(Model):
        # File field using GridFS
        file = fields.File(
            allowed_types=["application/pdf"],
            max_size=10 * 1024 * 1024  # 10MB
        )

        # Image field with thumbnails
        image = fields.Image(
            thumbnails={
                "small": (100, 100),
                "medium": (300, 300)
            }
        )

Relationship Fields
~~~~~~~~~~~~~~~~

One-to-One
^^^^^^^^

.. code-block:: python

    class User(Model):
        profile = fields.One2one(
            "Profile",
            reverse_name="user"
        )

    class Profile(Model):
        user = fields.One2one(
            User,
            reverse_name="profile"
        )

One-to-Many
^^^^^^^^^

.. code-block:: python

    class Author(Model):
        books = fields.One2many(
            "Book",
            "author",
            cascade_delete=True
        )

    class Book(Model):
        author = fields.Many2one(
            Author,
            required=True
        )

Many-to-Many
^^^^^^^^^^

.. code-block:: python

    class Book(Model):
        categories = fields.Many2many(
            "Category",
            reverse_name="books"
        )

    class Category(Model):
        books = fields.Many2many(
            Book,
            reverse_name="categories"
        )

Field Options
-----------

Common Options
~~~~~~~~~~~~

All fields support these common options:

.. code-block:: python

    field = fields.String(
        required=True,      # Field is required
        unique=True,        # Value must be unique
        default="value",    # Default value
        index=True,         # Create database index
        validators=[...],   # Custom validators
        choices=[...],      # Valid choices
        description="..."   # Field description
    )

Validation Options
~~~~~~~~~~~~~~~

Type-specific validation options:

.. code-block:: python

    # String validation
    name = fields.String(
        min_length=2,
        max_length=100,
        regex=r"^[a-zA-Z]+$"
    )

    # Numeric validation
    age = fields.Integer(
        min_value=0,
        max_value=150
    )

    # List validation
    tags = fields.List(
        fields.String(),
        min_length=1,
        max_length=10
    )

Database Options
~~~~~~~~~~~~~

Options for database storage:

.. code-block:: python

    field = fields.String(
        db_name="field_name",  # Name in database
        sparse=True,           # Sparse index
        expire_after=3600,     # TTL index
        default_language="en"  # Text search language
    )

Custom Fields
-----------

Creating Custom Fields
~~~~~~~~~~~~~~~~~~

You can create custom fields by subclassing Field:

.. code-block:: python

    class PhoneField(fields.String):
        """Field for phone numbers with validation."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.regex = r"^\+?1?\d{9,15}$"

        def validate(self, value):
            super().validate(value)
            if not re.match(self.regex, value):
                raise ValueError("Invalid phone number")

Using Custom Fields
~~~~~~~~~~~~~~~

.. code-block:: python

    class Contact(Model):
        name = fields.String()
        phone = PhoneField(required=True)

Best Practices
------------

1. **Field Selection**
   - Choose appropriate field types
   - Use specialized fields when available
   - Consider validation requirements
   - Think about indexing needs

2. **Validation**
   - Add field-level validation
   - Use custom validators for complex rules
   - Validate data as early as possible
   - Handle validation errors gracefully

3. **Performance**
   - Index frequently queried fields
   - Use appropriate field types for queries
   - Consider storage requirements
   - Monitor field usage patterns

4. **Relationships**
   - Choose appropriate relationship types
   - Consider cascade operations
   - Use lazy loading when appropriate
   - Monitor relationship performance

Next Steps
---------

- Learn about :doc:`models` and how to use fields
- Understand :doc:`queries` and field operators
- Work with :doc:`relationships` between models
- See :doc:`examples/basic` for practical examples
