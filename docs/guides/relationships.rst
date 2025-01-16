Relationships
============

EarnORM provides powerful relationship management between models, supporting various types of relationships and operations.

Relationship Types
---------------

One-to-One (One2one)
~~~~~~~~~~~~~~~~~

.. code-block:: python

    class User(Model):
        profile = fields.One2one(
            "Profile",
            reverse_name="user"
        )

    class Profile(Model):
        user = fields.One2one(
            "User",
            reverse_name="profile"
        )

    # Usage
    user = await User.create({
        "name": "John Doe",
        "profile": {
            "bio": "Software Developer",
            "avatar_url": "https://example.com/avatar.jpg"
        }
    })

    # Access related record
    profile = await user.profile
    user = await profile.user

One-to-Many (One2many)
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class Author(Model):
        books = fields.One2many(
            "Book",
            "author",
            cascade_delete=True
        )

    class Book(Model):
        author = fields.Many2one(
            "Author",
            required=True
        )

    # Usage
    author = await Author.create({
        "name": "John Doe",
        "books": [
            {"title": "Book 1"},
            {"title": "Book 2"}
        ]
    })

    # Access related records
    books = await author.books
    for book in books:
        print(book.title)

    # Access reverse relation
    book = await Book.get(book_id)
    author = await book.author

Many-to-Many (Many2many)
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class Book(Model):
        categories = fields.Many2many(
            "Category",
            reverse_name="books"
        )

    class Category(Model):
        books = fields.Many2many(
            "Book",
            reverse_name="categories"
        )

    # Usage
    book = await Book.create({
        "title": "Python Programming",
        "categories": [
            {"name": "Programming"},
            {"name": "Python"}
        ]
    })

    # Access related records
    categories = await book.categories
    for category in categories:
        print(category.name)

    # Access reverse relation
    category = await Category.get(category_id)
    books = await category.books

Relationship Options
-----------------

Common Options
~~~~~~~~~~~~

.. code-block:: python

    field = fields.One2many(
        "Model",              # Related model
        "field_name",         # Reverse field name
        required=False,       # Field is required
        index=True,          # Create index
        cascade_delete=True,  # Delete related records
        lazy=True            # Lazy loading
    )

Cascade Options
~~~~~~~~~~~~

.. code-block:: python

    # Cascade delete
    books = fields.One2many(
        "Book",
        "author",
        cascade_delete=True  # Delete books when author is deleted
    )

    # Nullify
    books = fields.One2many(
        "Book",
        "author",
        cascade_delete=False  # Set author to null when deleted
    )

    # Restrict
    books = fields.One2many(
        "Book",
        "author",
        restrict_delete=True  # Prevent deletion if has books
    )

Loading Options
~~~~~~~~~~~~

.. code-block:: python

    # Lazy loading (default)
    books = fields.One2many(
        "Book",
        "author",
        lazy=True
    )

    # Eager loading
    books = fields.One2many(
        "Book",
        "author",
        lazy=False
    )

Working with Relationships
----------------------

Creating Records
~~~~~~~~~~~~~

.. code-block:: python

    # Create with related records
    author = await Author.create({
        "name": "John Doe",
        "books": [
            {
                "title": "Book 1",
                "isbn": "123456789"
            },
            {
                "title": "Book 2",
                "isbn": "987654321"
            }
        ]
    })

    # Create related records later
    book = await Book.create({
        "title": "New Book",
        "author": author.id
    })

Querying Related Records
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Query with related fields
    authors = await Author.search([
        ("books.title", "like", "Python")
    ])

    # Join queries
    books = await Book.search([
        ("author.name", "=", "John Doe"),
        ("categories.name", "in", ["Programming", "Python"])
    ])

    # Count related records
    authors = await Author.search([
        ("books", "count", ">", 5)
    ])

Updating Relationships
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Update related records
    await author.update({
        "books": [
            {"id": book1.id, "title": "Updated Title"},
            {"id": book2.id, "status": "published"}
        ]
    })

    # Add to many-to-many
    await book.categories.add(category)
    await book.categories.add([category1, category2])

    # Remove from many-to-many
    await book.categories.remove(category)
    await book.categories.remove([category1, category2])

    # Clear relationships
    await book.categories.clear()

Performance Optimization
--------------------

Eager Loading
~~~~~~~~~~~

.. code-block:: python

    # Load specific relationships
    users = await User.search(
        [("is_active", "=", True)],
        prefetch=["profile", "posts"]
    )

    # Nested prefetch
    users = await User.search(
        [("is_active", "=", True)],
        prefetch={
            "posts": {
                "prefetch": ["comments", "categories"]
            }
        }
    )

Batch Operations
~~~~~~~~~~~~~

.. code-block:: python

    # Batch create
    authors = await Author.create_many([
        {
            "name": "Author 1",
            "books": [{"title": "Book 1"}, {"title": "Book 2"}]
        },
        {
            "name": "Author 2",
            "books": [{"title": "Book 3"}, {"title": "Book 4"}]
        }
    ])

    # Batch update
    await Book.update_many(
        [("author", "=", author.id)],
        {"status": "published"}
    )

Best Practices
------------

1. **Relationship Design**
   - Choose appropriate relationship types
   - Consider data access patterns
   - Plan for scalability
   - Document relationships

2. **Performance**
   - Use lazy loading by default
   - Implement eager loading when needed
   - Batch operations for bulk changes
   - Monitor relationship queries

3. **Data Integrity**
   - Configure appropriate cascade options
   - Validate related records
   - Handle circular dependencies
   - Maintain referential integrity

4. **Code Organization**
   - Keep relationships focused
   - Document relationship behavior
   - Use consistent naming
   - Consider relationship impact

Common Issues
-----------

1. **N+1 Problem**
   - Use eager loading
   - Batch related queries
   - Monitor query count

2. **Circular Dependencies**
   - Use lazy imports
   - Break cycles when possible
   - Document dependencies

3. **Performance Issues**
   - Profile relationship queries
   - Optimize loading strategies
   - Use appropriate indexes

4. **Memory Usage**
   - Control prefetch depth
   - Implement pagination
   - Monitor memory usage

Next Steps
---------

- Learn about :doc:`models` structure
- Understand :doc:`fields` types
- Master :doc:`queries` system
- See :doc:`examples/relationships` for more examples
