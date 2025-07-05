"""Test cases for Pydantic-based configuration schema system."""

from enum import Enum
from typing import Literal

import pytest
import pytest_asyncio
from pydantic import BaseModel, Field

from runtime.core.template_manager import TemplateManager
from runtime.models import RuntimeCapabilities, RuntimeLimits, SchemaResponse
from runtime.template_agent.base import BaseAgentTemplate
from runtime.template_agent.langgraph.simple import SimpleTestAgent


class MyEnum(str, Enum):
    """Test enum for validation."""

    VALUE1 = "value1"
    VALUE2 = "value2"
    VALUE3 = "value3"


class MyConfig(BaseModel):
    """Test configuration with various field types."""

    string_field: str = Field(description="A string field", min_length=1, max_length=100)
    integer_field: int = Field(default=42, description="An integer field", ge=0, le=100)
    boolean_field: bool = Field(default=True, description="A boolean field")
    enum_field: MyEnum = Field(default=MyEnum.VALUE1, description="An enum field")
    literal_field: Literal["option1", "option2", "option3"] = Field(
        default="option1", description="A literal field"
    )
    optional_field: str = Field(default=None, description="An optional field")


class MyTemplate(BaseAgentTemplate):
    """Test template for schema generation."""

    template_name: str = "Test Template"
    template_id: str = "test-template"
    template_version: str = "1.0.0"
    template_description: str = "A test template"
    config_schema: type[BaseModel] = MyConfig

    def _build_graph(self):
        """Build the execution graph."""
        return None

    async def execute(self, messages, stream=False, temperature=None, max_tokens=None, metadata=None):
        """Execute the test template."""
        pass


@pytest_asyncio.fixture
async def template_manager():
    """Create a template manager for testing."""
    manager = TemplateManager()
    await manager.initialize()
    return manager


class TestSchemaGeneration:
    """Test schema generation."""

    def test_schema_generation_with_pydantic_models(self, template_manager: TemplateManager):
        """Test that schema generation works with Pydantic models."""
        fields = template_manager._convert_pydantic_schema(MyConfig, "Test Template", "1.0.0")

        assert fields.name == "Test Template"
        assert fields.description == "Test configuration with various field types."
        assert fields.version == "1.0.0"
        assert len(fields.config) == 6
        assert fields.config[0].key == "string_field"
        assert fields.config[0].type == "string"
        assert fields.config[0].description == "A string field"
        assert fields.config[0].validation.minLength == 1
        assert fields.config[0].validation.maxLength == 100
        assert fields.config[0].validation.required is True

        assert fields.config[1].key == "integer_field"
        assert fields.config[1].type == "integer"
        assert fields.config[1].description == "An integer field"
        assert fields.config[1].default == 42
        assert fields.config[1].validation.min == 0
        assert fields.config[1].validation.max == 100

        assert fields.config[2].key == "boolean_field"
        assert fields.config[2].type == "boolean"
        assert fields.config[2].description == "A boolean field"
        assert fields.config[2].default is True

        assert fields.config[3].key == "enum_field"
        assert fields.config[3].type == "string"
        assert fields.config[3].description == "An enum field"
        assert fields.config[3].default == MyEnum.VALUE1
        assert fields.config[3].validation.enum == ["value1", "value2", "value3"]

        assert fields.config[4].key == "literal_field"
        assert fields.config[4].type == "string"
        assert fields.config[4].description == "A literal field"
        assert fields.config[4].default == "option1"
        assert fields.config[4].validation.enum == ["option1", "option2", "option3"]

        assert fields.config[5].key == "optional_field"
        assert fields.config[5].type == "string"
        assert fields.config[5].description == "An optional field"
        assert fields.config[5].default is None
        assert fields.config[5].validation.required is False


