"""
Factory pour créer et configurer l'agent IA d'inclusion sociale.

Ce module contient la fonction factory qui instancie l'agent PydanticAI
avec sa configuration spécialisée pour l'inclusion sociale en France.
"""

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from ..core.config import settings


def create_inclusion_agent(mcp_server: MCPServerStreamableHTTP) -> Agent:
    """
    Crée et configure l'agent IA spécialisé dans l'inclusion sociale en France.

    Args:
        mcp_server: Instance du serveur MCP pour accéder aux données d'inclusion

    Returns:
        Agent configuré pour répondre aux questions sur l'inclusion sociale
    """

    # Configuration du provider OpenAI avec support des URLs personnalisées
    provider_args = {}

    # Ajouter l'API key si elle est configurée
    if settings.agent.OPENAI_API_KEY:
        provider_args["api_key"] = settings.agent.OPENAI_API_KEY

    # Ajouter l'URL de base personnalisée si elle est configurée
    if settings.agent.OPENAI_API_BASE_URL:
        provider_args["base_url"] = settings.agent.OPENAI_API_BASE_URL

    # Utiliser OpenAI au lieu de Gemini pour éviter les problèmes avec les schémas $ref
    # OpenAI gère mieux les schémas JSON complexes avec des références
    if provider_args:
        # Créer un provider personnalisé avec les arguments configurés
        provider = OpenAIProvider(**provider_args)
        model = OpenAIModel(
            model_name=settings.agent.AGENT_MODEL_NAME, provider=provider
        )
    else:
        # Utiliser le comportement par défaut sans provider personnalisé
        model = OpenAIModel(model_name=settings.agent.AGENT_MODEL_NAME)

    return Agent(
        # Modèle OpenAI qui supporte mieux les schémas JSON complexes
        model=model,
        # Prompt système définissant le rôle et les instructions de l'agent
        system_prompt=(
            "Tu es un assistant expert de l'inclusion sociale en France. "
            "Utilise les outils disponibles pour répondre aux questions sur les "
            "structures et services d'aide. Sois précis et factuel. "
            "Ton rôle est d'aider les utilisateurs à trouver des informations "
            "sur les services d'inclusion, les structures d'aide, et les "
            "ressources disponibles sur le territoire français."
        ),
        # Configuration des serveurs MCP pour accéder aux données
        mcp_servers=[mcp_server],
    )
