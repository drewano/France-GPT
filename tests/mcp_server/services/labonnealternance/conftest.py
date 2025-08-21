import pytest
from unittest.mock import patch
import os
import sys

# Ajout du chemin src pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))


@pytest.fixture(autouse=True)
def mock_lba_client():
    """Mock du client LBA pour éviter les erreurs d'environnement."""
    with patch(
        "src.mcp_server.services.labonnealternance.service._get_lba_client"
    ) as mock:
        mock.return_value = None
        yield mock
