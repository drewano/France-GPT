# src\mcp_server\services\labonnealternance\service.py

"""
Ce fichier contient les outils et la logique du serveur FastMCP pour interagir
avec l'API La Bonne Alternance, en intégrant les schémas de données.
"""

# --- Partie 2: Logique du Serveur FastMCP ---

import os
import logging
import httpx
import json
import aioboto3
from pathlib import Path
from typing import List, Optional, Union

from src.core.config import settings
from src.mcp_server.utils import api_call_handler
from .schemas import (
    EmploiSummary,
    EmploiDetails,
    FormationDetails,
    FormationSummary,
    JobOfferRead,
    Formation,
    RomeCode,
    RncpCode,  # Import du nouveau schéma
)


# --- Configuration du logging et du client API ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Définition des Outils ---


@api_call_handler
async def search_emploi(
    client: httpx.AsyncClient,
    romes: Union[str, List[str]],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: int = 30,
    target_diploma_level: Optional[str] = None,
) -> List[EmploiSummary]:
    """Recherche des offres d'emploi en alternance selon les critères fournis."""

    # Normalisation des ROMEs
    romes_str = ",".join(romes) if isinstance(romes, list) else romes

    params = {"romes": romes_str, "radius": radius}
    if latitude is not None and longitude is not None:
        params["latitude"] = latitude
        params["longitude"] = longitude

    # Ajout d'une conversion pour la robustesse
    if target_diploma_level:
        diploma_map = {
            "CAP": "3",
            "BAC": "4",
            "BAC+2": "5",
            "BTS": "5",
            "DUT": "5",
            "LICENCE": "6",
            "BAC+3": "6",
            "MASTER": "7",
            "BAC+5": "7",
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
            location=full_offer.workplace.location.get("address")
            if full_offer.workplace.location
            else "N/A",
            contract_type=full_offer.contract.type,
        )
        results.append(summary)
    return results


@api_call_handler
async def get_emploi(client: httpx.AsyncClient, id: str) -> EmploiDetails:
    """Récupère les informations détaillées d'une offre d'emploi spécifique. Utilise toujours une liste de romes pour élargir la recherche."""
    response = await client.get(f"/job/v1/offer/{id}")
    response.raise_for_status()
    full_offer = JobOfferRead.model_validate(response.json())
    return EmploiDetails(
        id=full_offer.identifier.id,
        title=full_offer.offer.title,
        company_name=full_offer.workplace.name,
        location=full_offer.workplace.location.get("address")
        if full_offer.workplace.location
        else "N/A",
        contract_type=full_offer.contract.type,
        description=full_offer.offer.description,
        desired_skills=full_offer.offer.desired_skills,
        application_url=full_offer.apply.url,
        start_date=str(full_offer.contract.start)
        if full_offer.contract.start
        else None,
        recipient_id=full_offer.apply.recipient_id,
    )


@api_call_handler
async def apply_for_job(
    client: httpx.AsyncClient,
    applicant_first_name: str,
    applicant_last_name: str,
    applicant_email: str,
    applicant_phone: str,
    applicant_attachment_name: str,
    cv_s3_object_key: str,
    recipient_id: str,
) -> dict:
    """Soumet une candidature à une offre d'emploi à l'API La Bonne Alternance."""

    # Import pour l'encodage base64
    import base64

    # Créer une session aioboto3
    session = aioboto3.Session(
        aws_access_key_id=settings.agent.APP_AWS_ACCESS_KEY,
        aws_secret_access_key=settings.agent.APP_AWS_SECRET_KEY,
        region_name=settings.agent.APP_AWS_REGION,
    )

    # Créer un client S3 asynchrone
    endpoint_url = settings.agent.DEV_AWS_ENDPOINT
    async with session.client("s3", endpoint_url=endpoint_url) as s3_client:
        # Télécharger le contenu du CV depuis S3
        response = await s3_client.get_object(
            Bucket=settings.agent.BUCKET_NAME, Key=cv_s3_object_key
        )

        # Lire le contenu du fichier de manière asynchrone
        async with response["Body"] as stream:
            file_content = await stream.read()

    # Encoder le contenu en base64
    encoded_content = base64.b64encode(file_content).decode("utf-8")

    # Construire le payload avec les données de la candidature
    payload = {
        "applicant_first_name": applicant_first_name,
        "applicant_last_name": applicant_last_name,
        "applicant_email": applicant_email,
        "applicant_phone": applicant_phone,
        "applicant_attachment_name": applicant_attachment_name,
        "applicant_attachment_content": encoded_content,
        "recipient_id": recipient_id,
    }

    # Faire un appel POST à l'endpoint /job/v1/apply
    response = await client.post("/job/v1/apply", json=payload)
    response.raise_for_status()

    # Retourner le JSON de la réponse
    return response.json()


