"""
Serveur FastAPI pour exposer l'agent Pydantic AI avec streaming.

Ce serveur fournit une API REST pour interagir avec l'agent IA spécialisé
dans l'inclusion sociale, avec support du streaming de réponses.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage
from pydantic_ai.mcp import MCPServerStreamableHTTP

from .config import Settings
from .agent import create_inclusion_agent


class ChatRequest(BaseModel):
    """
    Modèle Pydantic pour les requêtes de chat.
    
    Attributes:
        prompt: Le message de l'utilisateur
        history: Historique des messages précédents (optionnel)
    """
    prompt: str
    history: list[ModelMessage] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application FastAPI.
    
    Gère la connexion au serveur MCP et l'initialisation de l'agent
    avec logique de retry et backoff exponentiel.
    
    Args:
        app: Instance de l'application FastAPI
    """
    # Chargement de la configuration
    settings = Settings()
    
    # Initialisation du serveur MCP
    mcp_server = MCPServerStreamableHTTP(settings.MCP_SERVER_URL)
    
    # Création de l'agent avec le serveur MCP
    agent = create_inclusion_agent(mcp_server)
    
    # Logique de connexion au MCP avec retry et backoff exponentiel
    max_retries = settings.AGENT_MCP_CONNECTION_MAX_RETRIES
    base_delay = settings.AGENT_MCP_CONNECTION_BASE_DELAY
    backoff_multiplier = settings.AGENT_MCP_CONNECTION_BACKOFF_MULTIPLIER
    
    for attempt in range(max_retries):
        try:
            async with agent.run_mcp_servers():
                # Stocker l'instance de l'agent dans l'état de l'application
                app.state.agent = agent
                
                # Yield pour indiquer que l'application est prête
                yield
                
                # Code après yield s'exécute lors du shutdown
                break
                
        except Exception as e:
            if attempt == max_retries - 1:
                # Dernière tentative échouée
                raise RuntimeError(f"Échec de la connexion au serveur MCP après {max_retries} tentatives: {e}")
            
            # Calcul du délai avec backoff exponentiel
            delay = base_delay * (backoff_multiplier ** attempt)
            
            print(f"Tentative {attempt + 1}/{max_retries} échouée. Nouvelle tentative dans {delay:.2f}s...")
            await asyncio.sleep(delay)


# Création de l'application FastAPI avec lifespan
app = FastAPI(
    title="Agent IA d'Inclusion Sociale",
    description="API pour interagir avec l'agent IA spécialisé dans l'inclusion sociale en France",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/chat/stream")
async def chat_stream(chat_request: ChatRequest, request: Request):
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
    
    async def generate_response() -> AsyncGenerator[str, None]:
        """
        Générateur asynchrone pour le streaming de la réponse.
        
        Yields:
            Chunks de texte de la réponse de l'agent
        """
        try:
            # Lancement du streaming avec l'agent
            async with agent.run_stream(
                prompt=chat_request.prompt,
                message_history=chat_request.history
            ) as result:
                # Iteration sur les chunks de texte
                async for text_chunk in result.stream_text():
                    yield text_chunk
                    
        except Exception as e:
            # En cas d'erreur, envoyer un message d'erreur
            yield f"Erreur lors du traitement: {str(e)}"
    
    # Retour de la réponse en streaming
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )


@app.get("/health")
async def health_check():
    """
    Endpoint de vérification de santé du serveur.
    
    Returns:
        Statut OK avec code HTTP 200
    """
    return {"status": "OK"} 