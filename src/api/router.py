"""
Router API pour l'agent IA d'inclusion sociale.

Ce module contient les routes et endpoints de l'API REST pour l'agent IA.
"""

from typing import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage

# Variable globale pour stocker l'instance de l'application FastAPI
_app_instance = None


def set_app_instance(app_instance):
    """
    Définit l'instance de l'application FastAPI.

    Args:
        app_instance: Instance de l'application FastAPI
    """
    global _app_instance
    _app_instance = app_instance


def get_agent():
    """
    Récupère l'agent depuis l'état de l'application FastAPI.

    Returns:
        Agent: L'instance de l'agent ou None si pas encore initialisé
    """
    if _app_instance is None:
        return None
    return getattr(_app_instance.state, "agent", None)


class ChatRequest(BaseModel):
    """
    Modèle Pydantic pour les requêtes de chat.

    Attributes:
        prompt: Le message de l'utilisateur
        history: Historique des messages précédents (optionnel)
    """

    prompt: str
    history: list[ModelMessage] | None = None


async def stream_agent_response(
    agent, prompt: str, history: list[ModelMessage] | None = None
) -> AsyncGenerator[str, None]:
    """
    Fonction de streaming pour l'API FastAPI.

    Args:
        agent: Instance de l'agent PydanticAI
        prompt: Le message de l'utilisateur
        history: Historique des messages précédents (optionnel)

    Yields:
        Chunks de texte de la réponse de l'agent
    """
    try:
        async with agent.run_stream(prompt, message_history=history) as result:
            async for text_chunk in result.stream_text():
                yield text_chunk
    except Exception as e:
        yield f"Erreur lors du traitement: {str(e)}"


# Créer l'APIRouter pour l'API agent
api_router = APIRouter()


@api_router.post("/chat/stream")
async def chat_stream_api(chat_request: ChatRequest, request: Request):
    """
    Endpoint de chat avec streaming des réponses.

    Args:
        chat_request: Requête contenant le prompt et l'historique
        request: Objet Request de FastAPI pour accéder à l'état de l'application

    Returns:
        StreamingResponse avec les chunks de texte de la réponse
    """
    # Récupération de l'agent depuis l'état de l'application
    agent = request.app.state.agent

    # Retour de la réponse en streaming
    return StreamingResponse(
        stream_agent_response(agent, chat_request.prompt, chat_request.history),
        media_type="text/event-stream",
    )


@api_router.get("/health")
async def api_health_check():
    """
    Endpoint de vérification de santé de l'API agent.

    Returns:
        Statut OK avec code HTTP 200
    """
    return {"status": "OK"}
