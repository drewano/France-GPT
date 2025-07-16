"""
Utilitaires Gradio pour l'affichage des appels aux outils MCP.

Ce module contient des fonctions utilitaires pour créer des messages Gradio
avec des métadonnées appropriées pour afficher les appels aux outils MCP
de manière claire et informative.
"""

import gradio as gr
from typing import Dict, Any, Optional, List, Literal, NotRequired, TypedDict
import json
import logging
from datetime import datetime

# Configuration du logger
logger = logging.getLogger(__name__)


# Types Gradio corrects selon la documentation
class MetadataDict(TypedDict):
    """Structure des métadonnées pour les messages Gradio ChatMessage."""
    title: NotRequired[str]
    id: NotRequired[int | str]
    parent_id: NotRequired[int | str]
    log: NotRequired[str]
    duration: NotRequired[float]
    status: NotRequired[Literal["pending", "done"]]


def create_tool_call_message(tool_name: str, arguments: Dict[str, Any] | str | None, call_id: Optional[str] = None) -> gr.ChatMessage:
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
            import json
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
    
    # Contenu du message
    content = f"**🛠️ Appel d'outil: {tool_name}**\n\n"
    if normalized_args:
        content += f"**Arguments:**\n{args_formatted}"
    else:
        content += "*Aucun argument*"
    
    # Métadonnées pour l'affichage - utiliser MetadataDict
    metadata: MetadataDict = {
        "title": f"🛠️ {tool_name}",
        "id": call_id or f"tool_{tool_name}_{datetime.now().strftime('%H%M%S')}"
    }
    
    return gr.ChatMessage(
        role="assistant",
        content=content,
        metadata=metadata
    )


def create_tool_result_message(tool_name: str, result: Any, call_id: Optional[str] = None, 
                             duration: Optional[float] = None, is_error: bool = False) -> gr.ChatMessage:
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
    
    # Emoji et titre selon le statut
    if is_error:
        emoji = "❌"
        title = f"❌ Erreur - {tool_name}"
        content = f"**❌ Erreur lors de l'exécution de {tool_name}**\n\n"
        status: Literal["pending", "done"] = "done"
    else:
        emoji = "✅"
        title = f"✅ Résultat - {tool_name}"
        content = f"**✅ Résultat de {tool_name}**\n\n"
        status = "done"
    
    # Ajouter la durée si disponible
    if duration is not None:
        content += f"**Durée:** {duration:.3f}s\n\n"
    
    # Ajouter le résultat
    content += f"**Résultat:**\n{result_formatted}"
    
    # Métadonnées pour l'affichage - utiliser MetadataDict
    metadata: MetadataDict = {
        "title": title,
        "id": f"result_{call_id}" if call_id else f"result_{tool_name}_{datetime.now().strftime('%H%M%S')}",
        "status": status
    }
    
    if duration is not None:
        metadata["duration"] = duration
    
    return gr.ChatMessage(
        role="assistant",
        content=content,
        metadata=metadata
    )


def create_thinking_message(content: str = "", title: str = "🤔 Réflexion...") -> gr.ChatMessage:
    """
    Crée un message Gradio pour indiquer que l'IA réfléchit.
    
    Args:
        content: Contenu du message de réflexion
        title: Titre du message
        
    Returns:
        gr.ChatMessage: Message Gradio formaté pour la réflexion
    """
    
    metadata: MetadataDict = {
        "title": title,
        "id": f"thinking_{datetime.now().strftime('%H%M%S')}",
        "status": "pending"
    }
    
    return gr.ChatMessage(
        role="assistant",
        content=content,
        metadata=metadata
    )


def create_final_response_message(content: str) -> gr.ChatMessage:
    """
    Crée un message Gradio pour la réponse finale de l'IA.
    
    Args:
        content: Contenu de la réponse finale
        
    Returns:
        gr.ChatMessage: Message Gradio formaté pour la réponse finale
    """
    
    metadata: MetadataDict = {
        "title": "💬 Réponse finale",
        "id": f"final_{datetime.now().strftime('%H%M%S')}",
        "status": "done"
    }
    
    return gr.ChatMessage(
        role="assistant",
        content=content,
        metadata=metadata
    )


def create_error_message(error_msg: str, title: str = "⚠️ Erreur") -> gr.ChatMessage:
    """
    Crée un message Gradio pour une erreur.
    
    Args:
        error_msg: Message d'erreur
        title: Titre du message d'erreur
        
    Returns:
        gr.ChatMessage: Message Gradio formaté pour l'erreur
    """
    
    metadata: MetadataDict = {
        "title": title,
        "id": f"error_{datetime.now().strftime('%H%M%S')}",
        "status": "done"
    }
    
    return gr.ChatMessage(
        role="assistant",
        content=f"❌ {error_msg}",
        metadata=metadata
    )


