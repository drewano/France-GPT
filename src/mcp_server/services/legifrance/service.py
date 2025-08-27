"""
Service MCP pour interagir avec l'API Légifrance via la bibliothèque pylegifrance.

Ce module expose plusieurs outils via FastMCP pour rechercher et consulter des
textes juridiques (lois, décrets, jurisprudence, etc.).
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- Dépendances Pylegifrance ---
# Assurez-vous que pylegifrance est installé : uv add pylegifrance
from pylegifrance import LegifranceClient
from pylegifrance.fonds.loda import Loda
from pylegifrance.fonds.juri import JuriAPI
from pylegifrance.fonds.code import Code

from src.mcp_server.utils import api_call_handler
from pydantic_ai.exceptions import ModelRetry

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Fonction de formatage partagée pour les documents complets ---
def _format_full_document_output(document: Any) -> Optional[Dict[str, str]]:
    """
    Formate un objet document (TexteLoda, JuriDecision, Article) en un dictionnaire.
    S'appuie sur les propriétés de pylegifrance pour obtenir le contenu HTML complet.
    """
    if not document:
        return None

    # pylegifrance fournit directement le HTML complet ou le texte brut.
    # La propriété .texte_html a une logique interne pour assembler le contenu.
    contenu_html = "Contenu non disponible"
    # Vérifier plusieurs attributs possibles dans l'ordre
    for attr in ["texte_html", "content_html", "content", "text"]:
        value = getattr(document, attr, None)
        if value:
            contenu_html = value
            break

    doc_id = getattr(document, "id", "ID non disponible")
    titre = (
        getattr(document, "title", "")
        or getattr(document, "titre", "")
        or "Titre non disponible"
    )

    # L'URL est disponible sur l'objet Article, mais pas toujours sur les autres
    url = getattr(document, "url", f"https://www.legifrance.gouv.fr/loda/id/{doc_id}")

    return {
        "titre": titre,
        "id": doc_id,
        "contenu_html": contenu_html,
        "url_legifrance": url,
    }


# --- Fonction d'assistance privée pour traiter les résultats LODA ---
def _process_loda_result(res: Any) -> Optional[Dict[str, str]]:
    """
    Traite et formate un résultat de recherche LODA en un dictionnaire standardisé.

    Args:
        res: Objet résultat de la bibliothèque pylegifrance

    Returns:
        Dictionnaire avec clés 'titre', 'id', et 'outil_recommande', ou None si res.id est None
    """
    # Gérer le cas où res.id est None
    if not res or not res.id:
        return None

    # Déterminer l'outil recommandé selon le préfixe de l'ID
    outil_recommande = "outil_inconnu"
    if res.id.startswith("JURI"):
        outil_recommande = "consulter_decision_justice"
    elif res.id.startswith("LEGIARTI"):
        outil_recommande = "consulter_article_code"
    elif res.id.startswith("KALITEXT"):
        outil_recommande = "consulter_convention_collective"
    elif res.id.startswith("LEGITEXT") or res.id.startswith("JORFTEXT"):
        outil_recommande = "consulter_texte_loi_decret"

    # Extraire le titre
    titre = (
        getattr(res, "title", "") or getattr(res, "titre", "") or "Titre non disponible"
    )

    return {"titre": titre, "id": res.id, "outil_recommande": outil_recommande}


# --- Fonction d'assistance privée pour traiter les résultats JURI ---
def _process_juri_result(res: Any) -> Optional[Dict[str, str]]:
    """
    Traite et formate un résultat de recherche JURI en un dictionnaire standardisé.

    Args:
        res: Objet résultat de la bibliothèque pylegifrance (JuriDecision)

    Returns:
        Dictionnaire avec clés 'titre', 'id', et 'outil_recommande', ou None si res.id est None
    """
    # Gérer le cas où res.id est None
    if not res or not res.id:
        return None

    # Pour les résultats JURI, l'outil recommandé est toujours le même
    outil_recommande = "consulter_decision_justice"

    # Utiliser res.title comme demandé
    titre = getattr(res, "title", "") or "Titre non disponible"

    return {"titre": titre, "id": res.id, "outil_recommande": outil_recommande}


# ==============================================================================
# === DÉFINITION DES OUTILS MCP                                              ===
# ==============================================================================


# --- Outil 1: Découverte ---
@api_call_handler
async def rechercher_textes_juridiques(mots_cles: str, loda_service: Loda, juri_api: JuriAPI) -> List[Dict[str, str]]:
    """
    Outil de recherche initial. Cherche des documents par mots-clés et retourne des candidats.
    Pour chaque candidat, utilisez l'ID avec l'outil spécialisé recommandé.
    """
    logger.info("Recherche de textes pour les mots-clés : '%s'", mots_cles)

    # Effectuer les recherches LODA et JURI de manière concurrente
    loda_results, juri_results = await asyncio.gather(
        asyncio.to_thread(loda_service.search, query=mots_cles),
        asyncio.to_thread(juri_api.search, query=mots_cles),
        return_exceptions=True,
    )

    # Vérifier explicitement les exceptions et les lever comme ModelRetry
    if isinstance(loda_results, Exception):
        logger.error(f"Erreur lors de la recherche LODA: {loda_results}", exc_info=True)
        raise ModelRetry(
            f"Erreur lors de la recherche LODA: {loda_results}"
        ) from loda_results
    if isinstance(juri_results, Exception):
        logger.error(f"Erreur lors de la recherche JURI: {juri_results}", exc_info=True)
        raise ModelRetry(
            f"Erreur lors de la recherche JURI: {juri_results}"
        ) from juri_results

    # S'assurer que les résultats sont des listes (au cas où ils seraient None)
    loda_results = loda_results or []
    juri_results = juri_results or []

    # Traiter les résultats LODA avec la fonction d'assistance
    processed_loda = [_process_loda_result(res) for res in loda_results]
    # Traiter les résultats JURI avec la fonction d'assistance
    processed_juri = [_process_juri_result(res) for res in juri_results]

    # Filtrer les résultats None et concaténer les listes
    all_candidates = [
        item for item in processed_loda + processed_juri if item is not None
    ]

    logger.info("Trouvé %d candidats.", len(all_candidates))
    return all_candidates


# --- Outils 2: Spécialistes de la Consultation ---


@api_call_handler
async def consulter_article_code(id_article: str, code_service: Code) -> Optional[Dict[str, str]]:
    """Récupère le contenu d'un ARTICLE DE CODE via son ID (ex: 'LEGIARTI...')."""
    logger.info("Consultation de l'article de code ID: %s", id_article)
    # Pour les articles, la consultation à la date du jour est la plus sûre
    todays_date_iso = datetime.now().strftime("%Y-%m-%d")
    document = code_service.fetch_article(id_article).at(todays_date_iso)
    return _format_full_document_output(document) if document else None


