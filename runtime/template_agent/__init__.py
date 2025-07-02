"""Agent Template System - Enhanced Agent Classes with Template Metadata."""

from .base import BaseAgentTemplate, TemplateMetadata, ValidationResult

# Import templates here to register them
try:
    from .conversation import ConversationAgent
except ImportError as e:
    print(f"Failed to import ConversationAgent: {e}")

try:
    from .simple import SimpleTestAgent
except ImportError as e:
    print(f"Failed to import SimpleTestAgent: {e}")

__all__ = [
    'BaseAgentTemplate',
    'TemplateMetadata', 
    'ValidationResult'
] 