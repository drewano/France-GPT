from typing import List, Optional
from pydantic import BaseModel


class StarterConfig(BaseModel):
    """
    Configuration pour les messages de démarrage suggérés.
    """
    label: str
    message: str
    icon: str


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
    mcp_service_name: str
    starters: Optional[List[StarterConfig]] = None

# Base de données centrale des profils d'agents disponibles dans l'application.
# Ce dictionnaire utilise un identifiant unique comme clé pour chaque profil,
# permettant de les charger dynamiquement en fonction de la sélection de l'utilisateur.
AGENT_PROFILES: dict[str, AgentProfile] = {
    "social_agent": AgentProfile(
        id="social_agent",
        name="Agent Social",
        description="Un assistant expert de l'inclusion sociale en France.",
        icon="/public/avatars/social_agent.svg",
        system_prompt=(
            "Tu es un assistant expert de l'inclusion sociale en France. "
            "Utilise les outils disponibles pour répondre aux questions sur les "
            "structures et services d'aide. Sois précis et factuel. "
            "Ton rôle est d'aider les utilisateurs à trouver des informations "
            "sur les services d'inclusion, les structures d'aide, et les "
            "ressources disponibles sur le territoire français. "
            "Tu disposes également d'un outil nommé `display_website` qui prend une URL en argument. "
            "Lorsque l'utilisateur te demande plus de détails sur un service ou une structure, "
            "utilise directement 'display_website' pour afficher le site web de la structure ou du service directement dans l'interface de chat."
        ),
        mcp_service_name="datainclusion",
        starters=[
            StarterConfig(
                label="Aide alimentaire",
                message="Où puis-je trouver des banques alimentaires ou des distributions de repas près de Paris ?",
                icon="/public/avatars/social_agent.svg"
            ),
            StarterConfig(
                label="Aide au logement",
                message="Quelles sont les aides disponibles pour payer mon loyer ou trouver un logement social ?",
                icon="/public/icons/social_agent.svg"
            ),
            StarterConfig(
                label="Rechercher une structure",
                message="Trouve-moi les structures d'accompagnement pour les jeunes en difficulté à Lyon.",
                icon="/public/icons/search.svg"
            ),
        ],
    ),
    "legal_agent": AgentProfile(
        id="legal_agent",
        name="Agent Juridique",
        description="Un assistant expert de la législation française, capable de rechercher des textes de loi et des articles du code.",
        icon="/public/icons/lawyer_agent.svg",
        system_prompt=(
            "Tu es un assistant expert en droit français. "
            "Utilise les outils de l'API Légifrance pour répondre aux questions sur les codes, "
            "les lois et la jurisprudence. Sois précis, cite tes sources et n'interprète pas la loi."
        ),
        mcp_service_name="legifrance",
    ),
}
