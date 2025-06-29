"""Many-to-many relation field implementation.

This module provides the ManyToManyField class for defining many-to-many relations in EarnORM.
It allows multiple records in the source model to reference multiple records in the target model.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields.relations import ManyToManyField

    >>> class User(BaseModel):
    ...     _name = 'res.user'
    ...     roles = ManyToManyField(
    ...         'res.role',  # Using string reference
    ...         related_name='users',
    ...         through='UserRole'
    ...     )

    >>> class Role(BaseModel):
    ...     _name = 'res.role'

    >>> class UserRole(BaseModel):
    ...     _name = 'res.user.role'
    ...     user = ManyToOneField('res.user')
    ...     role = ManyToOneField('res.role')
    ...     assigned_at = DateTimeField()

    >>> # Create related records
    >>> user = await User.create({'name': 'John'})
    >>> admin = await Role.create({'name': 'Admin'})
    >>> editor = await Role.create({'name': 'Editor'})

    >>> # Add roles to user
    >>> await user.roles.add(admin)
    >>> await user.roles.add(editor)

    >>> # Access related records
    >>> roles = await user.roles
    >>> users = await admin.users
"""

import logging
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from earnorm.fields.relations.base import ModelType, RelationField
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationType, RelationOptions

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)


class ManyToManyDescriptor(Generic[T]):
    """Descriptor for Many-to-Many field access.

    This descriptor returns a ManyToManyManager instead of the field value,
    allowing for M2M operations like add(), remove(), all().
    """

    def __init__(self, field: "ManyToManyField[T]") -> None:
        """Initialize M2M descriptor.

        Args:
            field: M2M field instance
        """
        self.field = field
        self._managers: dict[str, "ManyToManyManager[T]"] = {}

    def __get__(self, instance: Any | None, owner: type | None = None) -> "ManyToManyManager[T]":
        """Get M2M manager for the instance.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            M2M manager for this field
        """
        if instance is None:
            return self  # type: ignore

        # Get or create manager for this instance
        instance_id = getattr(instance, 'id', id(instance))
        if instance_id not in self._managers:
            self._managers[instance_id] = ManyToManyManager(instance, self.field)

        return self._managers[instance_id]

    def __set__(self, instance: Any, value: Any) -> None:
        """Set M2M relationships.

        Args:
            instance: Model instance
            value: Related records to set
        """
        # Get manager and set relationships
        manager = self.__get__(instance, type(instance))
        # This will be handled by the manager's _set_related method
        # For now, we'll just log a warning
        logging.getLogger(__name__).warning(
            "Direct assignment to M2M field not supported. Use manager.add() or manager.clear() instead."
        )


