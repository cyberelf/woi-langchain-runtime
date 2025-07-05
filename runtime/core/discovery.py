"""Template Discovery System - Framework-agnostic template autodiscovery.

This module provides interfaces and implementations for discovering agent templates
across different underlying frameworks. It supports:
- File system scanning
- Dynamic module loading
- Hot-reload capabilities
- Multiple template formats
"""

import importlib
import inspect
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """Information about a discovered template."""

    template_class: type
    template_id: str
    template_name: str
    version: str
    module_path: str
    file_path: Path
    framework: str  # 'langchain', 'custom', etc.
    metadata: dict[str, Any]


class DiscoveryInterface(ABC):
    """Interface for template discovery implementations."""

    @abstractmethod
    async def discover_templates(self, scan_paths: list[Path]) -> list[TemplateInfo]:
        """Discover templates in the given paths."""
        pass

    @abstractmethod
    def supports_framework(self, framework: str) -> bool:
        """Check if this discovery mechanism supports the given framework."""
        pass

    @abstractmethod
    def get_template_info(self, template_class: type) -> Optional[TemplateInfo]:
        """Extract template information from a class."""
        pass


class TemplateDiscovery(DiscoveryInterface):
    """
    Main template discovery engine with multi-framework support.

    This implementation provides:
    - File system scanning for template modules
    - Dynamic loading and introspection
    - Framework detection and validation
    - Hot-reload support
    """

    def __init__(self, base_package: str = "runtime.template_agent"):
        self.base_package = base_package
        self.discovered_templates: dict[str, TemplateInfo] = {}
        self.watched_paths: set[Path] = set()
        self.discovery_hooks: list[Callable[[TemplateInfo], None]] = []

        # Framework-specific discovery handlers
        self.framework_handlers = {
            "langchain": self._discover_langchain_templates,
            "custom": self._discover_custom_templates,
        }

    async def discover_templates(self, scan_paths: list[Path]) -> list[TemplateInfo]:
        """
        Discover templates from the given paths using multiple strategies.

        Args:
            scan_paths: List of paths to scan

        Returns:
            List of discovered template information
        """
        templates = []

        # Strategy 1: File-based discovery
        for path in scan_paths:
            try:
                discovered = await self._scan_path(path)
                templates.extend(discovered)
            except Exception as e:
                logger.warning(f"File-based discovery failed for {path}: {e}")

        # Strategy 2: Inheritance-based discovery (fallback)
        if not templates:
            logger.info(
                "File-based discovery found no templates, falling back to inheritance-based discovery"
            )
            templates.extend(await self._inheritance_based_discovery())

        # Store discovered templates
        for template in templates:
            self.discovered_templates[template.template_id] = template

            # Call discovery hooks
            for hook in self.discovery_hooks:
                try:
                    hook(template)
                except Exception as e:
                    logger.warning(f"Discovery hook failed: {e}")

        logger.info(f"Discovered {len(templates)} templates")
        return templates

    async def _inheritance_based_discovery(self) -> list[TemplateInfo]:
        """
        Discover templates using class inheritance mechanism.

        This is a fallback when file-based discovery fails due to import issues.
        """
        templates = []

        try:
            # Import the base module to trigger template registrations
            from ..template_agent.base import get_all_agent_templates

            # Get all template classes
            template_classes = get_all_agent_templates()

            for template_class in template_classes:
                template_info = self.get_template_info(template_class)
                if template_info:
                    # Set some default values for inheritance-based discovery
                    template_info.module_path = f"{template_class.__module__}"
                    template_info.file_path = Path(f"{template_class.__module__.replace('.', '/')}.py")
                    templates.append(template_info)
                    logger.debug(f"Found template via inheritance: {template_info.template_id}")

        except Exception as e:
            logger.error(f"Inheritance-based discovery failed: {e}")

        return templates

    async def _scan_path(self, path: Path) -> list[TemplateInfo]:
        """
        Scan a single path (file or directory) for templates.

        Args:
            path: Path to scan

        Returns:
            List of discovered templates
        """
        templates = []

        logger.info(f"Scanning for templates in: {path}")

        if path.is_file() and path.suffix == ".py":
            # Single file
            template_infos = await self._scan_file(path)
            templates.extend(template_infos)
        elif path.is_dir():
            # Directory - scan recursively
            for py_file in path.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue  # Skip __init__.py and __pycache__

                template_infos = await self._scan_file(py_file)
                templates.extend(template_infos)

        return templates

    async def _scan_file(self, file_path: Path) -> list[TemplateInfo]:
        """Scan a single Python file for template classes."""
        templates = []

        try:
            # Convert file path to module path
            module_path = self._file_to_module_path(file_path)

            # Load the module
            module = await self._load_module(module_path)
            if not module:
                return templates

            # Inspect module for template classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if self._is_template_class(obj):
                    template_info = self.get_template_info(obj)
                    if template_info:
                        template_info.file_path = file_path
                        template_info.module_path = module_path
                        templates.append(template_info)
                        logger.debug(f"Found template: {template_info.template_id}")

        except Exception as e:
            logger.warning(f"Failed to scan {file_path}: {e}")

        return templates

    def _file_to_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path."""
        try:
            # Convert to absolute path for consistent handling
            abs_path = file_path.resolve()

            # Find the project root (where runtime/ is located)
            current = abs_path
            while current != current.parent:
                if (current / "runtime").exists():
                    # Found project root
                    rel_path = abs_path.relative_to(current)
                    module_path = str(rel_path.with_suffix("")).replace("/", ".")
                    return module_path
                current = current.parent

            # If we can't find project root, try using current working directory
            cwd = Path.cwd()
            if abs_path.is_relative_to(cwd):
                rel_path = abs_path.relative_to(cwd)
                module_path = str(rel_path.with_suffix("")).replace("/", ".")
                return module_path

            # Last fallback: construct from file path structure
            if "runtime/template_agent" in str(file_path):
                # Extract the part after runtime/template_agent
                parts = file_path.parts
                runtime_idx = None
                for i, part in enumerate(parts):
                    if part == "runtime":
                        runtime_idx = i
                        break

                if runtime_idx is not None:
                    module_parts = parts[runtime_idx:]
                    module_path = ".".join(module_parts[:-1]) + "." + file_path.stem
                    return module_path

            # Final fallback
            return f"{self.base_package}.{file_path.stem}"

        except Exception as e:
            logger.warning(f"Failed to convert file path to module path for {file_path}: {e}")
            # Fallback: use the base package + filename
            return f"{self.base_package}.{file_path.stem}"

    async def _load_module(self, module_path: str):
        """Dynamically load a module."""
        try:
            # Check if module is already loaded
            if module_path in sys.modules:
                return sys.modules[module_path]

            # Load the module
            module = importlib.import_module(module_path)
            return module

        except Exception as e:
            logger.warning(f"Failed to load module {module_path}: {e}")
            return None

    def _is_template_class(self, cls: type) -> bool:
        """Check if a class is a valid template class."""
        # Check if it's a subclass of BaseAgentTemplate
        try:
            from ..template_agent.base import BaseAgentTemplate

            return (
                inspect.isclass(cls)
                and issubclass(cls, BaseAgentTemplate)
                and not inspect.isabstract(cls)
                and cls is not BaseAgentTemplate
            )
        except ImportError:
            # Fallback: check for required template attributes
            return (
                inspect.isclass(cls)
                and hasattr(cls, "template_id")
                and hasattr(cls, "template_name")
                and hasattr(cls, "execute")
            )

    def get_template_info(self, template_class: type) -> Optional[TemplateInfo]:
        """Extract template information from a class."""
        try:
            # Detect framework
            framework = self._detect_framework(template_class)

            # Get template metadata
            metadata = template_class.get_metadata()
            template_id = metadata.template_id
            version = metadata.version
            extra_metadata = {
                "description": metadata.description,
                "config_schema": metadata.config_schema,
            }

            return TemplateInfo(
                template_class=template_class,
                template_id=template_id,
                template_name=metadata.name,
                version=version,
                module_path="",  # Will be set by caller
                file_path=Path(),  # Will be set by caller
                framework=framework,
                metadata=extra_metadata,
            )

        except Exception as e:
            logger.warning(f"Failed to extract template info from {template_class}: {e}")
            return None

    def _detect_framework(self, template_class: type) -> str:
        """Detect which framework a template class belongs to."""
        # Check for LangChain/LangGraph indicators
        if hasattr(template_class, "_build_graph"):
            return "langchain"

        # Check module path
        module = inspect.getmodule(template_class)
        if module:
            if "langchain" in module.__name__ or "langgraph" in module.__name__:
                return "langchain"

        # Default to custom
        return "custom"

    def supports_framework(self, framework: str) -> bool:
        """Check if this discovery mechanism supports the given framework."""
        return framework in self.framework_handlers

    async def _discover_langchain_templates(self, path: Path) -> list[TemplateInfo]:
        """Framework-specific discovery for LangChain templates."""
        # Implementation specific to LangChain templates
        return await self._scan_file(path)

    async def _discover_custom_templates(self, path: Path) -> list[TemplateInfo]:
        """Framework-specific discovery for custom templates."""
        # Implementation specific to custom templates
        return await self._scan_file(path)

    def add_discovery_hook(self, hook: Callable[[TemplateInfo], None]) -> None:
        """Add a hook that gets called when a template is discovered."""
        self.discovery_hooks.append(hook)

    def remove_discovery_hook(self, hook: Callable[[TemplateInfo], None]) -> None:
        """Remove a discovery hook."""
        if hook in self.discovery_hooks:
            self.discovery_hooks.remove(hook)

    def get_discovered_templates(self) -> dict[str, TemplateInfo]:
        """Get all discovered templates."""
        return self.discovered_templates.copy()

    def clear_cache(self) -> None:
        """Clear the discovered templates cache."""
        self.discovered_templates.clear()


# Hot-reload support class
class HotReloadDiscovery(TemplateDiscovery):
    """Template discovery with hot-reload capabilities."""

    def __init__(self, base_package: str = "runtime.template_agent"):
        super().__init__(base_package)
        self.file_mtimes: dict[Path, float] = {}

    async def watch_for_changes(self, scan_paths: list[Path]) -> list[TemplateInfo]:
        """Watch for file changes and reload templates."""
        changed_templates = []

        for path in scan_paths:
            if path.is_file():
                mtime = path.stat().st_mtime
                if path not in self.file_mtimes or self.file_mtimes[path] != mtime:
                    self.file_mtimes[path] = mtime
                    templates = await self._scan_file(path)
                    changed_templates.extend(templates)
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    if py_file.name.startswith("__"):
                        continue

                    mtime = py_file.stat().st_mtime
                    if py_file not in self.file_mtimes or self.file_mtimes[py_file] != mtime:
                        self.file_mtimes[py_file] = mtime
                        templates = await self._scan_file(py_file)
                        changed_templates.extend(templates)

        return changed_templates
