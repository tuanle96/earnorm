"""Plugin system for EarnORM."""

import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar

from ..events.events import EventManager
from ..utils.singleton import Singleton

T = TypeVar("T", bound="Plugin")


class Plugin(ABC):
    """Base class for plugins."""

    def __init__(self) -> None:
        """Initialize plugin."""
        self.events = EventManager()
        self.config: Dict[str, Any] = {}

    @abstractmethod
    async def setup(self) -> None:
        """Set up plugin.

        This method is called when the plugin is loaded.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up plugin.

        This method is called when the plugin is unloaded.
        """
        pass

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure plugin.

        Args:
            config: Plugin configuration
        """
        self.config.update(config)


class PluginManager(metaclass=Singleton):
    """Manager for plugins."""

    def __init__(self) -> None:
        """Initialize plugin manager."""
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._plugin_order: List[str] = []

    def register_plugin(
        self,
        plugin_class: Type[T],
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> T:
        """Register plugin.

        Args:
            plugin_class: Plugin class
            name: Optional plugin name
            config: Optional plugin configuration

        Returns:
            Plugin: Plugin instance

        Raises:
            ValueError: If plugin is already registered
        """
        # Get plugin name
        plugin_name = name or plugin_class.__name__.lower()
        if plugin_name in self._plugins:
            raise ValueError(f"Plugin {plugin_name} is already registered")

        # Create plugin instance
        plugin = plugin_class()
        if config is not None:
            plugin.configure(config)

        # Store plugin
        self._plugins[plugin_name] = plugin
        self._plugin_configs[plugin_name] = config or {}
        self._plugin_order.append(plugin_name)

        return plugin

    def unregister_plugin(self, name: str) -> None:
        """Unregister plugin.

        Args:
            name: Plugin name

        Raises:
            ValueError: If plugin is not registered
        """
        if name not in self._plugins:
            raise ValueError(f"Plugin {name} is not registered")

        # Remove plugin
        del self._plugins[name]
        del self._plugin_configs[name]
        self._plugin_order.remove(name)

    def get_plugin(self, name: str) -> Plugin:
        """Get plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin: Plugin instance

        Raises:
            ValueError: If plugin is not registered
        """
        if name not in self._plugins:
            raise ValueError(f"Plugin {name} is not registered")
        return self._plugins[name]

    async def load_plugins(self) -> None:
        """Load all registered plugins."""
        for name in self._plugin_order:
            plugin = self._plugins[name]
            await plugin.setup()

    async def unload_plugins(self) -> None:
        """Unload all registered plugins."""
        for name in reversed(self._plugin_order):
            plugin = self._plugins[name]
            await plugin.cleanup()

    def load_plugin_from_path(
        self,
        path: str,
        class_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Plugin:
        """Load plugin from Python module path.

        Args:
            path: Python module path (e.g. "myapp.plugins.myplugin")
            class_name: Optional plugin class name
            config: Optional plugin configuration

        Returns:
            Plugin: Plugin instance

        Raises:
            ImportError: If module cannot be imported
            ValueError: If plugin class cannot be found
        """
        # Import module
        try:
            module = importlib.import_module(path)
        except ImportError as e:
            raise ImportError(f"Failed to import plugin module {path}: {str(e)}")

        # Find plugin class
        if class_name is not None:
            if not hasattr(module, class_name):
                raise ValueError(
                    f"Plugin class {class_name} not found in module {path}"
                )
            plugin_class = getattr(module, class_name)
        else:
            # Find first class that inherits from Plugin
            plugin_class = None
            for _, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, Plugin)
                    and obj is not Plugin
                ):
                    plugin_class = obj
                    break
            if plugin_class is None:
                raise ValueError(f"No plugin class found in module {path}")

        # Register plugin
        return self.register_plugin(plugin_class, config=config)

    def get_plugin_names(self) -> List[str]:
        """Get list of registered plugin names.

        Returns:
            List[str]: List of plugin names
        """
        return self._plugin_order.copy()

    def get_plugin_config(self, name: str) -> Dict[str, Any]:
        """Get plugin configuration.

        Args:
            name: Plugin name

        Returns:
            dict: Plugin configuration

        Raises:
            ValueError: If plugin is not registered
        """
        if name not in self._plugin_configs:
            raise ValueError(f"Plugin {name} is not registered")
        return self._plugin_configs[name].copy()

    def set_plugin_config(self, name: str, config: Dict[str, Any]) -> None:
        """Set plugin configuration.

        Args:
            name: Plugin name
            config: Plugin configuration

        Raises:
            ValueError: If plugin is not registered
        """
        if name not in self._plugins:
            raise ValueError(f"Plugin {name} is not registered")

        # Update config
        self._plugin_configs[name] = config.copy()
        self._plugins[name].configure(config)
