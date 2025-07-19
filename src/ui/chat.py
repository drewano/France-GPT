import chainlit as cl
from src.ui.streaming import process_agent_stream_chainlit
from src.agent.history import format_chainlit_history
from src.agent.agent import create_inclusion_agent
from src.core.config import settings
from pydantic_ai.mcp import MCPServerStreamableHTTP
from typing import List, Dict, Any


@cl.on_chat_start
async def on_chat_start():
    """
    Fonction appelée au démarrage d'une nouvelle session de chat.
    Initialise l'historique de la conversation et l'agent.
    """
    # Initialiser l'historique vide pour cette session
    cl.user_session.set("history", [])

    # Créer l'agent pour cette session
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


@cl.on_message
async def on_message(message: cl.Message):
    """
    Fonction appelée à chaque message reçu de l'utilisateur.

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

        # Récupérer l'historique depuis la session utilisateur
        history_raw = cl.user_session.get("history", [])

        # S'assurer que history est une liste et bien typée
        if isinstance(history_raw, list):
            history: List[Dict[str, Any]] = history_raw
        else:
            history = []

        # Ajouter le nouveau message de l'utilisateur à l'historique local
        user_message = {"role": "user", "content": message.content}
        history.append(user_message)

        # Formater l'historique pour pydantic-ai
        formatted_history = format_chainlit_history(history)

        # Appeler la fonction de streaming avec l'agent
        await process_agent_stream_chainlit(agent, message.content, formatted_history)

        # Récupérer la réponse de l'assistant depuis cl.chat_context
        # et mettre à jour l'historique
        current_history = cl.chat_context.to_openai()

        # Filtrer pour ne garder que les messages pertinents (user/assistant)
        filtered_history: List[Dict[str, Any]] = []
        for msg in current_history:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")

                # Ne garder que les messages utilisateur et assistant avec du contenu
                if role in ["user", "assistant"] and content:
                    # Éviter les messages de traitement temporaires
                    if content != "Traitement en cours...":
                        filtered_history.append({"role": role, "content": content})

        # Mettre à jour l'historique dans la session utilisateur
        cl.user_session.set("history", filtered_history)

    except Exception as e:
        # Gestion des erreurs générales
        await cl.Message(
            content=f"❌ **Erreur lors du traitement**: {str(e)}\n\n"
            "Veuillez réessayer ou reformuler votre question."
        ).send()
