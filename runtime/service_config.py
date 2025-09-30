"""Services configuration loader and parser.

This module handles loading and parsing of services configuration
(LLM providers, toolsets, etc.) from files or JSON strings.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ServicesConfig:
    """Services configuration loader for LLM providers, toolsets, etc.
    
    This class focuses solely on loading and parsing services configuration,
    while application settings are handled by the Settings class.
    """
    
    def __init__(self, config_file: Optional[str] = None, config_json: Optional[str] = None):
        """Initialize services configuration.
        
        Args:
            config_file: Path to JSON configuration file (takes priority)
            config_json: JSON string as fallback if no file specified
        """
        self._config_data: Optional[dict[str, Any]] = None
        self._config_file = config_file
        self._config_json = config_json or "{}"
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file or JSON string."""
        try:
            # Try to load from file first
            if self._config_file:
                config_path = Path(self._config_file)
                if config_path.exists():
                    logger.info(f"Loading services config from file: {config_path}")
                    with open(config_path, 'r') as f:
                        self._config_data = json.load(f)
                        
                    logger.debug(f"Services config loaded from file: {self._config_data}")
                    return
                else:
                    logger.warning(f"Services config file not found: {config_path}")
            
            # Fallback to JSON string
            logger.info("Loading services config from JSON string")
            self._config_data = json.loads(self._config_json)

            logger.debug(f"Services config loaded from JSON string: {self._config_data}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in services configuration: {e}")
            self._config_data = {}
        except Exception as e:
            logger.error(f"Failed to load services configuration: {e}")
            self._config_data = {}
    
    def reload(self) -> None:
        """Reload configuration from source."""
        logger.info("Reloading services configuration")
        self._load_config()
    
    def get_config_dict(self) -> dict[str, Any]:
        """Get complete services configuration as dictionary."""
        return self._config_data or {}
    
    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM providers configuration."""
        return self.get_config_dict().get("llm", {})
    
    def get_toolsets_config(self) -> dict[str, Any]:
        """Get toolsets configuration."""
        return self.get_config_dict().get("toolsets", {})
    
    # Backward compatibility method - use get_toolsets_config() instead
    def get_toolset_config(self) -> dict[str, Any]:
        """Get toolset service configuration (deprecated - use get_toolsets_config)."""
        return self.get_toolsets_config()
    
    def get_monitoring_config(self) -> dict[str, Any]:
        """Get monitoring configuration."""
        return self.get_config_dict().get("monitoring", {})
    
    def get_security_config(self) -> dict[str, Any]:
        """Get security configuration."""
        return self.get_config_dict().get("security", {})
    
    def is_loaded(self) -> bool:
        """Check if configuration was loaded successfully."""
        return self._config_data is not None and len(self._config_data) > 0
    
    def get_config_source(self) -> str:
        """Get information about configuration source."""
        if self._config_file and Path(self._config_file).exists():
            return f"file: {self._config_file}"
        else:
            return "JSON string"


def create_services_config(config_file: Optional[str] = None, config_json: Optional[str] = None) -> ServicesConfig:
    """Create a services configuration instance.
    
    Args:
        config_file: Path to JSON configuration file
        config_json: JSON string as fallback
        
    Returns:
        ServicesConfig instance
    """
    return ServicesConfig(config_file=config_file, config_json=config_json)


# Lazy-initialized global instance (will be created when first accessed)
_global_services_config: Optional[ServicesConfig] = None


def get_services_config() -> ServicesConfig:
    """Get global services configuration instance.
    
    This function creates the global instance on first access using values from Settings.
    """
    global _global_services_config
    
    if _global_services_config is None:
        # Import here to avoid circular imports
        from .settings import settings
        
        _global_services_config = create_services_config(
            config_file=settings.services_config_file,
            config_json=settings.services_config_json
        )
        
        logger.info(f"Initialized global services config from {_global_services_config.get_config_source()}")
    
    return _global_services_config


# For backward compatibility - deprecated, use get_services_config() instead
service_config = None  # Will be set to actual instance on first access


def __getattr__(name: str):
    """Handle backward compatibility for service_config access."""
    if name == "service_config":
        global service_config
        if service_config is None:
            service_config = get_services_config()
        return service_config
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")