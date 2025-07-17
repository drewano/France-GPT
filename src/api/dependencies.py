from fastapi import Depends, Request, HTTPException
from pydantic_ai import Agent
from typing import Annotated


def get_agent_from_app_state(request: Request) -> Agent:
    """
    Récupère l'agent depuis l'état de l'application FastAPI.

    Args:
        request: Requête FastAPI contenant l'état de l'application

    Returns:
        Agent: L'instance de l'agent

    Raises:
        HTTPException: Si l'agent n'est pas initialisé
    """
    if not hasattr(request.app.state, "agent"):
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return request.app.state.agent


# Type alias pour l'injection de dépendance
AgentDep = Annotated[Agent, Depends(get_agent_from_app_state)]
