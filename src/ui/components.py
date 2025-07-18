"""
Module de création de composants Gradio pour l'interface utilisateur.

Ce module contient toutes les fonctions responsables de la création
des composants gr.ChatMessage pour l'affichage des interactions avec l'agent.
"""

import gradio as gr
from typing import Dict, Any, Optional, Literal, NotRequired, TypedDict, Final
import json
import uuid

# Imports des fonctions de formatage
from .formatters import (
    get_friendly_tool_name,
    format_arguments_for_display,
    format_result_for_display,
)


class Emojis:
    """Emoji constants for consistent visual representation."""

    SUCCESS: Final[str] = "✅"
    ERROR: Final[str] = "❌"
    WARNING: Final[str] = "⚠️"


class ConfigDefaults:
    """Default configuration values for roles."""

    LABEL_ASSISTANT: Final[Literal["assistant"]] = "assistant"


# Types Gradio corrects selon la documentation
class MetadataDict(TypedDict):
    """Structure des métadonnées pour les messages Gradio ChatMessage."""

    title: NotRequired[str]
    id: NotRequired[int | str]
    parent_id: NotRequired[int | str]
    log: NotRequired[str]
    duration: NotRequired[float]
    status: NotRequired[Literal["pending", "done"]]


def create_tool_call_message(
    tool_name: str,
    arguments: Dict[str, Any] | str | None,
    call_id: Optional[str] = None,
) -> gr.ChatMessage:
    """
    Crée un message Gradio pour un appel d'outil MCP.

    Args:
        tool_name: Nom de l'outil appelé
        arguments: Arguments passés à l'outil (dict, str, ou None)
        call_id: ID unique de l'appel (optionnel)

    Returns:
        gr.ChatMessage: Message Gradio formaté pour l'appel d'outil
    """

    # Normaliser les arguments en dict pour le formatage
    if isinstance(arguments, str):
        try:
            # Tenter de parser comme JSON
            parsed_args = json.loads(arguments)
            if isinstance(parsed_args, dict):
                normalized_args = parsed_args
            else:
                normalized_args = {"value": arguments}
        except (json.JSONDecodeError, ValueError):
            # Si ce n'est pas du JSON, traiter comme string
            normalized_args = {"value": arguments}
    elif isinstance(arguments, dict):
        normalized_args = arguments
    else:
        # arguments est None ou autre type
        normalized_args = {}

    # Formatage des arguments pour l'affichage
    args_formatted = format_arguments_for_display(normalized_args)

    # Nom convivial de l'outil
    friendly_name = get_friendly_tool_name(tool_name)

    # Contenu du message
    content = f"**{friendly_name}**\n\n"
    if normalized_args:
        content += f"**Paramètres:**\n{args_formatted}"
    else:
        content += "*Aucun paramètre*"

    # Métadonnées pour l'affichage - utiliser MetadataDict
    # Générer un ID unique si call_id n'est pas fourni
    unique_id = call_id if call_id else f"tool_{tool_name}_{uuid.uuid4().hex[:8]}"

    metadata: MetadataDict = {
        "title": friendly_name,
        "id": unique_id,
    }

    return gr.ChatMessage(
        role=ConfigDefaults.LABEL_ASSISTANT, content=content, metadata=metadata
    )


def create_tool_result_message(
    tool_name: str,
    result: Any,
    call_id: Optional[str] = None,
    duration: Optional[float] = None,
    is_error: bool = False,
) -> gr.ChatMessage:
    """
    Crée un message Gradio pour le résultat d'un outil MCP.

    Args:
        tool_name: Nom de l'outil
        result: Résultat de l'outil
        call_id: ID unique de l'appel (optionnel)
        duration: Durée d'exécution en secondes (optionnel)
        is_error: Si True, affiche comme une erreur

    Returns:
        gr.ChatMessage: Message Gradio formaté pour le résultat
    """

    # Formatage du résultat pour l'affichage
    result_formatted = format_result_for_display(result)

    # Nom convivial de l'outil
    friendly_name = get_friendly_tool_name(tool_name)

    # Emoji et titre selon le statut
    if is_error:
        title = f"{Emojis.ERROR} {friendly_name} - Erreur"
        content = f"**{Emojis.ERROR} Erreur lors de l'exécution**\n\n"
    else:
        title = f"{Emojis.SUCCESS} {friendly_name} - Résultat"
        content = f"**{Emojis.SUCCESS} Résultat obtenu**\n\n"

    # Ajouter la durée si disponible
    if duration is not None:
        content += f"**Durée:** {duration:.3f}s\n\n"

    # Ajouter le résultat
    content += f"**Données:**\n{result_formatted}"

    # Métadonnées pour l'affichage - utiliser MetadataDict
    # Générer un ID unique pour le résultat
    result_id = (
        f"result_{call_id}" if call_id else f"result_{tool_name}_{uuid.uuid4().hex[:8]}"
    )

    metadata: MetadataDict = {
        "title": title,
        "id": result_id,
        "status": "done",
    }

    # Ajouter la durée dans les métadonnées si disponible
    if duration is not None:
        metadata["duration"] = duration

    return gr.ChatMessage(
        role=ConfigDefaults.LABEL_ASSISTANT, content=content, metadata=metadata
    )


def create_error_message(
    error_msg: str, title: str = f"{Emojis.WARNING} Erreur"
) -> gr.ChatMessage:
    """
    Crée un message Gradio pour une erreur.

    Args:
        error_msg: Message d'erreur
        title: Titre du message d'erreur

    Returns:
        gr.ChatMessage: Message Gradio formaté pour l'erreur
    """

    # Générer un ID unique pour l'erreur
    error_id = f"error_{uuid.uuid4().hex[:8]}"

    metadata: MetadataDict = {
        "title": title,
        "id": error_id,
        "status": "done",
    }

    return gr.ChatMessage(
        role=ConfigDefaults.LABEL_ASSISTANT,
        content=f"{Emojis.ERROR} {error_msg}",
        metadata=metadata,
    )
