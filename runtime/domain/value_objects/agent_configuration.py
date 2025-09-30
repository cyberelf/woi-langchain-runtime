"""Agent configuration value object - Domain layer."""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass(frozen=True)
class AgentConfiguration:
    """Domain model for agent configuration.
    
    Immutable value object representing agent configuration.
    No framework dependencies - pure domain concept.
    
    This is used in Agent entities and CreateAgentCommand, providing type safety
    and validation for all agent configuration data.
    """
    
    # Core agent configuration
    system_prompt: Optional[str] = None
    llm_config_id: Optional[str] = None
    
    # Conversation configuration (consolidates execution parameters)
    conversation_config: Optional[dict[str, Any]] = None
    
    # Toolset configuration (list of toolset names, not objects)
    toolsets: list[str] = field(default_factory=list)
    
    # Template-specific configuration
    template_config: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration data."""
        if self.conversation_config is not None and not isinstance(self.conversation_config, dict):
            raise ValueError("conversation_config must be a dictionary")
        if not isinstance(self.toolsets, list):
            raise ValueError("toolsets must be a list")
        if not isinstance(self.template_config, dict):
            raise ValueError("template_config must be a dictionary")
        
        # Validate temperature range if present
        if (self.conversation_config and 
            "temperature" in self.conversation_config):
            temp = self.conversation_config["temperature"]
            if not isinstance(temp, int | float) or temp < 0.0 or temp > 2.0:
                raise ValueError("temperature must be between 0.0 and 2.0")
        
        # Validate max_tokens if present
        if (self.conversation_config and 
            "max_tokens" in self.conversation_config):
            max_tokens = self.conversation_config["max_tokens"]
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                raise ValueError("max_tokens must be a positive integer")
    
    def get_toolset_names(self) -> list[str]:
        """Get list of configured toolset names."""
        return self.toolsets.copy()
    
    def get_template_config_value(self, key: str, default: Any = None) -> Any:
        """Get a value from template configuration."""
        return self.template_config.get(key, default)
    
    def get_temperature(self) -> Optional[float]:
        """Get temperature from conversation config."""
        if self.conversation_config:
            return self.conversation_config.get("temperature")
        return None
    
    def get_max_tokens(self) -> Optional[int]:
        """Get max_tokens from conversation config."""
        if self.conversation_config:
            return self.conversation_config.get("max_tokens")
        return None
    
    def get_conversation_config_value(self, key: str, default: Any = None) -> Any:
        """Get a value from conversation configuration."""
        if self.conversation_config:
            return self.conversation_config.get(key, default)
        return default
    
    def has_toolsets(self) -> bool:
        """Check if any toolsets are configured."""
        return len(self.toolsets) > 0
    
    def has_execution_params(self) -> bool:
        """Check if any execution parameters are configured."""
        if not self.conversation_config:
            return False
        return "temperature" in self.conversation_config or "max_tokens" in self.conversation_config
    
    def get_execution_params(self) -> dict[str, Any]:
        """Get execution parameters for agent.execute() calls.
        
        Extracts temperature and max_tokens from conversation_config.
        
        Returns:
            Dictionary of execution parameters to pass to execute methods
        """
        params = {}
        if self.conversation_config:
            if "temperature" in self.conversation_config:
                params["temperature"] = self.conversation_config["temperature"]
            if "max_tokens" in self.conversation_config:
                params["max_tokens"] = self.conversation_config["max_tokens"]
        return params
    
    def get_template_configuration(self) -> dict[str, Any]:
        """Get the template configuration that should be passed to agent templates.
        
        This merges template_config with core fields and conversation_config.
        The result is what gets passed as the 'configuration' parameter to agent template constructors.
        
        Returns:
            Dictionary suitable for agent template constructors
        """
        merged = self.template_config.copy()
        
        # Add core fields that templates expect to access
        if self.system_prompt:
            merged["system_prompt"] = self.system_prompt
        if self.llm_config_id:
            merged["llm_config_id"] = self.llm_config_id
        if self.toolsets:
            # Templates expect 'toolset_configs' but we store simple names
            # Framework implementations will convert names to actual configs
            merged["toolset_configs"] = self.toolsets
            
        # Merge conversation config including execution parameters
        if self.conversation_config:
            conv_config = self.conversation_config.copy()
            # Convert camelCase to snake_case for backward compatibility
            if "historyLength" in conv_config:
                conv_config["history_length"] = conv_config.pop("historyLength")
            merged.update(conv_config)
            
        return merged
    
    def with_conversation_config(self, **config_values) -> "AgentConfiguration":
        """Create a new configuration with updated conversation config.
        
        Args:
            **config_values: Configuration values to set
            
        Returns:
            New AgentConfiguration with updated conversation config
        """
        current_conv_config = self.conversation_config.copy() if self.conversation_config else {}
        current_conv_config.update(config_values)
        
        return AgentConfiguration(
            system_prompt=self.system_prompt,
            llm_config_id=self.llm_config_id,
            conversation_config=current_conv_config,
            toolsets=self.toolsets,
            template_config=self.template_config
        )
    
    def with_toolsets(self, toolsets: list[str]) -> "AgentConfiguration":
        """Create a new configuration with updated toolsets.
        
        Args:
            toolsets: List of toolset names
            
        Returns:
            New AgentConfiguration with updated toolsets
        """
        return AgentConfiguration(
            system_prompt=self.system_prompt,
            llm_config_id=self.llm_config_id,
            conversation_config=self.conversation_config,
            toolsets=toolsets,
            template_config=self.template_config
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "system_prompt": self.system_prompt,
            "llm_config_id": self.llm_config_id,
            "conversation_config": self.conversation_config,
            "toolsets": self.toolsets,
            "template_config": self.template_config
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfiguration":
        """Create from dictionary."""
        return cls(
            system_prompt=data.get("system_prompt"),
            llm_config_id=data.get("llm_config_id"),
            conversation_config=data.get("conversation_config"),
            toolsets=data.get("toolsets", []),
            template_config=data.get("template_config", {})
        )
    
    def __str__(self) -> str:
        """String representation."""
        parts = []
        if self.system_prompt:
            parts.append(f"prompt='{self.system_prompt[:50]}...'")
        if self.llm_config_id:
            parts.append(f"llm={self.llm_config_id}")
        if self.toolsets:
            parts.append(f"toolsets={len(self.toolsets)}")
        if self.conversation_config:
            conv_parts = []
            if "temperature" in self.conversation_config:
                conv_parts.append(f"temp={self.conversation_config['temperature']}")
            if "max_tokens" in self.conversation_config:
                conv_parts.append(f"max_tokens={self.conversation_config['max_tokens']}")
            if conv_parts:
                parts.append(f"conversation=({', '.join(conv_parts)})")
        return f"AgentConfiguration({', '.join(parts)})"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return (f"AgentConfiguration(system_prompt={bool(self.system_prompt)}, "
                f"llm_config_id='{self.llm_config_id}', toolsets={len(self.toolsets)})")