class TestPydanticSchemaGeneration:
    """Test Pydantic-based schema generation."""

    @pytest.mark.asyncio
    async def test_schema_generation_with_pydantic_models(self, template_manager):
        """Test that schema generation works with Pydantic models."""
        schema_response = template_manager.generate_schema()

        # Verify basic schema structure
        assert isinstance(schema_response, SchemaResponse)
        assert schema_response.version is not None
        assert schema_response.lastUpdated is not None
        assert isinstance(schema_response.supportedAgentTemplates, list)
        assert isinstance(schema_response.capabilities, RuntimeCapabilities)
        assert isinstance(schema_response.limits, RuntimeLimits)

    @pytest.mark.asyncio
    async def test_simple_template_schema_generation(self, template_manager: TemplateManager):
        """Test schema generation for the simple test template."""
        schema_response = template_manager.generate_schema()

        # Find the simple-test template
        simple_template = None
        for template in schema_response.supportedAgentTemplates:
            if template.template_id == "simple-test":
                simple_template = template
                break

        assert simple_template is not None
        assert simple_template.template_id == "simple-test"
        assert simple_template.template_name == "Simple Test Agent"
        assert simple_template.version == "1.0.0"

        # Check config schema
        config_schema = simple_template.configSchema
        assert config_schema.name == "Simple Test Agent"
        assert config_schema.description == "Configuration for Simple Test Agent."
        assert config_schema.version == "1.0.0"
        assert len(config_schema.config) == 2  # response_prefix and response_style

        # Check response_prefix field
        prefix_field = next(f for f in config_schema.config if f.key == "response_prefix")
        assert prefix_field.type == "string"
        assert prefix_field.description == "Prefix for test responses"
        assert prefix_field.default == "Test: "
        assert prefix_field.validation is not None
        assert prefix_field.validation.minLength == 1
        assert prefix_field.validation.maxLength == 50

        # Check response_style field (enum)
        style_field = next(f for f in config_schema.config if f.key == "response_style")
        assert style_field.type == "string"
        assert style_field.description == "Style of response to generate"
        assert style_field.default == "friendly"
        assert style_field.validation is not None
        assert style_field.validation.enum == ["formal", "casual", "technical", "friendly"]

    @pytest.mark.asyncio
    async def test_enum_validation_extraction(self, template_manager):
        """Test that enum validation rules are properly extracted."""
        # Test the helper method directly
        field_info = {"$ref": "#/$defs/ResponseStyle"}
        definitions = {
            "ResponseStyle": {"enum": ["formal", "casual", "technical", "friendly"], "type": "string"}
        }

        validation = template_manager._extract_validation_rules(field_info, False, definitions)

        assert validation is not None
        assert validation.enum == ["formal", "casual", "technical", "friendly"]

    @pytest.mark.asyncio
    async def test_literal_validation_extraction(self, template_manager):
        """Test that Literal validation rules are properly extracted."""
        # Test the helper method directly with Literal type
        field_info = {"anyOf": [{"const": "option1"}, {"const": "option2"}, {"const": "option3"}]}

        validation = template_manager._extract_validation_rules(field_info, False)

        assert validation is not None
        assert validation.enum == ["option1", "option2", "option3"]

    @pytest.mark.asyncio
    async def test_type_mapping(self, template_manager):
        """Test Pydantic type mapping to ConfigField types."""
        assert template_manager._map_pydantic_type("string") == "string"
        assert template_manager._map_pydantic_type("integer") == "integer"
        assert template_manager._map_pydantic_type("number") == "number"
        assert template_manager._map_pydantic_type("boolean") == "boolean"
        assert template_manager._map_pydantic_type("array") == "array"
        assert template_manager._map_pydantic_type("object") == "object"
        assert template_manager._map_pydantic_type("unknown") == "string"  # fallback

    @pytest.mark.asyncio
    async def test_validation_rules_extraction(self, template_manager):
        """Test extraction of various validation rules."""
        field_info = {"type": "string", "minLength": 5, "maxLength": 100, "pattern": r"^[a-zA-Z]+$"}

        validation = template_manager._extract_validation_rules(field_info, False)

        assert validation is not None
        assert validation.minLength == 5
        assert validation.maxLength == 100
        assert validation.pattern == r"^[a-zA-Z]+$"

    @pytest.mark.asyncio
    async def test_numeric_validation_rules(self, template_manager):
        """Test extraction of numeric validation rules."""
        field_info = {"type": "integer", "minimum": 0, "maximum": 100}

        validation = template_manager._extract_validation_rules(field_info, False)

        assert validation is not None
        assert validation.min == 0
        assert validation.max == 100

    @pytest.mark.asyncio
    async def test_array_validation_rules(self, template_manager):
        """Test extraction of array validation rules."""
        field_info = {"type": "array", "minItems": 1, "maxItems": 10}

        validation = template_manager._extract_validation_rules(field_info, False)

        assert validation is not None
        assert validation.minItems == 1
        assert validation.maxItems == 10


