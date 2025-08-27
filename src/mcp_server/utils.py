"""
Utility functions for the MCP server.
"""

import logging
import functools
from fastmcp.utilities.openapi import HTTPRoute
from pydantic_ai import ModelRetry


def deep_clean_schema(schema: dict) -> None:
    """Nettoie récursivement un schéma JSON en supprimant tous les champs "title".

    Cette fonction parcourt récursivement un dictionnaire représentant un schéma JSON
    et supprime toutes les clés "title" trouvées, y compris dans les dictionnaires
    imbriqués et les listes de dictionnaires.

    Args:
        schema: Dictionnaire représentant un schéma JSON à nettoyer

    Note:
        Cette fonction modifie le dictionnaire en place et ne retourne rien.
    """
    if not isinstance(schema, dict):
        return

    # Collecter les clés "title" à supprimer pour éviter de modifier
    # le dictionnaire pendant l'itération
    keys_to_remove = []

    for key, value in schema.items():
        if key == "title":
            keys_to_remove.append(key)
        elif isinstance(value, dict):
            # Nettoyer récursivement les dictionnaires imbriqués
            deep_clean_schema(value)
        elif isinstance(value, list):
            # Nettoyer récursivement les éléments de liste qui sont des dictionnaires
            for item in value:
                if isinstance(item, dict):
                    deep_clean_schema(item)

    # Supprimer toutes les clés "title" collectées
    for key in keys_to_remove:
        del schema[key]


async def find_route_by_id(
    operation_id: str, routes: list[HTTPRoute]
) -> HTTPRoute | None:
    """
    Recherche un objet HTTPRoute par son operation_id.

    Cette fonction parcourt une liste d'objets HTTPRoute et retourne le premier
    objet dont l'attribut operation_id correspond à l'operation_id fourni.

    Args:
        operation_id: L'identifiant d'opération à rechercher
        routes: La liste des objets HTTPRoute à parcourir

    Returns:
        HTTPRoute | None: L'objet HTTPRoute correspondant ou None si aucune "
        "correspondance n'est trouvée
    """
    for route in routes:
        if hasattr(route, "operation_id") and route.operation_id == operation_id:
            return route
    return None


def api_call_handler(func):
    """Décorateur pour la gestion centralisée des appels API, du logging et des erreurs."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Note: Specific exception handling should be done in the service modules
            # This is a generic fallback
            raise ModelRetry(f"Erreur lors de l'appel à l'API {tool_name}: {e}") from e

    return wrapper


def clean_json_schema(component, logger: logging.Logger):
    """
    Simplifie les schémas d'un composant pour une meilleure compatibilité avec les LLMs stricts.

    Cette fonction nettoie les schémas JSON des outils MCP en supprimant les titres et autres
    éléments qui peuvent causer des problèmes avec certains modèles de langage.
    Elle utilise la fonction `deep_clean_schema` pour s'assurer que les schémas sont
    compatibles avec les spécifications strictes des LLMs.

    Args:
        component: Le composant FastMCP à personnaliser.
        logger: Instance du logger pour enregistrer les opérations de nettoyage.

    Note:
        Cette fonction modifie directement les schémas du composant (modification in-place).
        Elle nettoie à la fois les schémas d'entrée et de sortie s'ils existent.
    """
    tool_name = getattr(component, "name", "Unknown")
    cleaned_schemas = []

    # Nettoyer le schéma d'entrée
    if hasattr(component, "input_schema") and component.input_schema:
        deep_clean_schema(component.input_schema)
        cleaned_schemas.append("input schema")
        logger.info(f"Input schema cleaned for tool: {tool_name}")

    # Nettoyer le schéma de sortie
    if hasattr(component, "output_schema") and component.output_schema:
        deep_clean_schema(component.output_schema)
        cleaned_schemas.append("output schema")
        logger.info(f"Output schema cleaned for tool: {tool_name}")

    # Message de résumé si des schémas ont été nettoyés
    if cleaned_schemas:
        logger.info(
            f"Schema cleaning completed for tool '{tool_name}': {', '.join(cleaned_schemas)}"
        )
    else:
        logger.debug(f"No schemas found to clean for tool: {tool_name}")
