"""
Service MCP pour interagir avec l'API Légifrance via la bibliothèque pylegifrance.

Ce module expose plusieurs outils via FastMCP pour rechercher et consulter des
textes juridiques (lois, décrets, jurisprudence, etc.).
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- Dépendances Pylegifrance ---
# Assurez-vous que pylegifrance est installé : uv add pylegifrance
from pylegifrance import LegifranceClient
from pylegifrance.fonds.loda import Loda
from pylegifrance.fonds.juri import JuriAPI
from pylegifrance.fonds.code import Code

# --- Dépendances FastMCP ---
# Assurez-vous que fastmcp est installé : uv add fastmcp
from fastmcp import FastMCP
from pydantic_ai import ModelRetry
from fastmcp.tools import Tool
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialisation du Client Légifrance ---
def _get_legifrance_client() -> LegifranceClient:
    """
    Initialise et retourne une instance du client Legifrance.
    Charge les identifiants depuis les variables d'environnement.
    """
    client_id = os.getenv("LEGIFRANCE_CLIENT_ID")
    client_secret = os.getenv("LEGIFRANCE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "Les variables d'environnement LEGIFRANCE_CLIENT_ID et "
            "LEGIFRANCE_CLIENT_SECRET sont requises."
        )

    logger.info("Initialisation du client Legifrance...")
    # La documentation montre l'init avec les clés, mais le client les charge
    # automatiquement depuis les variables d'environnement si elles existent.
    new_client = LegifranceClient()
    logger.info("Client Legifrance initialisé.")
    return new_client

# --- Instanciation des services API ---
try:
    client = _get_legifrance_client()
    loda_service = Loda(client)
    juri_api = JuriAPI(client)
    code_service = Code(client)
except ValueError as e:
    logger.error("Erreur critique lors de l'initialisation des services: %s", e)
    # Cette exception arrêtera le programme si les clés ne sont pas configurées.
    raise

# --- Fonction de formatage partagée pour les documents complets ---
def _format_full_document_output(document: Any) -> Dict[str, str]:
    """
    Formate un objet document (TexteLoda, JuriDecision, Article) en un dictionnaire.
    S'appuie sur les propriétés de pylegifrance pour obtenir le contenu HTML complet.
    """
    if not document:
        return {}

    # pylegifrance fournit directement le HTML complet ou le texte brut.
    # La propriété .texte_html a une logique interne pour assembler le contenu.
    contenu_html = (
        getattr(document, 'texte_html', '') or
        getattr(document, 'content_html', '') or
        getattr(document, 'content', '') or
        getattr(document, 'text', '') or
        'Contenu non disponible'
    )

    doc_id = getattr(document, 'id', 'ID non disponible')
    titre = (
        getattr(document, 'title', '') or
        getattr(document, 'titre', '') or
        'Titre non disponible'
    )

    # L'URL est disponible sur l'objet Article, mais pas toujours sur les autres
    url = getattr(document, 'url', f"https://www.legifrance.gouv.fr/loda/id/{doc_id}")

    return {
        "titre": titre,
        "id": doc_id,
        "contenu_html": contenu_html,
        "url_legifrance": url
    }

# ==============================================================================
# === DÉFINITION DES OUTILS MCP                                              ===
# ==============================================================================

# --- Outil 1: Découverte ---
async def rechercher_textes_juridiques(mots_cles: str) -> List[Dict[str, str]]:
    """
    Outil de recherche initial. Cherche des documents par mots-clés et retourne des candidats.
    Pour chaque candidat, utilisez l'ID avec l'outil spécialisé recommandé.
    """
    try:
        logger.info("Recherche de textes pour les mots-clés : '%s'", mots_cles)
        # La recherche LODA est très large et couvre codes, lois, décrets, conventions...
        loda_results = loda_service.search(query=mots_cles)
        # La recherche JURI est spécifique à la jurisprudence
        juri_results = juri_api.search(query=mots_cles)

        all_candidates = []
        for res in loda_results + juri_results:
            doc_id = res.id
            if not doc_id:
                continue

            # Détermine le meilleur outil pour la consultation
            outil_suivant = "outil_inconnu"
            if doc_id.startswith('JURI'):
                outil_suivant = "consulter_decision_justice"
            elif doc_id.startswith('LEGIARTI'):
                outil_suivant = "consulter_article_code"
            elif doc_id.startswith('KALITEXT'):
                outil_suivant = "consulter_convention_collective"
            elif doc_id.startswith('LEGITEXT') or doc_id.startswith('JORFTEXT'):
                outil_suivant = "consulter_texte_loi_decret"

            titre_res = (getattr(res, 'title', '') or
                         getattr(res, 'titre', '') or
                         'Titre non disponible')
            all_candidates.append({
                "titre": titre_res,
                "id": doc_id,
                "outil_recommande": outil_suivant
            })

        logger.info("Trouvé %d candidats.", len(all_candidates))
        return all_candidates
    except (ValueError, AttributeError) as e:
        logger.error("Erreur lors de la recherche: %s", e, exc_info=True)
        raise ModelRetry(f"Une erreur est survenue lors de la recherche: {e}") from e

# --- Outils 2: Spécialistes de la Consultation ---

async def consulter_article_code(id_article: str) -> Optional[Dict[str, str]]:
    """Récupère le contenu d'un ARTICLE DE CODE via son ID (ex: 'LEGIARTI...')."""
    try:
        logger.info("Consultation de l'article de code ID: %s", id_article)
        # Pour les articles, la consultation à la date du jour est la plus sûre
        todays_date_iso = datetime.now().strftime("%Y-%m-%d")
        document = code_service.fetch_article(id_article).at(todays_date_iso)
        return _format_full_document_output(document) if document else None
    except (ValueError, AttributeError) as e:
        logger.error(
            "Erreur sur consulter_article_code (ID: %s): %s", id_article, e, exc_info=True
        )
        raise ModelRetry(f"Impossible de récupérer l'article {id_article}: {e}") from e

