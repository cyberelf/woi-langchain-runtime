"""Agent Template System - Enhanced Agent Classes with Template Metadata."""

from .base import BaseAgentTemplate, TemplateMetadata, ValidationResult
from .discovery import TemplateDiscovery
from .manager import TemplateManager

__all__ = [
    'BaseAgentTemplate',
    'TemplateMetadata', 
    'ValidationResult',
    'TemplateDiscovery',
    'TemplateManager'
] 