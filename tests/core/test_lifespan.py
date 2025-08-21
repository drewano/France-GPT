import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from src.core.lifespan import lifespan


@pytest_asyncio.fixture
async def mock_app():
    """Fixture to create a mock FastAPI app for testing."""
    return FastAPI()


@pytest.mark.asyncio
async def test_lifespan_nominal_case(httpx_mock):
    """Test the nominal case where all services are healthy."""

    # Mock the health check responses
    httpx_mock.add_response(
        url="http://mcp_server:8001/health",
        method="GET",
        status_code=200,
        json={"status": "healthy"},
    )

    httpx_mock.add_response(
        url="http://mcp_server:8002/health",
        method="GET",
        status_code=200,
        json={"status": "healthy"},
    )

    # Patch the database initialization
    with (
        patch(
            "src.core.lifespan.initialize_database", new_callable=AsyncMock
        ) as mock_init_db,
        patch(
            "src.core.lifespan.settings.mcp_server.MCP_SERVICES_CONFIG",
            '[{"name": "datainclusion", "port": 8001}, {"name": "legifrance", "port": 8002}]',
        ),
    ):
        mock_init_db.return_value = None

        # Create a mock app
        app = FastAPI()

        # Test the lifespan context manager
        async with lifespan(app):
            # If we reach here without exception, the test passes
            pass

        # Verify that database initialization was called
        mock_init_db.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_failure_case(httpx_mock):
    """Test the failure case where a service is unhealthy."""

    # Mock the health check to return an error (twice for retry attempts)
    httpx_mock.add_response(
        url="http://mcp_server:8001/health",
        method="GET",
        status_code=500,
        json={"error": "Service unavailable"},
    )

    # Add the same response again for the retry attempt
    httpx_mock.add_response(
        url="http://mcp_server:8001/health",
        method="GET",
        status_code=500,
        json={"error": "Service unavailable"},
    )

    # Patch settings to reduce retries for faster testing
    with (
        patch("src.core.lifespan.settings.agent.AGENT_MCP_CONNECTION_MAX_RETRIES", 2),
        patch(
            "src.core.lifespan.settings.mcp_server.MCP_SERVICES_CONFIG",
            '[{"name": "datainclusion", "port": 8001}]',
        ),
        patch("src.core.lifespan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch(
            "src.core.lifespan.initialize_database", new_callable=AsyncMock
        ) as mock_init_db,
    ):
        mock_init_db.return_value = None
        mock_sleep.return_value = None

        # Create a mock app
        app = FastAPI()

        # Test that RuntimeError is raised
        with pytest.raises(
            RuntimeError,
            match="Échec de la connexion aux serveurs MCP après 2 tentatives",
        ):
            async with lifespan(app):
                pass  # This should not be reached

        # Verify that sleep was called for retries
        assert mock_sleep.await_count > 0
