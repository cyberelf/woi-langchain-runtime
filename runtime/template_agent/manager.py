"""Template Manager - Discover and Manage Agent Templates."""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from datetime import datetime

from .base import BaseAgentTemplate, TemplateMetadata, get_all_agent_templates, get_template_by_id
from ..models import AgentTemplate, SchemaResponse, RuntimeCapabilities, RuntimeLimits, AgentCreateRequest
from .. import __version__


class TemplateManager:
    """
    Manager for agent templates using the agent-as-template approach.
    
    This manager discovers agent classes automatically and provides
    template metadata and creation capabilities.
    """
    
    def __init__(self):
        """Initialize template manager."""
        self.templates: Dict[str, Type[BaseAgentTemplate]] = {}
        self.version_map: Dict[str, List[str]] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load all agent templates by importing template modules."""
        # Import all template modules to register their classes
        template_dir = Path(__file__).parent
        
        try:
            # Import conversation template
            from .conversation import ConversationAgent
            self._register_template_class(ConversationAgent)
        except ImportError as e:
            print(f"Failed to import ConversationAgent: {e}")
        
        # TODO: Import other templates (task, custom) when they're implemented
        # from .task import TaskAgent
        # from .custom import CustomAgent
        
        # Also discover any templates that are already loaded
        self._discover_loaded_templates()
    
    def _discover_loaded_templates(self) -> None:
        """Discover already loaded template classes using introspection."""
        for template_class in get_all_agent_templates():
            if not inspect.isabstract(template_class):  # Skip abstract base classes
                self._register_template_class(template_class)
    
    def _register_template_class(self, template_class: Type[BaseAgentTemplate]) -> None:
        """Register a template class."""
        if inspect.isabstract(template_class):
            return  # Skip abstract classes
        
        metadata = template_class.get_metadata()
        template_key = f"{metadata.template_id}:{metadata.version}"
        
        self.templates[template_key] = template_class
        
        # Update version map
        if metadata.template_id not in self.version_map:
            self.version_map[metadata.template_id] = []
        
        if metadata.version not in self.version_map[metadata.template_id]:
            self.version_map[metadata.template_id].append(metadata.version)
            # Sort versions (simple string sort for now)
            self.version_map[metadata.template_id].sort(reverse=True)
    
    def get_template_class(self, template_id: str, version: Optional[str] = None) -> Optional[Type[BaseAgentTemplate]]:
        """
        Get template class by ID and optional version.
        
        Args:
            template_id: Template identifier
            version: Specific version (if None, returns latest)
            
        Returns:
            Template class or None if not found
        """
        if version:
            template_key = f"{template_id}:{version}"
            return self.templates.get(template_key)
        
        # Return latest version
        versions = self.version_map.get(template_id, [])
        if versions:
            latest_version = versions[0]  # Already sorted in reverse order
            template_key = f"{template_id}:{latest_version}"
            return self.templates.get(template_key)
        
        return None
    
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
        template_class = self.get_template_class(
            agent_data.template_id,
            agent_data.template_version_id
        )
        
        if not template_class:
            raise ValueError(f"Template {agent_data.template_id}:{agent_data.template_version_id} not found")
        
        # Use the class method to create and validate the instance
        return template_class.create_instance(agent_data)
    
    def get_all_templates(self) -> List[TemplateMetadata]:
        """Get metadata for all registered templates."""
        templates = []
        
        for template_id, versions in self.version_map.items():
            for version in versions:
                template_key = f"{template_id}:{version}"
                template_class = self.templates.get(template_key)
                if template_class:
                    templates.append(template_class.get_metadata())
        
        return templates
    
    def get_latest_templates(self) -> List[TemplateMetadata]:
        """Get metadata for latest version of each template."""
        templates = []
        
        for template_id, versions in self.version_map.items():
            if versions:
                latest_version = versions[0]  # Already sorted in reverse order
                template_class = self.get_template_class(template_id, latest_version)
                if template_class:
                    templates.append(template_class.get_metadata())
        
        return templates
    
    def generate_schema(self) -> SchemaResponse:
        """
        Generate runtime schema including all template information.
        
        Returns:
            Complete schema response for the runtime
        """
        # Get all latest templates
        template_metadata = self.get_latest_templates()
        
        # Convert to AgentTemplate format for schema
        agent_templates = []
        for metadata in template_metadata:
            agent_template = AgentTemplate(
                template_name=metadata.name,
                template_id=metadata.template_id,
                version=metadata.version,
                configSchema={
                    "template_name": metadata.name,
                    "template_id": metadata.template_id,
                    "version": metadata.version,
                    "config": metadata.config_schema
                },
                runtimeRequirements=metadata.runtime_requirements
            )
            agent_templates.append(agent_template)
        
        # Define runtime capabilities
        capabilities = RuntimeCapabilities(
            streaming=True,
            toolCalling=True,
            multimodal=False,
            codeExecution=True
        )
        
        # Define runtime limits
        limits = RuntimeLimits(
            maxConcurrentAgents=100,
            maxMessageLength=32000,
            maxConversationHistory=100
        )
        
        return SchemaResponse(
            version=__version__,
            lastUpdated=datetime.now().isoformat(),
            supportedAgentTemplates=agent_templates,
            capabilities=capabilities,
            limits=limits
        )
    
    def validate_template_config(self, template_id: str, version: str, config: Dict[str, Any]) -> Any:
        """
        Validate configuration for a specific template.
        
        Args:
            template_id: Template identifier
            version: Template version
            config: Configuration to validate
            
        Returns:
            ValidationResult
            
        Raises:
            ValueError: If template not found
        """
        template_class = self.get_template_class(template_id, version)
        if not template_class:
            raise ValueError(f"Template {template_id}:{version} not found")
        
        return template_class.validate_config(config)
    
    def get_template_info(self, template_id: str, version: Optional[str] = None) -> Optional[TemplateMetadata]:
        """Get detailed information about a template."""
        template_class = self.get_template_class(template_id, version)
        if template_class:
            return template_class.get_metadata()
        return None
    
    def list_template_versions(self, template_id: str) -> List[str]:
        """List all available versions for a template."""
        return self.version_map.get(template_id, [])
    
    def reload_templates(self) -> None:
        """Reload all templates (useful for development)."""
        self.templates.clear()
        self.version_map.clear()
        self._load_templates()


# Global template manager instance
template_manager = TemplateManager() 