async def consulter_texte_loi_decret(id_texte: str) -> Optional[Dict[str, str]]:
    """Récupère le contenu d'une LOI ou d'un DÉCRET via son ID (ex: 'LEGITEXT...')."""
    try:
        logger.info("Consultation du texte/loi/décret ID: %s", id_texte)

        # Assurer qu'une date est fournie pour la robustesse.
        # Si l'ID ne contient pas de '_', on ajoute la date du jour.
        id_a_consulter = id_texte
        if "_" not in id_texte:
            todays_date_fr = datetime.now().strftime("%d-%m-%Y")
            id_a_consulter = f"{id_texte}_{todays_date_fr}"
            logger.info("ID sans date, utilisation de l'ID enrichi: %s", id_a_consulter)

        document = loda_service.fetch(id_a_consulter)
        return _format_full_document_output(document) if document else None
    except (ValueError, AttributeError) as e:
        logger.error(
            "Erreur sur consulter_texte_loi_decret (ID: %s): %s", id_texte, e, exc_info=True
        )
        raise ModelRetry(f"Impossible de récupérer le texte {id_texte}: {e}") from e

async def consulter_decision_justice(id_decision: str) -> Optional[Dict[str, str]]:
    """Récupère le contenu d'une DÉCISION DE JUSTICE via son ID (ex: 'JURI...')."""
    try:
        logger.info("Consultation de la décision de justice ID: %s", id_decision)
        # Pour la jurisprudence, un fetch simple est généralement suffisant
        document = juri_api.fetch(id_decision)
        return _format_full_document_output(document) if document else None
    except (ValueError, AttributeError) as e:
        logger.error(
            "Erreur sur consulter_decision_justice (ID: %s): %s", id_decision, e, exc_info=True
        )
        raise ModelRetry(f"Impossible de récupérer la décision {id_decision}: {e}") from e

async def consulter_convention_collective(id_convention: str) -> Optional[Dict[str, str]]:
    """Récupère le contenu d'une CONVENTION COLLECTIVE via son ID (ex: 'KALITEXT...')."""
    try:
        logger.info("Consultation de la convention collective ID: %s", id_convention)
        # Même logique que pour les décrets : on s'assure d'avoir une date.
        id_a_consulter = id_convention
        if "_" not in id_convention:
            todays_date_fr = datetime.now().strftime("%d-%m-%Y")
            id_a_consulter = f"{id_convention}_{todays_date_fr}"
            logger.info("ID sans date, utilisation de l'ID enrichi: %s", id_a_consulter)

        document = loda_service.fetch(id_a_consulter)
        return _format_full_document_output(document) if document else None
    except (ValueError, AttributeError) as e:
        logger.error(
            "Erreur sur consulter_convention_collective (ID: %s): %s",
            id_convention, e, exc_info=True
        )
        raise ModelRetry(f"Impossible de récupérer la convention {id_convention}: {e}") from e

# ==============================================================================
# === CONFIGURATION DU SERVEUR MCP                                           ===
# ==============================================================================

def create_legifrance_mcp_server() -> FastMCP:
    """Crée et configure le serveur FastMCP avec tous les outils Légifrance."""
    mcp = FastMCP(name="legifrance_service_pylegifrance")

    logger.info("Enregistrement des outils dans le serveur MCP...")

    # Création des outils à partir des fonctions
    tool_recherche = Tool.from_function(fn=rechercher_textes_juridiques)
    tool_article = Tool.from_function(fn=consulter_article_code)
    tool_loi = Tool.from_function(fn=consulter_texte_loi_decret)
    tool_juri = Tool.from_function(fn=consulter_decision_justice)
    tool_kali = Tool.from_function(fn=consulter_convention_collective)

    # Ajout des outils au serveur MCP
    mcp.add_tool(tool_recherche)
    mcp.add_tool(tool_article)
    mcp.add_tool(tool_loi)
    mcp.add_tool(tool_juri)
    mcp.add_tool(tool_kali)

    # Ajout d'un endpoint de santé
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    # Retourne l'instance FastMCP configurée
    return mcp