@api_call_handler
async def consulter_texte_loi_decret(id_texte: str, loda_service: Loda) -> Optional[Dict[str, str]]:
    """Récupère le contenu d'une LOI ou d'un DÉCRET via son ID (ex: 'LEGITEXT...')."""
    logger.info("Consultation du texte/loi/décret ID: %s", id_texte)

    # La librairie pylegifrance gère implicitement la date du jour si elle n'est pas spécifiée dans l'ID
    document = loda_service.fetch(id_texte)
    return _format_full_document_output(document) if document else None


@api_call_handler
async def consulter_decision_justice(id_decision: str, juri_api: JuriAPI) -> Optional[Dict[str, str]]:
    """Récupère le contenu d'une DÉCISION DE JUSTICE via son ID (ex: 'JURI...')."""
    logger.info("Consultation de la décision de justice ID: %s", id_decision)
    # Pour la jurisprudence, un fetch simple est généralement suffisant
    document = juri_api.fetch(id_decision)
    return _format_full_document_output(document) if document else None


@api_call_handler
async def consulter_convention_collective(
    id_convention: str, loda_service: Loda
) -> Optional[Dict[str, str]]:
    """Récupère le contenu d'une CONVENTION COLLECTIVE via son ID (ex: 'KALITEXT...')."""
    logger.info("Consultation de la convention collective ID: %s", id_convention)

    # La librairie pylegifrance gère implicitement la date du jour si elle n'est pas spécifiée dans l'ID
    document = loda_service.fetch(id_convention)
    return _format_full_document_output(document) if document else None


__all__ = [
    "rechercher_textes_juridiques",
    "consulter_article_code",
    "consulter_texte_loi_decret",
    "consulter_decision_justice",
    "consulter_convention_collective",
]