@api_call_handler
async def search_formations(
    client: httpx.AsyncClient,
    romes: Optional[Union[str, List[str]]] = None,
    rncp: Optional[Union[str, List[str]]] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[int] = None,
) -> List[FormationSummary]:
    """Recherche des formations en alternance selon les critères fournis. Utilise toujours un seul RNCP et une liste de romes pour élargir la recherche."""
    params = {}
    if romes:
        params["romes"] = ",".join(romes) if isinstance(romes, list) else romes
    if rncp:
        params["rncp"] = ",".join(rncp) if isinstance(rncp, list) else rncp
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
                if data is None:
                    return default
                data = getattr(data, attr, None)
            return data

        summary = FormationSummary(
            id=full_formation.identifiant.cle_ministere_educatif,
            title=safe_get(
                full_formation, ["certification", "valeur", "intitule", "cfd", "long"]
            ),
            organisme_name=safe_get(
                full_formation, ["formateur", "organisme", "etablissement", "enseigne"]
            ),
            city=safe_get(full_formation, ["lieu", "adresse", "commune", "nom"]),
        )
        results.append(summary)
    return results


@api_call_handler
async def get_formations(client: httpx.AsyncClient, id: str) -> FormationDetails:
    """Récupère les informations détaillées d'une formation spécifique."""
    response = await client.get(f"/formation/v1/{id}")
    response.raise_for_status()
    full_formation = Formation.model_validate(response.json())

    # Helper function to safely get nested attributes
    def safe_get(data, attrs, default=None):
        for attr in attrs:
            if data is None:
                return default
            data = getattr(data, attr, None)
        return data

    return FormationDetails(
        id=full_formation.identifiant.cle_ministere_educatif,
        title=safe_get(
            full_formation, ["certification", "valeur", "intitule", "cfd", "long"]
        ),
        organisme_name=safe_get(
            full_formation, ["formateur", "organisme", "etablissement", "enseigne"]
        ),
        city=safe_get(full_formation, ["lieu", "adresse", "commune", "nom"]),
        educational_content=safe_get(full_formation, ["contenu_educatif", "contenu"]),
        objective=safe_get(full_formation, ["contenu_educatif", "objectif"]),
        sessions=[s.model_dump() for s in full_formation.sessions]
        if full_formation.sessions
        else None,
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
        with open(data_file_path, "r", encoding="utf-8") as f:
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
        RomeCode(code=item["code"], libelle=item["libelle"])
        for item in data
        if mots_cles_lower in item.get("libelle", "").lower()
    ]

    # Limite le nombre de résultats
    return results[:nb_resultats]


@api_call_handler
async def get_rncp(mots_cles: str, nb_resultats: int = 10) -> List[RncpCode]:
    """
    Recherche des codes RNCP par mots-clés dans un fichier JSON local.

    Cette fonction lit un fichier `rncp.json` situé dans le répertoire `data` adjacent,
    et retourne une liste de codes RNCP dont l'intitulé contient les mots-clés fournis.
    La recherche est insensible à la casse. Le nombre de résultats est limité.

    Args:
        mots_cles (str): La chaîne de caractères à rechercher dans les intitulés.
        nb_resultats (int, optional): Le nombre maximum de résultats à retourner. Défaut à 10. Maximum 10.

    Returns:
        List[RncpCode]: Une liste d'objets RncpCode correspondant aux critères de recherche.
    """
    # Limite le nombre de résultats à 10
    nb_resultats = min(nb_resultats, 10)

    # Chemin vers le fichier de données
    data_file_path = Path(__file__).parent / "data" / "rncp.json"

    # Vérifie l'existence du fichier
    if not data_file_path.exists():
        logger.warning(f"Fichier de données RNCP introuvable: {data_file_path}")
        return []

    # Lit et parse le contenu du fichier
    try:
        with open(data_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Erreur lors de la lecture du fichier RNCP {data_file_path}: {e}")
        return []

    # Si le fichier est vide ou mal formé
    if not isinstance(data, list):
        logger.warning(f"Fichier de données RNCP mal formé ou vide: {data_file_path}")
        return []

    # Recherche insensible à la casse
    mots_cles_lower = mots_cles.lower()
    results = [
        RncpCode(**item)
        for item in data
        if mots_cles_lower in item.get("Intitulé de la certification", "").lower()
    ]

    # Limite le nombre de résultats
    return results[:nb_resultats]


__all__ = [
    "search_emploi",
    "get_emploi",
    "apply_for_job",
    "search_formations",
    "get_formations",
    "get_romes",
    "get_rncp",
]
