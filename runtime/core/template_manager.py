"""Enhanced Template Manager - Multi-framework template management system.

This module provides comprehensive template management including:
- Template registry with version management
- Framework-agnostic template handling
- Configuration validation and schema generation
- Template lifecycle management
"""

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import semver
from pydantic import BaseModel

from .. import __version__
from ..generated import Configfield, Fieldvalidation, TemplateConfigSchema
from ..models import (AgentCreateRequest, AgentTemplate, RuntimeCapabilities,
                      RuntimeLimits, RuntimeRequirements, SchemaResponse)
from ..template_agent.base import (BaseAgentTemplate, TemplateMetadata,
                                   ValidationResult)
from .discovery import DiscoveryInterface, TemplateDiscovery, TemplateInfo

logger = logging.getLogger(__name__)


class TemplateRegistryInterface(ABC):
    """Interface for template registry implementations."""

    @abstractmethod
    def register_template(self, template_info: TemplateInfo) -> bool:
        """Register a template in the registry."""
        pass

    @abstractmethod
    def unregister_template(self, template_id: str, version: Optional[str] = None) -> bool:
        """Unregister a template from the registry."""
        pass

    @abstractmethod
    def get_template(self, template_id: str, version: Optional[str] = None) -> Optional[TemplateInfo]:
        """Get a template by ID and optional version."""
        pass

    @abstractmethod
    def list_templates(self) -> list[TemplateInfo]:
        """List all registered templates."""
        pass

    @abstractmethod
    def list_versions(self, template_id: str) -> list[str]:
        """List all versions of a template."""
        pass


