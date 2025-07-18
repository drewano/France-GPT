"""
Module de formatage des données pour l'affichage dans l'interface Gradio.

Ce module contient toutes les fonctions responsables de la mise en forme
des données pour l'affichage convivial dans l'interface utilisateur.
"""

import json
from typing import Dict, Any, Final


class Emojis:
    """Emoji constants for consistent visual representation."""

    SETTINGS: Final[str] = "⚙️"
    FOLDER: Final[str] = "📁"


class ToolNames:
    """Standardized tool names for MCP operations."""

    FRIENDLY_NAMES: Final[dict[str, str]] = {
        "search_structures": "Recherche de structures",
        "get_structure_details": "Détails d'une structure",
        "search_services": "Recherche de services",
        "get_service_details": "Détails d'un service",
        "get_cities": "Liste des villes",
        "get_departments": "Liste des départements",
        "get_categories": "Liste des catégories",
    }


class DefaultValues:
    """Default values for UI display."""

    AUTRES_SERVICES_PLURAL: Final[str] = "autres services"


def get_friendly_tool_name(tool_name: str) -> str:
    """
    Convertit un nom d'outil technique en nom convivial.

    Args:
        tool_name: Nom technique de l'outil

    Returns:
        str: Nom convivial avec emoji
    """
    return ToolNames.FRIENDLY_NAMES.get(
        tool_name, f"{Emojis.SETTINGS} {tool_name.replace('_', ' ').title()}"
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
        result += (
            f"... et {total - 5} {DefaultValues.AUTRES_SERVICES_PLURAL} {Emojis.FOLDER}"
        )

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
        result += (
            f"... et {total - 5} {DefaultValues.AUTRES_SERVICES_PLURAL} {Emojis.FOLDER}"
        )

    return result