def format_arguments_for_display(arguments: Dict[str, Any]) -> str:
    """
    Formate les arguments d'un outil pour l'affichage dans Gradio.
    
    Args:
        arguments: Arguments de l'outil
        
    Returns:
        str: Arguments formatés pour l'affichage
    """
    
    if not arguments:
        return "*Aucun argument*"
    
    formatted_args = []
    
    for key, value in arguments.items():
        # Formatage spécial selon le type
        if isinstance(value, str):
            if len(value) > 100:
                formatted_value = f'"{value[:100]}..."'
            else:
                formatted_value = f'"{value}"'
        elif isinstance(value, (dict, list)):
            formatted_value = json.dumps(value, ensure_ascii=False, indent=2)
            if len(formatted_value) > 200:
                formatted_value = formatted_value[:200] + "..."
        else:
            formatted_value = str(value)
        
        formatted_args.append(f"- **{key}**: {formatted_value}")
    
    return "\n".join(formatted_args)


def format_result_for_display(result: Any) -> str:
    """
    Formate le résultat d'un outil pour l'affichage dans Gradio.
    
    Args:
        result: Résultat de l'outil
        
    Returns:
        str: Résultat formaté pour l'affichage
    """
    
    if result is None:
        return "*Aucun résultat*"
    
    # Formatage selon le type
    if isinstance(result, str):
        if len(result) > 500:
            return f"```\n{result[:500]}...\n```"
        else:
            return f"```\n{result}\n```"
    elif isinstance(result, (dict, list)):
        formatted_json = json.dumps(result, ensure_ascii=False, indent=2)
        if len(formatted_json) > 500:
            formatted_json = formatted_json[:500] + "..."
        return f"```json\n{formatted_json}\n```"
    else:
        result_str = str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "..."
        return f"```\n{result_str}\n```"


def create_tool_summary_message(tool_calls: List[Dict[str, Any]]) -> gr.ChatMessage:
    """
    Crée un message de résumé des appels d'outils.
    
    Args:
        tool_calls: Liste des appels d'outils avec leurs détails
        
    Returns:
        gr.ChatMessage: Message Gradio avec le résumé
    """
    
    if not tool_calls:
        return create_error_message("Aucun appel d'outil à résumer")
    
    content = f"**📊 Résumé des appels d'outils ({len(tool_calls)} appels)**\n\n"
    
    for i, tool_call in enumerate(tool_calls, 1):
        tool_name = tool_call.get("tool_name", "Inconnu")
        duration = tool_call.get("duration", 0)
        success = tool_call.get("success", True)
        
        status_emoji = "✅" if success else "❌"
        content += f"{i}. {status_emoji} **{tool_name}** ({duration:.3f}s)\n"
    
    metadata: MetadataDict = {
        "title": "📊 Résumé des outils",
        "id": f"summary_{datetime.now().strftime('%H%M%S')}",
        "status": "done"
    }
    
    return gr.ChatMessage(
        role="assistant",
        content=content,
        metadata=metadata
    )


def update_message_metadata(message: gr.ChatMessage, new_metadata: MetadataDict) -> gr.ChatMessage:
    """
    Met à jour les métadonnées d'un message Gradio.
    
    Args:
        message: Message Gradio existant
        new_metadata: Nouvelles métadonnées à ajouter/modifier
        
    Returns:
        gr.ChatMessage: Message avec métadonnées mises à jour
    """
    
    # Copier les métadonnées existantes
    current_metadata: MetadataDict = message.metadata.copy() if message.metadata else {}
    
    # Ajouter les nouvelles métadonnées
    current_metadata.update(new_metadata)
    
    # Créer un nouveau message avec les métadonnées mises à jour
    return gr.ChatMessage(
        role=message.role,
        content=message.content,
        metadata=current_metadata
    )


def log_gradio_message(message: gr.ChatMessage, context: str = "GRADIO") -> None:
    """
    Log un message Gradio pour le debugging.
    
    Args:
        message: Message Gradio à logger
        context: Contexte du message (pour le logging)
    """
    
    logger.debug(f"[{context}] Message: {message.role} - {message.metadata}")
    if isinstance(message.content, str) and len(message.content) < 200:
        logger.debug(f"[{context}] Content: {message.content}")
    else:
        logger.debug(f"[{context}] Content: {len(str(message.content))} caractères")


# Constantes utiles
TOOL_ICONS = {
    "search": "🔍",
    "database": "🗃️",
    "api": "🌐",
    "file": "📄",
    "calculation": "🧮",
    "default": "🛠️"
}


def get_tool_icon(tool_name: str) -> str:
    """
    Retourne l'icône appropriée pour un outil selon son nom.
    
    Args:
        tool_name: Nom de l'outil
        
    Returns:
        str: Emoji représentant l'outil
    """
    
    tool_name_lower = tool_name.lower()
    
    for category, icon in TOOL_ICONS.items():
        if category in tool_name_lower:
            return icon
    
    return TOOL_ICONS["default"] 