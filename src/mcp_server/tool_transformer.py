"""
Module de transformation des outils MCP.

Ce module contient la logique pour transformer et enrichir les outils MCP générés à partir 
de la spécification OpenAPI de l'API Data Inclusion. Il permet de :

- Personnaliser les noms des outils pour une meilleure lisibilité
- Enrichir les descriptions des outils et de leurs paramètres
- Optimiser les schémas pour une meilleure compatibilité avec les LLMs
- Limiter les paramètres de pagination pour éviter les surcharges
- Ajouter des tags pour l'organisation des outils

Le processus de transformation se déroule en plusieurs étapes :
1. Modification de la spécification OpenAPI pour limiter les tailles de page
2. Génération des outils de base par FastMCP
3. Personnalisation et enrichissement des outils
4. Remplacement des outils originaux par les versions transformées
"""

import logging
from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransform
from fastmcp.utilities.components import FastMCPComponent
from fastmcp.utilities.openapi import HTTPRoute

from .utils import deep_clean_schema, find_route_by_id


def limit_page_size_in_spec(spec: dict, logger: logging.Logger, max_size: int = 25) -> dict:
    """
    Modifie la spécification OpenAPI pour limiter la taille des pages.

    Cette fonction parcourt les points de terminaison pertinents et ajuste le paramètre
    'size' pour qu'il ait une valeur maximale et par défaut de `max_size`. Cela permet
    d'éviter que les LLMs demandent des résultats trop volumineux qui pourraient 
    dépasser les limites de contexte ou ralentir les réponses.

    Args:
        spec: Le dictionnaire de la spécification OpenAPI à modifier.
        logger: Instance du logger pour enregistrer les modifications effectuées.
        max_size: La taille maximale à définir pour les résultats paginés (défaut: 25).

    Returns:
        dict: Le dictionnaire de la spécification modifié avec les limites de page appliquées.
    """
    paths_to_modify = [
        "/api/v0/structures",
        "/api/v0/services",
        "/api/v0/search/services",
    ]

    logger.info(f"Applying page size limit (max_size={max_size}) to spec...")

    for path in paths_to_modify:
        if path in spec["paths"] and "get" in spec["paths"][path]:
            params = spec["paths"][path]["get"].get("parameters", [])
            for param in params:
                if param.get("name") == "size":
                    param["schema"]["maximum"] = max_size
                    param["schema"]["default"] = max_size
                    logger.info(f"  - Limited 'size' parameter for endpoint: GET {path}")
    
    return spec


def customize_for_gemini(route, component, logger: logging.Logger):
    """
    Simplifie les schémas d'un composant pour une meilleure compatibilité avec les LLMs stricts.
    
    Cette fonction nettoie les schémas JSON des outils MCP en supprimant les titres et autres
    éléments qui peuvent causer des problèmes avec certains modèles de langage comme Gemini.
    Elle utilise la fonction `deep_clean_schema` pour s'assurer que les schémas sont 
    compatibles avec les spécifications strictes des LLMs.
    
    Args:
        route: La route HTTP OpenAPI associée à l'outil.
        component: Le composant FastMCP à personnaliser.
        logger: Instance du logger pour enregistrer les opérations de nettoyage.
    
    Note:
        Cette fonction modifie directement les schémas du composant (modification in-place).
        Elle nettoie à la fois les schémas d'entrée et de sortie s'ils existent.
    """
    tool_name = getattr(component, 'name', 'Unknown')
    cleaned_schemas = []
    
    # Nettoyer le schéma d'entrée
    if hasattr(component, 'input_schema') and component.input_schema:
        deep_clean_schema(component.input_schema)
        cleaned_schemas.append("input schema")
        logger.info(f"Input schema cleaned for tool: {tool_name}")
    
    # Nettoyer le schéma de sortie
    if hasattr(component, 'output_schema') and component.output_schema:
        deep_clean_schema(component.output_schema)
        cleaned_schemas.append("output schema")
        logger.info(f"Output schema cleaned for tool: {tool_name}")
    
    # Message de résumé si des schémas ont été nettoyés
    if cleaned_schemas:
        logger.info(f"Schema cleaning completed for tool '{tool_name}': {', '.join(cleaned_schemas)}")
    else:
        logger.debug(f"No schemas found to clean for tool: {tool_name}")


