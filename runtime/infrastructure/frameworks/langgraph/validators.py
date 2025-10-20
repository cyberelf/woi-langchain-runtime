"""LangGraph framework validators for plugins.

This module provides validation functions for LangGraph-specific plugins.
"""

import logging
from typing import Type

from langchain_core.tools import BaseTool
from .templates.base import BaseLangGraphAgent

logger = logging.getLogger(__name__)


def validate_agent_class(cls: Type) -> bool:
    """Validate that a class meets LangGraph agent plugin requirements.
    
    Args:
        cls: Class to validate
        
    Returns:
        True if valid agent plugin, False otherwise
    """
    try:
        # Must be subclass of BaseLangGraphAgent
        if not issubclass(cls, BaseLangGraphAgent):
            return False
        
        # Cannot be the base class itself
        if cls == BaseLangGraphAgent:
            return False
        
        # Must have required attributes
        required_attrs = ['template_id', 'template_name', 'template_version', 'template_description']
        for attr in required_attrs:
            if not hasattr(cls, attr):
                logger.debug(f"Agent class {cls.__name__} missing required attribute: {attr}")
                return False
        
        return True
        
    except (TypeError, ImportError) as e:
        logger.debug(f"Agent validation failed for {cls}: {e}")
        return False


def validate_tool_class(cls: Type) -> bool:
    """Validate that a class meets tool plugin requirements.
    
    Args:
        cls: Class to validate
        
    Returns:
        True if valid tool plugin, False otherwise
    """
    try:
        # Simple validation for LangChain tools
        # Must be subclass of BaseTool
        if not issubclass(cls, BaseTool):
            return False
        
        # Cannot be the base class itself
        if cls == BaseTool:
            return False
        
        return True
        
    except (TypeError, ImportError) as e:
        logger.debug(f"Tool validation failed for {cls}: {e}")
        return False
