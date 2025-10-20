"""Tool plugins registry.

This module explicitly declares all available tool plugins.
To add a new tool: import it and add to __tools__ list.
To disable a tool: comment it out from the list.
"""

from .file_tools import CreateFileTool, DeleteFileTool, GrepFileTool, ReadLinesTool
from .web_tools import FetchUrlTool, ParseUrlTool

# Explicitly registered tools
# Tools will be loaded in the order they appear in this list
__tools__ = [
    # File operation tools
    ReadLinesTool,
    CreateFileTool,
    GrepFileTool,
    DeleteFileTool,
    
    # Web operation tools
    FetchUrlTool,
    ParseUrlTool,
]

__all__ = [
    "__tools__",
]
