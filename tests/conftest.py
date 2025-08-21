# tests/conftest.py

"""
Configuration file for pytest.
"""

import sys
from pathlib import Path
import pytest

# Add the src directory to the path so we can import modules from it
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """
    Fixture pour simuler les variables d'environnement nécessaires pour les tests.
    Grâce à `autouse=True`, cette fixture sera automatiquement appliquée à chaque test,
    évitant ainsi d'avoir à la spécifier manuellement partout.
    """
    # Utilise monkeypatch, l'outil intégré de pytest pour modifier des variables, dictionnaires ou modules.
    monkeypatch.setenv("DATAINCLUSION_API_KEY", "dummy-api-key-for-testing")
    monkeypatch.setenv("LABONNEALTERNANCE_API_KEY", "dummy-api-key-for-testing")
    monkeypatch.setenv("LEGIFRANCE_CLIENT_ID", "dummy-client-id-for-testing")
    monkeypatch.setenv("LEGIFRANCE_CLIENT_SECRET", "dummy-client-secret-for-testing")
    monkeypatch.setenv("CHAINLIT_AUTH_SECRET", "a-dummy-secret-for-testing-purposes")
    monkeypatch.setenv(
        "OPENAI_API_KEY", "dummy-openai-key-for-testing"
    )  # C'est aussi une bonne pratique
