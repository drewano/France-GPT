"""
Router API pour l'agent IA d'inclusion sociale.

Ce module contient les routes et endpoints de l'API REST pour l'agent IA.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage
from .dependencies import AgentDep

# Plus de variables globales ! 🎉
api_router = APIRouter()

# Variable pour stocker l'instance de l'application (closure pattern pour Gradio)
_app_instance = None


def set_app_instance(app):
    """Configure l'instance de l'application pour l'accès Gradio."""
    global _app_instance
    _app_instance = app


def get_agent():
    """Récupère l'agent depuis l'état de l'application (pour Gradio)."""
    if _app_instance is None:
        return None
    return getattr(_app_instance.state, "agent", None)


class ChatRequest(BaseModel):
    prompt: str
    history: list[ModelMessage] | None = None


@api_router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    agent: AgentDep,  # Injection de dépendance native !
) -> StreamingResponse:
    """
    Endpoint pour le chat en streaming.

    Args:
        request: Requête de chat
        agent: Agent injecté automatiquement par FastAPI
    """

    async def generate():
        # Utiliser l'agent avec async with puis stream_text()
        async with agent.run_stream(request.prompt) as result:
            async for chunk in result.stream_text():
                yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/plain")


@api_router.get("/health")
async def api_health_check():
    """
    Endpoint de vérification de santé de l'API agent.

    Returns:
        Statut OK avec code HTTP 200
    """
    return {"status": "OK"}
