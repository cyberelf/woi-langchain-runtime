"""Tests for API endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from runtime.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers fixture."""
    return {"X-Runtime-Token": "test-token"}


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Agent Runtime Service"
    assert "version" in data


def test_ping_endpoint(client):
    """Test ping endpoint."""
    response = client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "pong"


@patch("runtime.config.settings.runtime_token", "test-token")
def test_get_schema(client, auth_headers):
    """Test schema endpoint."""
    response = client.get("/v1/schema", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "supportedAgentTemplates" in data
    assert "capabilities" in data
    assert "limits" in data


@patch("runtime.config.settings.runtime_token", "test-token")
def test_create_agent(client, auth_headers):
    """Test agent creation."""
    agent_data = {
        "id": "test-agent-1",
        "name": "Test Agent",
        "description": "A test agent",
        "type": "conversation",
        "template_id": "customer-service-bot",
        "template_version_id": "1.0.0",
        "template_config": {
            "conversation": {
                "continuous": True,
                "historyLength": 10,
            },
        },
        "system_prompt": "You are a test agent.",
        "llm_config_id": "test-llm-config",
    }

    response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["agent_id"] == "test-agent-1"


@patch("runtime.config.settings.runtime_token", "test-token")
def test_health_check(client, auth_headers):
    """Test health check endpoint."""
    response = client.get("/v1/health", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "architecture" in data
    assert "features" in data


def test_unauthorized_access(client):
    """Test unauthorized access."""
    response = client.get("/v1/schema")
    assert response.status_code == 401


@patch("runtime.config.settings.runtime_token", "test-token")
def test_invalid_token(client):
    """Test invalid token."""
    headers = {"X-Runtime-Token": "invalid-token"}
    response = client.get("/v1/schema", headers=headers)
    assert response.status_code == 401


@patch("runtime.config.settings.runtime_token", "test-token")
def test_execute_agent(client, auth_headers):
    """Test agent execution via OpenAI-compatible chat completions."""
    # First create an agent
    agent_data = {
        "id": "test-agent-execution",
        "name": "Test Execution Agent",
        "description": "A test agent for execution",
        "type": "conversation",
        "template_id": "simple-test",
        "template_version_id": "1.0.0",
        "template_config": {
            "conversation": {
                "continuous": True,
                "historyLength": 10,
            },
        },
        "system_prompt": "You are a helpful test agent.",
        "llm_config_id": "test-llm-config",
    }
    
    # Create the agent
    create_response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
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
            "session_id": "test-session-123",
            "user_id": "test-user-456"
        }
    }
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
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


@patch("runtime.config.settings.runtime_token", "test-token")
def test_execute_nonexistent_agent(client, auth_headers):
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
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 404


@patch("runtime.config.settings.runtime_token", "test-token") 
def test_execute_agent_streaming(client, auth_headers):
    """Test agent execution with streaming response."""
    # First create an agent
    agent_data = {
        "id": "test-agent-streaming",
        "name": "Test Streaming Agent",
        "template_id": "simple-test",
        "template_config": {
            "response_prefix": "Test: ",
            "system_prompt": "You are a helpful assistant."
        },
        "system_prompt": "You are a helpful assistant."
    }
    
    # Create the agent
    create_response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
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
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 200
    # For streaming, we expect either SSE format or chunked response
    # The exact implementation will depend on the framework


# === EXPANDED API TESTS FOR VALIDATION ERRORS AND EDGE CASES ===

@patch("runtime.config.settings.runtime_token", "test-token")
def test_create_agent_missing_required_fields(client, auth_headers):
    """Test agent creation with missing required fields."""
    # Missing name
    agent_data = {
        "id": "missing-name-agent",
        "template_id": "test-template",
        "template_version_id": "1.0.0"
    }
    
    response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    assert response.status_code == 422  # Unprocessable Entity
    data = response.json()
    assert "detail" in data
    
    # Missing template_id
    agent_data = {
        "id": "missing-template-agent",
        "name": "Missing Template Agent",
        "template_version_id": "1.0.0"
    }
    
    response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    assert response.status_code == 422


