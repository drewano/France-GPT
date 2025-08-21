import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_legifrance_client():
    """Mock du client Legifrance pour éviter les erreurs d'environnement."""
    with patch(
        "src.mcp_server.services.legifrance.service._get_legifrance_client"
    ) as mock_client:
        mock_client.return_value = MagicMock()
        yield mock_client
