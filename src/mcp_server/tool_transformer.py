"""
Module de transformation des outils MCP.

Ce module contient la classe ToolTransformer qui encapsule toute la logique pour transformer
et enrichir les outils MCP générés à partir de la spécification OpenAPI de l'API Data Inclusion.

La classe ToolTransformer permet de :
- Personnaliser les noms des outils pour une meilleure lisibilité
- Enrichir les descriptions des outils et de leurs paramètres
- Optimiser les schémas pour une meilleure compatibilité avec les LLMs
- Ajouter des tags pour l'organisation des outils

Le processus de transformation se déroule en plusieurs étapes :
1. Génération des outils de base par FastMCP avec callback de personnalisation
2. Transformation et enrichissement des outils
3. Remplacement des outils originaux par les versions transformées
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransform
from fastmcp.utilities.components import FastMCPComponent
from fastmcp.utilities.openapi import HTTPRoute

from .utils import find_route_by_id, clean_json_schema
from .services.legifrance.tool_definitions import LEGIFRANCE_TOOL_DEFINITIONS


@dataclass
class ToolTransformerConfig:
    """Configuration class for ToolTransformer to reduce argument count."""
    mcp_server: FastMCP
    http_routes: List[HTTPRoute]
    custom_tool_names: Dict[str, str]
    op_id_map: Dict[str, str]
    logger: logging.Logger


class ToolTransformer:
    """
    Classe responsable de la transformation et de l'enrichissement des outils MCP.

    Cette classe encapsule toute la logique de transformation des outils MCP générés
    automatiquement par FastMCP depuis la spécification OpenAPI, en les enrichissant
    avec des noms personnalisés, des descriptions améliorées et des métadonnées.
    """

    def __init__(self, config: ToolTransformerConfig):
        """
        Initialise le transformateur d'outils avec la configuration.

        Args:
            config: Configuration object containing all required parameters
        """
        self.mcp_server = config.mcp_server
        self.http_routes = config.http_routes
        self.custom_tool_names = config.custom_tool_names
        self.op_id_map = config.op_id_map
        self.logger = config.logger

    def discover_and_customize(
        self,
        route: HTTPRoute,
        component: FastMCPComponent,
    ):
        """
        Personnalise le composant pour les LLMs et découvre le nom de l'outil généré.

        Cette méthode combine la personnalisation des schémas pour les LLMs et la découverte
        du mapping entre les operation_ids OpenAPI et les noms d'outils générés par FastMCP.
        Elle est utilisée comme callback durant la génération automatique des outils.

        Args:
            route: La route HTTP OpenAPI contenant l'operation_id.
            component: Le composant FastMCP généré pour cette route.

        Note:
            Cette méthode modifie directement le dictionnaire op_id_map de l'instance
            pour stocker le mapping découvert entre operation_ids et noms d'outils.
        """
        # Appel de la fonction de nettoyage des schémas
        clean_json_schema(component, self.logger)

        # Découverte du nom de l'outil et stockage dans la map
        if (
            hasattr(route, "operation_id")
            and route.operation_id
            and hasattr(component, "name")
            and component.name
        ):
            self.op_id_map[route.operation_id] = component.name

    async def transform_tools(self) -> None:
        """
        Transforme et enregistre les outils MCP avec des noms personnalisés et des enrichissements.

        Cette méthode est le cœur du processus de transformation des outils MCP. Elle :

        1. Récupère les outils originaux générés par FastMCP
        2. Les enrichit avec des descriptions personnalisées et des métadonnées
        3. Ajoute des tags pour l'organisation des outils
        4. Enrichit les descriptions des paramètres à partir des spécifications OpenAPI
        5. Remplace les outils originaux par les versions transformées

        Le processus garantit qu'aucun outil en double n'existe et que les noms sont
        plus lisibles pour les LLMs tout en conservant toute la fonctionnalité originale.

        Raises:
            Exception: Si la transformation d'un outil échoue, l'erreur est loggée mais
                      le processus continue pour les autres outils.

        Note:
            Cette méthode est asynchrone car elle interagit avec l'API async du serveur MCP.
            Elle supprime les outils originaux après transformation pour éviter les doublons.
        """
        self.logger.info(
            "Applying advanced tool transformations using Tool.from_tool()..."
        )

        successful_renames = 0
        total_tools = len(self.custom_tool_names)

        for original_name, new_name in self.custom_tool_names.items():
            # Rechercher la route et le nom de l'outil
            route, mangled_tool_name = await self._find_route_and_tool_name(
                original_name
            )
            if route is None or mangled_tool_name is None:
                continue

            try:
                # Récupérer l'outil original
                original_tool = await self._get_original_tool(mangled_tool_name)
                if not original_tool:
                    continue

                # Process tool transformation
                transform_result = self._process_tool_transformation(route, new_name)               
                # Créer l'outil transformé
                transformed_tool = Tool.from_tool(
                    tool=original_tool,
                    name=new_name,
                    description=transform_result["description"],
                    transform_args=transform_result["arg_transforms"],
                    tags=transform_result["tags"],
                )

                # Remplacer l'outil original par le transformé
                self._replace_tool(original_tool, transformed_tool, mangled_tool_name)

                # Logging de succès
                successful_renames += 1
                enrichment_info = []

                if transform_result["description"]:
                    enrichment_info.append("description")
                if transform_result["param_count"] > 0:
                    enrichment_info.append(f"{transform_result['param_count']} param descriptions")
                if transform_result["tags"]:
                    enrichment_info.append(f"{len(transform_result['tags'])} tags")

                # Améliorer le message de log pour indiquer l'utilisation d'une définition détaillée
                enrichment_msg = ""
                if transform_result.get("detailed_definition", False):
                    enrichment_msg = " (enriched with detailed definition)"
                elif enrichment_info:
                    enrichment_msg = f" (enriched: {', '.join(enrichment_info)})"

                self.logger.info(
                    f"  ✓ Transformed tool: '{original_name}' -> '{new_name}'{enrichment_msg}"
                )

            except Exception as e:
                self.logger.error(
                    f"  ✗ Failed to transform tool '{original_name}' -> '{new_name}': {e}"
                )
                self.logger.debug(
                    f"    Exception details: {type(e).__name__}: {str(e)}"
                )

        await self._log_transformation_stats(successful_renames, total_tools)

    async def _find_route_and_tool_name(
        self, original_name: str
    ) -> tuple[HTTPRoute | None, str | None]:
        """
        Trouve la route OpenAPI et le nom de l'outil généré par FastMCP.

        Args:
            original_name: L'operation_id original de l'API OpenAPI

        Returns:
            Un tuple contenant la route OpenAPI et le nom de l'outil généré,
            ou (None, None) si non trouvé
        """
        # Rechercher la route correspondante dans les données OpenAPI
        route = await find_route_by_id(original_name, self.http_routes)
        if route is None:
            self.logger.warning(
                f"  ✗ Route not found for operation_id: '{original_name}' - skipping transformation"
            )
            return None, None

        # Utilise la map pour obtenir le nom de l'outil généré par FastMCP
        mangled_tool_name = self.op_id_map.get(original_name)
        if not mangled_tool_name:
            self.logger.warning(
                f"  ✗ Could not find a generated tool for operation_id: "
                f"'{original_name}' - skipping transformation"
            )
            return None, None

        return route, mangled_tool_name

    async def _get_original_tool(self, mangled_tool_name: str) -> Tool | None:
        """
        Récupère l'outil original à partir de son nom généré par FastMCP.

        Args:
            mangled_tool_name: Le nom de l'outil généré par FastMCP

        Returns:
            L'outil original ou None si non trouvé
        """
        original_tool = await self.mcp_server.get_tool(mangled_tool_name)
        if not original_tool:
            self.logger.warning(
                f"  ✗ Tool not found: '{mangled_tool_name}' "
                f"(may have been renamed during OpenAPI processing)"
            )
            return None

        return original_tool

    def _enrich_arguments(
        self, route: HTTPRoute
    ) -> tuple[dict[str, ArgTransform], int]:
        """
        Enrichit les arguments d'un outil avec des descriptions depuis l'OpenAPI.

        Args:
            route: La route OpenAPI contenant les paramètres

        Returns:
            Un tuple contenant le dictionnaire des transformations d'arguments
            et le nombre de paramètres enrichis
        """
        arg_transforms = {}
        param_count = 0

        # Enrichir les descriptions des paramètres depuis l'OpenAPI
        if hasattr(route, "parameters") and route.parameters:
            for param in route.parameters:
                if hasattr(param, "name") and param.name:
                    transforms = {}

                    # Ajouter une description si disponible
                    if (
                        hasattr(param, "description")
                        and param.description
                        and param.description.strip()
                    ):
                        transforms["description"] = param.description.strip()
                        param_count += 1

                    # Note: L'attribut 'example' n'est pas disponible sur ParameterInfo
                    # Les exemples peuvent être ajoutés via d'autres moyens si nécessaire

                    # Créer l'ArgTransform seulement s'il y a des transformations
                    if transforms:
                        arg_transforms[param.name] = ArgTransform(**transforms)
                        self.logger.debug(
                            f"    - Enriching parameter '{param.name}': {list(transforms.keys())}"
                        )

        return arg_transforms, param_count

    def _create_tool_description(self, route: HTTPRoute, new_name: str) -> str:
        """
        Crée une description enrichie pour l'outil à partir de la route OpenAPI.

        Args:
            route: La route OpenAPI contenant les descriptions
            new_name: Le nouveau nom de l'outil

        Returns:
            La description enrichie de l'outil
        """
        if (
            hasattr(route, "description")
            and route.description
            and route.description.strip()
        ):
            return route.description.strip()
        if hasattr(route, "summary") and route.summary and route.summary.strip():
            # Fallback vers le summary si pas de description
            return route.summary.strip()
        # Description par défaut basée sur le nom de l'outil
        return f"Execute the {new_name} operation on the Data Inclusion API"

    def _process_tool_transformation(self, route: HTTPRoute, new_name: str) -> dict:
        """
        Process tool transformation and return all necessary components.

        Args:
            route: The HTTP route for the tool
            new_name: The new name for the tool

        Returns:
            Dictionary containing description, arg_transforms, tags, and param_count
        """
        # Vérifier si une définition détaillée existe pour cet outil
        if new_name in LEGIFRANCE_TOOL_DEFINITIONS:
            # Utiliser la définition détaillée pour les outils Légifrance
            definition = LEGIFRANCE_TOOL_DEFINITIONS[new_name]
            
            # Utiliser la description de la définition détaillée
            tool_description = definition["description"]
            
            # Construire le dictionnaire arg_transforms à partir de la définition
            arg_transforms = {}
            param_count = 0
            
            for arg_name, arg_info in definition["arguments"].items():
                # Créer une instance de ArgTransform avec les valeurs de la définition
                transforms = {}
                
                if "description" in arg_info:
                    transforms["description"] = arg_info["description"]
                    
                if "hide" in arg_info:
                    transforms["hide"] = arg_info["hide"]
                    
                if "name" in arg_info:
                    transforms["name"] = arg_info["name"]
                    
                if transforms:
                    arg_transforms[arg_name] = ArgTransform(**transforms)
                    param_count += 1
                    
            # Créer les tags pour l'organisation
            tool_tags = self._create_tool_tags(new_name)
            
            return {
                "description": tool_description,
                "arg_transforms": arg_transforms,
                "tags": tool_tags,
                "param_count": param_count,
                "detailed_definition": True  # Indicateur pour le logging
            }
        else:
            # Conserver la logique existante (générique) comme fallback
            # Enrichir les arguments avec des descriptions
            arg_transforms, param_count = self._enrich_arguments(route)

            # Créer la description enrichie
            tool_description = self._create_tool_description(route, new_name)

            # Créer les tags pour l'organisation
            tool_tags = self._create_tool_tags(new_name)
            
            return {
                "description": tool_description,
                "arg_transforms": arg_transforms,
                "tags": tool_tags,
                "param_count": param_count,
                "detailed_definition": False  # Indicateur pour le logging
            }

    def _create_tool_tags(self, new_name: str) -> set[str]:
        """
        Crée les tags pour l'organisation des outils.

        Args:
            new_name: Le nouveau nom de l'outil

        Returns:
            Un ensemble de tags pour l'outil
        """
        tool_tags = {"data-inclusion", "api"}

        # Ajouter des tags spécifiques selon le type d'endpoint
        if "list_all" in new_name or "search" in new_name:
            tool_tags.add("listing")
        if "get_" in new_name and "details" in new_name:
            tool_tags.add("details")
        if "doc_" in new_name:
            tool_tags.add("documentation")
        if any(
            endpoint in new_name for endpoint in ["structures", "services", "sources"]
        ):
            tool_tags.add("core-data")

        return tool_tags

    def _replace_tool(
        self, original_tool: Tool, transformed_tool: Tool, mangled_tool_name: str
    ) -> None:
        """
        Remplace l'outil original par l'outil transformé.

        Args:
            original_tool: L'outil original à supprimer
            transformed_tool: L'outil transformé à ajouter
            mangled_tool_name: Le nom de l'outil original généré par FastMCP
        """
        # Ajouter le nouvel outil au serveur
        self.mcp_server.add_tool(transformed_tool)

        # IMPORTANT: Supprimer l'outil original pour éviter les doublons
        # et la confusion pour le LLM
        try:
            self.mcp_server.remove_tool(mangled_tool_name)
            self.logger.debug(f"    - Removed original tool: '{mangled_tool_name}'")
        except Exception as remove_error:
            # En cas d'échec de suppression, désactiver au moins l'outil
            self.logger.debug(
                f"    - Could not remove '{mangled_tool_name}', disabling instead: {remove_error}"
            )
            original_tool.disable()

    async def _log_transformation_stats(
        self, successful_renames: int, total_tools: int
    ) -> None:
        """
        Enregistre les statistiques de transformation et les informations de debug.

        Args:
            successful_renames: Nombre de transformations réussies
            total_tools: Nombre total d'outils à transformer
        """
        # === RÉSUMÉ FINAL ===
        if successful_renames > 0:
            self.logger.info(
                f"✓ Tool transformation completed: {successful_renames}/{total_tools} "
                f"tools successfully transformed"
            )
        else:
            self.logger.warning(
                f"⚠️  No tools were successfully transformed out of {total_tools} attempted"
            )

        # Vérifier que nous avons encore des outils après transformation
        final_tools = await self.mcp_server.get_tools()
        enabled_tools = [name for name, tool in final_tools.items() if tool.enabled]
        self.logger.info(
            f"📊 Final tool count: {len(enabled_tools)} enabled tools available"
        )

        # === DEBUG: AFFICHER LES OPERATION_IDS DISPONIBLES ===
        # Afficher les operation_ids non mappés pour aider au debug
        self.logger.info("=== OpenAPI Route Analysis ===")
        available_ops = [
            route.operation_id
            for route in self.http_routes
            if hasattr(route, "operation_id") and route.operation_id
        ]
        unmapped_ops = [
            op_id for op_id in available_ops if op_id not in self.custom_tool_names
        ]

        self.logger.info(f"Total OpenAPI routes: {len(available_ops)}")
        self.logger.info(f"Mapped routes: {len(self.custom_tool_names)}")
        self.logger.info(f"Unmapped routes: {len(unmapped_ops)}")

        if unmapped_ops:
            self.logger.info(
                "⚠️  Unmapped operation_ids (should be added to custom_mcp_tool_names):"
            )
            for op_id in sorted(unmapped_ops):
                self.logger.info(f"  - '{op_id}'")
