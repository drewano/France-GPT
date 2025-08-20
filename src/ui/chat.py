"""
Module for handling chat interactions and agent management in the Chainlit UI.
"""

from typing import Optional
import chainlit as cl

from chainlit.types import ThreadDict
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
from pydantic_ai.toolsets import FunctionToolset

from src.ui.streaming import process_agent_modern_with_history
from src.agent.agent import create_agent_from_profile
from src.agent.ui_tools import display_website
from src.core.profiles import AGENT_PROFILES
from src.ui import data_layer # noqa: F401


async def _setup_agent():
    """
    Fonction d'assistance pour configurer l'agent basé sur le profil sélectionné.
    Déplace la logique de sélection de profil et de création d'agent ici.
    """
    profile_name = cl.user_session.get("chat_profile")

    if profile_name:
        profile = next(
            (p for p in AGENT_PROFILES.values() if p.name == profile_name), None
        )
    else:
        profile = AGENT_PROFILES.get("social_agent")

    if not profile:
        raise ValueError(f"Profil de chat '{profile_name}' non trouvé.")

    # Créer le toolset d'interface utilisateur
    ui_toolset = FunctionToolset(tools=[display_website])

    # Créer l'agent avec le toolset d'interface utilisateur
    agent = create_agent_from_profile(profile, ui_toolsets=[ui_toolset])
    cl.user_session.set("agent", agent)
    cl.user_session.set("selected_profile_id", profile.id)


@cl.set_chat_profiles
async def chat_profile(user: Optional[cl.User]):
    """
    Sets up chat profiles for the Chainlit application.
    The 'user' argument is currently unused but kept for Chainlit's API compatibility.
    """
    return [
        cl.ChatProfile(
            name=profile.name,
            markdown_description=profile.description,
            icon=profile.icon,
            starters=[
                cl.Starter(
                    label=starter.label, message=starter.message, icon=starter.icon
                )
                for starter in profile.starters
            ]
            if profile.starters
            else [],
        )
        for profile in AGENT_PROFILES.values()
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
    return None


@cl.on_chat_start
async def on_chat_start():
    """
    Initialise la session de chat en créant un agent basé sur le profil sélectionné.
    """
    await _setup_agent()
    # Initialise un historique de messages vide pour cette nouvelle session.
    cl.user_session.set("message_history", [])


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    Gère la reprise d'une session de chat existante.

    Recrée l'agent pour assurer la cohérence de l'état et de la configuration.
    """
    print(f"Reprise du fil de discussion (thread) : {thread['id']}")

    try:
        await _setup_agent()  # Call the new setup function
        reconstructed_history = []
        for step in thread["steps"]:
            step_type = step.get("type")
            step_output = step.get("output")
            if step_type == "user_message" and step_output:
                reconstructed_history.append(
                    ModelRequest(parts=[UserPromptPart(content=step_output)])
                )
            elif step_type == "assistant_message" and step_output:
                reconstructed_history.append(
                    ModelResponse(parts=[TextPart(content=step_output)])
                )

        # L'historique des messages de l'UI est géré par Chainlit.
        # On réinitialise ici l'historique de l'agent Pydantic-AI pour cette session.
        cl.user_session.set("message_history", reconstructed_history)

    except RuntimeError as e:
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

        # Récupérer l'ID du profil sélectionné
        profile_id = cl.user_session.get("selected_profile_id", "social_agent")
        # Récupérer l'objet profil complet
        profile = AGENT_PROFILES[profile_id]

        # Extraire la limite d'appels d'outils du profil
        limit = profile.tool_call_limit

        # Récupérer l'historique existant depuis la session
        message_history = cl.user_session.get("message_history", [])

        # Traiter le message avec l'agent moderne et streaming parfait
        updated_history = await process_agent_modern_with_history(
            agent, message.content, message_history, tool_call_limit=limit
        )

        # Sauvegarder l'historique mis à jour dans la session
        cl.user_session.set("message_history", updated_history)

    except RuntimeError as e:
        # Gestion des erreurs générales
        await cl.Message(
            content=f"❌ **Erreur lors du traitement**: {str(e)}\n\n"
            "Veuillez réessayer ou reformuler votre question."
        ).send()


@cl.on_chat_end
def on_chat_end():
    """
    Fonction appelée à la fin d'une session de chat.
    Nettoie les ressources si nécessaire.
    """
    # Note: Pour l'instant, aucun nettoyage spécifique n'est requis
    # car pydantic-ai gère automatiquement les connexions MCP
