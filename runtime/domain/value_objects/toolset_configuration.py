from pydantic import BaseModel

class ToolsetConfiguration(BaseModel):
    """Toolset configuration value object."""
    name: str
    toolset_type: str
    config: dict