@patch("runtime.config.settings.runtime_token", "test-token")
def test_create_agent_invalid_field_types(client, auth_headers):
    """Test agent creation with invalid field types."""
    # Invalid temperature type
    agent_data = {
        "id": "invalid-temp-agent",
        "name": "Invalid Temp Agent",
        "template_id": "test-template",
        "template_version_id": "1.0.0",
        "template_config": {
            "conversation": {
                "temperature": "invalid"  # Should be float
            }
        }
    }
    
    response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    # Should either validate or handle gracefully
    assert response.status_code in [400, 422]
    
    # Invalid metadata type
    agent_data = {
        "id": "invalid-metadata-agent",
        "name": "Invalid Metadata Agent",
        "template_id": "test-template",
        "template_version_id": "1.0.0",
        "metadata": "should-be-object"  # Should be object
    }
    
    response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    assert response.status_code in [400, 422]


@patch("runtime.config.settings.runtime_token", "test-token")
def test_create_agent_duplicate_id(client, auth_headers):
    """Test creating agent with duplicate ID."""
    agent_data = {
        "id": "duplicate-agent",
        "name": "First Agent",
        "template_id": "test-template",
        "template_version_id": "1.0.0"
    }
    
    # Create first agent
    response1 = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    assert response1.status_code == 201
    
    # Try to create second agent with same ID
    agent_data["name"] = "Second Agent"  # Different name, same ID
    response2 = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    assert response2.status_code in [400, 409]  # Bad Request or Conflict


@patch("runtime.config.settings.runtime_token", "test-token")
def test_create_agent_with_invalid_template(client, auth_headers):
    """Test creating agent with non-existent template."""
    agent_data = {
        "id": "invalid-template-agent",
        "name": "Invalid Template Agent",
        "template_id": "non-existent-template",
        "template_version_id": "1.0.0"
    }
    
    response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    assert response.status_code == 400  # Should validate template exists


@patch("runtime.config.settings.runtime_token", "test-token")
def test_chat_completions_missing_required_fields(client, auth_headers):
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
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 422
    
    # Missing messages
    execution_data = {
        "model": "test-agent"
    }
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 422


@patch("runtime.config.settings.runtime_token", "test-token")
def test_chat_completions_invalid_parameters(client, auth_headers):
    """Test chat completions with invalid parameters."""
    # Invalid temperature range
    execution_data = {
        "model": "test-agent",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 3.0  # Should be between 0-2
    }
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]
    
    # Invalid max_tokens
    execution_data = {
        "model": "test-agent",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": -100  # Should be positive
    }
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]


@patch("runtime.config.settings.runtime_token", "test-token")
def test_chat_completions_invalid_message_format(client, auth_headers):
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
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
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
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
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
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 422


@patch("runtime.config.settings.runtime_token", "test-token")
def test_chat_completions_empty_messages(client, auth_headers):
    """Test chat completions with empty messages array."""
    execution_data = {
        "model": "test-agent",
        "messages": []
    }
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]


