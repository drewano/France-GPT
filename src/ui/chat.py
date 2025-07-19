import chainlit as cl
from src.ui.streaming import process_agent_modern_with_history, trim_message_history
from src.agent.agent import create_inclusion_agent
from src.core.config import settings
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.messages import ModelMessage
from typing import List, Dict, Any


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

        # Initialiser l'historique vide des messages pydantic-ai
        cl.user_session.set("messages", [])

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


def filter_conversation_history(
    chat_history: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Filtre l'historique pour pydantic-ai en s'assurant que :
    1. La conversation commence par un message utilisateur
    2. Les messages de bienvenue sont exclus
    3. Seuls les vrais échanges conversationnels sont inclus

    Args:
        chat_history: Historique brut du chat

    Returns:
        Historique filtré compatible avec pydantic-ai
    """
    filtered_history = []
    found_first_user_message = False

    for msg in chat_history:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role", "")
        content = msg.get("content", "")

        # Ignorer les messages sans contenu
        if not content:
            continue

        # Ignorer le message de bienvenue (commence par 👋)
        if role == "assistant" and content.strip().startswith("👋"):
            continue

        # Une fois qu'on a trouvé le premier message utilisateur,
        # on peut inclure les messages suivants
        if role == "user":
            found_first_user_message = True

        # N'inclure les messages qu'après avoir trouvé le premier message utilisateur
        if found_first_user_message and role in ["user", "assistant"]:
            filtered_history.append({"role": role, "content": content})

    return filtered_history


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

        # Récupérer l'historique des messages pydantic-ai depuis la session utilisateur
        messages_raw = cl.user_session.get("messages", [])
        messages: List[ModelMessage] = (
            messages_raw if isinstance(messages_raw, list) else []
        )

        # Traiter le message avec l'agent moderne
        updated_messages = await process_agent_modern_with_history(
            agent, message.content, messages
        )

        # Limiter l'historique et le sauvegarder dans la session
        trimmed_messages = trim_message_history(updated_messages)
        cl.user_session.set("messages", trimmed_messages)

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
