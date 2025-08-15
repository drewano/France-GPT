"""
Service MCP pour interagir avec l'API Data Inclusion.

Ce module initialise un client HTTP authentifié pour communiquer avec
l'API data.inclusion.beta.gouv.fr.
"""
import os
import logging
from typing import List, Literal, Optional, Tuple, Union

import httpx
from fastmcp import FastMCP
from pydantic_ai import ModelRetry

# --- Import des modèles de données ---
from .schemas import ReferenceItem, StructureSummary, ServiceSummary, StructureDetails, ServiceDetails, SearchedService

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialisation du Client Data Inclusion ---
def _get_datainclusion_client() -> httpx.AsyncClient:
    """
    Initialise et retourne un client httpx.AsyncClient configuré
    pour communiquer avec l'API Data Inclusion.
    Charge la clé API depuis les variables d'environnement.
    """
    api_key = os.getenv("DATAINCLUSION_API_KEY")

    if not api_key:
        raise ValueError(
            "La variable d'environnement DATAINCLUSION_API_KEY est requise."
        )

    logger.info("Initialisation du client Data Inclusion...")
    client = httpx.AsyncClient(
        base_url="https://api-staging.data.inclusion.gouv.fr",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    logger.info("Client Data Inclusion initialisé.")
    return client

# --- Instanciation du client ---
try:
    client = _get_datainclusion_client()
except ValueError as e:
    logger.error("Erreur critique lors de l'initialisation du client: %s", e)
    # Cette exception arrêtera le programme si la clé n'est pas configurée.
    raise

# --- Mapping des catégories aux endpoints ---
_REFERENCE_ENDPOINTS = {
    "themes": "/api/v1/doc/thematiques",
    "costs": "/api/v1/doc/frais",
    "reception_modes": "/api/v1/doc/modes-accueil",
    "mobilization_modes": "/api/v1/doc/modes-mobilisation",
    "mobilizing_persons": "/api/v1/doc/personnes-mobilisatrice",
    "target_audience": "/api/v1/doc/publics",
    "networks": "/api/v1/doc/reseaux-porteurs",
    "service_types": "/api/v1/doc/types-services",
}

async def get_reference_data(
    category: Literal[
        "themes", "costs", "reception_modes",
        "mobilization_modes", "mobilizing_persons",
        "target_audience", "networks", "service_types"
    ]
) -> List[ReferenceItem]:
    """
    Récupère les valeurs possibles pour les différentes catégories de filtres utilisées dans les autres outils.
    Utilisez cet outil pour savoir quelles options sont disponibles pour les paramètres 'themes', 'costs', 'target_audience', 'networks', etc. des outils de recherche.
    """
    # 1. Récupérer l'endpoint associé à la catégorie
    endpoint = _REFERENCE_ENDPOINTS.get(category)
    if not endpoint:
        raise ValueError(f"Catégorie de référence inconnue : {category}")

    try:
        # 2. Appeler l'API
        logger.info(f"Récupération des données de référence pour la catégorie '{category}'...")
        response = await client.get(endpoint)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP

        # 3. Parser la réponse JSON
        raw_data = response.json()

        # 4. Transformer en liste de ReferenceItem
        reference_items = [ReferenceItem(**item) for item in raw_data]

        logger.info(f"Récupéré {len(reference_items)} éléments pour la catégorie '{category}'.")
        return reference_items

    except httpx.HTTPError as e:
        logger.error(f"Erreur HTTP lors de la récupération des données de référence pour '{category}': {e}")
        raise ModelRetry(f"Erreur de communication avec l'API Data Inclusion pour la catégorie '{category}': {e}") from e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des données de référence pour '{category}': {e}")
        raise ModelRetry(f"Une erreur inattendue s'est produite lors de la récupération des données de référence pour la catégorie '{category}': {e}") from e


async def list_all_structures(
    location: Optional[str] = None,
    network: Optional[str] = None,
    limit: int = 20
) -> List[StructureSummary]:
    """
    Liste les structures d'inclusion en France. Peut être filtré par localisation (nom de commune, de département ou de région) ou par réseau porteur.
    Utilisez cet outil pour trouver des organisations spécifiques ou pour explorer les structures dans une zone administrative donnée.
    """
    # 1. Préparer les paramètres de requête
    params = {"limit": limit}
    if location:
        params["location"] = location
    if network:
        # Mapping du paramètre de la fonction vers le paramètre de l'API
        params["reseau_porteur"] = network

    try:
        # 2. Appeler l'API
        logger.info(f"Récupération de la liste des structures avec les paramètres: {params}")
        response = await client.get("/api/v1/structures", params=params)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP

        # 3. Parser la réponse JSON paginée
        raw_data = response.json()
        items = raw_data.get("items", [])

        # 4. Transformer en liste de StructureSummary
        structures = [StructureSummary(**item) for item in items]

        logger.info(f"Récupéré {len(structures)} structures.")
        return structures

    except httpx.HTTPError as e:
        logger.error(f"Erreur HTTP lors de la récupération des structures: {e}")
        raise ModelRetry(f"Erreur de communication avec l'API Data Inclusion lors de la récupération des structures: {e}") from e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des structures: {e}")
        raise ModelRetry(f"Une erreur inattendue s'est produite lors de la récupération des structures: {e}") from e


async def list_all_services(
    themes: Optional[Union[str, List[str]]] = None,
    costs: Optional[Union[str, List[str]]] = None,
    target_audience: Optional[Union[str, List[str]]] = None,
    limit: int = 20
) -> List[ServiceSummary]:
    """
    Liste les services d'inclusion disponibles en France, avec des options de filtrage non géographiques.
    Utilisez cet outil pour des recherches larges ou basées sur des critères spécifiques comme les thématiques, les frais ou les publics cibles, sans contrainte de lieu.
    Pour une recherche basée sur la localisation, préférez l'outil 'search_services'.
    """
    # 1. Normaliser les paramètres de type liste
    if isinstance(themes, str):
        themes = [themes]
    if isinstance(costs, str):
        costs = [costs]
    if isinstance(target_audience, str):
        target_audience = [target_audience]

    # 2. Préparer les paramètres de requête
    params = {"limit": limit}
    if themes:
        params["thematiques"] = ",".join(themes)
    if costs:
        params["frais"] = ",".join(costs)
    if target_audience:
        # Mapping du paramètre de la fonction vers le paramètre de l'API
        params["publics"] = ",".join(target_audience)

    try:
        # 3. Appeler l'API
        logger.info(f"Récupération de la liste des services avec les paramètres: {params}")
        response = await client.get("/api/v1/services", params=params)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP

        # 4. Parser la réponse JSON paginée
        raw_data = response.json()
        items = raw_data.get("items", [])

        # 5. Transformer en liste de ServiceSummary
        services = []
        for item in items:
            service_data = item.get("service", {})
            service_data["structure_id"] = item.get("structure", {}).get("id")
            services.append(ServiceSummary(**service_data))

        logger.info(f"Récupéré {len(services)} services.")
        return services

    except httpx.HTTPError as e:
        logger.error(f"Erreur HTTP lors de la récupération des services: {e}")
        raise ModelRetry(f"Erreur de communication avec l'API Data Inclusion lors de la récupération des services: {e}") from e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des services: {e}")
        raise ModelRetry(f"Une erreur inattendue s'est produite lors de la récupération des services: {e}") from e


async def get_structure_details(
    source: str,
    structure_id: str
) -> StructureDetails:
    """
    Récupère les informations détaillées d'une structure spécifique à partir de son identifiant et de sa source.
    Utilisez cet outil après avoir identifié une structure via 'list_all_structures' pour obtenir des informations complètes comme la description, les contacts et les horaires.
    """
    try:
        # 1. Construire l'URL avec les paramètres
        url = f"/api/v1/structures/{source}/{structure_id}"

        # 2. Appeler l'API
        logger.info(f"Récupération des détails de la structure '{structure_id}' de la source '{source}'...")
        response = await client.get(url)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP

        # 3. Parser la réponse JSON
        raw_data = response.json()

        # 4. Transformer en StructureDetails
        structure_details = StructureDetails(**raw_data)

        logger.info(f"Détails de la structure '{structure_id}' récupérés avec succès.")
        return structure_details

    except httpx.HTTPError as e:
        logger.error(f"Erreur HTTP lors de la récupération des détails de la structure '{structure_id}': {e}")
        raise ModelRetry(f"Erreur de communication avec l'API Data Inclusion lors de la récupération des détails de la structure '{structure_id}': {e}") from e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des détails de la structure '{structure_id}': {e}")
        raise ModelRetry(f"Une erreur inattendue s'est produite lors de la récupération des détails de la structure '{structure_id}': {e}") from e


async def get_service_details(
    source: str,
    service_id: str
) -> ServiceDetails:
    """
    Récupère les informations détaillées d'un service spécifique à partir de son identifiant et de sa source.
    Utilisez cet outil après avoir identifié un service via 'search_services' ou 'list_all_services' pour obtenir plus d'informations comme la description complète, les conditions d'accès ou les modes de mobilisation.
    """
    try:
        # 1. Construire l'URL avec les paramètres
        url = f"/api/v1/services/{source}/{service_id}"

        # 2. Appeler l'API
        logger.info(f"Récupération des détails du service '{service_id}' de la source '{source}'...")
        response = await client.get(url)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP

        # 3. Parser la réponse JSON
        raw_data = response.json()

        # 4. Transformer en ServiceDetails
        service_details = ServiceDetails(**raw_data)

        logger.info(f"Détails du service '{service_id}' récupérés avec succès.")
        return service_details

    except httpx.HTTPError as e:
        logger.error(f"Erreur HTTP lors de la récupération des détails du service '{service_id}': {e}")
        raise ModelRetry(f"Erreur de communication avec l'API Data Inclusion lors de la récupération des détails du service '{service_id}': {e}") from e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des détails du service '{service_id}': {e}")
        raise ModelRetry(f"Une erreur inattendue s'est produite lors de la récupération des détails du service '{service_id}': {e}") from e


async def search_services(
    location_text: Optional[str] = None,
    location_insee_code: Optional[str] = None,
    location_lat_lon: Optional[Tuple[float, float]] = None,
    themes: Optional[Union[str, List[str]]] = None,
    target_audience: Optional[Union[str, List[str]]] = None,
    limit: int = 10
) -> List[SearchedService]:
    """
    Recherche des services d'inclusion sociale et professionnelle à proximité d'un lieu en France.
    Les résultats sont triés par distance croissante.
    Utilisez cet outil pour répondre à des questions géolocalisées.
    Fournissez UN SEUL des paramètres de localisation suivants, du plus précis au moins précis : `location_lat_lon`, `location_insee_code`, ou `location_text`.
    Pour des recherches non géographiques, utilisez 'list_all_services'.
    """
    # 1. Normaliser les paramètres de type liste
    if isinstance(themes, str):
        themes = [themes]
    if isinstance(target_audience, str):
        target_audience = [target_audience]

    # 2. Gestion de la logique de localisation avec priorité
    params = {"limit": limit}
    
    if location_lat_lon:
        # Priorité 1: Coordonnées GPS
        lat, lon = location_lat_lon
        params["lat"] = lat
        params["lon"] = lon
        logger.info(f"Recherche par coordonnées GPS: lat={lat}, lon={lon}")
        
    elif location_insee_code:
        # Priorité 2: Code INSEE
        params["code_commune"] = location_insee_code
        logger.info(f"Recherche par code INSEE: {location_insee_code}")
        
    elif location_text:
        # Priorité 3: Texte libre -> géocodage
        logger.info(f"Recherche par texte libre: '{location_text}'. Géocodage en cours...")
        try:
            # Appel à l'API de géocodage
            async with httpx.AsyncClient() as geo_client:
                geo_response = await geo_client.get(
                    "https://api-adresse.data.gouv.fr/search/",
                    params={"q": location_text, "limit": 1}
                )
                geo_response.raise_for_status()
                geo_data = geo_response.json()
                
            # Extraction du code INSEE
            if geo_data.get("features"):
                insee_code = geo_data["features"][0]["properties"].get("citycode")
                if insee_code:
                    params["code_commune"] = insee_code
                    logger.info(f"Code INSEE trouvé via géocodage: {insee_code}")
                else:
                    raise ValueError("Le géocodage n'a pas retourné de code INSEE.")
            else:
                raise ValueError("Aucun résultat trouvé pour le géocodage.")
        except httpx.HTTPError as e:
            logger.error(f"Erreur HTTP lors du géocodage: {e}")
            raise ModelRetry(f"Erreur de géocodage pour '{location_text}': {e}") from e
        except Exception as e:
            logger.error(f"Erreur lors du géocodage: {e}")
            raise ModelRetry(f"Impossible de géocoder '{location_text}': {e}") from e
    else:
        # Aucun paramètre de localisation fourni
        raise ValueError("Un paramètre de localisation est requis (location_lat_lon, location_insee_code, ou location_text).")

    # 3. Ajout des filtres optionnels
    if themes:
        params["thematiques"] = ",".join(themes)
    if target_audience:
        # Mapping du paramètre de la fonction vers le paramètre de l'API
        params["publics"] = ",".join(target_audience)

    try:
        # 4. Appeler l'API Data Inclusion
        logger.info(f"Recherche de services avec les paramètres: {params}")
        response = await client.get("/api/v1/search/services", params=params)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP

        # 5. Parser la réponse JSON paginée
        raw_data = response.json()
        items = raw_data.get("items", [])

        # 6. Transformer en liste de SearchedService
        searched_services = []
        for item in items:
            service_data = item.get('service', {})
            service_data['structure_id'] = item.get('structure', {}).get('id')
            
            searched_service = SearchedService(
                id=service_data.get('id'),
                source=service_data.get('source'),
                name=service_data.get('name'),
                themes=service_data.get('thematiques'),
                structure_id=service_data.get('structure_id'),
                distance_meters=item.get('distance'),
                structure_details=StructureSummary(**item.get('structure', {}))
            )
            searched_services.append(searched_service)

        logger.info(f"Recherche terminée. Trouvé {len(searched_services)} services.")
        return searched_services

    except httpx.HTTPError as e:
        logger.error(f"Erreur HTTP lors de la recherche de services: {e}")
        raise ModelRetry(f"Erreur de communication avec l'API Data Inclusion lors de la recherche de services: {e}") from e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la recherche de services: {e}")
        raise ModelRetry(f"Une erreur inattendue s'est produite lors de la recherche de services: {e}") from e


def create_datainclusion_mcp_server() -> FastMCP:
    """
    Crée et configure le serveur FastMCP avec tous les outils Data Inclusion.
    """
    from fastmcp.tools import Tool
    from starlette.requests import Request
    from starlette.responses import PlainTextResponse
    
    mcp = FastMCP(name="datainclusion_service")

    logger.info("Enregistrement des outils dans le serveur MCP...")

    # Création des outils à partir des fonctions
    tool_search = Tool.from_function(fn=search_services)
    tool_list_services = Tool.from_function(fn=list_all_services)
    tool_get_service = Tool.from_function(fn=get_service_details)
    tool_list_structures = Tool.from_function(fn=list_all_structures)
    tool_get_structure = Tool.from_function(fn=get_structure_details)
    tool_reference = Tool.from_function(fn=get_reference_data)

    # Ajout des outils au serveur MCP
    mcp.add_tool(tool_search)
    mcp.add_tool(tool_list_services)
    mcp.add_tool(tool_get_service)
    mcp.add_tool(tool_list_structures)
    mcp.add_tool(tool_get_structure)
    mcp.add_tool(tool_reference)

    # Ajout d'un endpoint de santé
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    # Retourne l'instance FastMCP configurée
    return mcp