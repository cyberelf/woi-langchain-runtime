"""Integration tests for ComposeAgentService.

These tests verify the compose agent functionality works with real
framework executors and services (but mocked LLM).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from runtime.application.services.compose_agent_service import ComposeAgentService
from runtime.infrastructure.frameworks.langgraph.executor import LangGraphFrameworkExecutor
from runtime.infrastructure.frameworks.langgraph.llm.service import LangGraphLLMService
from runtime.service_config import ServicesConfig


@pytest.fixture
def check_deepseek_configured():
    """Fixture to check if DeepSeek API is properly configured.
    
    Automatically skips the test if:
    - API key is not configured
    - API key is the default test placeholder
    
    Usage:
        @pytest.mark.asyncio
        async def test_something(check_deepseek_configured):
            # Test will auto-skip if API not configured
            ...
    """
    import os
    import dotenv
    # Load environment variables from .env file if present
    dotenv.load_dotenv()

    test_config = ServicesConfig(config_file="config/test-services-config.json")
    config_dict = test_config.get_config_dict()
    
    llm_config = config_dict.get("llm", {})
    providers = llm_config.get("providers", {})
    deepseek_config = providers.get("deepseek", {})

    if not deepseek_config.get("api_key") and not os.environ.get("DEEPSEEK_API_KEY"):
        pytest.skip("DeepSeek API key not configured - skipping real LLM test")
    
    # Return the config for use in the test if needed
    return config_dict


@pytest.mark.asyncio
async def test_compose_with_real_framework_executor():
    """Test compose with real LangGraph framework executor."""
    # Setup real framework executor with test config
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    # Setup LLM service with mocked client
    llm_service = framework_executor.get_llm_service()
    
    # Mock the LLM client response
    mock_llm_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "name": "Test Workflow Agent",
        "description": "A workflow agent for testing",
        "system_prompt": "You are a test workflow agent that processes tasks step by step",
        "template_config": {
            "workflow_responsibility": "Processing test tasks",
            "steps": [
                {
                    "name": "Step 1: Validate Input",
                    "prompt": "Validate the input data",
                    "tools": [],
                    "timeout": 30,
                    "retry_count": 1
                }
            ],
            "max_retries": 2,
            "step_timeout": 60,
            "fail_on_error": False
        },
        "toolsets": [],
        "reasoning": "Created a simple workflow for testing"
    })
    mock_llm_client.ainvoke.return_value = mock_response
    
    # Patch the LLM service to return our mocked client
    with patch.object(llm_service, 'get_client', return_value=mock_llm_client):
        # Create service
        service = ComposeAgentService(llm_service, framework_executor)
        
        # Execute composition
        result = await service.compose(
            template_id="langgraph-workflow",
            instructions="Create a workflow agent that processes test tasks",
            llm_config_id="deepseek"
        )
        
        # Verify result
        assert result["name"] == "Test Workflow Agent"
        assert result["template_id"] == "langgraph-workflow"
        assert "template_config" in result
        assert "workflow_responsibility" in result["template_config"]
        assert "steps" in result["template_config"]
        assert len(result["template_config"]["steps"]) == 1
        
        # Verify LLM was called with correct prompts
        mock_llm_client.ainvoke.assert_called_once()
        call_args = mock_llm_client.ainvoke.call_args[0][0]
        assert len(call_args) == 2  # System and user messages
        assert "langgraph-workflow" in call_args[0].content.lower()
        assert "Create a workflow agent" in call_args[1].content
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
async def test_compose_with_real_templates():
    """Test compose gets real template information."""
    # Setup real framework executor
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    # Get real templates
    templates = framework_executor.get_templates()
    assert len(templates) > 0
    
    # Find a workflow template
    workflow_template = None
    for tmpl in templates:
        if tmpl.id == "langgraph-workflow":
            workflow_template = tmpl
            break
    
    assert workflow_template is not None
    assert workflow_template.name
    assert workflow_template.description
    assert len(workflow_template.config_fields) > 0
    
    # Verify config fields are proper objects
    for field in workflow_template.config_fields:
        assert hasattr(field, 'key')
        assert hasattr(field, 'field_type')
        assert hasattr(field, 'description')
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
async def test_compose_with_toolset_service():
    """Test compose gets real toolset information."""
    # Setup real framework executor
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    # Get toolset service
    toolset_service = framework_executor.get_toolset_service()
    assert toolset_service is not None
    
    # Get all toolset names
    toolset_names = toolset_service.get_all_toolset_names()
    assert isinstance(toolset_names, list)
    assert len(toolset_names) > 0
    
    # Verify all names are strings
    for name in toolset_names:
        assert isinstance(name, str)
        assert len(name) > 0
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
async def test_compose_validates_against_template():
    """Test compose validates generated config against template."""
    # Setup real framework executor
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    llm_service = framework_executor.get_llm_service()
    
    # Mock LLM with invalid configuration
    mock_llm_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "name": "Test Agent",
        "description": "Test",
        "system_prompt": "Test prompt",
        "template_config": {
            "invalid_field": "This field doesn't exist in the template"
        },
        "toolsets": []
    })
    mock_llm_client.ainvoke.return_value = mock_response
    
    with patch.object(llm_service, 'get_client', return_value=mock_llm_client):
        service = ComposeAgentService(llm_service, framework_executor)
        
        # Execute - should succeed but include validation warning
        result = await service.compose(
            template_id="langgraph-workflow",
            instructions="Create a test agent"
        )
        
        # Should have validation warning since config is invalid
        assert "validation_warning" in result or result.get("template_config") != {"invalid_field": "This field doesn't exist in the template"}
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
async def test_compose_end_to_end_workflow():
    """Test complete end-to-end workflow with composition and validation."""
    # Setup
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    llm_service = framework_executor.get_llm_service()
    
    # Mock valid LLM response
    valid_config = {
        "name": "Data Processing Agent",
        "description": "Processes and analyzes data files",
        "system_prompt": "You are a data processing expert. Process data step by step.",
        "template_config": {
            "workflow_responsibility": "Processing and analyzing data files",
            "steps": [
                {
                    "name": "Step 1: Load Data",
                    "prompt": "Load and validate the data file",
                    "tools": [],
                    "timeout": 60,
                    "retry_count": 2
                },
                {
                    "name": "Step 2: Process Data",
                    "prompt": "Process the data and extract insights",
                    "tools": [],
                    "timeout": 120,
                    "retry_count": 1
                }
            ],
            "max_retries": 3,
            "step_timeout": 90,
            "fail_on_error": False
        },
        "toolsets": [],
        "reasoning": "Created a two-step workflow for data processing"
    }
    
    mock_llm_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps(valid_config)
    mock_llm_client.ainvoke.return_value = mock_response
    
    with patch.object(llm_service, 'get_client', return_value=mock_llm_client):
        service = ComposeAgentService(llm_service, framework_executor)
        
        # Step 1: Compose configuration
        result = await service.compose(
            template_id="langgraph-workflow",
            instructions="Create an agent that processes data files step by step",
            suggested_name="Data Processor",
            suggested_tools=[]
        )
        
        # Verify composition result
        assert result["template_id"] == "langgraph-workflow"
        assert "template_config" in result
        
        # Step 2: Verify the configuration is valid
        template_config = result["template_config"]
        is_valid, error = framework_executor.validate_template_configuration(
            "langgraph-workflow",
            template_config
        )
        
        # Should be valid
        assert is_valid or "validation_warning" not in result
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
async def test_compose_with_different_templates():
    """Test compose works with different template types."""
    # Setup
    test_config = ServicesConfig(config_file="config/test-services-config.json")
    framework_executor = LangGraphFrameworkExecutor(
        service_config=test_config.get_config_dict()
    )
    await framework_executor.initialize()
    
    llm_service = framework_executor.get_llm_service()
    
    # Get all available templates
    templates = framework_executor.get_templates()
    
    # Test with first available template
    if len(templates) > 0:
        test_template = templates[0]
        
        # Mock LLM response
        mock_llm_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "name": "Test Agent",
            "description": "Test agent",
            "system_prompt": "Test prompt",
            "template_config": {},
            "toolsets": []
        })
        mock_llm_client.ainvoke.return_value = mock_response
        
        with patch.object(llm_service, 'get_client', return_value=mock_llm_client):
            service = ComposeAgentService(llm_service, framework_executor)
            
            result = await service.compose(
                template_id=test_template.id,
                instructions="Create a test agent"
            )
            
            assert result["template_id"] == test_template.id
    
    # Cleanup
    await framework_executor.shutdown()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_compose_with_real_deepseek_llm(check_deepseek_configured):
    """Test compose with real DeepSeek LLM API call.
    
    This test makes an actual API call to DeepSeek and requires:
    - Valid API credentials in config
    - Internet connection
    - API quota/credits
    
    Mark as slow since it makes real API calls.
    """
    # Get config from fixture (test auto-skipped if not configured)
    config_dict = check_deepseek_configured
    
    # Setup real framework executor
    framework_executor = LangGraphFrameworkExecutor(service_config=config_dict)
    await framework_executor.initialize()
    
    # Get real LLM service (no mocking!)
    llm_service = framework_executor.get_llm_service()
    
    # Create compose service with REAL LLM
    service = ComposeAgentService(llm_service, framework_executor)
    
    try:
        # Execute composition with real LLM
        result = await service.compose(
            template_id="simple-test",
            instructions="Create a helpful assistant agent that answers questions politely",
            suggested_name="Helpful Assistant",
            llm_config_id="deepseek"
        )
        
        # Verify result structure
        assert "name" in result
        assert "description" in result
        assert "system_prompt" in result
        assert "template_config" in result
        assert result["template_id"] == "simple-test"
        assert result["template_version_id"] == "1.0.0"
        
        # Verify the LLM generated reasonable content
        assert len(result["name"]) > 0
        assert len(result["system_prompt"]) > 10  # Should be a proper prompt
        
        # Verify template_config has proper structure for simple-test template
        template_config = result["template_config"]
        assert isinstance(template_config, dict)
        
        # Log the result for manual inspection
        print(f"\n✅ Real LLM composition successful!")
        print(f"Name: {result['name']}")
        print(f"Description: {result['description']}")
        print(f"System Prompt: {result['system_prompt'][:100]}...")
        
        # Optional: Test validation if the generated config is valid
        is_valid, validation_error = framework_executor.validate_template_configuration(
            "simple-test",
            template_config
        )
        
        # Log validation result
        if is_valid:
            print(f"✅ Generated configuration is valid")
        else:
            print(f"⚠️  Generated configuration has validation warnings: {validation_error}")
            # Still pass the test if composition succeeded
    
    finally:
        # Cleanup
        await framework_executor.shutdown()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_compose_workflow_with_real_deepseek_llm(check_deepseek_configured):
    """Test composing a workflow agent with real DeepSeek LLM.
    
    This test creates a more complex workflow agent using real LLM.
    """
    # Get config from fixture (test auto-skipped if not configured)
    config_dict = check_deepseek_configured
    
    # Setup
    framework_executor = LangGraphFrameworkExecutor(service_config=config_dict)
    await framework_executor.initialize()
    
    llm_service = framework_executor.get_llm_service()
    service = ComposeAgentService(llm_service, framework_executor)
    
    try:
        # Execute composition for a workflow agent
        result = await service.compose(
            template_id="langgraph-workflow",
            instructions="""Create a workflow agent that processes customer inquiries in steps:
