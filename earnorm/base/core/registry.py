"""Model registry for EarnORM."""

from typing import Dict, Optional, Type

from .model import BaseModel


class Registry:
    """Registry for model classes."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._models: Dict[str, Type[BaseModel]] = {}

    def register(self, model_cls: Type[BaseModel]) -> None:
        """Register model class.

        Args:
            model_cls: Model class to register
        """
        self._models[model_cls.get_collection()] = model_cls

    def unregister(self, model_cls: Type[BaseModel]) -> None:
        """Unregister model class.

        Args:
            model_cls: Model class to unregister
        """
        if model_cls.get_collection() in self._models:
            del self._models[model_cls.get_collection()]

    def get(self, collection: str) -> Optional[Type[BaseModel]]:
        """Get model class by collection name.

        Args:
            collection: Collection name

        Returns:
            Model class or None if not found
        """
        return self._models.get(collection)

    def __getitem__(self, collection: str) -> Type[BaseModel]:
        """Get model class by collection name.

        Args:
            collection: Collection name

        Returns:
            Model class

        Raises:
            KeyError: If model not found
        """
        model_cls = self.get(collection)
        if model_cls is None:
            raise KeyError(f"Model not found: {collection}")
        return model_cls

    def __contains__(self, collection: str) -> bool:
        """Check if collection exists.

        Args:
            collection: Collection name

        Returns:
            bool: True if collection exists
        """
        return collection in self._models

    def __iter__(self):
        """Iterate over registered models.

        Yields:
            tuple: (collection, model_cls)
        """
        return iter(self._models.items())

    def __len__(self) -> int:
        """Get number of registered models.

        Returns:
            int: Number of models
        """
        return len(self._models)


# Global registry instance
registry = Registry()