def discover_and_customize(route: HTTPRoute, component: FastMCPComponent, logger: logging.Logger, op_id_map: dict[str, str]):
    """
    Personnalise le composant pour Gemini et découvre le nom de l'outil généré.
    
    Cette fonction combine la personnalisation des schémas pour les LLMs et la découverte
    du mapping entre les operation_ids OpenAPI et les noms d'outils générés par FastMCP.
    Elle est utilisée comme callback durant la génération automatique des outils.
    
    Args:
        route: La route HTTP OpenAPI contenant l'operation_id.
        component: Le composant FastMCP généré pour cette route.
        logger: Instance du logger pour enregistrer les opérations.
        op_id_map: Dictionnaire qui sera rempli avec le mapping operation_id -> nom d'outil.
    
    Note:
        Cette fonction modifie directement le dictionnaire op_id_map passé en paramètre
        pour stocker le mapping découvert entre operation_ids et noms d'outils.
    """
    # Appel de la fonction de personnalisation existante
    customize_for_gemini(route, component, logger)
    
    # Découverte du nom de l'outil et stockage dans la map
    if hasattr(route, 'operation_id') and route.operation_id and hasattr(component, 'name') and component.name:
        op_id_map[route.operation_id] = component.name


async def transform_and_register_tools(
    mcp_server: FastMCP,
    http_routes: list[HTTPRoute],
    custom_tool_names: dict[str, str],
    op_id_map: dict[str, str],
    logger: logging.Logger
) -> None:
    """
    Transforme et enregistre les outils MCP avec des noms personnalisés et des enrichissements.
    
    Cette fonction est le cœur du processus de transformation des outils MCP. Elle :
    
    1. Récupère les outils originaux générés par FastMCP
    2. Les enrichit avec des descriptions personnalisées et des métadonnées
    3. Ajoute des tags pour l'organisation des outils
    4. Enrichit les descriptions des paramètres à partir des spécifications OpenAPI
    5. Remplace les outils originaux par les versions transformées
    
    Le processus garantit qu'aucun outil en double n'existe et que les noms sont 
    plus lisibles pour les LLMs tout en conservant toute la fonctionnalité originale.
    
    Args:
        mcp_server: Instance du serveur MCP où les outils seront enregistrés.
        http_routes: Liste des routes HTTP OpenAPI pour l'enrichissement des descriptions.
        custom_tool_names: Mapping des operation_ids vers les noms d'outils personnalisés.
        op_id_map: Mapping des operation_ids vers les noms d'outils générés par FastMCP.
        logger: Instance du logger pour enregistrer le processus de transformation.
    
    Returns:
        None: La fonction modifie directement le serveur MCP en place.
    
    Raises:
        Exception: Si la transformation d'un outil échoue, l'erreur est loggée mais 
                  le processus continue pour les autres outils.
    
    Note:
        Cette fonction est asynchrone car elle interagit avec l'API async du serveur MCP.
        Elle supprime les outils originaux après transformation pour éviter les doublons.
    """
    logger.info("Applying advanced tool transformations using Tool.from_tool()...")
    
    successful_renames = 0
    total_tools = len(custom_tool_names)
    
    for original_name, new_name in custom_tool_names.items():
        # Rechercher la route correspondante dans les données OpenAPI
        route = await find_route_by_id(original_name, http_routes)
        if route is None:
            logger.warning(f"  ✗ Route not found for operation_id: '{original_name}' - skipping transformation")
            continue
        
        # Utilise la map pour obtenir le nom de l'outil généré par FastMCP
        mangled_tool_name = op_id_map.get(original_name)
        if not mangled_tool_name:
            logger.warning(f"  ✗ Could not find a generated tool for operation_id: '{original_name}' - skipping transformation")
            continue
        
        try:
            # Récupérer l'outil original en utilisant son nom "manglé"
            original_tool = await mcp_server.get_tool(mangled_tool_name)
            if not original_tool:
                logger.warning(f"  ✗ Tool not found: '{mangled_tool_name}' (may have been renamed during OpenAPI processing)")
                continue
            
            # === ENRICHISSEMENT DES ARGUMENTS ===
            arg_transforms = {}
            param_count = 0
            
            # Enrichir les descriptions des paramètres depuis l'OpenAPI
            if hasattr(route, 'parameters') and route.parameters:
                for param in route.parameters:
                    if hasattr(param, 'name') and param.name:
                        transforms = {}
                        
                        # Ajouter une description si disponible
                        if hasattr(param, 'description') and param.description and param.description.strip():
                            transforms['description'] = param.description.strip()
                            param_count += 1
                        
                        # Note: L'attribut 'example' n'est pas disponible sur ParameterInfo
                        # Les exemples peuvent être ajoutés via d'autres moyens si nécessaire
                        
                        # Créer l'ArgTransform seulement s'il y a des transformations
                        if transforms:
                            arg_transforms[param.name] = ArgTransform(**transforms)
                            logger.debug(f"    - Enriching parameter '{param.name}': {list(transforms.keys())}")
            
            # === CRÉATION DE LA DESCRIPTION ENRICHIE ===
            tool_description = None
            if hasattr(route, 'description') and route.description and route.description.strip():
                tool_description = route.description.strip()
            elif hasattr(route, 'summary') and route.summary and route.summary.strip():
                # Fallback vers le summary si pas de description
                tool_description = route.summary.strip()
            else:
                # Description par défaut basée sur le nom de l'outil
                tool_description = f"Execute the {new_name} operation on the Data Inclusion API"
            
            # === AJOUT DE TAGS POUR ORGANISATION ===
            tool_tags = {"data-inclusion", "api"}
            
            # Ajouter des tags spécifiques selon le type d'endpoint
            if "list_all" in new_name or "search" in new_name:
                tool_tags.add("listing")
            if "get_" in new_name and "details" in new_name:
                tool_tags.add("details")
            if "doc_" in new_name:
                tool_tags.add("documentation")
            if any(endpoint in new_name for endpoint in ["structures", "services", "sources"]):
                tool_tags.add("core-data")
            
            # === CRÉATION DU NOUVEL OUTIL TRANSFORMÉ ===
            transformed_tool = Tool.from_tool(
                tool=original_tool,
                name=new_name,
                description=tool_description,
                transform_args=arg_transforms if arg_transforms else None,
                tags=tool_tags
            )
            
            # === AJOUT ET SUPPRESSION ===
            # Ajouter le nouvel outil au serveur
            mcp_server.add_tool(transformed_tool)
            
            # IMPORTANT: Supprimer l'outil original pour éviter les doublons
            # et la confusion pour le LLM
            try:
                mcp_server.remove_tool(mangled_tool_name)
                logger.debug(f"    - Removed original tool: '{mangled_tool_name}'")
            except Exception as remove_error:
                # En cas d'échec de suppression, désactiver au moins l'outil
                logger.debug(f"    - Could not remove '{mangled_tool_name}', disabling instead: {remove_error}")
                original_tool.disable()
            
            # === LOGGING DE SUCCÈS ===
            successful_renames += 1
            enrichment_info = []
            
            if tool_description:
                enrichment_info.append("description")
            if param_count > 0:
                enrichment_info.append(f"{param_count} param descriptions")
            if tool_tags:
                enrichment_info.append(f"{len(tool_tags)} tags")
            
            enrichment_msg = f" (enriched: {', '.join(enrichment_info)})" if enrichment_info else ""
            logger.info(f"  ✓ Transformed tool: '{original_name}' -> '{new_name}'{enrichment_msg}")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to transform tool '{original_name}' -> '{new_name}': {e}")
            logger.debug(f"    Exception details: {type(e).__name__}: {str(e)}")
    
    # === RÉSUMÉ FINAL ===
    if successful_renames > 0:
        logger.info(f"✓ Tool transformation completed: {successful_renames}/{total_tools} tools successfully transformed")
    else:
        logger.warning(f"⚠️  No tools were successfully transformed out of {total_tools} attempted")
    
    # Vérifier que nous avons encore des outils après transformation
    final_tools = await mcp_server.get_tools()
    enabled_tools = [name for name, tool in final_tools.items() if tool.enabled]
    logger.info(f"📊 Final tool count: {len(enabled_tools)} enabled tools available")
    
    # === DEBUG: AFFICHER LES OPERATION_IDS DISPONIBLES ===
    # Afficher les operation_ids non mappés pour aider au debug
    logger.info("=== OpenAPI Route Analysis ===")
    available_ops = [route.operation_id for route in http_routes if hasattr(route, 'operation_id') and route.operation_id]
    unmapped_ops = [op_id for op_id in available_ops if op_id not in custom_tool_names]
    
    logger.info(f"Total OpenAPI routes: {len(available_ops)}")
    logger.info(f"Mapped routes: {len(custom_tool_names)}")
    logger.info(f"Unmapped routes: {len(unmapped_ops)}")
    
    if unmapped_ops:
        logger.info("⚠️  Unmapped operation_ids (should be added to custom_mcp_tool_names):")
        for op_id in sorted(unmapped_ops):
            logger.info(f"  - '{op_id}'") 