"""Agent validation domain service - Pure business logic."""

from typing import Dict, Any, List
from ..entities.agent import Agent


class AgentValidationService:
    """Domain service for agent validation business logic.
    
    Contains business rules that don't belong to a single entity.
    Pure domain service with no external dependencies.
    """
    
    def __init__(self):
        # Configuration validation rules
        self.required_config_keys = {
            "conversation": ["history_length"],
            "task": ["steps", "timeout"],
            "custom": ["code", "runtime"]
        }
    
    def validate_agent_configuration(self, agent: Agent) -> List[str]:
        """Validate agent configuration against business rules.
        
        Returns list of validation errors.
        """
        errors = []
        
        # Basic validation
        if not agent.name.strip():
            errors.append("Agent name cannot be empty")
        
        if not agent.template_id.strip():
            errors.append("Template ID cannot be empty")
        
        # Template-specific validation
        template_errors = self._validate_template_configuration(
            agent.template_id, 
            agent.configuration
        )
        errors.extend(template_errors)
        
        # Business rule validation
        business_errors = self._validate_business_rules(agent)
        errors.extend(business_errors)
        
        return errors
    
    def _validate_template_configuration(self, template_id: str, config: Dict[str, Any]) -> List[str]:
        """Validate template-specific configuration."""
        errors = []
        
        # Extract template type from ID (business rule)
        template_type = self._extract_template_type(template_id)
        
        if template_type in self.required_config_keys:
            required_keys = self.required_config_keys[template_type]
            for key in required_keys:
                if key not in config:
                    errors.append(f"Missing required configuration key: {key}")
        
        # Validate specific configuration values
        if template_type == "conversation":
            errors.extend(self._validate_conversation_config(config))
        elif template_type == "task":
            errors.extend(self._validate_task_config(config))
        elif template_type == "custom":
            errors.extend(self._validate_custom_config(config))
        
        return errors
    
    def _validate_conversation_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate conversation agent configuration."""
        errors = []
        
        if "history_length" in config:
            history_length = config["history_length"]
            if not isinstance(history_length, int) or history_length <= 0:
                errors.append("History length must be a positive integer")
            elif history_length > 1000:
                errors.append("History length cannot exceed 1000 messages")
        
        return errors
    
    def _validate_task_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate task agent configuration."""
        errors = []
        
        if "steps" in config:
            steps = config["steps"]
            if not isinstance(steps, list) or len(steps) == 0:
                errors.append("Steps must be a non-empty list")
            elif len(steps) > 50:
                errors.append("Cannot have more than 50 steps")
        
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("Timeout must be a positive number")
            elif timeout > 3600:  # 1 hour max
                errors.append("Timeout cannot exceed 3600 seconds")
        
        return errors
    
    def _validate_custom_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate custom agent configuration."""
        errors = []
        
        if "code" in config:
            code = config["code"]
            if not isinstance(code, str) or not code.strip():
                errors.append("Code must be a non-empty string")
        
        if "runtime" in config:
            runtime = config["runtime"]
            allowed_runtimes = ["python", "nodejs", "typescript"]
            if runtime not in allowed_runtimes:
                errors.append(f"Runtime must be one of: {', '.join(allowed_runtimes)}")
        
        return errors
    
    def _validate_business_rules(self, agent: Agent) -> List[str]:
        """Validate general business rules."""
        errors = []
        
        # Agent name length rule
        if len(agent.name) > 100:
            errors.append("Agent name cannot exceed 100 characters")
        
        # Agent name uniqueness is handled by repository layer
        
        # Configuration size rule
        if len(str(agent.configuration)) > 10000:  # Rough size limit
            errors.append("Agent configuration is too large")
        
        return errors
    
    def _extract_template_type(self, template_id: str) -> str:
        """Extract template type from template ID."""
        # Business rule: template type mapping
        conversation_templates = [
            "customer-service-bot",
            "customer-support",
            "chat-assistant"
        ]
        
        task_templates = [
            "task-execution-bot",
            "workflow-agent"
        ]
        
        custom_templates = [
            "custom-code-agent"
        ]
        
        if template_id.lower() in [t.lower() for t in conversation_templates] or "conversation" in template_id.lower():
            return "conversation"
        elif template_id.lower() in [t.lower() for t in task_templates] or "task" in template_id.lower():
            return "task"
        elif template_id.lower() in [t.lower() for t in custom_templates] or "custom" in template_id.lower():
            return "custom"
        else:
            # Default to conversation type for unknown templates
            return "conversation"
    
    def is_agent_valid(self, agent: Agent) -> bool:
        """Check if agent is valid according to business rules."""
        errors = self.validate_agent_configuration(agent)
        return len(errors) == 0