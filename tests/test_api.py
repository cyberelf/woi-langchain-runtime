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
