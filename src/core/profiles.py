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
            "Utilise d'abord les outils 'doc' pour te documenter sur l'utilisation des outils avant de faire tes recherches sur les services et structures avec l'outil 'search'."
            "Fais maximum 5 tools calls par réponse."
            "Utilise uniquement comme source et contexte pour créer tes réponses les données de l'outil 'search'."
            "Tu peux élargir ta recherche en fonction de la locatisation de l'utilisateur. Exemple : Montreuil bah tu peux chercher en ile de france."
            "Ne sois pas trop long dans tes réponses, sois précis et concis."
            "Reasoning: high"
        ),
        mcp_service_name="datainclusion",
        starters=[
            StarterConfig(
                label="Aide alimentaire",
                message="Où puis-je trouver des banques alimentaires ou des distributions de repas près de Paris ?",
                icon="/public/icons/food.png",
            ),
            StarterConfig(
                label="Aide au logement",
                message="Quelles sont les aides disponibles pour payer mon loyer ou trouver un logement social ?",
                icon="/public/icons/house.png",
            ),
            StarterConfig(
                label="Rechercher une structure",
                message="Trouve-moi les structures d'accompagnement pour les jeunes en difficulté à Lyon.",
                icon="/public/icons/teen.png",
            ),
        ],
    ),
    "legal_agent": AgentProfile(
        id="legal_agent",
        name="Agent Juridique",
        description="Un assistant expert de la législation française, capable de rechercher des textes de loi et des articles du code.",
        icon="/public/avatars/lawyer_agent.svg",
        system_prompt=(
            "Tu es un assistant expert en droit français. Tu fournis des conseils juridiques et des informations sur la législation française en fonction des questions de l'utilisateur."
            "Utilise tes outils pour répondre aux questions des utilisateurs "
            "Recherches des jurisprudences en fonction des questions de l'utilisateur."
            "Sois précis et concis."
            "Sois factuel."
            "Fais maximum 10 tools calls par question."
            "Source tes réponses avec les résultats de tes recherches et consultations."
            "Ne retourne jamais de réponse vide. Envoie toujours une réponse avec des informations."
            "Tu dois répondre exactement comme un avocat qui parle à son client. Ne fais pas de tableaux, fais des réponses rédigées en paragraphes."
            "Cite toujours tes sources à la fin de ta réponse."
            "Reasoning: high"
        ),
        mcp_service_name="legifrance",
        starters=[
            StarterConfig(
                label="Rechercher un article de code",
                message="Trouve-moi l'article 111-1 du code civil.",
                icon="/public/icons/law.png",
            ),
            StarterConfig(
                label="Rechercher une loi",
                message="Trouve-moi la loi n°2024-1234 du 1er janvier 2024.",
                icon="/public/icons/law.png",
            ),
            StarterConfig(
                label="Rechercher une décision de justice",
                message="Trouve-moi la décision de justice n°2024-1234 du 1er janvier 2024.",
                icon="/public/icons/law.png",
            ),
        ],
    ),
    "insee_agent": AgentProfile(
        id="insee_agent",
        name="Agent Insee",
        description="Un assistant expert de l'INSEE, capable de rechercher des données statistiques et des données géographiques.",
        icon="/public/avatars/insee_agent.svg",
        system_prompt=(
            "Tu es un assistant expert de l'INSEE, capable de rechercher des données statistiques et des données géographiques."
        ),
        mcp_service_name="insee",
    ),
}
