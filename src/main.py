"""
DataInclusion MCP Server

Ce serveur MCP expose l'API data.inclusion.beta.gouv.fr via le protocole Model Context Protocol.
Il transforme automatiquement les endpoints OpenAPI en outils MCP.
"""

import asyncio
import json
import os
import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv
from fastmcp.server.openapi import RouteMap, MCPType
from .utils import inspect_mcp_components, create_api_client

# Chargement des variables d'environnement
load_dotenv()

# Configuration depuis les variables d'environnement avec valeurs par défaut
OPENAPI_URL = os.getenv("OPENAPI_URL", "https://api.data.inclusion.beta.gouv.fr/api/openapi.json")
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "DataInclusionAPI")
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
MCP_SSE_PATH = os.getenv("MCP_SSE_PATH", "/sse")

def limit_page_size_in_spec(spec: dict, max_size: int = 25) -> dict:
    """
    Modifie la spécification OpenAPI pour limiter la taille des pages.

    Cette fonction parcourt les points de terminaison pertinents et ajuste le paramètre
    'size' pour qu'il ait une valeur maximale et par défaut de `max_size`.

    Args:
        spec: Le dictionnaire de la spécification OpenAPI.
        max_size: La taille maximale à définir pour les résultats.

    Returns:
        Le dictionnaire de la spécification modifié.
    """
    paths_to_modify = [
        "/api/v0/structures",
        "/api/v0/services",
        "/api/v0/search/services",
    ]

    print(f"🔩 Applying page size limit (max_size={max_size}) to spec...")

    for path in paths_to_modify:
        if path in spec["paths"] and "get" in spec["paths"][path]:
            params = spec["paths"][path]["get"].get("parameters", [])
            for param in params:
                if param.get("name") == "size":
                    param["schema"]["maximum"] = max_size
                    param["schema"]["default"] = max_size
                    print(f"  - Limited 'size' parameter for endpoint: GET {path}")
    
    return spec


async def main():
    """
    Fonction principale qui configure et lance le serveur MCP.
    
    Cette fonction :
    1. Charge la spécification OpenAPI
    2. Crée un client HTTP authentifié
    3. Configure le serveur MCP avec des noms d'outils personnalisés
    4. Lance le serveur avec le transport SSE
    """
    
    api_client = None
    
    try:
        # === 1. CHARGEMENT DE LA SPÉCIFICATION OPENAPI VIA HTTP ===
        print(f"Loading OpenAPI specification from URL: '{OPENAPI_URL}'...")
        
        try:
            # On a besoin d'importer httpx si ce n'est pas déjà fait en haut du fichier
            
            async with httpx.AsyncClient() as client:
                response = await client.get(OPENAPI_URL)
                response.raise_for_status()  # Lève une exception si le statut n'est pas 2xx
                openapi_spec = response.json()
            
            api_title = openapi_spec.get("info", {}).get("title", "Unknown API")
            print(f"✅ Successfully loaded OpenAPI spec: '{api_title}'")
            
            # === MODIFICATION DES LIMITES DE PAGINATION ===
            # Limite la taille des pages pour les outils de listing à 25 éléments maximum
            # Cela s'applique aux outils: list_all_structures, list_all_services, search_services
            print("📄 Applying pagination limits to data-listing endpoints...")
            openapi_spec = limit_page_size_in_spec(openapi_spec, max_size=25)
            
        except httpx.RequestError as e:
            print(f"❌ Error: Failed to fetch OpenAPI specification from '{OPENAPI_URL}'.")
            print(f"Details: {e}")
            return
            
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in the response from '{OPENAPI_URL}'.")
            print(f"Details: {e}")
            return

        # === 2. DÉTERMINATION DE L'URL DE BASE ===
        servers = openapi_spec.get("servers", [])
        if servers and isinstance(servers, list) and len(servers) > 0 and "url" in servers[0]:
            base_url = servers[0]["url"]
            print(f"📡 Using base URL from OpenAPI spec: {base_url}")
        else:
            base_url = "http://localhost:8000"
            print(f"⚠️  Warning: No servers section found in OpenAPI spec.")
            print(f"Using default base URL: {base_url}")

        # === 3. CRÉATION DU CLIENT HTTP AUTHENTIFIÉ ===
        print("🔑 Configuring HTTP client with authentication...")
        api_client = create_api_client(base_url)

        # === 4. CONFIGURATION DES NOMS D'OUTILS PERSONNALISÉS ===
        print("🛠️  Configuring custom tool names...")
        
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

        # === 5. CONFIGURATION DES ROUTES MCP ===
        print("🗺️  Configuring route mappings...")
        
        # Configuration pour mapper tous les endpoints GET comme des outils MCP
        custom_route_maps = [
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.TOOL),
        ]

        # === 6. CRÉATION DU SERVEUR MCP ===
        print(f"🚀 Creating FastMCP server '{MCP_SERVER_NAME}'...")
        
        mcp_server = FastMCP.from_openapi(
            openapi_spec=openapi_spec,
            client=api_client,
            name=MCP_SERVER_NAME,
            route_maps=custom_route_maps,
            mcp_names=custom_mcp_tool_names
        )
        
        print(f"✅ FastMCP server '{mcp_server.name}' created successfully!")
        print("   - Custom GET-to-Tool mapping applied")
        print("   - Custom tool names configured")

        # === 7. INSPECTION DES COMPOSANTS MCP ===
        print("🔍 Inspecting MCP components...")
        await inspect_mcp_components(mcp_server)

        # === 8. LANCEMENT DU SERVEUR ===
        server_url = f"http://{MCP_HOST}:{MCP_PORT}{MCP_SSE_PATH}"
        print(f"🌐 Starting MCP server on {server_url}")
        print("Press Ctrl+C to stop the server")
        
        await mcp_server.run_async(
            transport="sse",
            host=MCP_HOST,
            port=MCP_PORT,
            path=MCP_SSE_PATH
        )

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Please check your configuration and try again.")
        
    finally:
        # === 9. NETTOYAGE DES RESSOURCES ===
        if api_client:
            print("🧹 Closing HTTP client...")
            await api_client.aclose()
            print("✅ HTTP client closed successfully")


if __name__ == "__main__":
    """
    Point d'entrée du script.
    Lance le serveur MCP avec gestion d'erreurs appropriée.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        exit(1)