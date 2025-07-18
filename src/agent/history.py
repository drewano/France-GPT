"""
Module de gestion de l'historique des messages pour l'agent.

Ce module contient toutes les fonctions responsables de la transformation
et validation des données d'historique entre les formats Gradio et pydantic-ai.
"""

from typing import Dict, Any, List, Final

# Imports pour pydantic-ai
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ModelMessage,
    UserPromptPart,
    SystemPromptPart,
    TextPart,
)


class Emojis:
    """Emoji constants for consistent visual representation."""

    SUCCESS: Final[str] = "✅"
    ERROR: Final[str] = "❌"
    TOOL: Final[str] = "🛠️"


class ConfigDefaults:
    """Default configuration values for roles."""

    LABEL_USER: Final[str] = "user"
    LABEL_ASSISTANT: Final[str] = "assistant"
    LABEL_SYSTEM: Final[str] = "system"


def format_gradio_history(history: List[Dict[str, str]]) -> List[ModelMessage]:
    """
    Convertit l'historique Gradio au format pydantic-ai ModelMessage.

    Filtre les messages d'outils pour ne pas polluer l'historique de l'agent.
    Ne garde que les messages utilisateur et assistant principaux.

    Args:
        history: Historique des messages au format Gradio

    Returns:
        Liste des messages au format pydantic-ai
    """
    formatted_history: List[ModelMessage] = []

    for msg in history:
        if isinstance(msg, dict):
            # Nettoyer le message pour ne garder que les champs essentiels
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Filtrer les messages d'outils en vérifiant les métadonnées
            metadata = msg.get("metadata", {})
            if metadata and isinstance(metadata, dict):
                title = metadata.get("title", "")
                # Ignorer les messages d'outils (ceux qui commencent par 🛠️ ou ✅/❌)
                if (
                    title.startswith(Emojis.TOOL)
                    or title.startswith(Emojis.SUCCESS)
                    or title.startswith(Emojis.ERROR)
                ):
                    continue

            if role == ConfigDefaults.LABEL_USER and content:
                # Créer un ModelRequest avec UserPromptPart
                user_request = ModelRequest(parts=[UserPromptPart(content=content)])
                formatted_history.append(user_request)
            elif role == ConfigDefaults.LABEL_ASSISTANT and content:
                # Créer un ModelResponse avec TextPart
                assistant_response = ModelResponse(parts=[TextPart(content=content)])
                formatted_history.append(assistant_response)
            elif role == ConfigDefaults.LABEL_SYSTEM and content:
                # Créer un ModelRequest avec SystemPromptPart
                system_request = ModelRequest(parts=[SystemPromptPart(content=content)])
                formatted_history.append(system_request)

    return formatted_history


def extract_tool_call_mapping(tool_calls: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extrait un mapping entre les ID d'appel d'outils et leurs noms.

    Args:
        tool_calls: Liste des appels d'outils

    Returns:
        Dict[str, str]: Mapping ID -> nom d'outil
    """
    mapping = {}
    for tool_call in tool_calls:
        if isinstance(tool_call, dict):
            call_id = tool_call.get("id") or tool_call.get("tool_call_id")
            tool_name = tool_call.get("name") or tool_call.get("tool_name")
            if call_id and tool_name:
                mapping[call_id] = tool_name
    return mapping


def validate_gradio_message(message: Dict[str, Any]) -> bool:
    """
    Valide qu'un message Gradio a la structure attendue.

    Args:
        message: Message à valider

    Returns:
        bool: True si le message est valide
    """
    if not isinstance(message, dict):
        return False

    required_fields = ["role", "content"]
    for field in required_fields:
        if field not in message:
            return False

    # Vérifier que le rôle est valide
    valid_roles = [
        ConfigDefaults.LABEL_USER,
        ConfigDefaults.LABEL_ASSISTANT,
        ConfigDefaults.LABEL_SYSTEM,
    ]
    if message["role"] not in valid_roles:
        return False

    return True


def clean_gradio_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Nettoie l'historique Gradio en supprimant les messages invalides ou d'outils.

    Args:
        history: Historique des messages Gradio

    Returns:
        List[Dict[str, str]]: Historique nettoyé
    """
    cleaned_history = []

    for msg in history:
        if not validate_gradio_message(msg):
            continue

        # Filtrer les messages d'outils en vérifiant les métadonnées
        metadata = msg.get("metadata", {})
        if metadata and isinstance(metadata, dict):
            title = metadata.get("title", "")
            # Ignorer les messages d'outils (ceux qui commencent par 🛠️ ou ✅/❌)
            if (
                title.startswith(Emojis.TOOL)
                or title.startswith(Emojis.SUCCESS)
                or title.startswith(Emojis.ERROR)
            ):
                continue

        cleaned_history.append(msg)

    return cleaned_history
