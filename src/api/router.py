"""
Router API pour l'agent IA d'inclusion sociale.

Ce module contient les routes et endpoints de l'API REST pour l'agent IA.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage
from .dependencies import AgentDep

# API router pour les endpoints de l'agent
api_router = APIRouter()


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
