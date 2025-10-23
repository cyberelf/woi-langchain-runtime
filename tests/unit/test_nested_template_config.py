"""Unit tests for nested template configuration support.

Tests verify that ConfigField and TemplateInfo can properly handle
nested structures (arrays with items, objects with properties) and
that serialization/deserialization round-trips work correctly.
"""

import pytest
from runtime.domain.value_objects.template import (
    ConfigField,
    ConfigFieldValidation,
    TemplateInfo
)


class TestNestedConfigField:
    """Test nested ConfigField structures."""
    
    def test_create_array_field_with_string_items(self):
        """Test creating an array field with simple string items."""
        items_field = ConfigField(
            key="items",
            field_type="string",
            description="A string item"
        )
        
        array_field = ConfigField.create_array_field(
            key="tags",
            items=items_field,
            description="List of tags"
        )
        
        assert array_field.key == "tags"
        assert array_field.field_type == "array"
        assert array_field.items is not None
        assert array_field.items.field_type == "string"
    
    def test_create_array_field_with_object_items(self):
        """Test creating an array field with object items."""
        # Create object schema for array items
        object_properties = {
            "name": ConfigField(
                key="name",
                field_type="string",
                description="Step name"
            ),
            "timeout": ConfigField(
                key="timeout",
                field_type="integer",
                description="Timeout in seconds",
                default_value=60
            )
        }
        
        items_field = ConfigField.create_object_field(
            key="items",
            properties=object_properties,
            description="A workflow step"
        )
        
        array_field = ConfigField.create_array_field(
            key="steps",
            items=items_field,
            description="Workflow steps"
        )
        
        assert array_field.key == "steps"
        assert array_field.field_type == "array"
        assert array_field.items is not None
        assert array_field.items.field_type == "object"
        assert array_field.items.properties is not None
        assert "name" in array_field.items.properties
        assert "timeout" in array_field.items.properties
        assert array_field.items.properties["timeout"].default_value == 60
    
    def test_create_object_field_with_nested_array(self):
        """Test creating an object field that contains an array property."""
        # Create an array property
        tools_field = ConfigField.create_array_field(
            key="tools",
            items=ConfigField(
                key="items",
                field_type="string",
                description="Tool name"
            ),
            description="Available tools"
        )
        
        # Create object with array property
        object_field = ConfigField.create_object_field(
            key="config",
            properties={
                "name": ConfigField(
                    key="name",
                    field_type="string",
                    description="Config name"
                ),
                "tools": tools_field
            },
            description="Configuration object"
        )
        
        assert object_field.field_type == "object"
        assert object_field.properties is not None
        assert "tools" in object_field.properties
        assert object_field.properties["tools"].field_type == "array"
        assert object_field.properties["tools"].items is not None
        assert object_field.properties["tools"].items.field_type == "string"
    
    def test_nested_array_serialization(self):
        """Test that nested array fields serialize correctly to dict."""
        items_field = ConfigField(
            key="items",
            field_type="string",
            description="String item"
        )
        
        array_field = ConfigField.create_array_field(
            key="tags",
            items=items_field,
            description="List of tags"
        )
        
        result = array_field.to_dict()
        
        assert result["key"] == "tags"
        assert result["type"] == "array"
        assert result["description"] == "List of tags"
        assert "items" in result
        assert result["items"]["type"] == "string"
        assert result["items"]["description"] == "String item"
    
    def test_nested_object_serialization(self):
        """Test that nested object fields serialize correctly to dict."""
        object_field = ConfigField.create_object_field(
            key="step",
            properties={
                "name": ConfigField(
                    key="name",
                    field_type="string",
                    description="Step name"
                ),
                "timeout": ConfigField(
                    key="timeout",
                    field_type="integer",
                    description="Timeout",
                    default_value=30
                )
            },
            description="A workflow step"
        )
        
        result = object_field.to_dict()
        
        assert result["key"] == "step"
        assert result["type"] == "object"
        assert "properties" in result
        assert "name" in result["properties"]
        assert "timeout" in result["properties"]
        assert result["properties"]["name"]["type"] == "string"
        assert result["properties"]["timeout"]["type"] == "integer"
        assert result["properties"]["timeout"]["default"] == 30
    
    def test_deeply_nested_serialization(self):
        """Test deeply nested structure (array of objects with array properties)."""
        # Create inner array (tools)
        tools_items = ConfigField(
            key="items",
            field_type="string",
            description="Tool name"
        )
        tools_field = ConfigField.create_array_field(
            key="tools",
            items=tools_items,
            description="Tools list"
        )
        
        # Create object with array property
        step_properties = {
            "name": ConfigField(
                key="name",
                field_type="string",
                description="Step name"
            ),
            "tools": tools_field
        }
        step_object = ConfigField.create_object_field(
            key="items",
            properties=step_properties,
            description="Step config"
        )
        
        # Create outer array
        steps_field = ConfigField.create_array_field(
            key="steps",
            items=step_object,
            description="Workflow steps"
        )
        
        result = steps_field.to_dict()
        
        # Verify structure
        assert result["type"] == "array"
        assert result["items"]["type"] == "object"
        assert "tools" in result["items"]["properties"]
        assert result["items"]["properties"]["tools"]["type"] == "array"
        assert result["items"]["properties"]["tools"]["items"]["type"] == "string"
    
    def test_array_deserialization(self):
        """Test that array fields deserialize correctly from dict."""
        data = {
            "key": "tags",
            "type": "array",
            "description": "List of tags",
            "items": {
                "key": "items",
                "type": "string",
                "description": "A tag"
            }
        }
        
        field = ConfigField.from_dict(data)
        
        assert field.key == "tags"
        assert field.field_type == "array"
        assert field.items is not None
        assert field.items.field_type == "string"
        assert field.items.description == "A tag"
    
    def test_object_deserialization(self):
        """Test that object fields deserialize correctly from dict."""
        data = {
            "key": "step",
            "type": "object",
            "description": "A step",
            "properties": {
                "name": {
                    "key": "name",
                    "type": "string",
                    "description": "Step name"
                },
                "timeout": {
                    "key": "timeout",
                    "type": "integer",
                    "description": "Timeout",
                    "default": 60
                }
            }
        }
        
        field = ConfigField.from_dict(data)
        
        assert field.key == "step"
        assert field.field_type == "object"
        assert field.properties is not None
        assert "name" in field.properties
        assert "timeout" in field.properties
        assert field.properties["name"].field_type == "string"
        assert field.properties["timeout"].default_value == 60
    
    def test_nested_round_trip(self):
        """Test that nested structures round-trip correctly through to_dict/from_dict."""
        # Create nested structure
        original = ConfigField.create_array_field(
            key="steps",
            items=ConfigField.create_object_field(
                key="items",
                properties={
                    "name": ConfigField(
                        key="name",
                        field_type="string",
                        description="Step name"
                    ),
                    "tools": ConfigField.create_array_field(
                        key="tools",
                        items=ConfigField(
                            key="items",
                            field_type="string"
                        )
                    )
                }
            ),
            description="Steps"
        )
        
        # Serialize
        serialized = original.to_dict()
        
        # Deserialize
        reconstructed = ConfigField.from_dict(serialized)
        
        # Verify
        assert reconstructed.key == original.key
        assert reconstructed.field_type == original.field_type
        assert reconstructed.items is not None
        assert reconstructed.items.properties is not None
        assert "tools" in reconstructed.items.properties
        assert reconstructed.items.properties["tools"].field_type == "array"
    
    def test_optional_field_serialization(self):
        """Test that an optional field serializes with 'optional': True."""
        field = ConfigField(
            key="optional_field",
            field_type="string",
            optional=True
        )
        
        result = field.to_dict()
        
        assert result["key"] == "optional_field"
        assert result["optional"] is True
    
    def test_optional_field_deserialization(self):
        """Test that an optional field deserializes correctly."""
        data = {
            "key": "optional_field",
            "type": "string",
            "optional": True
        }
        
        field = ConfigField.from_dict(data)
        
        assert field.key == "optional_field"
        assert field.optional is True
        
    def test_non_optional_field_serialization(self):
        """Test that a non-optional field does not include 'optional' key."""
        field = ConfigField(
            key="required_field",
            field_type="string",
            optional=False
        )
        
        result = field.to_dict()
        
        assert "optional" not in result
        
    def test_non_optional_field_deserialization(self):
        """Test that a non-optional field deserializes with optional=False."""
        data = {
            "key": "required_field",
            "type": "string"
        }
        
        field = ConfigField.from_dict(data)
        
        assert field.optional is False


