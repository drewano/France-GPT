"""
Ce fichier contient les outils et la logique du serveur FastMCP pour interagir
avec l'API La Bonne Alternance, en intégrant les schémas de données.
"""
# --- Partie 2: Logique du Serveur FastMCP ---

import os
import logging
import httpx
import functools
import json
from pathlib import Path
from typing import List, Optional

from fastmcp import FastMCP
from fastmcp.tools import Tool
from pydantic_ai import ModelRetry
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from .schemas import (
    EmploiSummary,
    EmploiDetails,
    FormationDetails,
    FormationSummary,
    JobOfferRead,
    Formation,
    RomeCode,  # Import du nouveau schéma
)


# --- Configuration du logging et du client API ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_lba_client() -> httpx.AsyncClient:
    """Initialise et retourne un client HTTP pour l'API La Bonne Alternance."""
    api_key = os.getenv("LABONNEALTERNANCE_API_KEY")
    if not api_key:
        raise ValueError(
            "La variable d'environnement LABONNEALTERNANCE_API_KEY est requise."
        )
    logger.info("Initialisation du client La Bonne Alternance...")
    client = httpx.AsyncClient(
        base_url="https://api.apprentissage.beta.gouv.fr/api",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    logger.info("Client La Bonne Alternance initialisé.")
    return client


try:
    client = _get_lba_client()
except ValueError as e:
    logger.error("Erreur critique lors de l'initialisation du client: %s", e)
    raise


def api_call_handler(func):
    """Décorateur pour la gestion centralisée des appels API, du logging et des erreurs."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Erreur HTTP dans '{tool_name}': {e.response.status_code} - {e.response.text}"
            )
            raise ModelRetry(
                f"Erreur de communication avec l'API La Bonne Alternance ({e.response.status_code}): {e.response.text}"
            ) from e
        except httpx.HTTPError as e:
            logger.error(f"Erreur de communication dans '{tool_name}': {e}")
            raise ModelRetry(
                f"Erreur de communication avec l'API La Bonne Alternance: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Erreur inattendue dans '{tool_name}': {e}", exc_info=True)
            raise ModelRetry(f"Une erreur inattendue s'est produite: {e}") from e

    return wrapper


# --- Définition des Outils ---


@api_call_handler
async def search_emploi(
    romes: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: int = 30,
    target_diploma_level: Optional[str] = None,
) -> List[EmploiSummary]:
    """Recherche des offres d'emploi en alternance selon les critères fournis."""
    params = {"romes": romes, "radius": radius}
    if latitude is not None and longitude is not None:
        params["latitude"] = latitude
        params["longitude"] = longitude
    
    # Ajout d'une conversion pour la robustesse
    if target_diploma_level:
        diploma_map = {
            "CAP": "3", "BAC": "4", "BAC+2": "5", "BTS": "5", "DUT": "5",
            "LICENCE": "6", "BAC+3": "6", "MASTER": "7", "BAC+5": "7"
        }
        # Chercher une clé correspondante en majuscules et sans accents
        normalized_level = target_diploma_level.upper().replace("É", "E")
        for key, value in diploma_map.items():
            if key in normalized_level:
                params["target_diploma_level"] = value
                break
        else:
            # Si aucune correspondance textuelle, on suppose que c'est déjà un code
            params["target_diploma_level"] = target_diploma_level

    response = await client.get("/job/v1/search", params=params)
    response.raise_for_status()
    jobs = response.json().get("jobs", [])
    
    results = []
    for job in jobs:
        full_offer = JobOfferRead.model_validate(job)
        summary = EmploiSummary(
            id=full_offer.identifier.id,
            title=full_offer.offer.title,
            company_name=full_offer.workplace.name,
            location=full_offer.workplace.location.get("address") if full_offer.workplace.location else "N/A",
            contract_type=full_offer.contract.type
        )
        results.append(summary)
    return results


@api_call_handler
async def get_emploi(id: str) -> EmploiDetails:
    """Récupère les informations détaillées d'une offre d'emploi spécifique."""
    response = await client.get(f"/job/v1/offer/{id}")
    response.raise_for_status()
    full_offer = JobOfferRead.model_validate(response.json())
    return EmploiDetails(
        id=full_offer.identifier.id,
        title=full_offer.offer.title,
        company_name=full_offer.workplace.name,
        location=full_offer.workplace.location.get("address") if full_offer.workplace.location else "N/A",
        contract_type=full_offer.contract.type,
        description=full_offer.offer.description,
        desired_skills=full_offer.offer.desired_skills,
        application_url=full_offer.apply.url,
        start_date=str(full_offer.contract.start) if full_offer.contract.start else None
    )


@api_call_handler
async def search_formations(
    romes: Optional[str] = None,
    rncp: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[int] = None,
) -> List[FormationSummary]:
    """Recherche des formations en alternance selon les critères fournis."""
    params = {}
    if romes:
        params["romes"] = romes
    if rncp:
        params["rncp"] = rncp
    if latitude is not None and longitude is not None:
        params["latitude"] = latitude
        params["longitude"] = longitude
    if radius is not None:
        params["radius"] = radius

    response = await client.get("/formation/v1/search", params=params)
    response.raise_for_status()
    formations = response.json().get("data", [])
    
    results = []
    for formation_data in formations:
        full_formation = Formation.model_validate(formation_data)
        
        # Helper function to safely get nested attributes
        def safe_get(data, attrs, default=None):
            for attr in attrs:
                if data is None: return default
                data = getattr(data, attr, None)
            return data

        summary = FormationSummary(
            id=full_formation.identifiant.cle_ministere_educatif,
            title=safe_get(full_formation, ['certification', 'valeur', 'intitule', 'cfd', 'long']),
            organisme_name=safe_get(full_formation, ['formateur', 'organisme', 'etablissement', 'enseigne']),
            city=safe_get(full_formation, ['lieu', 'adresse', 'commune', 'nom'])
        )
        results.append(summary)
    return results


@api_call_handler
async def get_formations(id: str) -> FormationDetails:
    """Récupère les informations détaillées d'une formation spécifique."""
    response = await client.get(f"/formation/v1/{id}")
    response.raise_for_status()
    full_formation = Formation.model_validate(response.json())
    
    # Helper function to safely get nested attributes
    def safe_get(data, attrs, default=None):
        for attr in attrs:
            if data is None: return default
            data = getattr(data, attr, None)
        return data

    return FormationDetails(
        id=full_formation.identifiant.cle_ministere_educatif,
        title=safe_get(full_formation, ['certification', 'valeur', 'intitule', 'cfd', 'long']),
        organisme_name=safe_get(full_formation, ['formateur', 'organisme', 'etablissement', 'enseigne']),
        city=safe_get(full_formation, ['lieu', 'adresse', 'commune', 'nom']),
        educational_content=safe_get(full_formation, ['contenu_educatif', 'contenu']),
        objective=safe_get(full_formation, ['contenu_educatif', 'objectif']),
        sessions=[s.dict() for s in full_formation.sessions] if full_formation.sessions else None
    )


# --- Fonctions utilitaires locales ---


@api_call_handler
async def get_romes(mots_cles: str, nb_resultats: int = 10) -> List[RomeCode]:
    """
    Recherche des codes ROME par mots-clés dans un fichier JSON local.

    Cette fonction lit un fichier `romes.json` situé dans le répertoire `data` adjacent,
    et retourne une liste de codes ROME dont le libellé contient les mots-clés fournis.
    La recherche est insensible à la casse. Le nombre de résultats est limité.

    Args:
        mots_cles (str): La chaîne de caractères à rechercher dans les libellés.
        nb_resultats (int, optional): Le nombre maximum de résultats à retourner. Défaut à 10. Maximum 10.

    Returns:
        List[RomeCode]: Une liste d'objets RomeCode correspondant aux critères de recherche.
    """
    # Limite le nombre de résultats à 10
    nb_resultats = min(nb_resultats, 10)
    
    # Chemin vers le fichier de données
    data_file_path = Path(__file__).parent / "data" / "romes.json"
    
    # Vérifie l'existence du fichier
    if not data_file_path.exists():
        logger.warning(f"Fichier de données ROME introuvable: {data_file_path}")
        return []
    
    # Lit et parse le contenu du fichier
    try:
        with open(data_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Erreur lors de la lecture du fichier ROME {data_file_path}: {e}")
        return []

    # Si le fichier est vide ou mal formé
    if not isinstance(data, list):
        logger.warning(f"Fichier de données ROME mal formé ou vide: {data_file_path}")
        return []
        
    # Recherche insensible à la casse
    mots_cles_lower = mots_cles.lower()
    results = [
        RomeCode(code=item['code'], libelle=item['libelle'])
        for item in data
        if mots_cles_lower in item.get('libelle', '').lower()
    ]
    
    # Limite le nombre de résultats
    return results[:nb_resultats]


# --- Création du serveur MCP ---


def create_labonnealternance_mcp_server() -> FastMCP:
    """Crée et configure une instance du serveur FastMCP avec tous les outils La Bonne Alternance."""
    mcp = FastMCP(
        name="labonnealternance_service",
        instructions="Ce serveur fournit des outils pour rechercher et consulter des offres d'emploi et des formations en alternance en France. Utilisez `search_emploi` pour rechercher des offres d'emploi et `search_formations` pour rechercher des formations. Vous pouvez ensuite utiliser `get_emploi` et `get_formations` pour obtenir les détails.",
    )
    logger.info("Enregistrement des outils dans le serveur MCP...")
    mcp.add_tool(Tool.from_function(fn=search_emploi))
    mcp.add_tool(Tool.from_function(fn=get_emploi))
    mcp.add_tool(Tool.from_function(fn=search_formations))
    mcp.add_tool(Tool.from_function(fn=get_formations))
    mcp.add_tool(Tool.from_function(fn=get_romes))  # Enregistrement du nouvel outil

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> PlainTextResponse:
        """Endpoint de health check pour la surveillance."""
        return PlainTextResponse("OK")

    logger.info("Serveur MCP configuré avec succès.")
    return mcp