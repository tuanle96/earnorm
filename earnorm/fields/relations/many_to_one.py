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
"""

from typing import TYPE_CHECKING, Any, Generic, List, Optional, TypeVar, Union, cast

from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.fields import DatabaseValue
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
    in the target model.

    Args:
        model: Related model class or string reference
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        required: Whether relation is required
        help: Help text for the field
        **options: Additional field options

    Raises:
        ValueError: If on_delete value is invalid
        RuntimeError: If environment is not set

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.user'

        >>> class Post(BaseModel):
        ...     _name = 'res.post'
        ...     author = ManyToOneField(
        ...         'res.user',  # Using string reference
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
    """

    field_type = "many2one"

    def __init__(
        self,
        model: ModelType[T],
        *,
        on_delete: str = "CASCADE",
        required: bool = False,
        help: Optional[str] = None,
        **options: Any,
    ) -> None:
        """Initialize many-to-one field.

        Args:
            model: Related model class or string reference
            on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
            required: Whether relation is required
            help: Help text for the field
            **options: Additional field options

        Raises:
            ValueError: If on_delete value is invalid
        """
        if on_delete not in ("CASCADE", "SET_NULL", "PROTECT"):
            raise ValueError(
                f"Invalid on_delete value: {on_delete}. "
                "Must be one of: CASCADE, SET_NULL, PROTECT"
            )

        field_options = {
            **options,
            "index": True,
        }

        super().__init__(
            model,
            RelationType.MANY_TO_ONE,
            related_name=None,
            on_delete=on_delete,
            required=required,
            lazy=True,
            help=help,
            **field_options,
        )

    def __set__(self, instance: Any, value: Optional[T]) -> None:
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

    async def to_db(self, value: Optional[T], backend: str) -> DatabaseValue:
        """Convert model instance to database ID.

        Args:
            value: Model instance or ID string or None
            backend: Database backend type

        Returns:
            String ID or None

        Raises:
            ValueError: If value is invalid or missing ID

        Examples:
            >>> user = User(id="123")
            >>> await field.to_db(user, "mongodb")  # From instance
            '123'
            >>> await field.to_db("123", "mongodb")  # From ID string
            '123'
        """
        if value is None:
            return None

        # Handle ID string
        if isinstance(value, str):
            return value

        # Handle model instance
        if not hasattr(value, "id"):
            raise ValueError(f"Invalid value for {self.name}: {value}")

        if value.id is None:  # type: ignore
            raise ValueError(f"Value {value} has no ID")

        return str(value.id)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[T]:
        """Convert database ID to model instance.

        Args:
            value: Database ID value
            backend: Database backend type

        Returns:
            Model instance or None

        Raises:
            RuntimeError: If model resolution fails
            ValueError: If database value is invalid

        Examples:
            >>> user = await field.from_db("123", "mongodb")
            >>> print(user.id)
            '123'
        """
        if value is None:
            return None

        if not isinstance(value, (str, int)):
            raise ValueError(f"Invalid database value for {self.name}: {value}")

        try:
            model = await self._resolve_model()
            return await model.browse(str(value))
        except Exception as e:
            raise RuntimeError(f"Failed to resolve model: {str(e)}") from e

    async def get_related(self, source_instance: Any) -> Optional[T]:
        """Get single related record for many-to-one relationship.

        Args:
            source_instance: Instance chứa reference (VD: Employee instance có reference đến Department)

        Returns:
            Related record (VD: Department instance được reference bởi Employee) hoặc None nếu không có reference

        Raises:
            RuntimeError: Nếu environment chưa được set
            ValueError: Nếu source_instance không hợp lệ hoặc giá trị từ database không hợp lệ
            DatabaseError: Nếu có lỗi khi truy cập database

        Examples:
            >>> employee = Employee.browse("emp_1")  # source_instance
            >>> department = await employee.department  # target_instance
            >>> print(department.name)  # "IT Department"
        """
        try:
            # 1. Validate environment
            if not self.env:
                raise RuntimeError(f"Environment not set for field {self.name}")

            # 2. Validate source instance
            if not hasattr(source_instance, "id") or not source_instance.id:
                self.env.logger.debug(
                    f"Source instance has no ID: {source_instance._name}",
                    extra={"field": self.name},
                )
                return None

            # 3. Get source record để lấy reference_id
            source_record = await self.env.adapter.read(
                store=str(source_instance._name),
                id_or_ids=source_instance.id,
                fields=[self.name],
            )

            if not source_record:
                self.env.logger.debug(
                    f"Source record not found: {source_instance._name}#{source_instance.id}",
                    extra={"field": self.name},
                )
                return None

            # 4. Lấy reference_id từ source record
            reference_id = source_record.get(self.name)
            if not reference_id:
                self.env.logger.debug(
                    f"No reference ID found for {self.name} in {source_instance._name}#{source_instance.id}"
                )
                return None

            # 5. Load target model class
            target_model = await self.get_model()

            # 6. Browse target record với reference_id
            target_instance = await target_model.browse(str(reference_id))

            # 7. Cache kết quả trong source instance
            if hasattr(source_instance, "_cache"):
                source_instance._cache[self.name] = target_instance

            return target_instance

        except Exception as e:
            self.env.logger.error(
                f"Error getting related record for {self.name}",
                extra={
                    "source_model": source_instance._name,
                    "source_id": source_instance.id,
                    "relation_field": self.name,
                    "error": str(e),
                },
            )
            raise

    async def set_related(
        self, source_instance: Any, value: Union[Optional[T], List[T]]
    ) -> None:
        """Set single related record.

        Args:
            source_instance: Model instance to set related record for
            value: Related record or None

        Raises:
            RuntimeError: If environment is not set
            ValueError: If value is a list or invalid
            ValidationError: If validation fails

        Examples:
            >>> post = Post()
            >>> user = User()
            >>> await post.author.set_related(post, user)
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        await self.validate(value)

        if isinstance(value, list):
            raise ValueError("ManyToOneField does not support multiple values")

        db_value = await self.to_db(
            cast(Optional[T], value), self.env.adapter.backend_type
        )
        setattr(source_instance, f"_{self.name}", db_value)

    async def delete_related(self, source_instance: Any) -> None:
        """Handle deletion based on on_delete policy.

        Args:
            source_instance: Model instance to delete related record for

        Raises:
            RuntimeError: If deletion fails
            ValueError: If instance is invalid

        Examples:
            >>> post = Post()
            >>> await post.author.delete_related(post)  # Handles based on on_delete
        """
        try:
            value = await self.get_related(source_instance)
            if value is None:
                return

            if self.on_delete == "CASCADE":
                await value.unlink()
            elif self.on_delete == "SET_NULL":
                await self.set_related(source_instance, None)
            # PROTECT is handled by database constraint
        except Exception as e:
            raise RuntimeError(f"Failed to delete related record: {str(e)}") from e
