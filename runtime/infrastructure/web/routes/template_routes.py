"""Template management routes - Infrastructure layer."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
import logging

from ..dependencies import get_framework_executor
from ...frameworks.executor_base import FrameworkExecutor

router = APIRouter(prefix="/v1/templates", tags=["templates"])

logger = logging.getLogger(__name__)


@router.get("/")
async def list_templates(
    framework: Optional[str] = Query(None, description="Filter templates by framework"),
    executor: FrameworkExecutor = Depends(get_framework_executor)
):
    """List all available agent templates."""
    try:
        # Get templates from the framework executor
        templates = executor.get_templates()
        
        # Filter by framework if specified
        if framework:
            templates = [t for t in templates if t.get("framework") == framework]
   
        return {"templates": templates}
    except Exception as e:
        # Log the error and return a meaningful error response
        logger.error(f"Error getting templates from executor: {e}")
        
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve templates: {str(e)}"
        )


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    executor: FrameworkExecutor = Depends(get_framework_executor)
):
    """Get detailed information about a specific template."""
    templates = executor.get_templates()
    
    # Find the template by ID
    for template in templates:
        if template.get("template_id") == template_id:
            return template
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
