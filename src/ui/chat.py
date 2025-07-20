import chainlit as cl
from src.ui.streaming import process_agent_modern_with_history
from src.ui import data_layer
from src.agent.agent import create_inclusion_agent
from src.core.config import settings
from pydantic_ai.mcp import MCPServerStreamableHTTP
from typing import Optional
from chainlit.types import ThreadDict


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

        # Envoyer un message de bienvenue
        await cl.Message(
            content="👋 **Bienvenue !** Je suis votre assistant IA d'inclusion sociale. "
            "Posez-moi vos questions sur les structures et services d'inclusion."
        ).send()

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

        # Traiter le message avec l'agent moderne et streaming parfait
        # L'historique est maintenant géré automatiquement par la couche de persistance
        await process_agent_modern_with_history(agent, message.content, None)

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