#!/usr/bin/env python3
"""
Application Gradio intégrée avec FastAPI pour l'agent IA d'Inclusion Sociale.

Cette application combine :
- Le serveur FastAPI existant de l'agent IA (routes /api/*)
- L'interface Gradio moderne (routes /chat/*)
- Health checks pour les deux services

Architecture :
- /api/* : API REST de l'agent IA (chat/stream, health)
- /chat/* : Interface Gradio interactive
- / : Redirection vers l'interface Gradio
- /health : Health check global
- /docs : Documentation API FastAPI
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, AsyncGenerator, Optional

import gradio as gr
import uvicorn
from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
    ModelRequest,
    UserPromptPart,
    SystemPromptPart,
    TextPart,
    ModelResponse,
    ModelMessage
)

# Imports locaux
from .agent.config import Settings
from .agent.agent import create_inclusion_agent
from .gradio_utils import (
    create_tool_call_message,
    create_tool_result_message,
    create_error_message,
    log_gradio_message
)

# Configuration du logging unifié
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# L'agent sera stocké dans l'état de l'application FastAPI (app.state.agent)

# Variable globale pour stocker l'instance de l'application FastAPI
_app_instance = None

def get_agent():
    """
    Récupère l'agent depuis l'état de l'application FastAPI.
    
    Returns:
        Agent: L'instance de l'agent ou None si pas encore initialisé
    """
    if _app_instance is None:
        return None
    return getattr(_app_instance.state, 'agent', None)


class ChatRequest(BaseModel):
    """
    Modèle Pydantic pour les requêtes de chat.
    
    Attributes:
        prompt: Le message de l'utilisateur
        history: Historique des messages précédents (optionnel)
    """
    prompt: str
    history: list[ModelMessage] | None = None


async def stream_agent_response(agent, prompt: str, history: list[ModelMessage] | None = None) -> AsyncGenerator[str, None]:
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


def create_complete_interface():
    """
    Crée l'interface Gradio complète avec streaming et affichage des appels aux outils MCP.
    """
    
    async def chat_stream(message: str, history: List[Dict[str, str]], request: gr.Request) -> AsyncGenerator[List[gr.ChatMessage], None]:
        """
        Fonction de streaming pour l'interface de chat avec affichage des appels aux outils MCP.
        
        Args:
            message: Message de l'utilisateur
            history: Historique des messages
            request: Objet Request de Gradio (non utilisé pour l'accès à l'agent)
            
        Yields:
            Listes de ChatMessage formatées incluant les détails des appels aux outils MCP
        """
        if not message or not message.strip():
            yield [gr.ChatMessage(role="assistant", content="⚠️ Veuillez entrer un message valide.")]
            return
        
        try:
            # Utilisation de l'agent récupéré depuis l'état de l'application
            agent = get_agent()
            if agent is None:
                yield [gr.ChatMessage(role="assistant", content="❌ Erreur: Agent non initialisé")]
                return
            
            # Convertir l'historique Gradio au format pydantic-ai
            formatted_history: List[ModelMessage] = []
            for msg in history:
                if isinstance(msg, dict):
                    # Nettoyer le message pour ne garder que les champs essentiels
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    
                    if role == "user" and content:
                        # Créer un ModelRequest avec UserPromptPart
                        user_request = ModelRequest(
                            parts=[UserPromptPart(content=content)]
                        )
                        formatted_history.append(user_request)
                    elif role == "assistant" and content:
                        # Créer un ModelResponse avec TextPart
                        assistant_response = ModelResponse(
                            parts=[TextPart(content=content)]
                        )
                        formatted_history.append(assistant_response)
                    elif role == "system" and content:
                        # Créer un ModelRequest avec SystemPromptPart
                        system_request = ModelRequest(
                            parts=[SystemPromptPart(content=content)]
                        )
                        formatted_history.append(system_request)
            
            # Initialiser la liste des messages de réponse
            response_messages = []
            
            # Utiliser l'API avancée d'itération pour capturer les détails des outils
            async with agent.iter(message, message_history=formatted_history) as run:
                async for node in run:
                    if Agent.is_user_prompt_node(node):
                        # Nœud de prompt utilisateur
                        logger.info(f"Traitement du message utilisateur: {node.user_prompt}")
                        
                    elif Agent.is_model_request_node(node):
                        # Nœud de requête modèle - streaming des tokens
                        logger.info("Streaming de la requête modèle...")
                        
                        # Ajouter un message assistant normal pour le streaming
                        streaming_message = gr.ChatMessage(role="assistant", content="")
                        response_messages.append(streaming_message)
                        yield response_messages
                        
                        # Stream les tokens partiels
                        async with node.stream(run.ctx) as request_stream:
                            async for event in request_stream:
                                if isinstance(event, PartStartEvent):
                                    logger.debug(f"Début de la partie {event.index}: {event.part}")
                                elif isinstance(event, PartDeltaEvent):
                                    if isinstance(event.delta, TextPartDelta):
                                        # Mettre à jour le message avec le contenu streamé
                                        current_content = str(streaming_message.content) if streaming_message.content else ""
                                        streaming_message.content = current_content + event.delta.content_delta
                                        yield response_messages
                                    elif isinstance(event.delta, ToolCallPartDelta):
                                        logger.debug(f"Appel d'outil en cours: {event.delta.args_delta}")
                                elif isinstance(event, FinalResultEvent):
                                    logger.debug("Streaming de la réponse terminé")
                                    yield response_messages
                                    
                    elif Agent.is_call_tools_node(node):
                        # Nœud d'appel d'outils - ici on capture les appels aux outils MCP
                        logger.info("Traitement des appels d'outils...")
                        
                        async with node.stream(run.ctx) as handle_stream:
                            async for event in handle_stream:
                                if isinstance(event, FunctionToolCallEvent):
                                    # Afficher l'appel d'outil en utilisant l'utilitaire
                                    tool_call_message = create_tool_call_message(
                                        event.part.tool_name,
                                        event.part.args,
                                        event.part.tool_call_id
                                    )
                                    response_messages.append(tool_call_message)
                                    log_gradio_message(tool_call_message, "TOOL_CALL")
                                    yield response_messages
                                    
                                elif isinstance(event, FunctionToolResultEvent):
                                    # Afficher le résultat de l'outil en utilisant l'utilitaire
                                    result_message = create_tool_result_message(
                                        tool_name="Outil MCP",  # Nom générique car pas disponible dans l'event
                                        result=event.result.content,
                                        call_id=event.tool_call_id
                                    )
                                    response_messages.append(result_message)
                                    log_gradio_message(result_message, "TOOL_RESULT")
                                    yield response_messages
                                    
                    elif Agent.is_end_node(node):
                        # Nœud de fin - traitement terminé
                        logger.info("Traitement terminé avec succès")
                        break
            
        except Exception as e:
            logger.error(f"Erreur lors du streaming: {e}")
            error_message = create_error_message(str(e))
            log_gradio_message(error_message, "ERROR")
            yield [error_message]
    
    # Exemples de conversation
    examples = [
        "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
        "Trouve des structures d'aide près de 75001 Paris",
        "Quels services d'insertion professionnelle à Lyon ?",
        "Aide au logement d'urgence à Marseille",
        "Services pour personnes handicapées à Lille",
        "Comment obtenir une aide alimentaire ?",
        "Structures d'accueil pour familles monoparentales"
    ]
    
    # Créer l'interface ChatInterface
    chat_interface = gr.ChatInterface(
        fn=chat_stream,
        type="messages",
        title="🤖 Agent IA d'Inclusion Sociale",
        description="Assistant intelligent spécialisé dans l'inclusion sociale en France - Affichage des appels aux outils MCP",
        examples=examples,
        cache_examples=False,
        chatbot=gr.Chatbot(
            label="Assistant IA",
            height=1100,
            show_copy_button=True,
            type="messages",
            avatar_images=(
                "https://em-content.zobj.net/source/twitter/376/bust-in-silhouette_1f464.png",
                "https://em-content.zobj.net/source/twitter/376/robot-face_1f916.png"
            ),
            placeholder="Bienvenue ! Posez votre question sur l'inclusion sociale...",
        ),
        textbox=gr.Textbox(
            placeholder="Ex: Aide au logement près de 75001 Paris",
            lines=1,
            max_lines=3,
            show_label=False
        )
    )
    
    return chat_interface


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie pour l'application combinée.
    
    Gère la connexion au serveur MCP et l'initialisation de l'agent
    avec logique de retry et backoff exponentiel.
    
    Args:
        app: Instance FastAPI
    """
    logger.info("🚀 Démarrage de l'application Gradio + FastAPI...")
    
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
                
                # Création des répertoires nécessaires
                Path("feedback_data").mkdir(exist_ok=True)
                Path("exports").mkdir(exist_ok=True)
                Path("logs").mkdir(exist_ok=True)
                
                logger.info("✅ Application initialisée avec succès")
                
                # Application prête
                yield
                
                # Code après yield s'exécute lors du shutdown
                break
                
        except Exception as e:
            if attempt == max_retries - 1:
                # Dernière tentative échouée
                raise RuntimeError(f"Échec de la connexion au serveur MCP après {max_retries} tentatives: {e}")
            
            # Calcul du délai avec backoff exponentiel
            delay = base_delay * (backoff_multiplier ** attempt)
            
            logger.warning(f"Tentative {attempt + 1}/{max_retries} échouée. Nouvelle tentative dans {delay:.2f}s...")
            await asyncio.sleep(delay)
    
    # Nettoyage lors du shutdown
    logger.info("🛑 Arrêt de l'application...")
    logger.info("✅ Nettoyage terminé")


