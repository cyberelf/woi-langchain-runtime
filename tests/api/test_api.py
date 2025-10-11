"""Tests for API endpoints.

In-memory queue and orchestrator requires the event loop to be consistent, so that workers are scheduled correctly.
The fastapi test client is a sync client and creates a new event loop for each request, which breaks this assumption.
So we use an async client for these tests.
Specifically, in-memory queue requires the same event loop for putting and getting messages from a specific queue, 
and the orchestrator initialization, which creates background async worker, is tied to the event loop it was created in.
"""

from unittest.mock import patch

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
import pytest_asyncio

from runtime.main import app
from runtime.infrastructure.web.dependencies import (
    shutdown_dependencies,
    get_message_queue,
    get_framework_executor,
    get_unit_of_work,
    get_agent_template_validator
)


@pytest_asyncio.fixture
async def async_client():
    """Async test client fixture with proper lifespan management."""
    # Clear caches before starting a new test
    get_message_queue.cache_clear()
    get_framework_executor.cache_clear()
    get_unit_of_work.cache_clear()
    get_agent_template_validator.cache_clear()
    
    # Use the app with ASGI transport - this properly triggers lifespan events
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    # Cleanup: Shutdown dependencies after each test to avoid event loop issues
    await shutdown_dependencies()
    
    # Clear caches after test
    get_message_queue.cache_clear()
    get_framework_executor.cache_clear()
    get_unit_of_work.cache_clear()
    get_agent_template_validator.cache_clear()

@pytest.fixture
def auth_headers():
    """Authentication headers fixture."""
    return {"X-Runtime-Token": "test-token"}


