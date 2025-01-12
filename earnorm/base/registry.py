"""Model registry management."""

from typing import Dict, Optional, Type

from .model import BaseModel


class Registry:
    """Model registry for managing all models in the system."""

    def __init__(self):
        self._models: Dict[str, Type[BaseModel]] = {}
        self._env = None

    def register_model(self, name: str, model: Type[BaseModel]) -> None:
        """Register a model with the given name."""
        self._models[name] = model

    def get_model(self, name: str) -> Optional[Type[BaseModel]]:
        """Get a model by name."""
        return self._models.get(name)

    def set_env(self, env) -> None:
        """Set the environment for all models."""
        self._env = env
        for model in self._models.values():
            model._env = env

    def __getitem__(self, name: str) -> Type[BaseModel]:
        """Get a model by name using dict-like syntax."""
        model = self.get_model(name)
        if model is None:
            raise KeyError(f"Model {name} not found in registry")
        return model

    @property
    def env(self):
        """Get the current environment."""
        return self._env


# Global registry instance
registry = Registry()