# Création de l'application FastAPI principale
def create_app() -> FastAPI:
    """
    Crée l'application FastAPI combinée avec Gradio.
    
    Returns:
        Instance FastAPI configurée
    """
    global _app_instance
    
    settings = Settings()
    
    # Application principale
    app = FastAPI(
        title="Agent IA d'Inclusion Sociale - Interface Complète",
        description="Application complète combinant l'agent IA et l'interface Gradio",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Stocker l'instance de l'application dans la variable globale
    _app_instance = app
    
    # Configuration CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Servir les fichiers statiques
    static_path = Path("static")
    if static_path.exists():
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Routes de l'application principale
    
    @app.get("/")
    async def root():
        """Redirection vers l'interface Gradio."""
        return RedirectResponse(url="/chat")
    
    @app.get("/health")
    async def health_check():
        """Health check global de l'application."""
        try:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "agent": {"healthy": True},
                        "interface": {"healthy": True}
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du health check: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
    
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
            media_type="text/event-stream"
        )
    
    @api_router.get("/health")
    async def api_health_check():
        """
        Endpoint de vérification de santé de l'API agent.
        
        Returns:
            Statut OK avec code HTTP 200
        """
        return {"status": "OK"}
    
    # Monter l'APIRouter sous /api
    app.include_router(api_router, prefix="/api")
    
    # Créer et monter l'interface Gradio
    gradio_interface = create_complete_interface()
    
    # Monter l'interface Gradio
    app = gr.mount_gradio_app(
        app=app,
        blocks=gradio_interface,
        path="/chat"
    )
    
    logger.info("🎯 Application FastAPI + Gradio configurée:")
    logger.info("   - Interface Gradio : http://localhost:8000/chat")
    logger.info("   - API Agent : http://localhost:8000/api")
    logger.info("   - Documentation : http://localhost:8000/docs")
    logger.info("   - Health Check : http://localhost:8000/health")
    
    return app


# Instance de l'application
app = create_app()


# Fonction utilitaire pour le développement
def run_development():
    """Lance l'application en mode développement avec rechargement automatique."""
    settings = Settings()
    
    uvicorn.run(
        "src.gradio_app:app",
        host="0.0.0.0",
        port=settings.AGENT_PORT,
        reload=True,
        reload_dirs=["src"],
        reload_excludes=["*.pyc", "__pycache__", "*.log"],
        log_level="info",
        access_log=True,
        use_colors=True
    )


if __name__ == "__main__":
    """Point d'entrée pour l'exécution directe."""
    run_development() 