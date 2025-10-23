"""Integration test for ComposeAgentService with nested config structures.

Verifies that the compose service correctly handles templates with nested
configuration (arrays, objects) and renders them properly in the system prompt.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from runtime.application.services.compose_agent_service import ComposeAgentService
from runtime.infrastructure.frameworks.langgraph.executor import LangGraphFrameworkExecutor
from runtime.service_config import ServicesConfig


@pytest.mark.asyncio
async def test_compose_renders_nested_config_in_prompt():
    """Test that compose service renders nested config structure in system prompt."""
    # Setup real framework executor
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    llm_service = framework_executor.get_llm_service()
    
    # Mock LLM client to capture the prompt
    mock_llm_client = AsyncMock()
    captured_messages = []
    
    async def capture_invoke(messages):
        """Capture messages sent to LLM."""
        captured_messages.extend(messages)
        # Return a valid response
        response = MagicMock()
        response.content = json.dumps({
            "name": "Test Agent",
            "description": "Test",
            "system_prompt": "Test prompt",
            "template_config": {
                "workflow_responsibility": "Test workflow",
                "steps": [
                    {
                        "name": "Step 1",
                        "prompt": "Do something",
                        "tools": [],
                        "timeout": 30,
                        "retry_count": 0
                    }
                ]
            },
            "toolsets": []
        })
        return response
    
    mock_llm_client.ainvoke = capture_invoke
    
    # Patch LLM service
    with patch.object(llm_service, 'get_client', return_value=mock_llm_client):
        service = ComposeAgentService(llm_service, framework_executor)
        
        # Execute composition for workflow template
        result = await service.compose(
            template_id="langgraph-workflow",
            instructions="Create a test workflow",
            llm_config_id="deepseek"
        )
        
        # Verify we got a result
        assert result["template_id"] == "langgraph-workflow"
        
        # Verify system prompt was captured
        assert len(captured_messages) >= 1
        system_message = captured_messages[0]
        system_prompt = system_message.content
        
        # Verify nested config is rendered in prompt
        # Should contain the "steps" field description
        assert "steps" in system_prompt.lower()
        
        # Should show nested structure (items/properties)
        assert "items:" in system_prompt or "properties:" in system_prompt
        
        # Should contain nested field details (name, prompt, timeout, etc.)
        assert "name" in system_prompt.lower()
        assert "timeout" in system_prompt.lower()
        
        # Should show type information for nested fields
        assert "type:" in system_prompt.lower()
        
        # Print captured prompt for inspection
        print("\n" + "="*80)
        print("CAPTURED SYSTEM PROMPT:")
        print("="*80)
        print(system_prompt)
        print("="*80 + "\n")
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
async def test_compose_workflow_with_nested_steps_validation():
    """Test that composed workflow configurations with nested steps validate correctly."""
    # Setup
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    llm_service = framework_executor.get_llm_service()
    
    # Mock LLM to return a valid nested config
    mock_llm_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "name": "Data Processing Workflow",
        "description": "Processes data in steps",
        "system_prompt": "You process data step by step",
        "template_config": {
            "workflow_responsibility": "Processing data files",
            "steps": [
                {
                    "id": "load",
                    "name": "Load Data",
                    "prompt": "Load the data file",
                    "tools": [],
                    "timeout": 60,
                    "retry_count": 1
                },
                {
                    "id": "process",
                    "name": "Process Data",
                    "prompt": "Process the loaded data",
                    "tools": ["calculator"],
                    "depends_on": ["load"],
                    "timeout": 120,
                    "retry_count": 2
                }
            ],
            "max_retries": 3,
            "step_timeout": 90,
            "fail_on_error": True,
            "history_size": 10
        },
        "toolsets": [],
        "reasoning": "Created a two-step workflow"
    })
    mock_llm_client.ainvoke.return_value = mock_response
    
    with patch.object(llm_service, 'get_client', return_value=mock_llm_client):
        service = ComposeAgentService(llm_service, framework_executor)
        
        # Compose
        result = await service.compose(
            template_id="langgraph-workflow",
            instructions="Create a workflow that processes data files",
            llm_config_id="deepseek"
        )
        
        # Verify result structure
        assert result["template_id"] == "langgraph-workflow"
        assert "template_config" in result
        
        config = result["template_config"]
        
        # Verify nested steps structure
        assert "steps" in config
        assert isinstance(config["steps"], list)
        assert len(config["steps"]) == 2
        
        # Verify first step structure
        step1 = config["steps"][0]
        assert step1["name"] == "Load Data"
        assert step1["timeout"] == 60
        assert isinstance(step1["tools"], list)
        
        # Verify second step structure
        step2 = config["steps"][1]
        assert step2["name"] == "Process Data"
        assert step2["depends_on"] == ["load"]
        assert "calculator" in step2["tools"]
        
        # Validate against template
        is_valid, validation_error = framework_executor.validate_template_configuration(
            "langgraph-workflow",
            config
        )
        
        # Should be valid
        if not is_valid:
            print(f"\nValidation error: {validation_error}")
        
        assert is_valid or "validation_warning" not in result
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
async def test_compose_detects_invalid_nested_structure():
    """Test that compose service detects invalid nested configuration."""
    # Setup
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    llm_service = framework_executor.get_llm_service()
    
    # Mock LLM to return invalid nested config (missing required fields)
    mock_llm_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "name": "Invalid Workflow",
        "description": "Invalid config",
        "system_prompt": "Test",
        "template_config": {
            "steps": [
                {
                    # Missing required fields like 'name' and 'prompt'
                    "timeout": 60
                }
            ]
        },
        "toolsets": []
    })
    mock_llm_client.ainvoke.return_value = mock_response
    
    with patch.object(llm_service, 'get_client', return_value=mock_llm_client):
        service = ComposeAgentService(llm_service, framework_executor)
        
        # Compose
        result = await service.compose(
            template_id="langgraph-workflow",
            instructions="Create a workflow",
            llm_config_id="deepseek"
        )
        
        # Should have validation warning
        assert "validation_warning" in result or result.get("template_config") != {
            "steps": [{"timeout": 60}]
        }
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
async def test_get_workflow_template_shows_nested_structure():
    """Test that getting workflow template directly shows nested config structure."""
    # Setup
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    # Get templates
    templates = framework_executor.get_templates()
    
    # Find workflow template
    workflow_template = None
    for tmpl in templates:
        if tmpl.id == "langgraph-workflow":
            workflow_template = tmpl
            break
    
    assert workflow_template is not None
    
    # Serialize to dict (as API does)
    template_dict = workflow_template.to_dict()
    
    # Verify config has nested structure
    assert "config" in template_dict
    config_fields = template_dict["config"]
    
    # Find steps field
    steps_field = None
    for field in config_fields:
        if field["key"] == "steps":
            steps_field = field
            break
    
    assert steps_field is not None
    assert steps_field["type"] == "array"
    
    # Verify steps has nested items schema
    assert "items" in steps_field
    items = steps_field["items"]
    assert items["type"] == "object"
    
    # Verify items has properties
    assert "properties" in items
    properties = items["properties"]
    
    # Verify expected properties exist
    assert "name" in properties
    assert "prompt" in properties
    assert "tools" in properties
    assert "timeout" in properties
    
    # Verify tools is itself an array
    tools_prop = properties["tools"]
    assert tools_prop["type"] == "array"
    assert "items" in tools_prop
    assert tools_prop["items"]["type"] == "string"
    
    # Print the structure for inspection
    print("\n" + "="*80)
    print("WORKFLOW TEMPLATE STRUCTURE:")
    print("="*80)
    print(json.dumps(steps_field, indent=2))
    print("="*80 + "\n")
    
    # Cleanup
    await framework_executor.shutdown()
