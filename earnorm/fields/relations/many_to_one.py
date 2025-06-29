"""Many-to-one relation field implementation.

This module provides the ManyToOneField class for defining many-to-one relations in EarnORM.
It allows multiple records in the source model to reference one record in the target model.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields.relations import ManyToOneField

    >>> class User(BaseModel):
    ...     _name = 'res.user'

    >>> class Post(BaseModel):
    ...     _name = 'res.post'
    ...     author = ManyToOneField(
    ...         'res.user',  # Using string reference
    ...         related_name='posts',
    ...         on_delete='CASCADE'
    ...     )

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
    >>> author = await post1.author
    >>> posts = await user.posts
"""

from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationType

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


class ManyToOneField(RelationField[T], Generic[T]):
    """Field for many-to-one relations.

    This field allows multiple records in the source model to reference one record
    in the target model. It automatically creates a reverse one-to-many relation field
    on the target model.

    Args:
        model: Related model class or string reference
        related_name: Name of reverse relation field
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        required: Whether relation is required
        help: Help text for the field
        **options: Additional field options

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.user'

        >>> class Post(BaseModel):
        ...     _name = 'res.post'
        ...     author = ManyToOneField(
        ...         'res.user',  # Using string reference
        ...         related_name='posts',
        ...         on_delete='CASCADE'
        ...     )

        >>> # Create related records
        >>> user = await User.create({'name': 'John'})
        >>> post = await Post.create({
        ...     'author': user,
        ...     'title': 'First post'
        ... })

        >>> # Access related records
        >>> author = await post.author
        >>> posts = await user.posts
    """

    field_type = "many2one"

    def __init__(
        self,
        model: ModelType[T],
        *,
        related_name: str | None = None,
        on_delete: str = "CASCADE",
        required: bool = False,
        help: str | None = None,
        **options: dict[str, Any],
    ) -> None:
        field_options = cast(
            dict[str, Any],
            {
                **options,
                "index": True,
            },
        )
        super().__init__(
            model,
            RelationType.MANY_TO_ONE,
            related_name=related_name,
            on_delete=on_delete,
            required=required,
            lazy=True,
            help=help,
            **field_options,
        )

    def __set__(self, instance: Any, value: T | None) -> None:
        """Set related record.

        Args:
            instance: Model instance
            value: Related record or None

        Examples:
            >>> post = Post()
            >>> user = User()
            >>> post.author = user  # Sets relation
        """
        super().__set__(instance, value)
