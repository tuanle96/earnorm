"""Model descriptors.

This module contains descriptors used by models to implement
special attribute access behavior.

Currently supported descriptors:
- FieldsDescriptor: Access model fields through __fields__ attribute
"""

from typing import Any, Dict, Type

from earnorm.fields import BaseField


class FieldsDescriptor:
    """Descriptor for accessing model fields.

    This descriptor provides access to model fields through __fields__ attribute.
    It works both on class level and instance level.

    Examples:
        >>> class MyModel(BaseModel):
        ...     name = StringField()
        ...     age = IntegerField()
        ...
        >>> # Class level access
        >>> MyModel.__fields__  # {'name': StringField(...), 'age': IntegerField(...)}
        >>> # Instance level access
        >>> instance = MyModel()
        >>> instance.__fields__  # Same as class level
    """

    def __get__(self, instance: Any, owner: Type[Any]) -> Dict[str, BaseField[Any]]:
        """Get fields dictionary.

        Args:
            instance: Model instance or None
            owner: Model class

        Returns:
            Dictionary mapping field names to field instances
        """
        # Return fields from class
        return owner.fields