@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    """Test root endpoint."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Agent Runtime Service"
    assert "version" in data


@pytest.mark.asyncio
async def test_ping_endpoint(async_client):
    """Test ping endpoint."""
    response = await async_client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "pong"


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_get_schema(async_client, auth_headers):
    """Test templates endpoint (replaces schema endpoint)."""
    response = await async_client.get("/v1/templates/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_create_agent(async_client, auth_headers):
    """Test agent creation."""
    agent_data = {
        "id": "test-agent-1",
        "name": "Test Agent",
        "description": "A test agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "template_config": {
            "response_prefix": "Test: ",
            "system_prompt": "You are a helpful assistant."
        },
        "system_prompt": "You are a test agent.",
        "llm_config_id": "test-mock",
    }

    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["agent_id"] == "test-agent-1"


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_health_check(async_client, auth_headers):
    """Test health check endpoint."""
    response = await async_client.get("/v1/health", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "architecture" in data
    assert "features" in data


@pytest.mark.asyncio
async def test_unauthorized_access(async_client):
    """Test unauthorized access."""
    response = await async_client.get("/v1/templates/")
    assert response.status_code == 401


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_invalid_token(async_client):
    """Test invalid token."""
    headers = {"X-Runtime-Token": "invalid-token"}
    response = await async_client.get("/v1/templates/", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_execute_agent(async_client, auth_headers):
    """Test agent execution via OpenAI-compatible chat completions."""
    # First create an agent
    agent_data = {
        "id": "test-agent-execution",
        "name": "Test Execution Agent",
        "description": "A test agent for execution",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "template_config": {
            "response_prefix": "Test: ",
            "system_prompt": "You are a helpful test agent."
        },
        "system_prompt": "You are a helpful test agent.",
        "llm_config_id": "test-mock",
    }
    
    # Create the agent
    create_response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert create_response.status_code == 201
    
    # Execute the agent using OpenAI-compatible format
    execution_data = {
        "model": "test-agent-execution",
        "messages": [
            {
                "role": "user",
                "content": "Hello, can you help me?"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "stream": False,
        "metadata": {
            "task_id": "test-task-123",
            "context_id": "ctx-456",
            "user_id": "test-user-456"
        }
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    # Check OpenAI-compatible response format
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert "created" in data
    assert data["model"] == "test-agent-execution"
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "usage" in data
    
    # Check the response message
    choice = data["choices"][0]
    assert "index" in choice
    assert "message" in choice
    assert choice["message"]["role"] == "assistant"
    assert "content" in choice["message"]
    assert "finish_reason" in choice
    
    # Check usage statistics
    usage = data["usage"]
    assert "prompt_tokens" in usage
    assert "completion_tokens" in usage
    assert "total_tokens" in usage


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_execute_nonexistent_agent(async_client, auth_headers):
    """Test execution of non-existent agent."""
    execution_data = {
        "model": "non-existent-agent",
        "messages": [
            {
                "role": "user",
                "content": "Hello"
            }
        ]
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_execute_agent_streaming(async_client, auth_headers):
    """Test agent execution with streaming response."""
    # First create an agent
    agent_data = {
        "id": "test-agent-streaming",
        "name": "Test Streaming Agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "template_config": {
            "response_prefix": "Test: ",
            "system_prompt": "You are a helpful assistant."
        },
        "system_prompt": "You are a helpful assistant.",
        "llm_config_id": "test"
    }
    
    # Create the agent
    create_response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert create_response.status_code == 201
    
    # Execute with streaming
    execution_data = {
        "model": "test-agent-streaming", 
        "messages": [
            {
                "role": "user",
                "content": "Tell me a short story"
            }
        ],
        "stream": True
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 200
    # For streaming, we expect either SSE format or chunked response
    # The exact implementation will depend on the framework


# === EXPANDED API TESTS FOR VALIDATION ERRORS AND EDGE CASES ===

@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_create_agent_missing_required_fields(async_client, auth_headers):
    """Test agent creation with missing required fields."""
    # Missing name
    agent_data = {
        "id": "missing-name-agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "llm_config_id": "test"
    }

    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response.status_code == 422  # Unprocessable Entity
    data = response.json()
    assert "detail" in data

    # Missing template
    agent_data = {
        "id": "missing-template-agent",
        "name": "Missing Template Agent",
        "llm_config_id": "test"
    }

    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_create_agent_invalid_field_types(async_client, auth_headers):
    """Test agent creation with invalid field types."""
    # Invalid temperature type
    agent_data = {
        "id": "invalid-temp-agent",
        "name": "Invalid Temp Agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "llm_config_id": "test-mock",
        "template_config": {
            "response_prefix": ["not a string"],
        }
    }

    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    # Should either validate or handle gracefully
    assert response.status_code in [400, 422]

    # Invalid metadata type
    agent_data = {
        "id": "invalid-metadata-agent",
        "name": "Invalid Metadata Agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "llm_config_id": "test-mock",
        "metadata": "should-be-object"  # Should be object
    }

    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_create_agent_duplicate_id(async_client, auth_headers):
    """Test creating agent with duplicate ID."""
    agent_data = {
        "id": "duplicate-agent",
        "name": "First Agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "llm_config_id": "test"
    }

    # Create first agent
    response1 = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response1.status_code == 201

    # Try to create second agent with same ID
    agent_data["name"] = "Second Agent"  # Different name, same ID
    response2 = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response2.status_code in [400, 409]  # Bad Request or Conflict


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_create_agent_with_invalid_template(async_client, auth_headers):
    """Test creating agent with non-existent template."""
    agent_data = {
        "id": "invalid-template-agent",
        "name": "Invalid Template Agent",
        "template_id": "non-existent-template",
        "llm_config_id": "test"
    }

    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response.status_code == 400  # Should validate template exists


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_chat_completions_missing_required_fields(async_client, auth_headers):
    """Test chat completions with missing required fields."""
    # Missing model
    execution_data = {
        "messages": [
            {
                "role": "user",
                "content": "Hello"
            }
        ]
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 422
    
    # Missing messages
    execution_data = {
        "model": "test-agent"
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_chat_completions_invalid_parameters(async_client, auth_headers):
    """Test chat completions with invalid parameters."""
    # Invalid temperature range
    execution_data = {
        "model": "test-agent",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 3.0  # Should be between 0-2
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]
    
    # Invalid max_tokens
    execution_data = {
        "model": "test-agent",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": -100  # Should be positive
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_chat_completions_invalid_message_format(async_client, auth_headers):
    """Test chat completions with invalid message format."""
    # Missing role
    execution_data = {
        "model": "test-agent",
        "messages": [
            {
                "content": "Hello"
                # Missing role
            }
        ]
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 422
    
    # Invalid role
    execution_data = {
        "model": "test-agent",
        "messages": [
            {
                "role": "invalid_role",
                "content": "Hello"
            }
        ]
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]
    
    # Missing content
    execution_data = {
        "model": "test-agent",
        "messages": [
            {
                "role": "user"
                # Missing content
            }
        ]
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_chat_completions_empty_messages(async_client, auth_headers):
    """Test chat completions with empty messages array."""
    execution_data = {
        "model": "test-agent",
        "messages": []
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_missing_authentication_various_endpoints(async_client):
    """Test missing authentication on various endpoints."""
    endpoints = [
        ("GET", "/v1/templates/"),
        ("GET", "/v1/health"),
        ("POST", "/v1/agents/"),
        ("POST", "/v1/chat/completions")
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            response = await async_client.get(endpoint)
        elif method == "POST":
            response = await async_client.post(endpoint, json={})
        
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_json_requests(async_client, auth_headers):
    """Test malformed JSON in request bodies."""
    # Test with invalid JSON
    response = await async_client.post(
        "/v1/agents/",
        data="invalid json",
        headers={**auth_headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_content_type_validation(async_client, auth_headers):
    """Test content type validation for POST requests."""
    agent_data = {
        "id": "content-type-test",
        "name": "Content Type Test",
        "template_id": "simple-test",
        "template_version_id": "1.0.0"
    }
    
    # Test with wrong content type
    response = await async_client.post(
        "/v1/agents/",
        content=str(agent_data),
        headers={**auth_headers, "Content-Type": "text/plain"}
    )
    assert response.status_code in [400, 415, 422]


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_large_request_payload(async_client, auth_headers):
    """Test handling of large request payloads."""
    # Create very large system prompt
    large_prompt = "x" * 100000  # 100KB prompt
    
    agent_data = {
        "id": "large-payload-agent",
        "name": "Large Payload Agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "system_prompt": large_prompt
    }
    
    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    # Should either accept or reject gracefully
    assert response.status_code == 400 # Agent configuration is too large


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_unicode_and_special_characters(async_client, auth_headers):
    """Test handling of unicode and special characters."""
    agent_data = {
        "id": "unicode-test-agent",
        "name": "Unicode Test: 🤖 中文 العربية русский",
        "description": "Testing special chars: <>&\"'\n\t",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "system_prompt": "You are 🤖 multilingual: Hola, مرحبا, 你好, Привет"
    }
    
    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_boundary_values_temperature(async_client, auth_headers):
    """Test boundary values for temperature parameter."""
    # First create an agent
    agent_data = {
        "id": "boundary-test-agent",
        "name": "Boundary Test Agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "llm_config_id": "test-mock"
    }
    response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
    assert response.status_code == 201
    
    # Test minimum boundary (0.0)
    execution_data = {
        "model": "boundary-test-agent",
        "messages": [{"role": "user", "content": "Test"}],
        "temperature": 0.0
    }
    
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 200
    
    # Test maximum boundary (2.0)
    execution_data["temperature"] = 2.0
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 200
    
    # Test just outside boundaries
    execution_data["temperature"] = -0.1
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]
    
    execution_data["temperature"] = 2.1
    response = await async_client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_various_http_methods_unsupported_endpoints(async_client, auth_headers):
    """Test unsupported HTTP methods on endpoints."""
    # Test unsupported methods
    unsupported_tests = [
        ("DELETE", "/v1/templates/"),
        ("PUT", "/v1/templates/"),
        ("PATCH", "/v1/templates/"),
        ("DELETE", "/v1/agents/"),
        ("PUT", "/v1/chat/completions"),
        ("PATCH", "/v1/chat/completions")
    ]
    
    for method, endpoint in unsupported_tests:
        response = await async_client.request(method, endpoint, headers=auth_headers)
        assert response.status_code == 405  # Method Not Allowed


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_concurrent_agent_creation(async_client, auth_headers):
    """Test concurrent agent creation requests."""    
    async def create_agent(agent_id):
        agent_data = {
            "id": f"concurrent-{agent_id}",
            "name": f"Concurrent Agent {agent_id}",
            "template_id": "simple-test",
            "template_version_id": "1.0.0"
        }
        response = await async_client.post("/v1/agents/", json=agent_data, headers=auth_headers)
        return (agent_id, response.status_code)
    
    # Create multiple concurrent tasks
    tasks = [create_agent(i) for i in range(5)]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    # Verify results
    assert len(results) == 5
    success_count = sum(1 for _, status in results if status == 201)
    assert success_count == 5  # All should succeed with different IDs


@pytest.mark.asyncio
@patch("runtime.settings.settings.runtime_token", "test-token")
async def test_error_response_format_consistency(async_client, auth_headers):
    """Test that error responses have consistent format."""
    # Test various error scenarios and ensure consistent response format
    error_scenarios = [
        # Invalid JSON
        {
            "method": "post",
            "endpoint": "/v1/agents/",
            "data": "invalid json",
            "content_type": "application/json"
        },
        # Missing required field
        {
            "method": "post",
            "endpoint": "/v1/agents/", 
            "json": {"id": "test"}  # Missing required fields
        },
        # Non-existent agent execution
        {
            "method": "post",
            "endpoint": "/v1/chat/completions",
            "json": {
                "model": "non-existent",
                "messages": [{"role": "user", "content": "test"}]
            }
        }
    ]
    
    for scenario in error_scenarios:
        if scenario["method"] == "post":
            if "json" in scenario:
                response = await async_client.post(
                    scenario["endpoint"],
                    json=scenario["json"],
                    headers=auth_headers
                )
            else:
                headers = dict(auth_headers)
                if "content_type" in scenario:
                    headers["Content-Type"] = scenario["content_type"]
                response = await async_client.post(
                    scenario["endpoint"],
                    data=scenario["data"],
                    headers=headers
                )
        
        # All error responses should have consistent structure
        assert response.status_code >= 400
        data = response.json()
        # Should have either 'detail' (FastAPI standard) or 'error' field
        assert "detail" in data or "error" in data or "message" in data
