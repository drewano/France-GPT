# src/mcp_server/services/insee/service.py

"""
Service MCP pour interagir avec les API de l'INSEE via la bibliothèque pynsee.

Ce module expose plusieurs outils via FastMCP pour rechercher et obtenir des données
macroéconomiques, géographiques et locales (recensement) de l'INSEE.
Il est conçu pour être utilisé par une IA dotée d'un interpréteur de code Python
pour des tâches d'analyse de données et de visualisation.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

import pandas as pd
import geopandas as gpd

# --- Dépendances Pynsee ---
# Assurez-vous que pynsee est installé : pip install "pynsee[full]"
from pynsee.utils import init_conn
from pynsee.macrodata import search_macrodata, get_series
from pynsee.geodata import get_geodata_list, get_geodata
from pynsee.localdata import get_local_metadata, get_local_data, get_geo_list

# --- Dépendances FastMCP ---
# Assurez-vous que fastmcp est installé : pip install fastmcp
from fastmcp import FastMCP
from fastmcp.tools import Tool
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Initialisation de la connexion Pynsee ---
def _initialize_pynsee_connection():
    """
    Initialise la connexion pour pynsee en utilisant les clés API
    depuis les variables d'environnement.
    Les clés ne sont pas obligatoires pour toutes les API de l'INSEE,
    une simple alerte est donc émise si elles sont absentes.
    """
    insee_key = os.getenv("INSEE_KEY")
    insee_secret = os.getenv("INSEE_SECRET")

    if not insee_key or not insee_secret:
        logger.info(
            "Les variables d'environnement INSEE_KEY et INSEE_SECRET ne sont pas définies. "
            "Le service pynsee fonctionnera en mode public sans authentification."
        )
    else:
        logger.info("Initialisation de la connexion pynsee avec les clés API...")
        init_conn(insee_key=insee_key, insee_secret=insee_secret)
        logger.info("Connexion pynsee initialisée.")


# ==============================================================================
# === DÉFINITION DES OUTILS MCP                                              ===
# ==============================================================================

# --- Outils Macroéconomiques ---

async def rechercher_donnees_macroeconomiques(mot_cle: str) -> pd.DataFrame:
    """
    Recherche des séries temporelles macroéconomiques de l'INSEE à partir d'un mot-clé.
    Utilisez cet outil pour trouver des identifiants de séries (IDBANK) sur des sujets comme le PIB, l'inflation, le chômage.
    Retourne un DataFrame avec les résultats, incluant les IDBANK à utiliser avec 'get_series_macroeconomiques'.
    """
    try:
        logger.info("Recherche de données macroéconomiques pour: '%s'", mot_cle)
        results = search_macrodata(pattern=mot_cle)
        if results is None or results.empty:
            return pd.DataFrame({'info': [f"Aucun résultat trouvé pour '{mot_cle}'."]})
        return results
    except Exception as e:
        logger.error("Erreur dans rechercher_donnees_macroeconomiques: %s", e, exc_info=True)
        return pd.DataFrame({'error': [f"Une erreur est survenue: {e}"]})

async def get_series_macroeconomiques(idbanks: List[str]) -> pd.DataFrame:
    """
    Récupère les données d'une ou plusieurs séries temporelles macroéconomiques à partir de leurs IDBANK.
    Utilisez 'rechercher_donnees_macroeconomiques' au préalable pour trouver les bons IDBANKs.
    """
    try:
        logger.info("Récupération des séries macroéconomiques pour les IDBANKs: %s", idbanks)
        data = get_series(idbank_list=idbanks)
        if data is None or data.empty:
            return pd.DataFrame({'info': [f"Aucune donnée trouvée pour les IDBANKs: {idbanks}."]})
        return data
    except Exception as e:
        logger.error("Erreur dans get_series_macroeconomiques: %s", e, exc_info=True)
        return pd.DataFrame({'error': [f"Une erreur est survenue: {e}"]})

# --- Outils Géographiques ---

async def rechercher_couches_geographiques(mot_cle: str) -> List[Dict[str, Any]]:
    """
    Recherche des couches de données géographiques (cartes) disponibles à partir d'un mot-clé.
    Retourne une liste de dictionnaires avec les noms ('id') et descriptions des couches.
    """
    try:
        logger.info("Recherche de couches géographiques pour: '%s'", mot_cle)
        # AJOUT DE update=True POUR FORCER LA MISE À JOUR DU CACHE
        geo_list = get_geodata_list(update=True) 
        
        string_columns = geo_list.select_dtypes(include=['object']).columns
        mask = pd.Series(False, index=geo_list.index)
        
        for col in string_columns:
            # CORRECTION : Utiliser le singulier pour la recherche, c'est plus robuste
            search_term = mot_cle.rstrip('s')
            mask |= geo_list[col].str.contains(search_term, case=False, na=False)
        
        results = geo_list[mask]
        
        if results.empty:
            return [{'info': f"Aucune couche géographique trouvée pour '{mot_cle}'."}]
        
        if 'name' in results.columns:
            results = results.rename(columns={'name': 'id'})

        return results.to_dict(orient='records')
    except Exception as e:
        logger.error("Erreur dans rechercher_couches_geographiques: %s", e, exc_info=True)
        return [{'error': f"Une erreur est survenue: {e}"}]
# --- Outils de Données Locales (Recensement) ---

async def rechercher_metadonnees_locales(mot_cle: str) -> pd.DataFrame:
    """
    Recherche des jeux de données et des variables de recensement local à partir d'un mot-clé.
    Utile pour trouver les identifiants de 'dataset' et 'variables' pour des thèmes comme 'population', 'âge', 'logement', 'pauvreté'.
    """
    try:
        logger.info("Recherche de métadonnées locales pour: '%s'", mot_cle)
        metadata = get_local_metadata()
        mask = metadata['dataset_label'].str.contains(mot_cle, case=False) | metadata['variable_label'].str.contains(mot_cle, case=False)
        results = metadata[mask]
        if results.empty:
            return pd.DataFrame({'info': [f"Aucune métadonnée locale trouvée pour '{mot_cle}'."]})
        return results
    except Exception as e:
        logger.error("Erreur dans rechercher_metadonnees_locales: %s", e, exc_info=True)
        return pd.DataFrame({'error': [f"Une erreur est survenue: {e}"]})

async def rechercher_codes_geographiques(nom_zone: str, niveau_geographique: str) -> pd.DataFrame:
    """
    Recherche les codes INSEE officiels pour une zone géographique à partir de son nom.
    - 'nom_zone': Le nom à rechercher (ex: 'Paris', 'Gironde').
    - 'niveau_geographique': Le niveau ('communes', 'departements', 'regions').
    Retourne un DataFrame avec le nom et le code INSEE ('CODE').
    """
    try:
        logger.info("Recherche des codes géo pour '%s' au niveau '%s'", nom_zone, niveau_geographique)
        geo_list = get_geo_list(nivgeo=niveau_geographique)
        mask = geo_list['TITLE'].str.contains(nom_zone, case=False)
        results = geo_list[mask]
        if results.empty:
            return pd.DataFrame({'info': [f"Aucune zone trouvée pour '{nom_zone}' au niveau '{niveau_geographique}'."]})
        return results
    except Exception as e:
        logger.error("Erreur dans rechercher_codes_geographiques: %s", e, exc_info=True)
        return pd.DataFrame({'error': [f"Une erreur est survenue: {e}"]})

async def get_donnees_locales(dataset: str, variables: str, niveau_geographique: str, codes_geo: List[str]) -> pd.DataFrame:
    """
    Récupère des données de recensement pour des zones spécifiques via leurs codes.
    - 'dataset': L'ID du jeu de données (trouvé avec 'rechercher_metadonnees_locales').
    - 'variables': L'ID de la variable (trouvé avec 'rechercher_metadonnees_locales').
    - 'niveau_geographique': Le niveau ('COM', 'DEP', 'REG').
    - 'codes_geo': Une liste de codes INSEE (trouvés avec 'rechercher_codes_geographiques').
    """
    try:
        nivgeo_short = niveau_geographique.upper()[:3]
        logger.info("Récupération des données locales pour dataset '%s', variables '%s'...", dataset, variables)
        data = get_local_data(dataset_version=dataset, variables=variables, nivgeo=nivgeo_short, geocodes=codes_geo)
        if data is None or data.empty:
            return pd.DataFrame({'info': ["Aucune donnée locale trouvée pour ces paramètres."]})
        return data
    except Exception as e:
        logger.error("Erreur dans get_donnees_locales: %s", e, exc_info=True)
        return pd.DataFrame({'error': [f"Une erreur est survenue: {e}"]})

# ==============================================================================
# === CONFIGURATION DU SERVEUR MCP                                           ===
# ==============================================================================

def create_insee_mcp_server() -> FastMCP:
    """Crée et configure le serveur FastMCP avec tous les outils Pynsee."""
    mcp = FastMCP(name="insee_service_pynsee")

    # Initialiser la connexion pynsee
    _initialize_pynsee_connection()

    logger.info("Enregistrement des outils INSEE dans le serveur MCP...")

    # Création des outils à partir des fonctions
    mcp.add_tool(Tool.from_function(fn=rechercher_donnees_macroeconomiques))
    mcp.add_tool(Tool.from_function(fn=get_series_macroeconomiques))
    mcp.add_tool(Tool.from_function(fn=rechercher_couches_geographiques))
    mcp.add_tool(Tool.from_function(fn=rechercher_metadonnees_locales))
    mcp.add_tool(Tool.from_function(fn=rechercher_codes_geographiques))
    mcp.add_tool(Tool.from_function(fn=get_donnees_locales))
    
    # Ajout d'un endpoint de santé
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    return mcp