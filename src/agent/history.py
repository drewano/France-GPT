"""
Module de gestion de l'historique des messages pour l'agent.

Ce module contient toutes les fonctions responsables de la transformation
des données d'historique au format pydantic-ai pour l'agent IA.
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


def format_chainlit_history(history: List[Dict[str, Any]]) -> List[ModelMessage]:
    """
    Convertit l'historique Chainlit au format pydantic-ai ModelMessage.

    Filtre les messages d'outils et les steps pour ne pas polluer l'historique de l'agent.
    Ne garde que les messages utilisateur et assistant principaux.

    Args:
        history: Historique des messages au format Chainlit (souvent obtenu via cl.chat_context.to_openai())

    Returns:
        Liste des messages au format pydantic-ai
    """
    formatted_history: List[ModelMessage] = []

    for msg in history:
        if isinstance(msg, dict):
            # Nettoyer le message pour ne garder que les champs essentiels
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Filtrer les messages vides ou non pertinents
            if not content or not role:
                continue

            # Filtrer les messages d'outils en vérifiant différents indices
            # Messages avec des noms d'outils ou des emojis d'outils dans le contenu
            if (
                content.startswith(Emojis.TOOL)
                or content.startswith(Emojis.SUCCESS)
                or content.startswith(Emojis.ERROR)
                or "**🛠️" in content  # Messages de steps d'outils
                or "**✅" in content  # Messages de résultats d'outils
                or "**❌" in content  # Messages d'erreur d'outils
            ):
                continue

            # Filtrer les messages de traitement (Chainlit spécifique)
            if "Traitement en cours..." in content:
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


def get_chainlit_chat_history() -> List[Dict[str, Any]]:
    """
    Récupère l'historique de chat Chainlit au format standardisé.

    Cette fonction doit être appelée depuis un contexte Chainlit actif.

    Returns:
        List[Dict[str, Any]]: Historique des messages au format Chainlit/OpenAI
    """
    try:
        # Importer cl seulement quand nécessaire pour éviter les dépendances circulaires
        import chainlit as cl

        # Utiliser cl.chat_context.to_openai() pour récupérer l'historique
        return cl.chat_context.to_openai()
    except ImportError:
        # Si chainlit n'est pas disponible, retourner une liste vide
        return []
    except Exception:
        # Si nous ne sommes pas dans un contexte Chainlit actif, retourner une liste vide
        return []