def test_missing_authentication_various_endpoints(client):
    """Test missing authentication on various endpoints."""
    endpoints = [
        ("GET", "/v1/schema"),
        ("GET", "/v1/health"),
        ("POST", "/v1/agents"),
        ("POST", "/v1/chat/completions")
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        
        assert response.status_code == 401


def test_malformed_json_requests(client, auth_headers):
    """Test malformed JSON in request bodies."""
    # Test with invalid JSON
    response = client.post(
        "/v1/agents",
        data="invalid json",
        headers={**auth_headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 422


@patch("runtime.config.settings.runtime_token", "test-token")
def test_content_type_validation(client, auth_headers):
    """Test content type validation for POST requests."""
    agent_data = {
        "id": "content-type-test",
        "name": "Content Type Test",
        "template_id": "test-template",
        "template_version_id": "1.0.0"
    }
    
    # Test with wrong content type
    response = client.post(
        "/v1/agents",
        data=str(agent_data),
        headers={**auth_headers, "Content-Type": "text/plain"}
    )
    assert response.status_code in [400, 415, 422]


@patch("runtime.config.settings.runtime_token", "test-token")
def test_large_request_payload(client, auth_headers):
    """Test handling of large request payloads."""
    # Create very large system prompt
    large_prompt = "x" * 100000  # 100KB prompt
    
    agent_data = {
        "id": "large-payload-agent",
        "name": "Large Payload Agent",
        "template_id": "test-template",
        "template_version_id": "1.0.0",
        "system_prompt": large_prompt
    }
    
    response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    # Should either accept or reject gracefully
    assert response.status_code in [201, 413, 422]  # Created, Payload Too Large, or Validation Error


@patch("runtime.config.settings.runtime_token", "test-token")
def test_unicode_and_special_characters(client, auth_headers):
    """Test handling of unicode and special characters."""
    agent_data = {
        "id": "unicode-test-agent",
        "name": "Unicode Test: 🤖 中文 العربية русский",
        "description": "Testing special chars: <>&\"'\n\t",
        "template_id": "test-template",
        "template_version_id": "1.0.0",
        "system_prompt": "You are 🤖 multilingual: Hola, مرحبا, 你好, Привет"
    }
    
    response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True


@patch("runtime.config.settings.runtime_token", "test-token")
def test_boundary_values_temperature(client, auth_headers):
    """Test boundary values for temperature parameter."""
    # First create an agent
    agent_data = {
        "id": "boundary-test-agent",
        "name": "Boundary Test Agent",
        "template_id": "simple-test",
        "template_version_id": "1.0.0"
    }
    client.post("/v1/agents", json=agent_data, headers=auth_headers)
    
    # Test minimum boundary (0.0)
    execution_data = {
        "model": "boundary-test-agent",
        "messages": [{"role": "user", "content": "Test"}],
        "temperature": 0.0
    }
    
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 200
    
    # Test maximum boundary (2.0)
    execution_data["temperature"] = 2.0
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code == 200
    
    # Test just outside boundaries
    execution_data["temperature"] = -0.1
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]
    
    execution_data["temperature"] = 2.1
    response = client.post("/v1/chat/completions", json=execution_data, headers=auth_headers)
    assert response.status_code in [400, 422]


@patch("runtime.config.settings.runtime_token", "test-token")
def test_various_http_methods_unsupported_endpoints(client, auth_headers):
    """Test unsupported HTTP methods on endpoints."""
    # Test unsupported methods
    unsupported_tests = [
        ("DELETE", "/v1/schema"),
        ("PUT", "/v1/schema"),
        ("PATCH", "/v1/schema"),
        ("DELETE", "/v1/agents"),
        ("PUT", "/v1/chat/completions"),
        ("PATCH", "/v1/chat/completions")
    ]
    
    for method, endpoint in unsupported_tests:
        response = client.request(method, endpoint, headers=auth_headers)
        assert response.status_code == 405  # Method Not Allowed


@patch("runtime.config.settings.runtime_token", "test-token")
def test_concurrent_agent_creation(client, auth_headers):
    """Test concurrent agent creation requests."""
    import threading
    import time
    
    results = []
    
    def create_agent(agent_id):
        agent_data = {
            "id": f"concurrent-{agent_id}",
            "name": f"Concurrent Agent {agent_id}",
            "template_id": "test-template",
            "template_version_id": "1.0.0"
        }
        response = client.post("/v1/agents", json=agent_data, headers=auth_headers)
        results.append((agent_id, response.status_code))
    
    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=create_agent, args=(i,))
        threads.append(thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    # Verify results
    assert len(results) == 5
    success_count = sum(1 for _, status in results if status == 201)
    assert success_count == 5  # All should succeed with different IDs


@patch("runtime.config.settings.runtime_token", "test-token")
def test_error_response_format_consistency(client, auth_headers):
    """Test that error responses have consistent format."""
    # Test various error scenarios and ensure consistent response format
    error_scenarios = [
        # Invalid JSON
        {
            "method": "post",
            "endpoint": "/v1/agents",
            "data": "invalid json",
            "content_type": "application/json"
        },
        # Missing required field
        {
            "method": "post",
            "endpoint": "/v1/agents", 
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
                response = client.post(
                    scenario["endpoint"],
                    json=scenario["json"],
                    headers=auth_headers
                )
            else:
                headers = dict(auth_headers)
                if "content_type" in scenario:
                    headers["Content-Type"] = scenario["content_type"]
                response = client.post(
                    scenario["endpoint"],
                    data=scenario["data"],
                    headers=headers
                )
        
        # All error responses should have consistent structure
        assert response.status_code >= 400
        data = response.json()
        # Should have either 'detail' (FastAPI standard) or 'error' field
        assert "detail" in data or "error" in data or "message" in data
