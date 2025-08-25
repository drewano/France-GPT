"""
Module for handling chat interactions and agent management in the Chainlit UI.
"""

import io
import base64
from typing import Optional, Dict, List, Tuple, Any
import PyPDF2
import chainlit as cl

from chainlit.types import ThreadDict
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
from pydantic_ai.toolsets import FunctionToolset

from src.ui.streaming import process_agent_modern_with_history
from src.agent.agent import create_agent_from_profile
from src.agent.ui_tools import display_website, ask_for_cv
from src.core.profiles import AGENT_PROFILES
from src.ui import data_layer  # noqa: F401


async def _process_files(
    files: List[cl.File],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Fonction utilitaire pour traiter les fichiers uploadés.

    Args:
        files: Liste des fichiers uploadés

    Returns:
        Tuple contenant les textes extraits et les données des fichiers
    """
    extracted_texts = []
    file_data_list = []

    for file in files:
        # Lire le contenu du fichier en utilisant son chemin
        try:
            with open(file.path, "rb") as f:
                content_bytes = f.read()
        except Exception as e:
            # En cas d'erreur lors de la lecture du fichier
            extracted_texts.append(
                f"Erreur lors de la lecture du fichier '{file.name}': {str(e)}"
            )
            file_data_list.append({"name": file.name, "content_b64": ""})
            continue

        # Si c'est un PDF, extraire le texte
        if file.mime == "application/pdf":
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
                full_text = ""
                for page in pdf_reader.pages:
                    full_text += page.extract_text() + "\n"

                # Ajouter une note d'en-tête et le texte extrait
                extracted_texts.append(
                    f"Contenu extrait du PDF '{file.name}':\n\n{full_text}"
                )
            except Exception as e:
                # En cas d'erreur lors de l'extraction, ajouter un message d'erreur
                extracted_texts.append(
                    f"Erreur lors de l'extraction du PDF '{file.name}': {str(e)}"
                )

        # Créer un dictionnaire avec les données du fichier encodé en base64
        file_data = {
            "name": file.name,
            "content_b64": base64.b64encode(content_bytes).decode("utf-8"),
        }
        file_data_list.append(file_data)

    return extracted_texts, file_data_list


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
    ui_toolset = FunctionToolset(tools=[display_website, ask_for_cv])

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


@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict,
    default_user: cl.User,
) -> Optional[cl.User]:
    """
    Fonction de callback OAuth pour l'authentification Google.

    Args:
        provider_id: L'identifiant du fournisseur OAuth
        token: Le jeton d'accès
        raw_user_data: Les données brutes de l'utilisateur
        default_user: L'utilisateur par défaut

    Returns:
        Un objet cl.User si l'authentification réussit, None sinon
    """
    # Pour cette implémentation, nous autorisons tout utilisateur qui s'authentifie avec succès via Google
    if provider_id == "google":
        return default_user
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

        # Initialiser la variable user_input
        user_input = message.content

        # Vérifier si des fichiers sont présents dans le message
        if message.elements:
            # Filtrer les éléments pour ne garder que les fichiers
            files = [
                element for element in message.elements if isinstance(element, cl.File)
            ]

            if files:
                # Traiter les fichiers uploadés
                extracted_texts, file_data_list = await _process_files(files)

                # Commencer avec le texte de l'utilisateur
                full_text = message.content

                # Ajouter chaque texte extrait des PDF
                for extracted_text in extracted_texts:
                    full_text += "\n\n" + extracted_text

                # Pour l'instant, nous n'incluons pas les fichiers dans le message
                # Nous pourrions les inclure plus tard si l'agent les supporte
                user_input = full_text

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
            agent, user_input, message_history, tool_call_limit=limit
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
