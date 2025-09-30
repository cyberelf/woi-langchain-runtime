"""Web layer request models - Infrastructure layer."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

from ....domain.value_objects.chat_message import MessageRole


class AgentIdentityModel(BaseModel):
    """Model for core agent identity attributes."""
    
    id: str = Field(..., description="Unique identifier for the agent.")
    name: str = Field(..., description="A human-readable name for the agent.")
    description: Optional[str] = Field(default=None, description="A brief description of the agent's purpose.")
    avatar_url: Optional[str] = Field(default=None, description="URL for the agent's avatar.")
    type: Optional[str] = Field(default=None, description="Agent type")
    owner_id: Optional[str] = Field(default=None, description="Owner ID")
    status: str = Field(default="draft", description="Agent status")
    agent_line_id: Optional[str] = Field(default=None, description="Agent line ID")
    version_type: str = Field(default="beta", description="Version type (beta or release)")
    version_number: str = Field(default="v1", description="Version number")
    
    model_config = ConfigDict(extra="forbid")


class AgentTemplateModel(BaseModel):
    """Model for agent template selection."""
    
    template_id: str = Field(..., description="The ID of the template to use for this agent.")
    template_version_id: Optional[str] = Field(default=None, description="Template version ID (alias)")
    
    model_config = ConfigDict(extra="forbid")

    def get_template_version(self) -> Optional[str]:
        """Get template version."""
        return self.template_version_id

class AgentConfigurationModel(BaseModel):
    """Model for agent configuration."""
    
    template_config: Optional[dict] = Field(default=None, description="Template configuration")
    system_prompt: Optional[str] = Field(default=None, description="System prompt")
    conversation_config: Optional[dict] = Field(default=None, description="Conversation configuration")
    toolsets: Optional[list[str]] = Field(default=None, description="List of available toolsets")
    llm_config_id: Optional[str] = Field(default=None, description="LLM configuration ID")
    
    model_config = ConfigDict(extra="forbid")

    def get_configuration(self) -> dict:
        """Get configuration from template_config."""
        config = {}
        if self.template_config:
            # Handle nested conversation config with camelCase conversion
            template_config = self.template_config.copy()
            if "conversation" in template_config:
                conv_config = template_config["conversation"]
                if "historyLength" in conv_config:
                    conv_config["history_length"] = conv_config.pop("historyLength")
                template_config.update(conv_config)
                template_config.pop("conversation")
            config.update(template_config)
        return config
    
    def to_agent_configuration(self):
        """Convert web model to domain AgentConfiguration.
        
        Returns:
            AgentConfiguration domain value object
        """
        from ....domain.value_objects.agent_configuration import AgentConfiguration
        
        return AgentConfiguration(
            system_prompt=self.system_prompt,
            llm_config_id=self.llm_config_id,
            conversation_config=self.conversation_config,
            toolsets=self.toolsets or [],
            template_config=self.template_config or {}
        )


class CreateAgentRequest(BaseModel):
    """HTTP request model for creating agents.
    
    Infrastructure layer model that handles HTTP/JSON serialization.
    Maps to domain command objects.
    """
    
    # Core fields - following API specification
    id: str = Field(..., description="Agent line ID (logical identifier)")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(default=None, description="Agent description")
    avatar_url: Optional[str] = Field(default=None, description="Agent avatar URL")
    type: str = Field(..., description="Agent type")
    
    # Template fields - following API specification
    template_id: str = Field(..., description="Template type identifier")
    template_version_id: str = Field(default="1.0.0", description="Template version string")
    
    # Configuration fields
    system_prompt: Optional[str] = Field(default=None, description="System prompt")
    conversation_config: Optional[dict] = Field(default=None, description="Conversation configuration")
    toolsets: Optional[list[str]] = Field(default=None, description="Available toolsets")
    llm_config_id: Optional[str] = Field(default=None, description="LLM configuration ID")
    template_config: Optional[dict] = Field(default=None, description="Template configuration")

    # Metadata - following API specification
    agent_line_id: Optional[str] = Field(default=None, description="Agent line ID")
    version_type: str = Field(default="beta", description="Version type: beta or release (default: beta)")
    version_number: str = Field(default="v1", description="Version number: 'v1', 'v2', etc. (default: v1)")
    owner_id: Optional[str] = Field(default=None, description="Agent owner ID for beta access control")
    status: str = Field(
        default="draft", 
        description="Agent status: draft, submitted, pending, published, revoked (default: draft)"
    )
    
    @model_validator(mode="before")
    @classmethod
    def set_agent_line_id_default(cls, values):
        # If agent_line_id is not provided, set it to id (agent_id)
        if values.get("agent_line_id") is None and "id" in values:
            values["agent_line_id"] = values["id"]
        return values
    
    def get_identity(self) -> AgentIdentityModel:
        """Parse identity-related fields into AgentIdentityModel."""
        return AgentIdentityModel(
            id=self.id,
            name=self.name,
            description=self.description,
            avatar_url=self.avatar_url,
            type=self.type,
            owner_id=self.owner_id,
            status=self.status,
            agent_line_id=self.agent_line_id,
            version_type=self.version_type,
            version_number=self.version_number,
        )

    def get_template(self) -> AgentTemplateModel:
        """Parse template-related fields into AgentTemplateModel."""
        return AgentTemplateModel(
            template_id=self.template_id,
            template_version_id=self.template_version_id,
        )

    def get_agent_configuration(self):
        """Parse configuration-related fields into domain AgentConfiguration."""
        web_config = AgentConfigurationModel(
            template_config=self.template_config,
            system_prompt=self.system_prompt,
            conversation_config=self.conversation_config,
            toolsets=self.toolsets,
            llm_config_id=self.llm_config_id
        )
        return web_config.to_agent_configuration()
    
    def get_agent_configuration_model(self) -> AgentConfigurationModel:
        """Parse configuration-related fields into AgentConfigurationModel (for backward compatibility)."""
        return AgentConfigurationModel(
            template_config=self.template_config,
            system_prompt=self.system_prompt,
            conversation_config=self.conversation_config,
            toolsets=self.toolsets,
            llm_config_id=self.llm_config_id
        )
    
    def get_template_version(self) -> Optional[str]:
        """Get template version, preferring template_version_id over template_version."""
        return self.get_template().get_template_version()
    
    def get_configuration(self) -> dict:
        """Get merged configuration from template_config and configuration."""
        return self.get_agent_configuration_model().get_configuration()
    
    def get_metadata(self) -> dict:
        """Get metadata with additional fields."""
        identity = self.get_identity()
        config = self.get_agent_configuration_model()
        
        meta = {}
        if identity.description:
            meta["description"] = identity.description
        if identity.type:
            meta["type"] = identity.type
        if config.system_prompt:
            meta["system_prompt"] = config.system_prompt
        if config.llm_config_id:
            meta["llm_config_id"] = config.llm_config_id
        return meta
    
    model_config = ConfigDict(extra="forbid")


class ChatMessageRequest(BaseModel):
    """HTTP request model for chat messages."""
    
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    
    model_config = ConfigDict(extra="forbid")


class ExecuteAgentRequest(BaseModel):
    """HTTP request model for executing agents.
    
    OpenAI-compatible chat completion request.
    """
    
    model: str = Field(..., description="Agent ID (OpenAI model field)")
    messages: list[ChatMessageRequest] = Field(..., description="Conversation messages")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    stream: bool = Field(False, description="Enable streaming response")
    metadata: Optional[dict] = Field(None, description="Request metadata including session_id, user_id")
    
    model_config = ConfigDict(extra="forbid")
    
    def get_session_id(self) -> Optional[str]:
        """Extract session ID from metadata."""
        if self.metadata:
            return self.metadata.get("session_id")
        return None
    
    def get_user_id(self) -> Optional[str]:
        """Extract user ID from metadata."""
        if self.metadata:
            return self.metadata.get("user_id")
        return None


class GetAgentRequest(BaseModel):
    """HTTP request model for getting agent."""
    
    agent_id: str = Field(..., description="Agent identifier")
    
    model_config = ConfigDict(extra="forbid")


class ListAgentsRequest(BaseModel):
    """HTTP request model for listing agents."""
    
    template_id: Optional[str] = Field(None, description="Filter by template ID")
    active_only: bool = Field(False, description="Only return active agents")
    limit: Optional[int] = Field(None, gt=0, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    
    model_config = ConfigDict(extra="forbid")


class ChatCompletionMessage(BaseModel):
    """OpenAI-compatible chat message."""
    
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Message sender name")
    
    model_config = ConfigDict(extra="forbid")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    
    model: str = Field(..., description="Agent ID (OpenAI model field)")
    messages: list[ChatCompletionMessage] = Field(..., description="Conversation messages")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Presence penalty")
    stream: bool = Field(False, description="Enable streaming response")
    stop: Optional[list[str]] = Field(None, description="Stop sequences")
    metadata: Optional[dict] = Field(None, description="Request metadata including session_id, user_id")
    
    model_config = ConfigDict(extra="forbid")
    
    def get_session_id(self) -> Optional[str]:
        """Extract session ID from metadata."""
        if self.metadata:
            return self.metadata.get("session_id")
        return None
    
    def get_user_id(self) -> Optional[str]:
        """Extract user ID from metadata."""
        if self.metadata:
            return self.metadata.get("user_id")
        return None