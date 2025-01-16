Quickstart
=========

This guide will help you get started with EarnORM quickly.

Basic Setup
----------

First, install EarnORM:

.. code-block:: bash

    poetry add earnorm

Then, create a simple model:

.. code-block:: python

    from earnorm import Model, fields

    class User(Model):
        _collection = "users"  # MongoDB collection name

        name = fields.String(required=True)
        email = fields.Email(required=True, unique=True)
        age = fields.Integer(min_value=0)
        is_active = fields.Boolean(default=True)

Initialize the Connection
-----------------------

Before using models, initialize the connection:

.. code-block:: python

    import asyncio
    from earnorm import init

    async def main():
        # Initialize connection
        await init(
            mongo_uri="mongodb://localhost:27017",
            database="mydb"
        )

        # Your code here

    if __name__ == "__main__":
        asyncio.run(main())

Basic Operations
--------------

Create Records
~~~~~~~~~~~~

.. code-block:: python

    # Create a single record
    user = await User.create({
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    })

    # Create multiple records
    users = await User.create_many([
        {
            "name": "Alice",
            "email": "alice@example.com",
            "age": 25
        },
        {
            "name": "Bob",
            "email": "bob@example.com",
            "age": 35
        }
    ])

Query Records
~~~~~~~~~~~

.. code-block:: python

    # Get by ID
    user = await User.get(user_id)

    # Find one
    user = await User.find_one({"email": "john@example.com"})

    # Find many
    adult_users = await User.search([
        ("age", ">=", 18),
        ("is_active", "=", True)
    ])

    # Complex queries
    from earnorm.domain import DomainBuilder

    domain = (
        DomainBuilder()
        .field("age").greater_than(18)
        .and_()
        .field("is_active").equals(True)
        .build()
    )

    users = await User.search(domain)

Update Records
~~~~~~~~~~~~

.. code-block:: python

    # Update a single record
    await user.update({
        "age": 31,
        "is_active": False
    })

    # Update many records
    await User.update_many(
        [("age", "<", 18)],
        {"is_active": False}
    )

Delete Records
~~~~~~~~~~~~

.. code-block:: python

    # Delete a single record
    await user.delete()

    # Delete many records
    await User.delete_many([("is_active", "=", False)])

Relationships
-----------

Define relationships between models:

.. code-block:: python

    class Post(Model):
        _collection = "posts"

        title = fields.String(required=True)
        content = fields.String()
        author = fields.Many2one("User", required=True)

    class User(Model):
        _collection = "users"

        name = fields.String(required=True)
        email = fields.Email(required=True, unique=True)
        posts = fields.One2many("Post", "author")

Use relationships:

.. code-block:: python

    # Create related records
    user = await User.create({
        "name": "John",
        "email": "john@example.com"
    })

    post = await Post.create({
        "title": "My First Post",
        "content": "Hello World!",
        "author": user.id
    })

    # Query related records
    user_posts = await user.posts.all()

    # Get author of a post
    author = await post.author.get()

Next Steps
---------

- Learn about :doc:`models` and field types
- Explore :doc:`queries` and domain expressions
- Understand :doc:`relationships` between models
- Check out more :doc:`examples/basic`
