"""
Ce fichier contient les outils et la logique du serveur FastMCP pour interagir
avec l'API Data Inclusion, en intégrant les schémas de données et les modifications
demandées pour rendre certains paramètres de recherche obligatoires.
"""
# --- Partie 2: Logique du Serveur FastMCP ---

import os
import logging
import httpx
from typing import List, Optional, Union, Literal

from fastmcp import FastMCP
from fastmcp.tools import Tool
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from src.mcp_server.utils import api_call_handler
from .schemas import (
    ReferenceItem,
    StructureSummary,
    ServiceSummary,
    StructureDetails,
    ServiceDetails,
    SearchedService,
)


# --- Configuration du logging et du client API ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_datainclusion_client() -> httpx.AsyncClient:
    """Initialise et retourne un client HTTP pour l'API Data Inclusion."""
    api_key = os.getenv("DATAINCLUSION_API_KEY")
    if not api_key:
        raise ValueError(
            "La variable d'environnement DATAINCLUSION_API_KEY est requise."
        )
    logger.info("Initialisation du client Data Inclusion...")
    client = httpx.AsyncClient(
        base_url="https://api-staging.data.inclusion.gouv.fr",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    logger.info("Client Data Inclusion initialisé.")
    return client


# Initialisation paresseuse du client
client: Optional[httpx.AsyncClient] = None


def _initialize_services() -> None:
    """
    Initialise le client API selon le pattern singleton.
    Cette fonction est appelée de manière paresseuse lorsque le client est nécessaire.
    """
    global client

    # Vérifie si le client est déjà initialisé
    if client is None:
        logger.info("Initialisation paresseuse du client Data Inclusion...")
        try:
            client = _get_datainclusion_client()
            logger.info("Client Data Inclusion initialisé avec succès.")
        except ValueError as e:
            logger.error("Erreur critique lors de l'initialisation du client: %s", e)
            # Réinitialise la variable en cas d'erreur
            client = None
            raise


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


# --- Définition des Outils ---


@api_call_handler
async def fetch_reference_values(
    category: Literal[
        "themes",
        "costs",
        "reception_modes",
        "mobilization_modes",
        "mobilizing_persons",
        "target_audience",
        "networks",
        "service_types",
    ],
) -> List[ReferenceItem]:
    """Récupère les listes de valeurs de référence (référentiel) disponibles dans la base Data Inclusion.

    Vous indiquez la catégorie souhaitée (themes, costs, target_audience, reception_modes, mobilization_modes, networks ou service_types) et l’API renvoie l’ensemble des entrées autorisées pour cette catégorie.

    Cela vous permet de connaître exactement les libellés à passer dans les filtres des autres endpoints (search_services, list_all_services, …) et d’éviter les erreurs de validation."""
    _initialize_services()

    endpoint = _REFERENCE_ENDPOINTS.get(category)
    if not endpoint:
        raise ValueError(f"Catégorie de référence inconnue : {category}")
    response = await client.get(endpoint)
    response.raise_for_status()
    return [ReferenceItem(**item) for item in response.json()]


@api_call_handler
async def list_all_structures(
    themes: Union[str, List[str]], network: Optional[str] = None
) -> List[StructureSummary]:
    """Liste les structures d'inclusion, avec un filtre thématique obligatoire. Limité à 15 résultats."""
    _initialize_services()
    if isinstance(themes, str):
        themes = [themes]

    params = {"size": 15, "thematiques": ",".join(themes)}
    if network:
        params["reseau_porteur"] = network

    # NOTE: L'endpoint v1 ne supportant pas le filtrage par thématique, nous utilisons l'endpoint v0.
    response = await client.get("/api/v0/structures", params=params)
    response.raise_for_status()
    return [StructureSummary(**item) for item in response.json().get("items", [])]


@api_call_handler
async def list_all_services(
    themes: Union[str, List[str]],
    costs: Optional[List[str]] = None,
    target_audience: Optional[List[str]] = None,
) -> List[ServiceSummary]:
    """Liste les services d'inclusion. Le filtre par thématiques est obligatoire. Limité à 15 résultats."""
    _initialize_services()
    # Normalisation de l'input pour accepter une string ou une liste
    if isinstance(themes, str):
        themes = [themes]

    params = {"size": 15}
    params["thematiques"] = ",".join(themes)

    if costs:
        params["frais"] = ",".join(costs)
    if target_audience:
        params["publics"] = ",".join(target_audience)

    response = await client.get("/api/v1/services", params=params)
    response.raise_for_status()
    return [ServiceSummary(**item) for item in response.json().get("items", [])]


@api_call_handler
async def get_structure_details(source: str, structure_id: str) -> StructureDetails:
    """Récupère les informations détaillées d'une structure spécifique à partir de sa source et de son ID."""
    _initialize_services()
    url = f"/api/v1/structures/{source}/{structure_id}"
    response = await client.get(url)
    response.raise_for_status()
    return StructureDetails(**response.json())


@api_call_handler
async def get_service_details(source: str, service_id: str) -> ServiceDetails:
    """Récupère les informations détaillées d'un service spécifique à partir de sa source et de son ID."""
    _initialize_services()
    url = f"/api/v1/services/{source}/{service_id}"
    response = await client.get(url)
    response.raise_for_status()
    return ServiceDetails(**response.json())


@api_call_handler
async def search_services(
    location_text: str,
    themes: Union[str, List[str]],
    target_audience: Optional[Union[str, List[str]]] = None,
) -> List[SearchedService]:
    """
    Recherche des services d'inclusion à proximité d'un lieu. Les résultats sont triés par distance.
    Le lieu (`location_text`) et la thématique (`themes`) sont obligatoires. La recherche est limitée à 10 résultats. Il faut passer qu'une seule chaîne de référentiel pour les thématiques. location_text doit contenir un seul nom de ville ou de région (ex.: «Paris», «Île-de-France»).
    """
    _initialize_services()
    if isinstance(themes, str):
        themes = [themes]
    if isinstance(target_audience, str):
        target_audience = [target_audience]

    # La limite est maintenant fixée à 10 et n'est plus un paramètre de la fonction.
    params = {"size": 10}

    # Le paramètre location_text est obligatoire
    async with httpx.AsyncClient() as geo_client:
        geo_response = await geo_client.get(
            "https://api-adresse.data.gouv.fr/search/",
            params={"q": location_text, "limit": 1},
        )
        geo_response.raise_for_status()
        geo_data = geo_response.json()

    if geo_data.get("features") and (
        insee_code := geo_data["features"][0]["properties"].get("citycode")
    ):
        params["code_commune"] = insee_code
    else:
        raise ValueError(
            f"Le géocodage pour '{location_text}' n'a pas retourné de code INSEE valide."
        )

    # Le paramètre themes est obligatoire
    params["thematiques"] = ",".join(themes)
    if target_audience:
        params["publics"] = ",".join(target_audience)

    response = await client.get("/api/v1/search/services", params=params)
    response.raise_for_status()
    items = response.json().get("items", [])

    # Transformation de la sortie pour être concise et utile à l'LLM
    return [SearchedService.model_validate(item) for item in items]


# --- Création du serveur MCP ---


def create_datainclusion_mcp_server() -> FastMCP:
    """Crée et configure une instance du serveur FastMCP avec tous les outils Data Inclusion."""
    mcp = FastMCP(
        name="datainclusion_service",
        instructions="Ce serveur fournit des outils pour rechercher et consulter des données sur les structures et services d'inclusion en France. Utilisez `search_services` pour des recherches géolocalisées et `list_*` pour des listes générales. La recherche de services (`search_services`) et la liste de services (`list_all_services`) requièrent obligatoirement un ou plusieurs thèmes.",
    )
    logger.info("Enregistrement des outils dans le serveur MCP...")
    mcp.add_tool(Tool.from_function(fn=search_services))
    mcp.add_tool(Tool.from_function(fn=list_all_services))
    mcp.add_tool(Tool.from_function(fn=get_service_details))
    mcp.add_tool(Tool.from_function(fn=list_all_structures))
    mcp.add_tool(Tool.from_function(fn=get_structure_details))
    mcp.add_tool(Tool.from_function(fn=fetch_reference_values))

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> PlainTextResponse:
        """Endpoint de health check pour la surveillance."""
        return PlainTextResponse("OK")

    logger.info("Serveur MCP configuré avec succès.")
    return mcp
