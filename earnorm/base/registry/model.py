"""Model registry implementation."""

from typing import Dict, List, Optional, Type, TypeVar, cast

from earnorm.base.fields.metadata import FieldMetadata
from earnorm.base.recordset.recordset import RecordSet
from earnorm.base.types import ModelProtocol

T = TypeVar("T", bound=ModelProtocol)


class ModelRegistry:
    """Model registry.

    This class manages model registration and metadata:
    - Stores mapping between model names and classes
    - Manages field metadata for each model
    - Creates record sets for querying

    Attributes:
        _models: Dict mapping model names to model classes
        _metadata: Dict mapping model names to field metadata
    """

    def __init__(self) -> None:
        """Initialize registry."""
        self._models: Dict[str, Type[ModelProtocol]] = {}
        self._metadata: Dict[str, Dict[str, FieldMetadata]] = {}

    def register(self, model: Type[ModelProtocol]) -> None:
        """Register model.

        Args:
            model: Model class to register

        Raises:
            ValueError: If model name is missing or already registered
            TypeError: If model does not implement ModelProtocol

        Example:
            >>> registry = ModelRegistry()
            >>> registry.register(UserModel)
        """
        # Check if model implements required attributes
        required_attrs = ["_name", "_abstract"]
        for attr in required_attrs:
            if not hasattr(model, attr):
                raise TypeError(f"model must have {attr} attribute")

        model_name = model.get_name()
        if getattr(model, "_abstract", False):
            return

        if not model_name:
            raise ValueError("Model name is required")

        if model_name in self._models:
            raise ValueError(f"Model {model_name} already registered")

        self._models[model_name] = model

    def get(self, name: str) -> Optional[Type[ModelProtocol]]:
        """Get model by name.

        Args:
            name: Model name

        Returns:
            Model class if found, None otherwise

        Raises:
            ValueError: If model name is empty

        Example:
            >>> registry = ModelRegistry()
            >>> user_model = registry.get("user")
        """
        if not name:
            raise ValueError("Model name cannot be empty")
        return self._models.get(name)

    def get_all(self) -> List[Type[ModelProtocol]]:
        """Get all models.

        Returns:
            List of all registered model classes

        Example:
            >>> registry = ModelRegistry()
            >>> all_models = registry.get_all()
        """
        return list(self._models.values())

    def add_metadata(
        self, model_name: str, field_name: str, metadata: FieldMetadata
    ) -> None:
        """Add field metadata.

        Args:
            model_name: Name of the model
            field_name: Name of the field
            metadata: Field metadata

        Raises:
            ValueError: If model name or field name is empty

        Example:
            >>> registry = ModelRegistry()
            >>> metadata = FieldMetadata(...)
            >>> registry.add_metadata("user", "email", metadata)
        """
        if not model_name:
            raise ValueError("Model name cannot be empty")
        if not field_name:
            raise ValueError("Field name cannot be empty")

        if model_name not in self._metadata:
            self._metadata[model_name] = {}

        self._metadata[model_name][field_name] = metadata

    def get_metadata(self, model_name: str) -> Dict[str, FieldMetadata]:
        """Get model metadata.

        Args:
            model_name: Name of the model

        Returns:
            Dict mapping field names to metadata

        Raises:
            ValueError: If model name is empty

        Example:
            >>> registry = ModelRegistry()
            >>> metadata = registry.get_metadata("user")
        """
        if not model_name:
            raise ValueError("Model name cannot be empty")
        return self._metadata.get(model_name, {})

    def create_recordset(self, model_name: str, records: List[T]) -> RecordSet[T]:
        """Create record set.

        Args:
            model_name: Name of the model
            records: List of model instances

        Returns:
            RecordSet instance for querying

        Raises:
            ValueError: If model name is empty or model is not found

        Example:
            >>> registry = ModelRegistry()
            >>> users = [User(...), User(...)]
            >>> recordset = registry.create_recordset("user", users)
        """
        if not model_name:
            raise ValueError("Model name cannot be empty")

        model_cls = self.get(model_name)
        if not model_cls:
            raise ValueError(f"Model {model_name} not found")

        return RecordSet(cast(Type[T], model_cls), records)