class TemplateRegistry(TemplateRegistryInterface):
    """
    Template registry with version management and framework support.

    Features:
    - Semantic versioning support
    - Version compatibility checking
    - Template conflict resolution
    - Framework-specific handling
    """

    def __init__(self):
        # Template storage: {template_id: {version: TemplateInfo}}
        self.templates: dict[str, dict[str, TemplateInfo]] = defaultdict(dict)

        # Version ordering for each template
        self.version_order: dict[str, list[str]] = defaultdict(list)

        # Framework-specific registries
        self.framework_templates: dict[str, set[str]] = defaultdict(set)

        # Template metadata cache
        self.metadata_cache: dict[str, TemplateMetadata] = {}

    def register_template(self, template_info: TemplateInfo) -> bool:
        """
        Register a template in the registry.

        Args:
            template_info: Template information to register

        Returns:
            True if registration successful, False otherwise
        """
        try:
            template_id = template_info.template_id
            version = template_info.version

            # Validate version format
            if not self._is_valid_version(version):
                logger.warning(f"Invalid version format: {version} for template {template_id}")
                return False

            # Check for conflicts
            if self._has_version_conflict(template_id, version, template_info):
                logger.warning(f"Version conflict detected for {template_id}:{version}")
                return False

            # Register the template
            self.templates[template_id][version] = template_info

            # Update version ordering
            self._update_version_order(template_id, version)

            # Update framework registry
            self.framework_templates[template_info.framework].add(template_id)

            # Cache metadata
            if hasattr(template_info.template_class, "get_metadata"):
                self.metadata_cache[f"{template_id}:{version}"] = template_info.template_class.get_metadata()

            logger.info(f"Registered template: {template_id}:{version} ({template_info.framework})")
            return True

        except Exception as e:
            logger.error(f"Failed to register template {template_info.template_id}: {e}")
            return False

    def unregister_template(self, template_id: str, version: Optional[str] = None) -> bool:
        """
        Unregister a template from the registry.

        Args:
            template_id: Template identifier
            version: Specific version to unregister (if None, removes all versions)

        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            if template_id not in self.templates:
                return False

            if version:
                # Remove specific version
                if version in self.templates[template_id]:
                    del self.templates[template_id][version]
                    self.version_order[template_id].remove(version)

                    # Clean up metadata cache
                    cache_key = f"{template_id}:{version}"
                    if cache_key in self.metadata_cache:
                        del self.metadata_cache[cache_key]

                    # If no versions left, clean up completely
                    if not self.templates[template_id]:
                        del self.templates[template_id]
                        del self.version_order[template_id]
                        # Remove from framework registries
                        for framework_set in self.framework_templates.values():
                            framework_set.discard(template_id)

                    logger.info(f"Unregistered template: {template_id}:{version}")
                    return True
            else:
                # Remove all versions
                del self.templates[template_id]
                del self.version_order[template_id]

                # Clean up metadata cache
                keys_to_remove = [k for k in self.metadata_cache.keys() if k.startswith(f"{template_id}:")]
                for key in keys_to_remove:
                    del self.metadata_cache[key]

                # Remove from framework registries
                for framework_set in self.framework_templates.values():
                    framework_set.discard(template_id)

                logger.info(f"Unregistered all versions of template: {template_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to unregister template {template_id}: {e}")
            return False

    def get_template(self, template_id: str, version: Optional[str] = None) -> Optional[TemplateInfo]:
        """
        Get a template by ID and optional version.

        Args:
            template_id: Template identifier
            version: Specific version (if None, returns latest)

        Returns:
            Template information or None if not found
        """
        if template_id not in self.templates:
            return None

        if version:
            return self.templates[template_id].get(version)

        # Return latest version
        versions = self.version_order.get(template_id, [])
        if versions:
            latest_version = versions[0]  # First in list is latest
            return self.templates[template_id].get(latest_version)

        return None

    def list_templates(self, framework: Optional[str] = None) -> list[TemplateInfo]:
        """
        List all registered templates.

        Args:
            framework: Filter by framework (if None, returns all)

        Returns:
            List of template information
        """
        templates = []

        for template_id, versions_dict in self.templates.items():
            for version, template_info in versions_dict.items():
                if framework is None or template_info.framework == framework:
                    templates.append(template_info)

        return templates

    def list_versions(self, template_id: str) -> list[str]:
        """
        List all versions of a template.

        Args:
            template_id: Template identifier

        Returns:
            List of versions (sorted latest first)
        """
        return self.version_order.get(template_id, []).copy()

    def get_latest_version(self, template_id: str) -> Optional[str]:
        """Get the latest version of a template."""
        versions = self.version_order.get(template_id, [])
        return versions[0] if versions else None

    def get_compatible_versions(self, template_id: str, min_version: str) -> list[str]:
        """Get versions compatible with the minimum version requirement."""
        versions = self.version_order.get(template_id, [])
        compatible = []

        for version in versions:
            if self._is_version_compatible(version, min_version):
                compatible.append(version)

        return compatible

    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid semantic version."""
        try:
            semver.VersionInfo.parse(version)
            return True
        except ValueError:
            return False

    def _update_version_order(self, template_id: str, version: str) -> None:
        """Update version ordering for a template."""
        versions = self.version_order[template_id]

        if version not in versions:
            versions.append(version)
            # Sort versions in descending order (latest first)
            versions.sort(key=lambda v: semver.VersionInfo.parse(v), reverse=True)

    def _has_version_conflict(self, template_id: str, version: str, new_template: TemplateInfo) -> bool:
        """Check if registering this version would cause conflicts."""
        existing = self.get_template(template_id, version)
        if existing is None:
            return False

        # Check if the template classes are different
        return existing.template_class != new_template.template_class

    def _is_version_compatible(self, version: str, min_version: str) -> bool:
        """Check if version is compatible with minimum version requirement."""
        try:
            v = semver.VersionInfo.parse(version)
            min_v = semver.VersionInfo.parse(min_version)
            return v >= min_v
        except ValueError:
            return False


