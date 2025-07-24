"""
Factory pour créer et configurer l'agent IA d'inclusion sociale.

Ce module contient la fonction factory qui instancie l'agent PydanticAI
avec sa configuration spécialisée pour l'inclusion sociale en France.
"""

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.core.config import settings
from src.core.profiles import AgentProfile


def create_agent_from_profile(profile: AgentProfile) -> Agent:
    """
    Crée et configure un agent IA à partir d'un profil donné.

    Cette factory utilise un objet `AgentProfile` pour configurer entièrement
    un agent, y compris son modèle, son prompt système et sa connexion au
    serveur MCP. Elle est générique et peut créer n'importe quel agent
    défini dans `src.core.profiles`.

    Args:
        profile: Le profil d'agent à utiliser pour la configuration.

    Returns:
        Un agent PydanticAI configuré et prêt à l'emploi.
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

    # Construire l'URL complète du sous-serveur MCP
    # Recherchez la configuration du service correspondant au profil
    service_config = next(
        (s for s in settings.mcp_services if s.name == profile.mcp_service_name),
        None,
    )

    if not service_config:
        raise ValueError(
            f"No MCP service configuration found for {profile.mcp_service_name}"
        )

    mcp_url = (
        f"{settings.agent.MCP_SERVER_HOST_URL}:{service_config.port}"
        f"{settings.mcp_server.MCP_API_PATH}"
    )

    mcp_server = MCPServerStreamableHTTP(mcp_url)
    return Agent(
        # Modèle OpenAI qui supporte mieux les schémas JSON complexes
        model=model,
        # Prompt système définissant le rôle et les instructions de l'agent
        system_prompt=profile.system_prompt,
        # Configuration des serveurs MCP pour accéder aux données
        mcp_servers=[mcp_server],
    )
