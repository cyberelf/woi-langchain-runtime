"""Agent validation domain service - Pure business logic."""

from ..entities.agent import Agent


class AgentValidationService:
    """Domain service for agent validation business logic.
    
    Contains cross-cutting business rules that don't belong to a single entity.
    Template-specific validation is handled by the templates themselves.
    Pure domain service with no external dependencies.
    """
    
    def __init__(self):
        pass
    
    def validate_agent_configuration(self, agent: Agent) -> list[str]:
        """Validate agent against cross-cutting business rules.
        
        Template-specific validation should be handled by the templates themselves
        via their validate_configuration() methods.
        
        Returns list of validation errors.
        """
        errors = []
        
        # Basic agent validation
        if not agent.name.strip():
            errors.append("Agent name cannot be empty")
        
        if not agent.template_id.strip():
            errors.append("Template ID cannot be empty")
        
        # Cross-cutting business rules
        errors.extend(self._validate_business_rules(agent))
        
        return errors
    
    
    def _validate_business_rules(self, agent: Agent) -> list[str]:
        """Validate cross-cutting business rules that apply to all agents."""
        errors = []
        
        # Agent name length rule
        if len(agent.name) > 100:
            errors.append("Agent name cannot exceed 100 characters")
        
        # Agent name uniqueness is handled by repository layer
        
        # General configuration size rule (cross-cutting business rule)
        config_dict = agent.configuration.get_template_configuration()
        if len(str(config_dict)) > 10000:  # Rough size limit
            errors.append("Agent configuration is too large")
        
        return errors
    
    def is_agent_valid(self, agent: Agent) -> bool:
        """Check if agent is valid according to business rules."""
        errors = self.validate_agent_configuration(agent)
        return len(errors) == 0