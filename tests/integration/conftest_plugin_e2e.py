"""Pytest configuration for E2E plugin tests."""

import asyncio
import pytest

from runtime.core.plugin.init import initialize_plugin_system


@pytest.fixture(scope="session", autouse=True)
def event_loop_policy():
    """Set event loop policy for session."""
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


@pytest.fixture(scope="session", autouse=True)
def setup_plugins():
    """Initialize plugin system before running tests."""
    asyncio.run(initialize_plugin_system())
    yield
