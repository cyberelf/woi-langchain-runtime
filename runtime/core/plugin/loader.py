"""Plugin loader for loading agent and tool plugins from manifest files.

This module loads plugins by importing manifest files (__init__.py) from
plugin directories and reading their __agents__ or __tools__ lists.
"""

import importlib.util
import inspect
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Type

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a discovered plugin.
    
    Attributes:
        plugin_id: Unique identifier (template_id for agents, name for tools)
        name: Class name
        module_path: Python module path
        file_path: Absolute path to plugin file
        plugin_type: "agent" or "tool"
        class_obj: The plugin class object
        version: Plugin version (from __version__ or default "1.0.0")
        description: Plugin description (from docstring)
        source: Discovery source (e.g., "plugins/agents", "built-in")
    """
    plugin_id: str
    name: str
    module_path: str
    file_path: Path
    plugin_type: str
    class_obj: Type
    version: str = "1.0.0"
    description: str = ""
    source: str = "plugin"


class PluginLoader:
    """Loads plugins from manifest files in plugin directories.
    
    Each plugin directory should have an __init__.py with:
    - __agents__ list for agent plugins
    - __tools__ list for tool plugins
    
    Features:
    - Explicit plugin registration via manifest
    - Validates classes against contracts
    - Clear error messages for misconfigured plugins
    
    Args:
        plugin_dirs: List of directories containing __init__.py manifests
        validator: Validation function to check plugin classes
        plugin_type: Type label ("agent" or "tool")
        manifest_attr: Attribute name in __init__.py ("__agents__" or "__tools__")
    """
    
    def __init__(
        self,
        plugin_dirs: list[Path],
        validator: Callable[[Type], bool],
        plugin_type: str,
        manifest_attr: str
    ):
        self.plugin_dirs = plugin_dirs
        self.validator = validator
        self.plugin_type = plugin_type
        self.manifest_attr = manifest_attr
        self.discovered_plugins: dict[str, PluginMetadata] = {}
        
    def discover_plugins(self) -> dict[str, PluginMetadata]:
        """Load all plugins from manifest files.
        
        Returns:
            Dict mapping plugin IDs to metadata
        """
        discovered = {}
        
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                logger.debug(f"Plugin directory does not exist: {plugin_dir}")
                continue
                
            if not plugin_dir.is_dir():
                logger.warning(f"Plugin path is not a directory: {plugin_dir}")
                continue
            
            # Check for __init__.py manifest
            init_file = plugin_dir / "__init__.py"
            if not init_file.exists():
                logger.warning(
                    f"No manifest file (__init__.py) found in {plugin_dir}. "
                    f"Skipping {self.plugin_type} discovery."
                )
                continue
            
            logger.info(f"Loading {self.plugin_type} plugins from manifest: {init_file}")
            
            try:
                plugins = self._load_plugins_from_manifest(plugin_dir, init_file)
                discovered.update(plugins)
            except Exception as e:
                logger.error(f"Failed to load plugins from {init_file}: {e}", exc_info=True)
                    
        self.discovered_plugins = discovered
        logger.info(
            f"Loaded {len(discovered)} {self.plugin_type} plugin(s) "
            f"from {len(self.plugin_dirs)} directory(ies)"
        )
        return discovered
    
    def _load_plugins_from_manifest(self, plugin_dir: Path, init_file: Path) -> dict[str, PluginMetadata]:
        """Load plugins from a manifest file.
        
        Args:
            plugin_dir: Directory containing the manifest
            init_file: Path to __init__.py manifest file
            
        Returns:
            Dict of plugin_id -> PluginMetadata
        """
        plugins = {}
        
        # Add parent directory to sys.path temporarily for relative imports
        parent_dir = str(plugin_dir.parent)
        path_added = False
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            path_added = True
        
        try:
            # Import the manifest module using the directory name
            module_name = plugin_dir.name
            spec = importlib.util.spec_from_file_location(module_name, init_file)
            
            if spec is None or spec.loader is None:
                logger.warning(f"Cannot create module spec for {init_file}")
                return plugins
                
            try:
                module = importlib.util.module_from_spec(spec)
                # Add to sys.modules temporarily for relative imports to work
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            except Exception as e:
                logger.error(f"Failed to import manifest {init_file}: {e}", exc_info=True)
                return plugins
            finally:
                # Clean up sys.modules
                if module_name in sys.modules:
                    del sys.modules[module_name]
        finally:
            # Remove from sys.path
            if path_added and parent_dir in sys.path:
                sys.path.remove(parent_dir)
        
        # Get the plugin list from manifest
        if not hasattr(module, self.manifest_attr):
            logger.warning(
                f"Manifest {init_file} does not define '{self.manifest_attr}'. "
                f"Expected a list of {self.plugin_type} classes."
            )
            return plugins
        
        plugin_list = getattr(module, self.manifest_attr)
        
        if not isinstance(plugin_list, list):
            logger.error(
                f"Manifest attribute '{self.manifest_attr}' in {init_file} "
                f"must be a list, got {type(plugin_list)}"
            )
            return plugins
        
        # Process each plugin class
        for idx, plugin_class in enumerate(plugin_list):
            if not inspect.isclass(plugin_class):
                logger.warning(
                    f"Item {idx} in {self.manifest_attr} is not a class: {plugin_class}"
                )
                continue
            
            # Validate the class
            if not self.validator(plugin_class):
                logger.error(
                    f"Plugin class {plugin_class.__name__} in {init_file} "
                    f"failed validation. Skipping."
                )
                continue
            
            # Extract plugin ID
            plugin_id = self._extract_plugin_id(plugin_class)
            if not plugin_id:
                logger.warning(
                    f"Cannot extract plugin ID from {plugin_class.__name__} in {init_file}"
                )
                continue
            
            # Check for duplicates within same manifest
            if plugin_id in plugins:
                logger.warning(
                    f"Duplicate plugin ID '{plugin_id}' in {init_file}. "
                    f"Using first occurrence."
                )
                continue
            
            # Create metadata
            plugins[plugin_id] = PluginMetadata(
                plugin_id=plugin_id,
                name=plugin_class.__name__,
                module_path=plugin_class.__module__,
                file_path=init_file,
                plugin_type=self.plugin_type,
                class_obj=plugin_class,
                version=getattr(plugin_class, '__version__', '1.0.0'),
                description=self._extract_description(plugin_class),
                source=str(plugin_dir)
            )
            logger.info(f"Loaded {self.plugin_type} plugin: {plugin_id} ({plugin_class.__name__})")
                
        return plugins
    
    def _extract_plugin_id(self, cls: Type) -> Optional[str]:
        """Extract plugin ID from class.
        
        For agents: use template_id attribute
        For tools: use name attribute (from Pydantic model fields if applicable)
        Fallback: lowercase class name
        """
        # Agent: template_id
        if hasattr(cls, 'template_id'):
            template_id = cls.template_id
            if isinstance(template_id, str):
                return template_id
        
        # Tool: name (check Pydantic model fields first)
        if hasattr(cls, 'model_fields') and 'name' in cls.model_fields:
            # Pydantic v2 model - get default value from field
            field = cls.model_fields['name']
            if field.default is not None and isinstance(field.default, str):
                return field.default
        elif hasattr(cls, '__fields__') and 'name' in cls.__fields__:
            # Pydantic v1 model - get default value from field
            field = cls.__fields__['name']
            if field.default is not None and isinstance(field.default, str):
                return field.default
        elif hasattr(cls, 'name'):
            # Regular class attribute (not Pydantic)
            name_val = cls.name
            if isinstance(name_val, str):
                return name_val
        
        # Fallback: class name in lowercase
        return cls.__name__.lower()
    
    def _extract_description(self, cls: Type) -> str:
        """Extract description from Pydantic field or class docstring."""
        # First try to get from Pydantic 'description' field (for tools)
        if hasattr(cls, 'model_fields') and 'description' in cls.model_fields:
            # Pydantic v2 model
            field = cls.model_fields['description']
            if field.default is not None and isinstance(field.default, str):
                return field.default
        elif hasattr(cls, '__fields__') and 'description' in cls.__fields__:
            # Pydantic v1 model
            field = cls.__fields__['description']
            if field.default is not None and isinstance(field.default, str):
                return field.default
        elif hasattr(cls, 'description'):
            # Regular class attribute
            desc = cls.description
            if isinstance(desc, str):
                return desc
        
        # Fallback to class docstring
        doc = inspect.getdoc(cls)
        if doc:
            # Return first line of docstring
            return doc.strip().split('\n')[0]
        return ""
