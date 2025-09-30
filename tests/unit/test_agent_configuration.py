"""Unit tests for AgentConfiguration value object."""

import pytest

from runtime.domain.value_objects.agent_configuration import AgentConfiguration


class TestAgentConfiguration:
    """Test the AgentConfiguration value object."""

    def test_create_minimal_configuration(self):
        """Test creating configuration with minimal fields."""
        config = AgentConfiguration()
        
        assert config.system_prompt is None
        assert config.llm_config_id is None
        assert config.conversation_config is None
        assert config.toolsets == []
        assert config.template_config == {}

    def test_create_full_configuration(self):
        """Test creating configuration with all fields."""
        conversation_config = {"temperature": 0.8, "max_tokens": 1500}
        toolsets = ["web_search", "calculator"]
        template_config = {"setting1": "value1", "setting2": "value2"}
        
        config = AgentConfiguration(
            system_prompt="You are a helpful assistant",
            llm_config_id="openai-gpt4",
            conversation_config=conversation_config,
            toolsets=toolsets,
            template_config=template_config
        )
        
        assert config.system_prompt == "You are a helpful assistant"
        assert config.llm_config_id == "openai-gpt4"
        assert config.conversation_config == conversation_config
        assert config.toolsets == toolsets
        assert config.template_config == template_config

    def test_validation_invalid_conversation_config(self):
        """Test that invalid conversation_config raises ValueError."""
        with pytest.raises(ValueError, match="conversation_config must be a dictionary"):
            AgentConfiguration(conversation_config="invalid")  # type: ignore

    def test_validation_invalid_toolsets(self):
        """Test that invalid toolsets raises ValueError."""
        with pytest.raises(ValueError, match="toolsets must be a list"):
            AgentConfiguration(toolsets="invalid")  # pyright: ignore

    def test_validation_invalid_template_config(self):
        """Test that invalid template_config raises ValueError."""
        with pytest.raises(ValueError, match="template_config must be a dictionary"):
            AgentConfiguration(template_config="invalid")  # type: ignore

    def test_validation_temperature_out_of_range_high(self):
        """Test that temperature > 2.0 raises ValueError."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            AgentConfiguration(conversation_config={"temperature": 2.5})

    def test_validation_temperature_out_of_range_low(self):
        """Test that temperature < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            AgentConfiguration(conversation_config={"temperature": -0.1})

    def test_validation_temperature_invalid_type(self):
        """Test that invalid temperature type raises ValueError."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            AgentConfiguration(conversation_config={"temperature": "invalid"})

    def test_validation_max_tokens_negative(self):
        """Test that negative max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be a positive integer"):
            AgentConfiguration(conversation_config={"max_tokens": -100})

    def test_validation_max_tokens_zero(self):
        """Test that zero max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be a positive integer"):
            AgentConfiguration(conversation_config={"max_tokens": 0})

    def test_validation_max_tokens_invalid_type(self):
        """Test that invalid max_tokens type raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be a positive integer"):
            AgentConfiguration(conversation_config={"max_tokens": "invalid"})

    def test_validation_max_tokens_float(self):
        """Test that float max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be a positive integer"):
            AgentConfiguration(conversation_config={"max_tokens": 100.5})

    def test_get_toolset_names_empty(self):
        """Test getting empty toolset names."""
        config = AgentConfiguration()
        assert config.get_toolset_names() == []

    def test_get_toolset_names_with_data(self):
        """Test getting toolset names with data."""
        toolsets = ["web_search", "calculator", "file_manager"]
        config = AgentConfiguration(toolsets=toolsets)
        
        result = config.get_toolset_names()
        assert result == toolsets
        # Ensure it's a copy, not the original
        result.append("new_tool")
        assert config.toolsets == toolsets

    def test_get_template_config_value(self):
        """Test getting template config values."""
        template_config = {"setting1": "value1", "setting2": 42}
        config = AgentConfiguration(template_config=template_config)
        
        assert config.get_template_config_value("setting1") == "value1"
        assert config.get_template_config_value("setting2") == 42
        assert config.get_template_config_value("nonexistent") is None
        assert config.get_template_config_value("nonexistent", "default") == "default"

    def test_get_temperature(self):
        """Test getting temperature."""
        # No conversation config
        config = AgentConfiguration()
        assert config.get_temperature() is None
        
        # With conversation config but no temperature
        config = AgentConfiguration(conversation_config={"max_tokens": 1000})
        assert config.get_temperature() is None
        
        # With temperature
        config = AgentConfiguration(conversation_config={"temperature": 0.7})
        assert config.get_temperature() == 0.7

    def test_get_max_tokens(self):
        """Test getting max_tokens."""
        # No conversation config
        config = AgentConfiguration()
        assert config.get_max_tokens() is None
        
        # With conversation config but no max_tokens
        config = AgentConfiguration(conversation_config={"temperature": 0.7})
        assert config.get_max_tokens() is None
        
        # With max_tokens
        config = AgentConfiguration(conversation_config={"max_tokens": 1500})
        assert config.get_max_tokens() == 1500

    def test_get_conversation_config_value(self):
        """Test getting conversation config values."""
        conversation_config = {"temperature": 0.8, "max_tokens": 1000, "custom": "value"}
        config = AgentConfiguration(conversation_config=conversation_config)
        
        assert config.get_conversation_config_value("temperature") == 0.8
        assert config.get_conversation_config_value("max_tokens") == 1000
        assert config.get_conversation_config_value("custom") == "value"
        assert config.get_conversation_config_value("nonexistent") is None
        assert config.get_conversation_config_value("nonexistent", "default") == "default"
        
        # No conversation config
        config_empty = AgentConfiguration()
        assert config_empty.get_conversation_config_value("temperature") is None
        assert config_empty.get_conversation_config_value("temperature", "default") == "default"

    def test_has_toolsets(self):
        """Test has_toolsets method."""
        # No toolsets
        config = AgentConfiguration()
        assert not config.has_toolsets()
        
        # Empty toolsets
        config = AgentConfiguration(toolsets=[])
        assert not config.has_toolsets()
        
        # With toolsets
        config = AgentConfiguration(toolsets=["web_search"])
        assert config.has_toolsets()

    def test_has_execution_params(self):
        """Test has_execution_params method."""
        # No conversation config
        config = AgentConfiguration()
        assert not config.has_execution_params()
        
        # Empty conversation config
        config = AgentConfiguration(conversation_config={})
        assert not config.has_execution_params()
        
        # Conversation config without execution params
        config = AgentConfiguration(conversation_config={"other": "value"})
        assert not config.has_execution_params()
        
        # With temperature
        config = AgentConfiguration(conversation_config={"temperature": 0.7})
        assert config.has_execution_params()
        
        # With max_tokens
        config = AgentConfiguration(conversation_config={"max_tokens": 1000})
        assert config.has_execution_params()
        
        # With both
        config = AgentConfiguration(conversation_config={"temperature": 0.7, "max_tokens": 1000})
        assert config.has_execution_params()

    def test_get_execution_params(self):
        """Test getting execution parameters."""
        # No conversation config
        config = AgentConfiguration()
        assert config.get_execution_params() == {}
        
        # Empty conversation config
        config = AgentConfiguration(conversation_config={})
        assert config.get_execution_params() == {}
        
        # Only temperature
        config = AgentConfiguration(conversation_config={"temperature": 0.8})
        params = config.get_execution_params()
        assert params == {"temperature": 0.8}
        
        # Only max_tokens
        config = AgentConfiguration(conversation_config={"max_tokens": 1500})
        params = config.get_execution_params()
        assert params == {"max_tokens": 1500}
        
        # Both parameters plus other data
        config = AgentConfiguration(conversation_config={
            "temperature": 0.9,
            "max_tokens": 2000,
            "other_param": "ignored"
        })
        params = config.get_execution_params()
        assert params == {"temperature": 0.9, "max_tokens": 2000}
        assert "other_param" not in params

    def test_get_template_configuration_minimal(self):
        """Test getting template configuration with minimal data."""
        config = AgentConfiguration()
        template_config = config.get_template_configuration()
        
        assert template_config == {}

    def test_get_template_configuration_full(self):
        """Test getting template configuration with all data."""
        conversation_config = {
            "temperature": 0.7,
            "max_tokens": 1000,
            "historyLength": 20,  # camelCase conversion test
            "other_param": "value"
        }
        
        config = AgentConfiguration(
            system_prompt="You are helpful",
            llm_config_id="gpt-4",
            toolsets=["web_search", "calculator"],
            template_config={"template_setting": "template_value"},
            conversation_config=conversation_config
        )
        
        template_config = config.get_template_configuration()
        
        # Core fields
        assert template_config["system_prompt"] == "You are helpful"
        assert template_config["llm_config_id"] == "gpt-4"
        assert template_config["toolset_configs"] == ["web_search", "calculator"]
        
        # Template config
        assert template_config["template_setting"] == "template_value"
        
        # Conversation config merged
        assert template_config["temperature"] == 0.7
        assert template_config["max_tokens"] == 1000
        assert template_config["other_param"] == "value"
        
        # camelCase conversion
        assert template_config["history_length"] == 20
        assert "historyLength" not in template_config

    def test_with_conversation_config(self):
        """Test creating new configuration with updated conversation config."""
        original_config = AgentConfiguration(
            system_prompt="Original prompt",
            conversation_config={"temperature": 0.5, "max_tokens": 500}
        )
        
        # Update with new values
        new_config = original_config.with_conversation_config(
            temperature=0.9,
            max_tokens=1500,
            new_param="new_value"
        )
        
        # Original unchanged
        assert original_config.get_temperature() == 0.5
        assert original_config.get_max_tokens() == 500
        assert original_config.get_conversation_config_value("new_param") is None
        
        # New config updated
        assert new_config.get_temperature() == 0.9
        assert new_config.get_max_tokens() == 1500
        assert new_config.get_conversation_config_value("new_param") == "new_value"
        
        # Other fields preserved
        assert new_config.system_prompt == "Original prompt"

    def test_with_conversation_config_no_existing(self):
        """Test creating conversation config when none exists."""
        original_config = AgentConfiguration(system_prompt="Test")
        
        new_config = original_config.with_conversation_config(temperature=0.8)
        
        assert original_config.conversation_config is None
        assert new_config.get_temperature() == 0.8

    def test_with_toolsets(self):
        """Test creating new configuration with updated toolsets."""
        original_config = AgentConfiguration(
            system_prompt="Original prompt",
            toolsets=["old_tool"]
        )
        
        new_toolsets = ["new_tool1", "new_tool2"]
        new_config = original_config.with_toolsets(new_toolsets)
        
        # Original unchanged
        assert original_config.toolsets == ["old_tool"]
        
        # New config updated
        assert new_config.toolsets == new_toolsets
        
        # Other fields preserved
        assert new_config.system_prompt == "Original prompt"

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        conversation_config = {"temperature": 0.7, "max_tokens": 1000}
        toolsets = ["web_search", "calculator"]
        template_config = {"setting": "value"}
        
        config = AgentConfiguration(
            system_prompt="Test prompt",
            llm_config_id="gpt-4",
            conversation_config=conversation_config,
            toolsets=toolsets,
            template_config=template_config
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["system_prompt"] == "Test prompt"
        assert config_dict["llm_config_id"] == "gpt-4"
        assert config_dict["conversation_config"] == conversation_config
        assert config_dict["toolsets"] == toolsets
        assert config_dict["template_config"] == template_config

    def test_from_dict(self):
        """Test creating configuration from dictionary."""
        config_dict = {
            "system_prompt": "From dict prompt",
            "llm_config_id": "claude-3",
            "conversation_config": {"temperature": 0.8},
            "toolsets": ["file_manager"],
            "template_config": {"key": "value"}
        }
        
        config = AgentConfiguration.from_dict(config_dict)
        
        assert config.system_prompt == "From dict prompt"
        assert config.llm_config_id == "claude-3"
        assert config.get_temperature() == 0.8
        assert config.toolsets == ["file_manager"]
        assert config.template_config == {"key": "value"}

    def test_from_dict_minimal(self):
        """Test creating configuration from minimal dictionary."""
        config_dict = {}
        config = AgentConfiguration.from_dict(config_dict)
        
        assert config.system_prompt is None
        assert config.llm_config_id is None
        assert config.conversation_config is None
        assert config.toolsets == []
        assert config.template_config == {}


    def test_roundtrip_serialization(self):
        """Test that configuration can be serialized and deserialized."""
        original = AgentConfiguration(
            system_prompt="Test prompt",
            llm_config_id="gpt-4",
            conversation_config={"temperature": 0.8, "max_tokens": 1500},
            toolsets=["web_search", "calculator"],
            template_config={"setting1": "value1", "setting2": 42}
        )
        
        # Serialize to dict
        config_dict = original.to_dict()
        
        # Deserialize from dict
        restored = AgentConfiguration.from_dict(config_dict)
        
        # Should be equivalent
        assert restored.system_prompt == original.system_prompt
        assert restored.llm_config_id == original.llm_config_id
        assert restored.conversation_config == original.conversation_config
        assert restored.toolsets == original.toolsets
        assert restored.template_config == original.template_config