class ManyToManyManager(Generic[T]):
    """Manager for Many-to-Many relationship operations.

    This class provides methods for managing M2M relationships:
    - add(): Add related records
    - remove(): Remove related records
    - all(): Get all related records
    - clear(): Remove all related records
    - count(): Count related records
    """

    def __init__(
        self,
        instance: Any,
        field: "ManyToManyField[T]",
    ) -> None:
        """Initialize M2M manager.

        Args:
            instance: Source model instance
            field: M2M field instance
        """
        self.instance = instance
        self.field = field
        self.logger = logging.getLogger(__name__)

    async def add(self, *records: T | list[T]) -> None:
        """Add related records to M2M relationship.

        Args:
            *records: Records to add (can be single records or lists)

        Examples:
            >>> await book.authors.add(author1)
            >>> await book.authors.add(author1, author2)
            >>> await book.authors.add([author1, author2])
        """
        if not records:
            return

        # Flatten records list
        all_records = []
        for record in records:
            if isinstance(record, list):
                all_records.extend(record)
            else:
                all_records.append(record)

        if not all_records:
            return

        # Get current related records
        current_records = await self.all()
        current_ids = {r.id for r in current_records} if current_records else set()

        # Filter out already related records
        new_records = [r for r in all_records if r.id not in current_ids]

        if not new_records:
            self.logger.info("All records already related, nothing to add")
            return

        # Add new records
        all_related = list(current_records) + new_records if current_records else new_records
        await self._set_related(all_related)

        self.logger.info(f"Added {len(new_records)} records to M2M relationship")

    async def remove(self, *records: T | list[T]) -> None:
        """Remove related records from M2M relationship.

        Args:
            *records: Records to remove (can be single records or lists)

        Examples:
            >>> await book.authors.remove(author1)
            >>> await book.authors.remove(author1, author2)
            >>> await book.authors.remove([author1, author2])
        """
        if not records:
            return

        # Flatten records list
        all_records = []
        for record in records:
            if isinstance(record, list):
                all_records.extend(record)
            else:
                all_records.append(record)

        if not all_records:
            return

        # Get current related records
        current_records = await self.all()
        if not current_records:
            self.logger.info("No related records to remove")
            return

        # Filter out records to remove - FIXED: Correct logic
        remove_ids = {r.id for r in all_records}
        self.logger.debug(f"Records to remove IDs: {remove_ids}")
        self.logger.debug(f"Current record IDs: {[r.id for r in current_records]}")

        remaining_records = [r for r in current_records if r.id not in remove_ids]
        self.logger.debug(f"Remaining record IDs: {[r.id for r in remaining_records]}")

        # Set remaining records
        await self._set_related(remaining_records)

        removed_count = len(current_records) - len(remaining_records)
        self.logger.info(f"Removed {removed_count} records from M2M relationship")

    async def all(self) -> list[T]:
        """Get all related records.

        Returns:
            List of related records (may be empty)

        Examples:
            >>> authors = await book.authors.all()
            >>> for author in authors:
            ...     print(await author.name)
        """
        try:
            # Get related records using adapter
            records = await self._get_related()
            return records

        except Exception as e:
            self.logger.error(f"Error getting M2M records: {e}")
            return []

    async def clear(self) -> None:
        """Remove all related records from M2M relationship.

        Examples:
            >>> await book.authors.clear()
        """
        await self._set_related([])
        self.logger.info("Cleared all M2M relationships")

    async def count(self) -> int:
        """Count related records.

        Returns:
            Number of related records

        Examples:
            >>> count = await book.authors.count()
            >>> print(f"Book has {count} authors")
        """
        records = await self.all()
        return len(records)

    async def _set_related(self, records: list[T]) -> None:
        """Set related records using database adapter.

        Args:
            records: Records to set as related
        """
        if not self.field.env:
            raise RuntimeError("Environment not set")

        # Create relation options
        options = RelationOptions(
            model=cast(type[ModelProtocol] | str, self.field._model_ref),
            related_name=self.field.related_name or "",
            on_delete=self.field.on_delete,
            through=None,
            through_fields=None,
        )

        # Set related records in database
        await self.field.env.adapter.set_related(
            self.instance,
            self.field.name,
            records,
            RelationType.MANY_TO_MANY,
            options,
        )

    async def _get_related(self) -> list[T]:
        """Get related records from database.

        Returns:
            List of related records
        """
        try:
            from earnorm.types.relations import RelationOptions, RelationType
            from typing import cast
            from earnorm.types.models import ModelProtocol

            # Create relation options
            options = RelationOptions(
                model=cast(type[ModelProtocol] | str, self.field._model_ref),
                related_name=self.field.related_name or "",
                on_delete=self.field.on_delete,
                through=None,
                through_fields=None
            )

            # Get related records using adapter
            records = await self.field.env.adapter.get_related(
                instance=self.instance,
                field_name=self.field.name,
                relation_type=RelationType.MANY_TO_MANY,
                options=options
            )

            # Convert to list if needed
            if isinstance(records, list):
                return records
            elif hasattr(records, '_ids') and hasattr(records, '_browse'):
                # This is a recordset - check this BEFORE checking _name
                # Use its iteration to get individual records
                result = list(records)  # This will use the recordset's __iter__ method
                return result
            elif hasattr(records, '_name'):
                # Single model instance - return as list
                return [records]
            elif hasattr(records, '__iter__') and not isinstance(records, str):
                # Regular iterable
                result = list(records)
                return result
            elif records:
                # Single record
                return [records]
            else:
                return []

        except Exception as e:
            self.logger.error(f"Error getting related records: {e}")
            return []


