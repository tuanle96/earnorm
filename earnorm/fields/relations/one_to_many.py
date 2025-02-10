"""One-to-many relation field implementation.

This module provides the OneToManyField class for defining one-to-many relations in EarnORM.
It allows one record in the source model to reference multiple records in the target model.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields.relations import OneToManyField

    >>> class User(BaseModel):
    ...     _name = 'res.user'
    ...     posts = OneToManyField(
    ...         'res.post',  # Using string reference
    ...         related_name='author',
    ...         on_delete='CASCADE'
    ...     )

    >>> class Post(BaseModel):
    ...     _name = 'res.post'

    >>> # Create related records
    >>> user = await User.create({'name': 'John'})
    >>> post1 = await Post.create({
    ...     'author': user,
    ...     'title': 'First post'
    ... })
    >>> post2 = await Post.create({
    ...     'author': user,
    ...     'title': 'Second post'
    ... })

    >>> # Access related records
    >>> posts = await user.posts
    >>> author = await post1.author
"""

from typing import TYPE_CHECKING, Any, Dict, Optional, TypeVar

from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationType

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


class OneToManyField(RelationField[T]):
    """Field for one-to-many relations.

    This field allows one record in the source model to reference multiple records
    in the target model. It automatically creates a reverse many-to-one relation field
    on the target model.

    Args:
        model: Related model class or string reference
        related_name: Name of reverse relation field
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        required: Whether relation is required
        **options: Additional field options

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.user'
        ...     posts = OneToManyField(
        ...         'res.post',  # Using string reference
        ...         related_name='author',
        ...         on_delete='CASCADE'
        ...     )

        >>> # Create related records
        >>> user = await User.create({'name': 'John'})
        >>> post = await Post.create({
        ...     'author': user,
        ...     'title': 'First post'
        ... })

        >>> # Access related records
        >>> posts = await user.posts
        >>> author = await post.author
    """

    def __init__(
        self,
        model: ModelType[T],
        *,
        related_name: Optional[str] = None,
        on_delete: str = "CASCADE",
        required: bool = False,
        **options: Dict[str, Any],
    ) -> None:
        """Initialize one-to-many field.

        Args:
            model: Related model class or string reference
            related_name: Name of reverse relation field
            on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
            required: Whether relation is required
            **options: Additional field options
        """
        super().__init__(
            model,
            RelationType.ONE_TO_MANY,
            related_name=related_name,
            on_delete=on_delete,
            required=required,
            lazy=True,
            **options,
        )
