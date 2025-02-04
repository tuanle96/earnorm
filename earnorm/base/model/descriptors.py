"""Model descriptors.

This module contains descriptors used by models to implement
special attribute access behavior.

Currently supported descriptors:
- FieldsDescriptor: Access model fields through __fields__ attribute
"""

from typing import Any, Dict, Optional

from earnorm.fields import BaseField


class FieldsDescriptor:
    """Descriptor for accessing model fields.

    This descriptor provides access to model fields through __fields__ attribute.
    It caches fields dictionary on first access.

    Examples:
        >>> class User(BaseModel):
        ...     name = fields.StringField()
        >>> user = User()
        >>> print(user.__fields__["name"])  # Access field
    """

    def __get__(
        self, obj: Any, objtype: Optional[type] = None
    ) -> Dict[str, BaseField[Any]]:
        """Get fields dictionary.

        Args:
            obj: Model instance
            objtype: Model class

        Returns:
            Dictionary mapping field names to field instances
        """
        if objtype is None:
            objtype = type(obj)

        # Get fields from class attributes
        fields_dict: Dict[str, BaseField[Any]] = {}
        for key, value in objtype.__dict__.items():
            if isinstance(value, BaseField):
                fields_dict[key] = value

        return fields_dict
