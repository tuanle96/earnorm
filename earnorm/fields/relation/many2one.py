"""Many-to-one field type.

This module provides the Many2oneField class for handling many-to-one relationships
between models in the EarnORM framework.
"""

from typing import Any, TypeVar

from earnorm.fields.relation.reference import ReferenceField
from earnorm.types import ModelInterface

M = TypeVar("M", bound=ModelInterface)


class Many2oneField(ReferenceField[M]):
    """Many-to-one field for storing references to other documents.

    This field is similar to ReferenceField but specifically indicates
    a many-to-one relationship between documents. For example, many posts
    can have the same author.

    The field stores a single ObjectId that references the related document.
    When accessed, it will automatically load the referenced document from
    the database.

    Examples:
        ```python
        class User(Model):
            name = StringField()
            email = StringField()

        class Post(Model):
            title = StringField()
            content = StringField()
            author = Many2oneField(User)  # Many posts can have the same author

        # Create a user
        user = await User.create(
            name="John Doe",
            email="john@example.com"
        )

        # Create multiple posts by the same author
        post1 = await Post.create(
            title="First Post",
            content="Hello World!",
            author=user
        )
        post2 = await Post.create(
            title="Second Post",
            content="Another post",
            author=user
        )

        # Load posts and access author
        posts = await Post.find().all()
        for post in posts:
            author = await post.author.async_convert()
            print(f"{post.title} by {author.name}")
            # Output:
            # First Post by John Doe
            # Second Post by John Doe

        # Find all posts by a specific author
        user_posts = await Post.find({"author": user.id}).all()
        ```

    Note:
        - The field stores only the ObjectId of the referenced document
        - The referenced document is loaded lazily when accessed
        - The field supports both synchronous and asynchronous access
        - The field can be used in queries to find related documents
    """

    def __init__(
        self,
        model: type[M],
        *,
        required: bool = False,
        unique: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            model: Related model class that this field references
            required: Whether this field is required
            unique: Whether field value must be unique
            **kwargs: Additional field options passed to the parent class

        Examples:
            ```python
            # Required author field
            author = Many2oneField(User, required=True)

            # Optional category field
            category = Many2oneField(Category, required=False)

            # Unique department field (one employee per department)
            department = Many2oneField(Department, unique=True)
            ```
        """
        super().__init__(
            model=model,
            required=required,
            unique=unique,
            **kwargs,
        )
