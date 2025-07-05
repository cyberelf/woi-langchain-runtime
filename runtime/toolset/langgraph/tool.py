"""Some sample local tools"""

from langchain_core.tools import tool
from .service import tool_registry


@tool
def calculator_tool(expression: str) -> float:
    """Calculator tool."""
    return eval(expression)


