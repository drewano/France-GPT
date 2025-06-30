"""
DataInclusion MCP Server

Ce serveur MCP expose l'API data.inclusion.beta.gouv.fr via le protocole Model Context Protocol.
Il transforme automatiquement les endpoints OpenAPI en outils MCP.
"""

import asyncio
import json
import logging
import os
import httpx
from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp.server.openapi import RouteMap, MCPType
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.bearer import RSAKeyPair
from .config import Settings
from .utils import inspect_mcp_components, create_api_client
from .logging_config import setup_logging
from .middleware import ErrorHandlingMiddleware, TimingMiddleware

def limit_page_size_in_spec(spec: dict, logger: logging.Logger, max_size: int = 25) -> dict:
    """
    Modifie la spécification OpenAPI pour limiter la taille des pages.

    Cette fonction parcourt les points de terminaison pertinents et ajuste le paramètre
    'size' pour qu'il ait une valeur maximale et par défaut de `max_size`.

    Args:
        spec: Le dictionnaire de la spécification OpenAPI.
        logger: Instance du logger pour les messages.
        max_size: La taille maximale à définir pour les résultats.

    Returns:
        Le dictionnaire de la spécification modifié.
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


async def main():
    """
    Fonction principale qui configure et lance le serveur MCP.
    
    Cette fonction :
    1. Charge la configuration
    2. Charge la spécification OpenAPI
    3. Crée un client HTTP authentifié
    4. Configure le serveur MCP avec des noms d'outils personnalisés
    5. Lance le serveur avec le transport SSE
    """
    
    # === 0. CHARGEMENT DE LA CONFIGURATION ===
    settings = Settings()
    
    # === 1. CONFIGURATION DU LOGGING ===
    logger = setup_logging()
    
    api_client = None
    
    try:
        # === 2. CHARGEMENT DE LA SPÉCIFICATION OPENAPI VIA HTTP ===
        logger.info(f"Loading OpenAPI specification from URL: '{settings.OPENAPI_URL}'...")
        
        try:
            # On a besoin d'importer httpx si ce n'est pas déjà fait en haut du fichier
            
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.OPENAPI_URL)
                response.raise_for_status()  # Lève une exception si le statut n'est pas 2xx
                openapi_spec = response.json()
            
            api_title = openapi_spec.get("info", {}).get("title", "Unknown API")
            logger.info(f"Successfully loaded OpenAPI spec: '{api_title}'")
            
            # === MODIFICATION DES LIMITES DE PAGINATION ===
            # Limite la taille des pages pour les outils de listing à 25 éléments maximum
            # Cela s'applique aux outils: list_all_structures, list_all_services, search_services
            logger.info("Applying pagination limits to data-listing endpoints...")
            openapi_spec = limit_page_size_in_spec(openapi_spec, logger=logger, max_size=25)
            
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch OpenAPI specification from '{settings.OPENAPI_URL}'.")
            logger.error(f"Details: {e}")
            return
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in the response from '{settings.OPENAPI_URL}'.")
            logger.error(f"Details: {e}")
            return

        # === 3. DÉTERMINATION DE L'URL DE BASE ===
        servers = openapi_spec.get("servers", [])
        if servers and isinstance(servers, list) and len(servers) > 0 and "url" in servers[0]:
            base_url = servers[0]["url"]
            logger.info(f"Using base URL from OpenAPI spec: {base_url}")
        else:
            base_url = "http://localhost:8000"
            logger.warning("No servers section found in OpenAPI spec.")
            logger.warning(f"Using default base URL: {base_url}")

        # === 4. CRÉATION DU CLIENT HTTP AUTHENTIFIÉ ===
        logger.info("Configuring HTTP client with authentication...")
        api_client = create_api_client(base_url, logger, settings.DATA_INCLUSION_API_KEY)

        # === 5. CONFIGURATION DES NOMS D'OUTILS PERSONNALISÉS ===
        logger.info("Configuring custom tool names...")
        
        # Mapping des noms d'opérations OpenAPI vers des noms d'outils MCP plus conviviaux
        custom_mcp_tool_names = {
            # Endpoints de Structures
            "list_structures_endpoint_api_v0_structures_get": "list_all_structures",
            "retrieve_structure_endpoint_api_v0_structures__source___id__get": "get_structure_details",

            # Endpoints de Sources
            "list_sources_endpoint_api_v0_sources_get": "list_all_sources",

            # Endpoints de Services
            "list_services_endpoint_api_v0_services_get": "list_all_services",
            "retrieve_service_endpoint_api_v0_services__source___id__get": "get_service_details",
            "search_services_endpoint_api_v0_search_services_get": "search_services",

            # Endpoints de Documentation (ceux-ci fonctionnent maintenant)
            "as_dict_list_api_v0_doc_labels_nationaux_get": "doc_list_labels_nationaux",
            "as_dict_list_api_v0_doc_thematiques_get": "doc_list_thematiques",
            "as_dict_list_api_v0_doc_typologies_services_get": "doc_list_typologies_services",
            "as_dict_list_api_v0_doc_frais_get": "doc_list_frais",
            "as_dict_list_api_v0_doc_profils_get": "doc_list_profils_publics",
            "as_dict_list_api_v0_doc_typologies_structures_get": "doc_list_typologies_structures",
            "as_dict_list_api_v0_doc_modes_accueil_get": "doc_list_modes_accueil",
            "as_dict_list_api_v0_doc_modes_orientation_accompagnateur_get": "doc_list_modes_orientation_accompagnateur",
            "as_dict_list_api_v0_doc_modes_orientation_beneficiaire_get": "doc_list_modes_orientation_beneficiaire"
        }

        # === 6. CONFIGURATION DES ROUTES MCP ===
        logger.info("Configuring route mappings...")
        
        # Configuration pour mapper tous les endpoints GET comme des outils MCP
        custom_route_maps = [
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.TOOL),
        ]

        # === 7. CONFIGURATION DE L'AUTHENTIFICATION ===
        logger.info("Configuring server authentication...")
        
        # Lecture de la clé secrète depuis la configuration
        secret_key = settings.MCP_SERVER_SECRET_KEY
        auth_provider = None
        
        if secret_key and secret_key.strip():
            logger.info("Secret key found - configuring Bearer Token authentication...")
            try:
                # Si la clé ressemble à une clé RSA privée PEM, l'utiliser directement
                if secret_key.strip().startswith("-----BEGIN") and "PRIVATE KEY" in secret_key:
                    # Utiliser la clé privée pour créer une paire de clés
                    from cryptography.hazmat.primitives import serialization
                    private_key = serialization.load_pem_private_key(
                        secret_key.encode(), password=None
                    )
                    public_key_pem = private_key.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ).decode()
                    
                    auth_provider = BearerAuthProvider(
                        public_key=public_key_pem,
                        audience="datainclusion-mcp-client"
                    )
                else:
                    # Utiliser la clé comme seed pour générer une paire de clés déterministe
                    # Pour des raisons de simplicité, on génère une nouvelle paire de clés
                    key_pair = RSAKeyPair.generate()
                    
                    auth_provider = BearerAuthProvider(
                        public_key=key_pair.public_key,
                        audience="datainclusion-mcp-client"
                    )
                    
                    # Log du token de test (UNIQUEMENT pour le développement)
                    test_token = key_pair.create_token(
                        audience="datainclusion-mcp-client",
                        subject="test-user",
                        expires_in_seconds=3600
                    )
                    logger.info(f"🔑 Test Bearer Token (for development): {test_token}")
                
                logger.info("✓ Bearer Token authentication configured successfully")
                logger.info("   - Audience: datainclusion-mcp-client")
                logger.info("   - Server will require valid Bearer tokens for access")
                
            except Exception as e:
                logger.error(f"Failed to configure authentication: {e}")
                logger.warning("Continuing without authentication...")
                auth_provider = None
        else:
            logger.warning("MCP_SERVER_SECRET_KEY not set - server will run WITHOUT authentication")
            logger.warning("⚠️  All clients will have unrestricted access to the server")

        # === 8. CRÉATION DU SERVEUR MCP ===
        logger.info(f"Creating FastMCP server '{settings.MCP_SERVER_NAME}'...")
        
        mcp_server = FastMCP.from_openapi(
            openapi_spec=openapi_spec,
            client=api_client,
            name=settings.MCP_SERVER_NAME,
            route_maps=custom_route_maps,
            auth=auth_provider
        )
        
        logger.info(f"FastMCP server '{mcp_server.name}' created successfully!")
        logger.info("   - Custom GET-to-Tool mapping applied")

        # === 9. AJOUT DES MIDDLEWARES ===
        logger.info("Adding middleware stack...")
        
        # Ajouter le middleware de gestion d'erreurs EN PREMIER
        # Il doit capturer toutes les erreurs des autres middlewares
        error_handling_middleware = ErrorHandlingMiddleware(logger)
        mcp_server.add_middleware(error_handling_middleware)
        logger.info("   - Error handling middleware added successfully")
        
        # Ajouter le middleware de timing APRÈS la gestion d'erreurs
        timing_middleware = TimingMiddleware(logger)
        mcp_server.add_middleware(timing_middleware)
        logger.info("   - Timing middleware added successfully")

        # === 10. MODERNISATION DU RENOMMAGE DES OUTILS ===
        logger.info("Applying custom tool names using Tool.from_tool()...")
        
        successful_renames = 0
        total_tools = len(custom_mcp_tool_names)
        
        for original_name, new_name in custom_mcp_tool_names.items():
            try:
                # Récupérer l'outil original depuis le serveur
                original_tool = await mcp_server.get_tool(original_name)
                if original_tool:
                    # Créer un nouvel outil transformé avec le nouveau nom
                    # Utilisation explicite du paramètre 'name' pour plus de clarté
                    transformed_tool = Tool.from_tool(
                        tool=original_tool, 
                        name=new_name
                    )
                    
                    # Ajouter le nouvel outil au serveur
                    mcp_server.add_tool(transformed_tool)
                    
                    # IMPORTANT: Désactiver l'outil original pour éviter les doublons
                    # et la confusion pour le LLM
                    original_tool.disable()
                    
                    successful_renames += 1
                    logger.info(f"  ✓ Transformed tool: '{original_name}' -> '{new_name}'")
                else:
                    logger.warning(f"  ✗ Tool not found: '{original_name}' (may have been renamed during OpenAPI processing)")
            except Exception as e:
                logger.warning(f"  ✗ Failed to transform tool '{original_name}' -> '{new_name}': {e}")
        
        logger.info(f"Tool transformation completed: {successful_renames}/{total_tools} tools successfully renamed")

        # === 11. INSPECTION DES COMPOSANTS MCP ===
        logger.info("Inspecting MCP components...")
        await inspect_mcp_components(mcp_server, logger)

        # === 12. LANCEMENT DU SERVEUR ===
        server_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}{settings.MCP_API_PATH}"
        logger.info(f"Starting MCP server on {server_url}")
        logger.info("Press Ctrl+C to stop the server")
        
        await mcp_server.run_async(
            transport="http",
            host=settings.MCP_HOST,
            port=settings.MCP_PORT,
            path=settings.MCP_API_PATH
        )

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error("Please check your configuration and try again.")
        
    finally:
        # === 13. NETTOYAGE DES RESSOURCES ===
        if api_client:
            logger.info("Closing HTTP client...")
            await api_client.aclose()
            logger.info("HTTP client closed successfully")


if __name__ == "__main__":
    """
    Point d'entrée du script.
    Lance le serveur MCP avec gestion d'erreurs appropriée.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(1)