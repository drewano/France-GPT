"""
Utilitaires Gradio pour l'affichage des appels aux outils MCP.

Ce module contient des fonctions utilitaires pour créer des messages Gradio
avec des métadonnées appropriées pour afficher les appels aux outils MCP
de manière claire et informative.
"""

import gradio as gr
from typing import Dict, Any, Optional, Literal, NotRequired, TypedDict
import json
import logging
import uuid

# Configuration du logger
logger = logging.getLogger("datainclusion.agent")


# Types Gradio corrects selon la documentation
class MetadataDict(TypedDict):
    """Structure des métadonnées pour les messages Gradio ChatMessage."""

    title: NotRequired[str]
    id: NotRequired[int | str]
    parent_id: NotRequired[int | str]
    log: NotRequired[str]
    duration: NotRequired[float]
    status: NotRequired[Literal["pending", "done"]]


def get_friendly_tool_name(tool_name: str) -> str:
    """
    Convertit un nom d'outil technique en nom convivial.

    Args:
        tool_name: Nom technique de l'outil

    Returns:
        str: Nom convivial avec emoji
    """
    friendly_names = {
        "search_services": "🔍 Recherche de services",
        "get_service_details": "📋 Détails du service",
        "search_structures": "🏢 Recherche de structures",
        "get_structure_info": "🏢 Informations sur la structure",
        "weather_forecast": "🌤️ Prévisions météo",
        "get_location": "📍 Localisation",
        "calculate": "🧮 Calcul",
        "translate": "🌐 Traduction",
        "send_email": "📧 Envoi d'email",
        "web_search": "🔍 Recherche web",
        "file_manager": "📁 Gestionnaire de fichiers",
        "database_query": "💾 Requête base de données",
    }

    return friendly_names.get(tool_name, f"🛠️ {tool_name.replace('_', ' ').title()}")


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

    return gr.ChatMessage(role="assistant", content=content, metadata=metadata)


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
        title = f"❌ {friendly_name} - Erreur"
        content = "**❌ Erreur lors de l'exécution**\n\n"
    else:
        title = f"✅ {friendly_name} - Résultat"
        content = "**✅ Résultat obtenu**\n\n"

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

    return gr.ChatMessage(role="assistant", content=content, metadata=metadata)


def create_error_message(error_msg: str, title: str = "⚠️ Erreur") -> gr.ChatMessage:
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
        role="assistant", content=f"❌ {error_msg}", metadata=metadata
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
        # Formatage spécial selon le type et la clé
        if key == "code_commune" and isinstance(value, str):
            formatted_value = f"**{value}** (code postal/commune)"
        elif key == "thematiques" and isinstance(value, list):
            if value:
                formatted_value = f"**{', '.join(value)}**"
            else:
                formatted_value = "*Toutes les thématiques*"
        elif key == "query" and isinstance(value, str):
            formatted_value = f'*"{value}"*'
        elif isinstance(value, str):
            if len(value) > 100:
                formatted_value = f'"{value[:100]}..."'
            else:
                formatted_value = f'"{value}"'
        elif isinstance(value, (dict, list)):
            # Formatage JSON indenté amélioré
            formatted_json = json.dumps(value, ensure_ascii=False, indent=2)
            # Troncature à 200 caractères comme demandé
            if len(formatted_json) > 200:
                formatted_value = f"```json\n{formatted_json[:200]}...\n```"
            else:
                formatted_value = f"```json\n{formatted_json}\n```"
        else:
            formatted_value = str(value)

        # Noms d'arguments plus conviviaux
        friendly_key = {
            "code_commune": "📍 Localisation",
            "thematiques": "🏷️ Thématiques",
            "query": "🔍 Recherche",
            "location": "📍 Lieu",
            "date": "📅 Date",
            "limit": "📊 Limite",
            "offset": "⏭️ Décalage",
        }.get(key, key.replace("_", " ").title())

        formatted_args.append(f"- **{friendly_key}**: {formatted_value}")

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
        # Essayer de parser comme JSON pour améliorer l'affichage
        try:
            parsed = json.loads(result)
            return format_json_result(parsed)
        except (json.JSONDecodeError, ValueError):
            # Si ce n'est pas du JSON, afficher comme texte
            if len(result) > 500:
                return f"```\n{result[:500]}...\n```"
            else:
                return f"```\n{result}\n```"
    elif isinstance(result, (dict, list)):
        return format_json_result(result)
    else:
        result_str = str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "..."
        return f"```\n{result_str}\n```"


def format_json_result(data: Any) -> str:
    """
    Formate un résultat JSON de manière conviviale.

    Args:
        data: Données à formater

    Returns:
        str: Résultat formaté
    """
    if isinstance(data, dict):
        # Cas spécial pour les résultats de recherche de services
        if "items" in data and isinstance(data["items"], list):
            return format_services_result(data)
        # Autres cas de dictionnaires
        formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
        if len(formatted_json) > 500:
            formatted_json = formatted_json[:500] + "..."
        return f"```json\n{formatted_json}\n```"
    elif isinstance(data, list):
        # Liste de services ou d'éléments
        if len(data) > 0 and isinstance(data[0], dict):
            return format_services_list(data)
        else:
            formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
            if len(formatted_json) > 500:
                formatted_json = formatted_json[:500] + "..."
            return f"```json\n{formatted_json}\n```"
    else:
        return str(data)


def format_services_result(data: dict) -> str:
    """
    Formate spécifiquement les résultats de recherche de services.

    Args:
        data: Données de services avec structure {"items": [...]}

    Returns:
        str: Résultat formaté de manière conviviale
    """
    items = data.get("items", [])
    if not items:
        return "**Aucun service trouvé** 🔍"

    total = len(items)
    result = f"**{total} service(s) trouvé(s)** 🎯\n\n"

    for i, item in enumerate(items[:5]):  # Limiter à 5 résultats pour l'affichage
        service_name = item.get("nom", "Service sans nom")
        service_type = item.get("typologie", "Type non spécifié")

        result += f"**{i + 1}. {service_name}**\n"
        result += f"   • *Type*: {service_type}\n"

        if "adresse" in item:
            result += f"   • *Adresse*: {item['adresse']}\n"

        if "telephone" in item:
            result += f"   • *Téléphone*: {item['telephone']}\n"

        if "courriel" in item:
            result += f"   • *Email*: {item['courriel']}\n"

        result += "\n"

    if total > 5:
        result += f"... et {total - 5} autre(s) service(s) 📋"

    return result


def format_services_list(services: list) -> str:
    """
    Formate une liste de services.

    Args:
        services: Liste de services

    Returns:
        str: Services formatés
    """
    if not services:
        return "**Aucun service trouvé** 🔍"

    total = len(services)
    result = f"**{total} service(s) trouvé(s)** 🎯\n\n"

    for i, service in enumerate(services[:5]):  # Limiter à 5 résultats
        if isinstance(service, dict):
            service_name = service.get("nom", service.get("name", "Service sans nom"))
            result += f"**{i + 1}. {service_name}**\n"

            # Ajouter des détails si disponibles
            for key, value in service.items():
                if key not in ["nom", "name"] and value and len(str(value)) < 100:
                    friendly_key = {
                        "adresse": "📍 Adresse",
                        "telephone": "📞 Téléphone",
                        "courriel": "📧 Email",
                        "typologie": "🏷️ Type",
                    }.get(key, key.replace("_", " ").title())
                    result += f"   • *{friendly_key}*: {value}\n"
            result += "\n"
        else:
            result += f"**{i + 1}.** {service}\n"

    if total > 5:
        result += f"... et {total - 5} autre(s) service(s) 📋"

    return result


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