class TestTemplateValidation:
    """Test template configuration validation."""

    def test_simple_template_validation_valid_config(self):
        """Test that valid configurations pass validation."""
        valid_config = {"response_prefix": "Hello: ", "response_style": "formal"}

        result = SimpleTestAgent.validate_config(valid_config)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_simple_template_validation_invalid_prefix(self):
        """Test that invalid prefix length fails validation."""
        invalid_config = {
            "response_prefix": "",  # Too short
            "response_style": "formal",
        }

        result = SimpleTestAgent.validate_config(invalid_config)
        assert result.valid is False
        assert len(result.errors) > 0
        error_msg = str(result.errors[0]).lower()
        assert any(keyword in error_msg for keyword in ["min_length", "string should have at least"])

    def test_simple_template_validation_invalid_enum(self):
        """Test that invalid enum values fail validation."""
        invalid_config = {"response_prefix": "Hello: ", "response_style": "invalid_style"}

        result = SimpleTestAgent.validate_config(invalid_config)
        assert result.valid is False
        assert len(result.errors) > 0
        assert "enum" in str(result.errors[0]).lower()

    def test_simple_template_validation_prefix_too_long(self):
        """Test that prefix that's too long fails validation."""
        invalid_config = {
            "response_prefix": "A" * 100,  # Too long
            "response_style": "formal",
        }

        result = SimpleTestAgent.validate_config(invalid_config)
        assert result.valid is False
        assert len(result.errors) > 0
        error_msg = str(result.errors[0]).lower()
        assert any(keyword in error_msg for keyword in ["max_length", "string should have at most"])


class TestSchemaResponseStructure:
    """Test the structure of generated schema responses."""

    @pytest.mark.asyncio
    async def test_schema_response_completeness(self, template_manager):
        """Test that schema response contains all required fields."""
        schema_response = template_manager.generate_schema()

        # Check required fields
        assert hasattr(schema_response, "version")
        assert hasattr(schema_response, "lastUpdated")
        assert hasattr(schema_response, "supportedAgentTemplates")
        assert hasattr(schema_response, "capabilities")
        assert hasattr(schema_response, "limits")

        # Check data types
        assert isinstance(schema_response.version, str)
        assert isinstance(schema_response.lastUpdated, str)
        assert isinstance(schema_response.supportedAgentTemplates, list)
        assert isinstance(schema_response.capabilities, RuntimeCapabilities)
        assert isinstance(schema_response.limits, RuntimeLimits)

    @pytest.mark.asyncio
    async def test_capabilities_structure(self, template_manager):
        """Test that capabilities are properly structured."""
        schema_response = template_manager.generate_schema()
        capabilities = schema_response.capabilities

        assert hasattr(capabilities, "streaming")
        assert hasattr(capabilities, "toolCalling")
        assert hasattr(capabilities, "multimodal")
        assert hasattr(capabilities, "codeExecution")

        assert isinstance(capabilities.streaming, bool)
        assert isinstance(capabilities.toolCalling, bool)
        assert isinstance(capabilities.multimodal, bool)
        assert isinstance(capabilities.codeExecution, bool)

    @pytest.mark.asyncio
    async def test_limits_structure(self, template_manager):
        """Test that limits are properly structured."""
        schema_response = template_manager.generate_schema()
        limits = schema_response.limits

        assert hasattr(limits, "maxConcurrentAgents")
        assert hasattr(limits, "maxMessageLength")
        assert hasattr(limits, "maxConversationHistory")

        assert isinstance(limits.maxConcurrentAgents, int)
        assert isinstance(limits.maxMessageLength, int)
        assert isinstance(limits.maxConversationHistory, int)
