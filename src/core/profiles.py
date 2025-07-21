from pydantic import BaseModel
from src.core.config import settings


class AgentProfile(BaseModel):
    """
    Définit la structure de données pour un profil d'agent.

    Chaque profil contient toutes les configurations nécessaires pour initialiser
    un agent spécifique, y compris son identité, son apparence dans l'interface
    utilisateur, et ses instructions système.
    """

    id: str
    name: str
    description: str
    icon: str
    system_prompt: str
    mcp_server_url: str


# Base de données centrale des profils d'agents disponibles dans l'application.
# Ce dictionnaire utilise un identifiant unique comme clé pour chaque profil,
# permettant de les charger dynamiquement en fonction de la sélection de l'utilisateur.
AGENT_PROFILES: dict[str, AgentProfile] = {
    "social_agent": AgentProfile(
        id="social_agent",
        name="Agent Social",
        description="Un assistant expert de l'inclusion sociale en France.",
        icon="/public/icons/agent-social.svg",
        system_prompt=(
            "Tu es un assistant expert de l'inclusion sociale en France. "
            "Utilise les outils disponibles pour répondre aux questions sur les "
            "structures et services d'aide. Sois précis et factuel. "
            "Ton rôle est d'aider les utilisateurs à trouver des informations "
            "sur les services d'inclusion, les structures d'aide, et les "
            "ressources disponibles sur le territoire français."
        ),
        mcp_server_url=settings.agent.MCP_SERVER_URL,
    ),
    "job_search_agent": AgentProfile(
        id="job_search_agent",
        name="Agent Recherche d'Emploi",
        description="Un conseiller expert pour trouver des structures d'aide à l'emploi.",
        icon="/public/icons/agent-job-search.svg",
        system_prompt=(
            "Tu es un conseiller expert en recherche d'emploi en France. "
            "Ton rôle est d'aider les utilisateurs à trouver des structures et des services "
            "qui peuvent les accompagner dans leur parcours professionnel. Utilise les outils "
            "à ta disposition pour identifier les ressources pertinentes, comme les points "
            "d'accès numérique pour postuler en ligne, les services d'aide à la rédaction "
            "de CV, ou les formations. Sois encourageant, précis et factuel."
        ),
        mcp_server_url=settings.agent.MCP_SERVER_URL,
    )
}
