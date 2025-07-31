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
from fastmcp.tools import Tool
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialisation du Client Légifrance (Singleton) ---
_legifrance_client: Optional[LegifranceClient] = None

def _get_legifrance_client() -> LegifranceClient:
    """
    Initialise et retourne une instance singleton du client Legifrance.
    Charge les identifiants depuis les variables d'environnement.
    """
    global _legifrance_client
    if _legifrance_client:
        return _legifrance_client
    
    client_id = os.getenv("LEGIFRANCE_CLIENT_ID")
    client_secret = os.getenv("LEGIFRANCE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("Les variables d'environnement LEGIFRANCE_CLIENT_ID et LEGIFRANCE_CLIENT_SECRET sont requises.")
    
    logger.info("Initialisation du client Legifrance...")
    # La documentation montre l'init avec les clés, mais le client les charge 
    # automatiquement depuis les variables d'environnement si elles existent.
    _legifrance_client = LegifranceClient()
    logger.info("Client Legifrance initialisé.")
    return _legifrance_client

# --- Instanciation des services API ---
try:
    client = _get_legifrance_client()
    loda_service = Loda(client)
    juri_api = JuriAPI(client)
    code_service = Code(client)
except ValueError as e:
    logger.error(f"Erreur critique lors de l'initialisation des services: {e}")
    # Cette exception arrêtera le programme si les clés ne sont pas configurées.
    raise

# --- Fonction de formatage partagée pour les documents complets ---
def _format_full_document_output(document: Any) -> Dict[str, str]:
    """
    Formate un objet document (TexteLoda, JuriDecision, Article) en un dictionnaire standardisé.
    S'appuie sur les propriétés de pylegifrance pour obtenir le contenu HTML complet.
    """
    if not document:
        return {}

    # pylegifrance fournit directement le HTML complet ou le texte brut.
    # La propriété .texte_html a déjà une logique interne pour assembler le contenu si besoin.
    contenu_html = getattr(document, 'texte_html', '') or \
                   getattr(document, 'content_html', '') or \
                   getattr(document, 'content', '') or \
                   getattr(document, 'text', '') or \
                   'Contenu non disponible'

    doc_id = getattr(document, 'id', 'ID non disponible')
    titre = getattr(document, 'title', '') or getattr(document, 'titre', '') or 'Titre non disponible'
    
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
    Outil de recherche initial. Cherche des documents juridiques (lois, décrets, jurisprudence) 
    par mots-clés et retourne une liste de candidats. Pour chaque candidat, utilisez l'ID 
    fourni avec l'outil spécialisé recommandé pour obtenir le contenu complet.
    """
    try:
        logger.info(f"Recherche de textes pour les mots-clés : '{mots_cles}'")
        # La recherche LODA est très large et couvre codes, lois, décrets, conventions...
        loda_results = loda_service.search(query=mots_cles)
        # La recherche JURI est spécifique à la jurisprudence
        juri_results = juri_api.search(query=mots_cles)
        
        all_candidates = []
        for res in loda_results + juri_results:
            doc_id = res.id
            if not doc_id:
                continue

            outil_suivant = "outil_inconnu"
            # Détermine le meilleur outil pour la consultation
            if doc_id.startswith('JURI'):
                outil_suivant = "consulter_decision_justice"
            elif doc_id.startswith('LEGIARTI'):
                outil_suivant = "consulter_article_code"
            elif doc_id.startswith('KALITEXT'):
                outil_suivant = "consulter_convention_collective"
            elif doc_id.startswith('LEGITEXT') or doc_id.startswith('JORFTEXT'):
                outil_suivant = "consulter_texte_loi_decret"
            
            all_candidates.append({
                "titre": getattr(res, 'title', '') or getattr(res, 'titre', '') or 'Titre non disponible',
                "id": doc_id,
                "outil_recommande": outil_suivant
            })
            
        logger.info(f"Trouvé {len(all_candidates)} candidats.")
        return all_candidates
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de textes juridiques : {e}", exc_info=True)
        return [{"erreur": f"Une erreur est survenue lors de la recherche: {e}"}]

# --- Outils 2: Spécialistes de la Consultation ---

async def consulter_article_code(id_article: str) -> Optional[Dict[str, str]]:
    """Récupère le contenu complet d'un ARTICLE DE CODE à partir de son ID (ex: 'LEGIARTI...')."""
    try:
        logger.info(f"Consultation de l'article de code ID: {id_article}")
        # Pour les articles, la consultation à la date du jour est la plus sûre
        todays_date_iso = datetime.now().strftime("%Y-%m-%d")
        document = code_service.fetch_article(id_article).at(todays_date_iso)
        return _format_full_document_output(document) if document else None
    except Exception as e:
        logger.error(f"Erreur sur consulter_article_code (ID: {id_article}): {e}", exc_info=True)
        return {"erreur": f"Impossible de récupérer l'article {id_article}: {e}"}

async def consulter_texte_loi_decret(id_texte: str) -> Optional[Dict[str, str]]:
    """Récupère le contenu complet d'une LOI, d'un DÉCRET ou d'un texte JORF à partir de son ID (ex: 'LEGITEXT...', 'JORFTEXT...')."""
    try:
        logger.info(f"Consultation du texte/loi/décret ID: {id_texte}")
        
        # CORRECTION : S'assurer qu'une date est toujours fournie pour la robustesse.
        # Si l'ID ne contient pas de date (pas de '_'), on ajoute la date du jour pour demander
        # la version en vigueur. La méthode `loda_service.fetch` sait gérer les ID au format "ID_DATE".
        id_a_consulter = id_texte
        if "_" not in id_texte:
            todays_date_fr = datetime.now().strftime("%d-%m-%Y")
            id_a_consulter = f"{id_texte}_{todays_date_fr}"
            logger.info(f"Aucune date dans l'ID, utilisation de l'ID enrichi: {id_a_consulter}")
        
        document = loda_service.fetch(id_a_consulter)
        return _format_full_document_output(document) if document else None
    except Exception as e:
        logger.error(f"Erreur sur consulter_texte_loi_decret (ID: {id_texte}): {e}", exc_info=True)
        return {"erreur": f"Impossible de récupérer le texte {id_texte}: {e}"}

async def consulter_decision_justice(id_decision: str) -> Optional[Dict[str, str]]:
    """Récupère le contenu complet d'une DÉCISION DE JUSTICE à partir de son ID (ex: 'JURI...')."""
    try:
        logger.info(f"Consultation de la décision de justice ID: {id_decision}")
        # Pour la jurisprudence, un fetch simple est généralement suffisant
        document = juri_api.fetch(id_decision)
        return _format_full_document_output(document) if document else None
    except Exception as e:
        logger.error(f"Erreur sur consulter_decision_justice (ID: {id_decision}): {e}", exc_info=True)
        return {"erreur": f"Impossible de récupérer la décision {id_decision}: {e}"}

async def consulter_convention_collective(id_convention: str) -> Optional[Dict[str, str]]:
    """Récupère le contenu complet d'une CONVENTION COLLECTIVE à partir de son ID (ex: 'KALITEXT...')."""
    try:
        logger.info(f"Consultation de la convention collective ID: {id_convention}")
        # Même logique que pour les décrets : on s'assure d'avoir une date.
        id_a_consulter = id_convention
        if "_" not in id_convention:
            todays_date_fr = datetime.now().strftime("%d-%m-%Y")
            id_a_consulter = f"{id_convention}_{todays_date_fr}"
            logger.info(f"Aucune date dans l'ID, utilisation de l'ID enrichi: {id_a_consulter}")
            
        document = loda_service.fetch(id_a_consulter)
        return _format_full_document_output(document) if document else None
    except Exception as e:
        logger.error(f"Erreur sur consulter_convention_collective (ID: {id_convention}): {e}", exc_info=True)
        return {"erreur": f"Impossible de récupérer la convention {id_convention}: {e}"}

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
    async def health_check(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")
    
    # Retourne l'instance FastMCP configurée
    return mcp