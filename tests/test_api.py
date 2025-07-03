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
    assert "checks" in data
    assert "metrics" in data


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