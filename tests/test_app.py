import pytest
from httpx import AsyncClient
from src.app.factory import create_app

# Crée une instance de l'application pour les tests
app = create_app()

@pytest.mark.asyncio
async def test_health_check():
    """
    Teste si le endpoint /health retourne un statut 200 OK.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}