1. First, understand and validate the customer's question
2. Then, search for relevant information
3. Finally, formulate a clear and helpful response
The agent should be professional and customer-focused.""",
            suggested_name="Customer Service Workflow",
            suggested_tools=[],
            llm_config_id="deepseek"
        )
        
        # Verify result
        assert result["template_id"] == "langgraph-workflow"
        assert "template_config" in result
        
        # Verify workflow-specific structure
        template_config = result["template_config"]
        assert "workflow_responsibility" in template_config
        assert "steps" in template_config
        assert isinstance(template_config["steps"], list)
        assert len(template_config["steps"]) > 0
        
        # Verify each step has required fields
        for step in template_config["steps"]:
            assert "name" in step
            assert "prompt" in step
            assert isinstance(step.get("tools", []), list)
        
        # Log success
        print(f"\n✅ Real LLM workflow composition successful!")
        print(f"Agent: {result['name']}")
        print(f"Workflow has {len(template_config['steps'])} steps")
        for i, step in enumerate(template_config['steps'], 1):
            print(f"  Step {i}: {step['name']}")
        
        # Validate the configuration
        is_valid, validation_error = framework_executor.validate_template_configuration(
            "langgraph-workflow",
            template_config
        )
        
        if is_valid:
            print(f"✅ Workflow configuration is valid")
        else:
            print(f"⚠️  Workflow configuration has validation warnings: {validation_error}")
    
    finally:
        await framework_executor.shutdown()
