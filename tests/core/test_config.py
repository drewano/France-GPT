"""Tests for the configuration module."""

import json
import os
from unittest.mock import patch

from pytest_mock import MockerFixture

from src.core.config import AppSettings, MCPServiceConfig


class TestAppSettings:
    """Test the AppSettings class."""

    def test_mcp_services_with_valid_json(self, mocker: MockerFixture) -> None:
        """Test parsing of MCP_SERVICES_CONFIG with valid JSON."""
        # Arrange
        valid_config = [
            {
                "name": "datainclusion",
                "auth": {
                    "method": "bearer",
                    "api_key_env_var": "DATAINCLUSION_API_KEY",
                },
                "port": 8001,
            },
            {"name": "legifrance", "port": 8002},
        ]

        # Act
        # Use unittest.mock.patch.dict to patch environment variables
        with patch.dict(os.environ, {"MCP_SERVICES_CONFIG": json.dumps(valid_config)}):
            settings = AppSettings()

        # Assert
        services = settings.mcp_services
        assert len(services) == 2
        assert isinstance(services[0], MCPServiceConfig)
        assert services[0].name == "datainclusion"
        assert services[0].port == 8001
        assert services[1].name == "legifrance"
        assert services[1].port == 8002

    def test_mcp_services_with_malformed_json(self, mocker: MockerFixture) -> None:
        """Test parsing of MCP_SERVICES_CONFIG with malformed JSON."""
        # Act
        # Use unittest.mock.patch.dict to patch environment variables
        with patch.dict(os.environ, {"MCP_SERVICES_CONFIG": '{"invalid": json}'}):
            settings = AppSettings()

        # Assert
        services = settings.mcp_services
        assert services == []  # Should return empty list on error

    def test_mcp_services_with_empty_string(self, mocker: MockerFixture) -> None:
        """Test parsing of MCP_SERVICES_CONFIG with empty string."""
        # Act
        # Use unittest.mock.patch.dict to patch environment variables
        with patch.dict(os.environ, {"MCP_SERVICES_CONFIG": ""}):
            settings = AppSettings()

        # Assert
        services = settings.mcp_services
        assert services == []  # Should return empty list when empty

    def test_default_values_when_env_vars_not_set(self, mocker: MockerFixture) -> None:
        """Test that default values are applied when env vars are not set."""
        # Act
        # Use unittest.mock.patch.dict to clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            settings = AppSettings()

        # Assert
        # Check agent defaults
        assert settings.agent.OPENAI_API_KEY == ""
        assert settings.agent.AGENT_MODEL_NAME == "gpt-4.1"
        assert settings.agent.MCP_SERVER_HOST_URL == "http://mcp_server"
        assert settings.agent.AGENT_PORT == 8001
        assert settings.agent.AGENT_MCP_CONNECTION_MAX_RETRIES == 10

        # Check MCP server defaults
        assert settings.mcp_server.MCP_HOST == "0.0.0.0"
        assert settings.mcp_server.MCP_PORT == 8000
        assert settings.mcp_server.MCP_API_PATH == "/mcp/"
        assert settings.mcp_server.MCP_SERVICES_CONFIG == "[]"

        # Check mcp_services property returns empty list for default "[]"
        assert settings.mcp_services == []
