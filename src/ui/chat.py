import chainlit as cl
from chainlit import Starter
from src.ui.streaming import process_agent_modern_with_history
from src.ui import data_layer
from src.agent.agent import create_inclusion_agent
from src.core.config import settings
from pydantic_ai.mcp import MCPServerStreamableHTTP
from typing import Optional
from chainlit.types import ThreadDict


@cl.set_starters
async def set_starters(user: Optional[cl.User]):
    return [
        cl.Starter(
            label="Rechercher des services",
            message="Je cherche des services d'aide alimentaire d'urgence à Paris 18ème.",
            icon="/public/icons/search.svg",
        ),
        cl.Starter(
            label="Comprendre les structures",
            message="Quels sont les différents types de structures d'aide disponibles en France ?",
            icon="/public/icons/help-circle.svg",
        ),
        cl.Starter(
            label="Explorer les données",
            message="Liste-moi tous les services disponibles près de Bordeaux.",
            icon="/public/icons/list.svg",
        ),
        cl.Starter(
            label="Découvrir les typologies",
            message="Donne-moi la liste des différentes typologies de services.",
            icon="/public/icons/info.svg",
        ),
    ]


@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """
    Fonction d'authentification par mot de passe pour Chainlit.

    Args:
        username: Le nom d'utilisateur fourni
        password: Le mot de passe fourni

    Returns:
        Un objet cl.User si l'authentification réussit, None sinon
    """
    # Pour les besoins du développement, utiliser des credentials codés en dur
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None


@cl.on_chat_start
async def on_chat_start():
    """
    Fonction appelée au démarrage d'une nouvelle session de chat.
    Initialise l'agent avec le serveur MCP et l'historique de session.
    """
    try:
        # Initialisation du serveur MCP
        mcp_server = MCPServerStreamableHTTP(settings.agent.MCP_SERVER_URL)

        # Création de l'agent avec le serveur MCP
        agent = create_inclusion_agent(mcp_server)

        # Stocker l'agent dans la session utilisateur
        cl.user_session.set("agent", agent)

        # Initialiser l'historique des messages vide
        cl.user_session.set("message_history", [])

    except Exception as e:
        await cl.Message(
            content="❌ **Erreur d'initialisation**: Impossible d'initialiser l'agent IA. "
            f"Détails: {str(e)}"
        ).send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    Fonction appelée lorsqu'un utilisateur reprend une conversation précédente.

    Cette fonction est automatiquement déclenchée par Chainlit quand :
    - L'authentification est activée
    - La persistance des données est configurée
    - L'utilisateur revient sur une conversation existante

    Args:
        thread: Dictionnaire contenant les informations du fil de discussion repris
    """
    print(f"Reprise du fil de discussion (thread) : {thread['id']}")

    # Réinitialiser l'agent pour la session reprise
    try:
        # Initialisation du serveur MCP
        mcp_server = MCPServerStreamableHTTP(settings.agent.MCP_SERVER_URL)

        # Création de l'agent avec le serveur MCP
        agent = create_inclusion_agent(mcp_server)

        # Stocker l'agent dans la session utilisateur
        cl.user_session.set("agent", agent)

        # Réinitialiser l'historique des messages (Chainlit gère la persistance des messages UI)
        # L'historique Pydantic-AI est séparé de l'historique UI de Chainlit
        cl.user_session.set("message_history", [])

    except Exception as e:
        print(f"Erreur lors de la reprise de session : {str(e)}")


@cl.on_message
async def on_message(message: cl.Message):
    """
    Fonction appelée à chaque message reçu de l'utilisateur.
    Utilise la nouvelle approche moderne avec gestion complète de l'historique.

    Args:
        message: Le message reçu de l'utilisateur
    """
    try:
        # Récupérer l'agent depuis la session utilisateur
        agent = cl.user_session.get("agent")

        if agent is None:
            await cl.Message(
                content="❌ **Erreur de configuration**: L'agent IA n'est pas disponible. "
                "Veuillez rafraîchir la page pour réinitialiser la session."
            ).send()
            return

        # Récupérer l'historique existant depuis la session
        message_history = cl.user_session.get("message_history", [])

        # Traiter le message avec l'agent moderne et streaming parfait
        updated_history = await process_agent_modern_with_history(
            agent, message.content, message_history
        )

        # Sauvegarder l'historique mis à jour dans la session
        cl.user_session.set("message_history", updated_history)

    except Exception as e:
        # Gestion des erreurs générales
        await cl.Message(
            content=f"❌ **Erreur lors du traitement**: {str(e)}\n\n"
            "Veuillez réessayer ou reformuler votre question."
        ).send()


@cl.on_chat_end
async def on_chat_end():
    """
    Fonction appelée à la fin d'une session de chat.
    Nettoie les ressources si nécessaire.
    """
    # Note: Pour l'instant, aucun nettoyage spécifique n'est requis
    # car pydantic-ai gère automatiquement les connexions MCP
    pass