class TemplateManager:
    """
    Main template manager with discovery and registry integration.

    This is the primary interface for template management, providing:
    - Automatic template discovery
    - Version management
    - Configuration validation
    - Schema generation
    - Framework abstraction
    """

    def __init__(self, discovery: Optional[DiscoveryInterface] = None):
        self.registry = TemplateRegistry()
        self.discovery = discovery or TemplateDiscovery()
        self.scan_paths: list[Path] = []
        self.auto_discovery_enabled = True

        # Framework-specific managers
        self.framework_managers: dict[str, Any] = {}

    async def initialize(self, scan_paths: Optional[list[Path]] = None) -> None:
        """
        Initialize the template manager.

        Args:
            scan_paths: Paths to scan for templates (defaults to template_agent directory)
        """
        if scan_paths:
            self.scan_paths = scan_paths
        else:
            # Default scan paths
            template_dir = Path(__file__).parent.parent / "template_agent"
            self.scan_paths = [template_dir]

        # Perform initial discovery
        await self.discover_templates()

        logger.info(f"Template manager initialized with {len(self.registry.list_templates())} templates")

    async def discover_templates(self) -> list[TemplateInfo]:
        """Discover and register templates from configured paths."""
        discovered = await self.discovery.discover_templates(self.scan_paths)

        # Register discovered templates
        for template_info in discovered:
            self.registry.register_template(template_info)

        return discovered

    def create_agent(self, agent_data: AgentCreateRequest) -> BaseAgentTemplate:
        """
        Create agent instance from template and configuration.

        Args:
            agent_data: Agent creation request data

        Returns:
            Agent instance

        Raises:
            ValueError: If template not found or configuration invalid
        """
        # Get template
        template_info = self.registry.get_template(
            agent_data.template_id,
            agent_data.template_version_id,
        )

        if not template_info:
            available_templates = [t.template_id for t in self.registry.list_templates()]
            raise ValueError(
                f"Template {agent_data.template_id}:{agent_data.template_version_id} not found. "
                f"Available templates: {available_templates}",
            )

        # Create instance using template class
        try:
            return template_info.template_class.create_instance(agent_data)
        except Exception as e:
            raise ValueError(f"Failed to create agent from template {agent_data.template_id}: {e}")

    def validate_template_config(
        self, template_id: str, version: str, config: dict[str, Any]
    ) -> ValidationResult:
        """
        Validate configuration for a specific template.

        Args:
            template_id: Template identifier
            version: Template version
            config: Configuration to validate

        Returns:
            Validation result
        """
        template_info = self.registry.get_template(template_id, version)
        if not template_info:
            return ValidationResult(
                valid=False,
                errors=[f"Template {template_id}:{version} not found"],
            )

        # Use template's validation method
        if hasattr(template_info.template_class, "validate_config"):
            return template_info.template_class.validate_config(config)

        # Fallback basic validation
        return ValidationResult(valid=True)

    def generate_schema(self) -> SchemaResponse:
        """
        Generate runtime schema including all template information.

        Returns:
            Complete schema response for the runtime
        """
        # Get latest version of each template
        latest_templates = {}
        for template_info in self.registry.list_templates():
            template_id = template_info.template_id
            if template_id not in latest_templates:
                latest_templates[template_id] = template_info
            else:
                # Compare versions and keep latest
                current = latest_templates[template_id]
                if self._is_newer_version(template_info.version, current.version):
                    latest_templates[template_id] = template_info

        # Convert to AgentTemplate format for schema
        agent_templates = []
        for template_info in latest_templates.values():
            # Get metadata
            metadata = template_info.metadata

            # Convert Pydantic config schema to proper format
            config_schema = metadata.get("config_schema", BaseModel)
            schema = self._convert_pydantic_schema(
                config_schema,
                metadata.get("name", template_info.template_name),
                template_info.version,
            )

            agent_template = AgentTemplate(
                template_name=metadata.get("name", template_info.template_name),
                template_id=template_info.template_id,
                template_type=template_info.framework,  # Use framework as template type
                version=template_info.version,
                configSchema=schema,
            )
            agent_templates.append(agent_template)

        # Define runtime capabilities
        capabilities = RuntimeCapabilities(
            streaming=True,
            toolCalling=True,
            multimodal=False,
            codeExecution=True,
        )

        # Define runtime limits
        limits = RuntimeLimits(
            maxConcurrentAgents=100,
            maxMessageLength=32000,
            maxConversationHistory=100,
        )

        return SchemaResponse(
            version=__version__,
            lastUpdated=datetime.now().isoformat(),
            supportedAgentTemplates=agent_templates,
            capabilities=capabilities,
            limits=limits,
        )

    def get_template_info(self, template_id: str, version: Optional[str] = None) -> Optional[TemplateInfo]:
        """Get template information."""
        return self.registry.get_template(template_id, version)

    def list_templates(self, framework: Optional[str] = None) -> list[TemplateInfo]:
        """List all templates, optionally filtered by framework."""
        return self.registry.list_templates(framework)

    def list_template_versions(self, template_id: str) -> list[str]:
        """List all versions of a template."""
        return self.registry.list_versions(template_id)

    def add_framework_manager(self, framework: str, manager: Any) -> None:
        """Add a framework-specific manager."""
        self.framework_managers[framework] = manager

    def get_framework_manager(self, framework: str) -> Optional[Any]:
        """Get framework-specific manager."""
        return self.framework_managers.get(framework)

    def enable_auto_discovery(self) -> None:
        """Enable automatic template discovery."""
        self.auto_discovery_enabled = True

    def disable_auto_discovery(self) -> None:
        """Disable automatic template discovery."""
        self.auto_discovery_enabled = False

    async def reload_templates(self) -> list[TemplateInfo]:
        """Reload all templates from scan paths."""
        # Clear registry
        for template_id in list(self.registry.templates.keys()):
            self.registry.unregister_template(template_id)

        # Clear discovery cache
        self.discovery.clear_cache()

        # Rediscover templates
        return await self.discover_templates()

    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """Check if version1 is newer than version2."""
        try:
            v1 = semver.VersionInfo.parse(version1)
            v2 = semver.VersionInfo.parse(version2)
            return v1 > v2
        except ValueError:
            # Fallback to string comparison
            return version1 > version2

    def _convert_pydantic_schema(
        self, config_schema: type[BaseModel], name: str, version: str
    ) -> TemplateConfigSchema:
        """Convert Pydantic model to TemplateConfigSchema."""
        # Get Pydantic model schema
        model_schema = config_schema.model_json_schema()
        properties = model_schema.get("properties", {})
        required_fields = set(model_schema.get("required", []))
        definitions = model_schema.get("$defs", {})

        # Create configuration fields
        config_fields = []
        for field_name, field_info in properties.items():
            # Map Pydantic types to our expected types
            field_type = self._map_pydantic_type(field_info.get("type", "string"))

            # Create validation rules if present
            validation = self._extract_validation_rules(
                field_info, field_name in required_fields, definitions
            )

            field = Configfield(
                key=field_name,
                type=field_type,
                description=field_info.get("description", ""),
                default=field_info.get("default"),
                validation=validation,
            )
            config_fields.append(field)

        return TemplateConfigSchema(
            name=name,
            description=model_schema.get("description", f"Configuration schema for {name}"),
            version=version,
            config=config_fields,
        )

    def _map_pydantic_type(self, pydantic_type: str) -> str:
        """Map Pydantic JSON schema types to our ConfigField types."""
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "number": "number",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
        }
        return type_mapping.get(pydantic_type, "string")

    def _extract_validation_rules(
        self, field_info: dict[str, Any], is_required: bool, definitions: dict[str, Any] = None
    ) -> Optional[Fieldvalidation]:
        """Extract validation rules from Pydantic field info."""
        validation_params = {"required": is_required}

        # Check for various validation constraints
        if "minimum" in field_info:
            validation_params["min"] = field_info["minimum"]
        if "maximum" in field_info:
            validation_params["max"] = field_info["maximum"]
        if "minLength" in field_info:
            validation_params["minLength"] = field_info["minLength"]
        if "maxLength" in field_info:
            validation_params["maxLength"] = field_info["maxLength"]
        if "minItems" in field_info:
            validation_params["minItems"] = field_info["minItems"]
        if "maxItems" in field_info:
            validation_params["maxItems"] = field_info["maxItems"]
        if "pattern" in field_info:
            validation_params["pattern"] = field_info["pattern"]
        if "enum" in field_info:
            validation_params["enum"] = field_info["enum"]

        # Handle enum references ($ref)
        if "$ref" in field_info and definitions:
            ref_path = field_info["$ref"]
            if ref_path.startswith("#/$defs/"):
                ref_name = ref_path[8:]  # Remove "#/$defs/" prefix
                if ref_name in definitions:
                    ref_def = definitions[ref_name]
                    if "enum" in ref_def:
                        validation_params["enum"] = ref_def["enum"]

        # Handle Literal types (which are also enums)
        if "anyOf" in field_info:
            # Check if this is a Literal type (anyOf with const values)
            literal_values = []
            for option in field_info["anyOf"]:
                if "const" in option:
                    literal_values.append(option["const"])

            if literal_values:
                validation_params["enum"] = literal_values

        # Return None if no validation rules found
        if not validation_params:
            return None

        return Fieldvalidation(**validation_params)