class TestTemplateInfoWithNestedConfig:
    """Test TemplateInfo with nested configuration fields."""
    
    def test_template_with_nested_array_config(self):
        """Test TemplateInfo with array config field."""
        config_fields = [
            ConfigField.create_array_field(
                key="tags",
                items=ConfigField(
                    key="items",
                    field_type="string",
                    description="Tag value"
                ),
                description="List of tags"
            )
        ]
        
        template = TemplateInfo(
            id="test-template",
            framework="langgraph",
            name="Test Template",
            description="A test template",
            version="1.0.0",
            config_fields=config_fields
        )
        
        assert template.has_config_fields()
        assert len(template.config_fields) == 1
        assert template.config_fields[0].field_type == "array"
        assert template.config_fields[0].items is not None
    
    def test_template_serialization_with_nested_config(self):
        """Test that TemplateInfo serializes nested config correctly."""
        config_fields = [
            ConfigField.create_array_field(
                key="steps",
                items=ConfigField.create_object_field(
                    key="items",
                    properties={
                        "name": ConfigField(
                            key="name",
                            field_type="string",
                            description="Step name"
                        ),
                        "timeout": ConfigField(
                            key="timeout",
                            field_type="integer",
                            description="Timeout",
                            default_value=60
                        )
                    },
                    description="Step configuration"
                ),
                description="Workflow steps"
            )
        ]
        
        template = TemplateInfo(
            id="workflow-template",
            framework="langgraph",
            name="Workflow Template",
            description="A workflow template",
            version="1.0.0",
            config_fields=config_fields
        )
        
        result = template.to_dict()
        
        assert result["id"] == "workflow-template"
        assert "config" in result
        assert len(result["config"]) == 1
        
        steps_config = result["config"][0]
        assert steps_config["key"] == "steps"
        assert steps_config["type"] == "array"
        assert "items" in steps_config
        assert steps_config["items"]["type"] == "object"
        assert "properties" in steps_config["items"]
        assert "name" in steps_config["items"]["properties"]
        assert "timeout" in steps_config["items"]["properties"]
    
    def test_template_deserialization_with_nested_config(self):
        """Test that TemplateInfo deserializes nested config correctly."""
        data = {
            "id": "workflow-template",
            "framework": "langgraph",
            "name": "Workflow Template",
            "description": "A workflow",
            "version": "1.0.0",
            "config": [
                {
                    "key": "steps",
                    "type": "array",
                    "description": "Steps",
                    "items": {
                        "key": "items",
                        "type": "object",
                        "properties": {
                            "name": {
                                "key": "name",
                                "type": "string",
                                "description": "Name"
                            },
                            "timeout": {
                                "key": "timeout",
                                "type": "integer",
                                "default": 60
                            }
                        }
                    }
                }
            ]
        }
        
        template = TemplateInfo.from_dict(data)
        
        assert template.id == "workflow-template"
        assert len(template.config_fields) == 1
        
        steps_field = template.config_fields[0]
        assert steps_field.key == "steps"
        assert steps_field.field_type == "array"
        assert steps_field.items is not None
        assert steps_field.items.field_type == "object"
        assert steps_field.items.properties is not None
        assert "name" in steps_field.items.properties
        assert "timeout" in steps_field.items.properties
        assert steps_field.items.properties["timeout"].default_value == 60
    
    def test_template_round_trip_with_nested_config(self):
        """Test that TemplateInfo with nested config round-trips correctly."""
        original = TemplateInfo(
            id="test-id",
            framework="langgraph",
            name="Test",
            description="Test template",
            version="1.0.0",
            config_fields=[
                ConfigField.create_array_field(
                    key="items",
                    items=ConfigField.create_object_field(
                        key="items",
                        properties={
                            "field1": ConfigField(
                                key="field1",
                                field_type="string"
                            )
                        }
                    )
                )
            ]
        )
        
        # Serialize and deserialize
        serialized = original.to_dict()
        reconstructed = TemplateInfo.from_dict(serialized)
        
        # Verify
        assert reconstructed.id == original.id
        assert len(reconstructed.config_fields) == len(original.config_fields)
        assert reconstructed.config_fields[0].field_type == "array"
        assert reconstructed.config_fields[0].items is not None
        assert reconstructed.config_fields[0].items.field_type == "object"
        assert reconstructed.config_fields[0].items.properties is not None
        assert "field1" in reconstructed.config_fields[0].items.properties
    
    def test_template_info_serialization_with_optional_field(self):
        """Test serialization of TemplateInfo with an optional config field."""
        config_field = ConfigField(
            key="optional_field",
            field_type="string",
            optional=True
        )
        
        template = TemplateInfo(
            id="test-template",
            framework="langgraph",
            name="Test Template",
            description="A test template",
            version="1.0.0",
            config_fields=[config_field]
        )
        
        result = template.to_dict()
        
        assert "config" in result
        assert len(result["config"]) == 1
        
        field_dict = result["config"][0]
        assert field_dict["key"] == "optional_field"
        assert field_dict["type"] == "string"
        assert "optional" in field_dict
        assert field_dict["optional"] is True
    
    def test_template_info_deserialization_with_optional_field(self):
        """Test deserialization of TemplateInfo with an optional config field."""
        data = {
            "id": "test-template",
            "framework": "langgraph",
            "name": "Test Template",
            "description": "A test template",
            "version": "1.0.0",
            "config": [
                {
                    "key": "optional_field",
                    "type": "string",
                    "optional": True
                }
            ]
        }
        
        template = TemplateInfo.from_dict(data)
        
        assert template.id == "test-template"
        assert len(template.config_fields) == 1
        
        config_field = template.config_fields[0]
        assert config_field.key == "optional_field"
        assert config_field.field_type == "string"
        assert config_field.optional is True
    
    def test_template_info_serialization_without_optional_field(self):
        """Test serialization of TemplateInfo with a non-optional config field."""
        config_field = ConfigField(
            key="required_field",
            field_type="string",
            optional=False
        )
        
        template = TemplateInfo(
            id="test-template",
            framework="langgraph",
            name="Test Template",
            description="A test template",
            version="1.0.0",
            config_fields=[config_field]
        )
        
        result = template.to_dict()
        
        assert "config" in result
        assert len(result["config"]) == 1
        
        field_dict = result["config"][0]
        assert field_dict["key"] == "required_field"
        assert field_dict["type"] == "string"
        assert "optional" not in field_dict
    
    def test_template_info_deserialization_without_optional_field(self):
        """Test deserialization of TemplateInfo with a non-optional config field."""
        data = {
            "id": "test-template",
            "framework": "langgraph",
            "name": "Test Template",
            "description": "A test template",
            "version": "1.0.0",
            "config": [
                {
                    "key": "required_field",
                    "type": "string"
                }
            ]
        }
        
        template = TemplateInfo.from_dict(data)
        
        assert template.id == "test-template"
        assert len(template.config_fields) == 1
        
        config_field = template.config_fields[0]
        assert config_field.key == "required_field"
        assert config_field.field_type == "string"
        assert config_field.optional is False
    
    def test_config_field_with_array_of_atomic_types(self):
        """Test serialization and deserialization of a field with an array of strings."""
        field = ConfigField(
            key="tags",
            field_type="array",
            items=ConfigField(key="items", field_type="string", optional=False),
        )
        field_dict = field.to_dict()
        assert field_dict == {
            "key": "tags",
            "type": "array",
            "items": {"key": "items", "type": "string"},
        }
        reconstructed_field = ConfigField.from_dict(field_dict)
        assert reconstructed_field == field

    def test_config_field_with_array_of_arrays(self):
        """Test serialization and deserialization of a field with a nested array."""
        field = ConfigField(
            key="matrix",
            field_type="array",
            items=ConfigField(
                key="items",
                field_type="array",
                optional=False,
                items=ConfigField(key="items", field_type="integer", optional=False),
            ),
        )
        field_dict = field.to_dict()
        assert field_dict == {
            "key": "matrix",
            "type": "array",
            "items": {
                "key": "items",
                "type": "array",
                "items": {"key": "items", "type": "integer"},
            },
        }
        reconstructed_field = ConfigField.from_dict(field_dict)
        assert reconstructed_field == field

    def test_config_field_with_array_of_objects(self):
        """Test serialization and deserialization of a field with an array of objects."""
        field = ConfigField(
            key="users",
            field_type="array",
            items=ConfigField(
                key="items",
                field_type="object",
                optional=False,
                properties={
                    "id": ConfigField(key="id", field_type="integer", optional=False),
                    "name": ConfigField(key="name", field_type="string", optional=True),
                },
            ),
        )
        field_dict = field.to_dict()
        assert field_dict == {
            "key": "users",
            "type": "array",
            "items": {
                "key": "items",
                "type": "object",
                "properties": {
                    "id": {"key": "id", "type": "integer"},
                    "name": {"key": "name", "type": "string", "optional": True},
                },
            },
        }
        reconstructed_field = ConfigField.from_dict(field_dict)
        assert reconstructed_field == field
