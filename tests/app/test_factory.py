import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from src.app.factory import create_app


@pytest_asyncio.fixture
async def test_client():
    """
    Fixture pour créer un client de test HTTP asynchrone.
    """
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    """
    Teste si le endpoint /health retourne un statut 200 OK.
    La fonction de test reçoit maintenant le 'client' directement depuis la fixture.
    """
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
