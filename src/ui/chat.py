import chainlit as cl
from src.ui.streaming import process_agent_modern_with_history
from src.ui import data_layer
from src.agent.agent import create_agent_from_profile
from src.core.config import settings
from pydantic_ai.mcp import MCPServerStreamableHTTP
from typing import Optional
from chainlit.types import ThreadDict
from src.core.profiles import AGENT_PROFILES


@cl.set_chat_profiles
async def chat_profile(user: Optional[cl.User]):
    return [
        cl.ChatProfile(
            name=profile.name,
            markdown_description=profile.description,
            icon=profile.icon,
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
    else:
        return None


@cl.on_chat_start
async def on_chat_start():
    """
    Initialise la session de chat en créant un agent basé sur le profil sélectionné.
    """
    try:
        # Récupère le nom du profil de chat sélectionné par l'utilisateur.
        profile_name = cl.user_session.get("chat_profile")

        # Trouve le profil correspondant dans le dictionnaire par son nom.
        if profile_name:
            profile = next((p for p in AGENT_PROFILES.values() if p.name == profile_name), None)
        else:
            # Si aucun profil n'est sélectionné, utilise le profil par défaut.
            profile = AGENT_PROFILES.get("social_agent")

        # Si aucun profil correspondant n'est trouvé, lève une exception.
        if not profile:
            raise ValueError(f"Profil de chat '{profile_name}' non trouvé.")

        # Crée une instance de l'agent en utilisant la factory et le profil chargé.
        agent = create_agent_from_profile(profile)

        # Stocke l'agent et l'ID du profil dans la session pour un accès ultérieur.
        cl.user_session.set("agent", agent)
        cl.user_session.set("selected_profile_id", profile.id)

        # Initialise un historique de messages vide pour cette nouvelle session.
        cl.user_session.set("message_history", [])

    except Exception as e:
        await cl.Message(
            content="❌ **Erreur d'initialisation**: Impossible d'initialiser l'agent IA. "
            f"Détails: {str(e)}"
        ).send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    Gère la reprise d'une session de chat existante.

    Recrée l'agent pour assurer la cohérence de l'état et de la configuration.
    """
    print(f"Reprise du fil de discussion (thread) : {thread['id']}")

    # TODO: Pour une reprise multi-profils complète, il faudra stocker l'ID du profil
    # dans les métadonnées du thread (`thread['metadata']`) et le lire ici pour
    # recréer l'agent avec le bon profil.
    try:
        # Pour l'instant, la reprise se fait systématiquement avec le profil par défaut.
        profile = AGENT_PROFILES["social_agent"]

        # Recrée l'agent pour la session reprise.
        agent = create_agent_from_profile(profile)

        # Met à jour l'agent dans la session utilisateur.
        cl.user_session.set("agent", agent)

        # L'historique des messages de l'UI est géré par Chainlit.
        # On réinitialise ici l'historique de l'agent Pydantic-AI pour cette session.
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
