import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from src.app.factory import create_app
from fastapi import FastAPI


@pytest_asyncio.fixture(scope="session")
async def fastapi_app() -> FastAPI:
    """
    Fixture pour créer l'instance de l'application FastAPI une seule fois par session de test.
    """
    return create_app()


@pytest_asyncio.fixture(scope="function")
async def test_client(fastapi_app: FastAPI) -> AsyncClient:
    """
    Fixture qui dépend de l'application et fournit un client de test.
    Le client est recréé pour chaque fonction de test pour garantir l'isolation.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    """
    Teste si le endpoint /health retourne un statut 200 OK.
    La fonction de test reçoit maintenant le 'client' directement depuis la fixture.
    """
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
