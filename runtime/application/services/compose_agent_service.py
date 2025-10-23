"""Compose agent application service - LLM-powered agent configuration generation."""

import json
import logging
from typing import Optional, TYPE_CHECKING

from isort import Config

from runtime.domain.value_objects.template import ConfigField, TemplateInfo

from ...infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService

if TYPE_CHECKING:
    from ...infrastructure.frameworks.executor_base import FrameworkExecutor
else:
    from ...core.executors import FrameworkExecutorInterface as FrameworkExecutor

from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class ComposeAgentService:
    """Application service for composing agent configurations using LLM.
    
    This service uses an LLM to generate agent configurations from natural
    language instructions, following the specified template structure.
    """
    
    def __init__(
        self, 
        llm_service: LangGraphLLMService,
        framework_executor: FrameworkExecutor
    ):
        self.llm_service = llm_service
        self.framework_executor = framework_executor
    
    async def compose(
        self,
        template_id: str,
        instructions: str,
        suggested_name: Optional[str] = None,
        suggested_tools: Optional[list[str]] = None,
        llm_config_id: str = "deepseek"
    ) -> dict:
        """Compose an agent configuration from natural language instructions.
        
        Args:
            template_id: Target template ID to use
            instructions: Natural language description of desired agent
            suggested_name: Optional suggested agent name
            suggested_tools: Optional list of suggested tools
            llm_config_id: LLM configuration to use for composition
            
        Returns:
            Dict with composed agent parameters
            
        Raises:
            ValueError: If template doesn't exist or composition fails
        """
        logger.info(f"Composing agent for template '{template_id}' with instructions: {instructions[:100]}...")
        
        # 1. Validate template exists and get template info
        templates = self.framework_executor.get_templates()
        template_info = None
        for tmpl in templates:
            if tmpl.id == template_id:
                template_info = tmpl
                break
        
        if not template_info:
            raise ValueError(f"Template '{template_id}' not found")
        
        # 2. Get LLM client
        llm = self.llm_service.get_client(llm_config_id)
        if not llm:
            logger.warning(f"LLM config '{llm_config_id}' not found, using default")
            llm = self.llm_service.get_client()
        
        # 3. Build composition prompt
        system_prompt = self._build_system_prompt(template_info)
        user_prompt = self._build_user_prompt(
            instructions, 
            suggested_name, 
            suggested_tools
        )
        
        # 4. Call LLM to generate configuration
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = await llm.ainvoke(messages)
            response_text = response.content
            
            # Handle list content type
            if isinstance(response_text, list):
                response_text = " ".join(str(item) for item in response_text)
            elif not isinstance(response_text, str):
                response_text = str(response_text)
            
            # 6. Parse LLM response
            composed_config = self._parse_llm_response(response_text, template_id)
            
            # 7. Validate generated configuration if possible
            config_dict = composed_config.get("template_config", {})
            is_valid, validation_error = self.framework_executor.validate_template_configuration(
                template_id,
                config_dict
            )
            
            if not is_valid:
                logger.warning(f"Generated configuration validation failed: {validation_error}")
                # Try to fix common issues or return with warning
                composed_config["validation_warning"] = validation_error
            
            logger.info(f"Successfully composed agent configuration")
            return composed_config
            
        except Exception as e:
            logger.error(f"Failed to compose agent: {e}")
            raise ValueError(f"Agent composition failed: {str(e)}")
    
    def _build_system_prompt(self, template_info: TemplateInfo) -> str:
        """Build the system prompt for agent composition."""
        # Get available toolset names from the toolset service
        toolset_service = self.framework_executor.get_toolset_service()
        if toolset_service:
            available_tools = toolset_service.get_all_toolset_names()
        else:
            available_tools = []
        # Build schema description (recursive for nested types)
        def render_field(field: ConfigField, indent: int = 0) -> str:
            pad = '  ' * indent
            lines = []
            lines.append(f"{pad}- {field.key}: {field.description or 'No description'}")
            lines.append(f"{pad}  Type: {field.field_type}")
            if field.default_value is not None:
                lines.append(f"{pad}  Default: {repr(field.default_value)}")
            if field.validation is not None and field.validation.has_constraints():
                lines.append(f"{pad}  Validation: {field.validation.to_dict()}")

            # Array items
            if field.field_type == 'array' and field.items is not None:
                lines.append(f"{pad}  Items:")
                lines.append(render_field(field.items, indent=indent + 2))

            # Object properties
            if field.field_type == 'object' and field.properties is not None:
                lines.append(f"{pad}  Properties:")
                for prop_name, prop_field in field.properties.items():
                    lines.append(render_field(prop_field, indent=indent + 2))

            return "\n".join(lines)

        schema_description = "\n".join([render_field(f) for f in template_info.config_fields])
        
        return f"""You are an AI agent configuration composer. Your task is to generate agent configurations based on user instructions.

Template ID: {template_info.id}
Template Name: {template_info.name}
Template Description: {template_info.description}
Template Configuration Fields:
{schema_description}
Available Tools: {', '.join(available_tools)}

Instructions:
1. Analyze the user's instructions carefully
2. Generate appropriate configuration parameters matching the template requirements
3. Create a clear, descriptive system prompt
4. Select relevant tools from the available tools list (only if needed)
5. Provide reasoning for your choices

Output Format (strict JSON):
{{
    "name": "Suggested Agent Name",
    "description": "Brief description of the agent's purpose",
    "system_prompt": "Detailed system prompt for the agent",
    "template_config": {{...template-specific config...}},
    "toolsets": ["tool1", "tool2"],
    "reasoning": "Explanation of composition decisions"
}}

Important:
- Match the template_config structure to the template requirements
- Only select tools that are truly needed for the task
- Keep system prompts clear, specific, and actionable
- Ensure all required fields are present
- Use descriptive step names for workflows
- Output ONLY valid JSON, no extra text"""

    def _build_user_prompt(
        self, 
        instructions: str,
        suggested_name: Optional[str],
        suggested_tools: Optional[list[str]]
    ) -> str:
        """Build the user prompt with instructions and suggestions."""
        prompt = f"User Instructions:\n{instructions}\n"
        
        if suggested_name:
            prompt += f"\nSuggested Name: {suggested_name}"
        
        if suggested_tools:
            prompt += f"\nSuggested Tools: {', '.join(suggested_tools)}"
        
        prompt += "\n\nGenerate the agent configuration as JSON:"
        return prompt
    
    def _parse_llm_response(self, response_text: str, template_id: str) -> dict:
        """Parse the LLM response and extract configuration."""
        # Try to extract JSON from response
        try:
            # Look for JSON block in response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Try to parse entire response as JSON
                json_text = response_text.strip()
            
            config = json.loads(json_text)
            
            # Validate required fields
            required_fields = ["name", "description", "system_prompt", "template_config"]
            missing_fields = [f for f in required_fields if f not in config]
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Set defaults
            config.setdefault("toolsets", [])
            config.setdefault("reasoning", "No reasoning provided")
            config["template_id"] = template_id
            config["template_version_id"] = "1.0.0"
            
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            raise ValueError(f"Could not parse LLM response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            raise ValueError(f"Failed to parse agent configuration: {str(e)}")
