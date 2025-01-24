"""Model registry for managing models.

This module provides a registry for managing models.
It supports lifecycle management and dependency injection.

Examples:
    >>> from earnorm.registry import ModelRegistry
    >>> from earnorm.di import container
    >>>
    >>> # Get registry instance
    >>> registry = await container.get("model_registry")
    >>>
    >>> # Register model
    >>> @ModelRegistry.register_model
    ... class User:
    ...     name: str
    ...     age: int
    >>>
    >>> # Get model
    >>> User = await registry.get("User")
"""

from typing import Any, Dict, Optional, Type, TypeVar, cast

from earnorm.base.model import BaseModel
from earnorm.di import container
from earnorm.di.lifecycle import LifecycleAware
from earnorm.registry.base import Registry

T = TypeVar("T", bound=BaseModel)


class ModelLifecycle(LifecycleAware):
    """Lifecycle wrapper for model classes.

    This class wraps model classes to make them lifecycle-aware.
    It provides lifecycle management for model registration and cleanup.
    """

    def __init__(self, model: Type[BaseModel]) -> None:
        """Initialize model lifecycle.

        Args:
            model: Model class to wrap
        """
        self._model = model
        self._id = model.__name__
        self._data = {
            "type": "model",
            "name": model.__name__,
            "table": getattr(model, "_table", None),
            "description": getattr(model, "_description", None),
        }

    @property
    def id(self) -> str:
        """Get model ID."""
        return self._id

    @property
    def data(self) -> Dict[str, Any]:
        """Get model metadata."""
        return self._data

    async def init(self) -> None:
        """Initialize model.

        This method is called when the model is registered.
        It can be used to create database tables, indexes, etc.
        """
        pass

    async def destroy(self) -> None:
        """Cleanup model.

        This method is called when the model is unregistered.
        It can be used to cleanup resources, drop tables, etc.
        """
        pass

    @property
    def model(self) -> Type[BaseModel]:
        """Get wrapped model class."""
        return self._model


class ModelRegistry(Registry[ModelLifecycle]):
    """Model registry for managing models.

    This class provides lifecycle-aware model registration and retrieval.
    It integrates with the DI container for dependency management.

    Examples:
        >>> registry = ModelRegistry()
        >>> await container.register("model_registry", registry)
        >>>
        >>> # Register model
        >>> class User(BaseModel):
        ...     name: str
        ...     age: int
        >>> await registry.register("User", User)
        >>>
        >>> # Get model
        >>> User = await registry.get("User")
    """

    def __init__(self) -> None:
        """Initialize registry."""
        super().__init__()
        self._id = "model_registry"
        self._data = {"type": "model", "description": "Registry for ORM models"}

    @property
    def id(self) -> str:
        """Get registry ID.

        Returns:
            Registry identifier
        """
        return self._id

    @property
    def data(self) -> Dict[str, Any]:
        """Get registry data.

        Returns:
            Registry metadata
        """
        return self._data

    async def init(self) -> None:
        """Initialize registry.

        This method is called by the lifecycle manager during initialization.
        """
        # Register self in container
        self._container.register("model_registry", self)

    async def destroy(self) -> None:
        """Cleanup registry.

        This method is called by the lifecycle manager during cleanup.
        """
        # Clear all caches
        await self.clear_caches()

        # Clear all options
        self._options.clear()

        # Reset default
        self._default = None

    async def register(
        self, name: str, instance: Type[ModelLifecycle], **options: Any
    ) -> None:
        """Register model.

        Args:
            name: Model name
            instance: Model lifecycle class
            **options: Additional options
                - abstract: Whether model is abstract
                - transient: Whether records are temporary
                - auto: Whether to create database table
                - table: Database table name
                - sequence: Sequence for ID generation
                - inherit: Parent model(s) to inherit from
                - inherits: Parent models to delegate to
                - order: Default ordering
                - rec_name: Field to use for record name

        Raises:
            ValueError: If model already registered

        Examples:
            >>> class User(BaseModel):
            ...     name: str
            ...     age: int
            >>> await registry.register("User", User)
        """
        if await self.has(name):
            raise ValueError(f"Model {name} already registered")

        # Create and initialize instance
        lifecycle = instance(cast(Type[BaseModel], instance))
        await lifecycle.init()

        # Store model options
        self._options[name] = options

        # Store model class in container
        self._container.register(name, lifecycle)

        # Set as default if first model
        if not self._default:
            await self.set_default(name)

    async def unregister(self, name: str) -> None:
        """Unregister model.

        Args:
            name: Model name

        Examples:
            >>> await registry.unregister("User")
        """
        if await self.has(name):
            try:
                # Get lifecycle
                lifecycle = await self._container.get(name)

                # Cleanup lifecycle
                await lifecycle.destroy()
            except KeyError:
                pass  # Model already removed
            finally:
                # Remove options
                del self._options[name]

                # Reset default if needed
                if self._default == name:
                    self._default = None

    async def get(self, name: Optional[str] = None) -> ModelLifecycle:
        """Get model by name.

        Args:
            name: Model name (optional)
                If None, returns default model

        Returns:
            Model lifecycle instance

        Raises:
            KeyError: If model not found
            RuntimeError: If no default model set when name is None

        Examples:
            >>> lifecycle = await registry.get("User")
            >>> User = lifecycle.model
            >>> DefaultModel = (await registry.get()).model  # Get default
        """
        # Get model name
        model_name = name
        if model_name is None:
            model_name = await self.get_default()
            if not model_name:
                raise RuntimeError("No default model set")

        # Get lifecycle from container
        try:
            return await self._container.get(model_name)
        except KeyError:
            raise KeyError(f"Model {model_name} not found")

    async def switch(self, name: str, **options: Any) -> None:
        """Switch default model.

        Args:
            name: Model name
            **options: Additional options

        Examples:
            >>> await registry.switch("User")
        """
        if not await self.has(name):
            raise ValueError(f"Model {name} not found")

        # Update options if provided
        if options:
            self._options[name].update(options)

        # Set as default
        await self.set_default(name)

    async def register_base_model(
        self, name: str, model: Type[BaseModel], **options: Any
    ) -> None:
        """Register a BaseModel class.

        This is a convenience method that wraps the model in a ModelLifecycle.

        Args:
            name: Model name
            model: Model class
            **options: Additional options
        """
        lifecycle = ModelLifecycle(model)
        await lifecycle.init()
        self._container.register(name, lifecycle)

        # Store model options and set default
        self._options[name] = options
        if not self._default:
            await self.set_default(name)

    @classmethod
    def register_model(
        cls, model: Optional[Type[T]] = None, *, name: Optional[str] = None
    ) -> Any:
        """Register model using decorator syntax.

        This method can be used as a decorator or called directly.

        Args:
            model: Model class to register
            name: Optional name for model, defaults to model class name

        Returns:
            Model class if used as decorator, None if called directly

        Examples:
            >>> # As decorator
            >>> @ModelRegistry.register_model
            ... class User(BaseModel):
            ...     name: str
            ...     age: int
            >>>
            >>> # Direct call
            >>> class User(BaseModel):
            ...     name: str
            ...     age: int
            >>> ModelRegistry.register_model(User)
        """

        async def _register(model_cls: Type[T]) -> Type[T]:
            # Get registry instance
            registry = await container.get("model_registry")

            # Register model
            model_name = name or model_cls.__name__
            await registry.register(model_name, model_cls)

            return model_cls

        if model is None:
            return _register
        return _register(model)