class ManyToManyField(RelationField[T], Generic[T]):
    """Field for many-to-many relations.

    This field allows multiple records in the source model to reference multiple records
    in the target model. It automatically creates a reverse many-to-many relation field
    on the target model.

    Args:
        model: Related model class or string reference
        related_name: Name of reverse relation field
        through: Through model for custom fields
        through_fields: Field names in through model (local_field, foreign_field)
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        required: Whether relation is required
        help: Help text for the field
        **options: Additional field options

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.user'
        ...     roles = ManyToManyField(
        ...         'res.role',  # Using string reference
        ...         related_name='users',
        ...         through='UserRole'
        ...     )

        >>> # Create related records
        >>> user = await User.create({'name': 'John'})
        >>> admin = await Role.create({'name': 'Admin'})
        >>> editor = await Role.create({'name': 'Editor'})

        >>> # Add roles to user
        >>> await user.roles.add(admin)
        >>> await user.roles.add(editor)

        >>> # Access related records
        >>> roles = await user.roles
        >>> users = await admin.users
    """

    field_type = "many2many"

    def __init__(
        self,
        model: ModelType[T],
        *,
        related_name: str | None = None,
        through: type[ModelProtocol] | None = None,
        through_fields: tuple[str, str] | None = None,
        on_delete: str = "CASCADE",
        required: bool = False,
        help: str | None = None,
        **options: dict[str, Any],
    ) -> None:
        """Initialize many-to-many field.

        Args:
            model: Related model class or string reference
            related_name: Name of reverse relation field
            through: Through model for custom fields
            through_fields: Field names in through model (local_field, foreign_field)
            on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
            required: Whether relation is required
            help: Help text for the field
            **options: Additional field options
        """
        field_options = {**options}
        if through is not None:
            field_options["through"] = cast(dict[str, Any], {"model": through})
        if through_fields is not None:
            field_options["through_fields"] = cast(dict[str, Any], {"fields": through_fields})

        super().__init__(
            model,
            RelationType.MANY_TO_MANY,
            related_name=related_name,
            on_delete=on_delete,
            required=required,
            help=help,
            lazy=True,
            **field_options,
        )

    def __set_name__(self, owner: type, name: str) -> None:
        """Set field name and create descriptor.

        This is called when the field is assigned to a class attribute.
        We use this to replace the field with a descriptor.
        """
        # Set field name manually (since RelationField doesn't have __set_name__)
        self.name = name
        self.model_name = getattr(owner, '_name', owner.__name__.lower())

        # Create and set the descriptor
        descriptor = ManyToManyDescriptor(self)
        setattr(owner, name, descriptor)

    @classmethod
    def add_to_model(cls, model_class: type, field_name: str, target_model, **kwargs) -> "ManyToManyDescriptor":
        """Helper method to add ManyToMany field to a model dynamically.

        This ensures proper field name setting and descriptor creation.

        Args:
            model_class: The model class to add the field to
            field_name: Name of the field
            target_model: The target model for the relationship
            **kwargs: Field initialization arguments

        Returns:
            The created ManyToMany descriptor

        Example:
            >>> Product.tags_m2m = ManyToManyField.add_to_model(Product, 'tags_m2m', Tag, related_name='products')
        """
        field = cls(target_model, **kwargs)
        field.name = field_name
        field.model_name = getattr(model_class, '_name', model_class.__name__.lower())

        # Set environment if model class has one
        if hasattr(model_class, '_env') and model_class._env:
            field.env = model_class._env

        # Create and set the descriptor directly
        descriptor = ManyToManyDescriptor(field)
        setattr(model_class, field_name, descriptor)

        # Also add to __fields__ if it exists
        if hasattr(model_class, '__fields__'):
            model_class.__fields__[field_name] = field

        return descriptor
