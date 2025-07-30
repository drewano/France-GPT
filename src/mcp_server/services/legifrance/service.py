import os
import logging
from typing import List, Dict, Any, Optional, Union
from fastmcp import FastMCP
from fastmcp.tools import Tool
from pylegifrance import LegifranceClient
from pylegifrance.config import ApiConfig
from pylegifrance.fonds.loda import Loda
from pylegifrance.fonds.juri import JuriAPI
from pylegifrance.fonds.code import Code
from starlette.requests import Request
from starlette.responses import PlainTextResponse

logger = logging.getLogger(__name__)

# Singleton client instance
_legifrance_client: Optional[LegifranceClient] = None

def _get_legifrance_client() -> LegifranceClient:
    """
    Helper function to initialize the Legifrance client with proper authentication.
    Implements a singleton pattern to reuse the client instance.
    
    Returns:
        LegifranceClient: An authenticated client instance.
        
    Raises:
        ValueError: If required environment variables are missing.
    """
    global _legifrance_client
    
    # Return the existing client if already initialized
    if _legifrance_client is not None:
        return _legifrance_client
    
    # Récupération des identifiants depuis les variables d'environnement
    client_id = os.getenv("LEGIFRANCE_CLIENT_ID")
    client_secret = os.getenv("LEGIFRANCE_CLIENT_SECRET")
    
    # Vérification que les variables sont définies
    if not client_id or not client_secret:
        raise ValueError("Les variables d'environnement LEGIFRANCE_CLIENT_ID et/ou LEGIFRANCE_CLIENT_SECRET ne sont pas définies.")
    
    # Initialisation du client sans paramètres - il lit automatiquement les variables d'environnement
    _legifrance_client = LegifranceClient()
    
    return _legifrance_client

async def rechercher_textes_juridiques(mots_cles: str) -> List[Dict[str, str]]:
    """
    Recherche des documents juridiques français (lois, décrets, articles de code, jurisprudences) par mots-clés.
    """
    try:
        # Initialisation du client Legifrance
        client = _get_legifrance_client()
        
        # Initialisation des classes LODA et JURI
        loda = Loda(client)
        juri = JuriAPI(client)
        
        # Recherche dans les deux fonds
        loda_results = loda.search(mots_cles)
        juri_results = juri.search(mots_cles)
        
        # Formatage des résultats LODA
        formatted_loda_results = []
        for result in loda_results:
            # Déterminer la nature du document
            nature = getattr(result, 'nature', 'ARTICLE_CODE')
            if not nature:
                nature = "ARTICLE_CODE"
            
            titre = getattr(result, 'title', '') or getattr(result, 'titre', '')
            doc_id = getattr(result, 'id', '')
            
            # Construction de l'URL selon le type de document
            if doc_id.startswith('LEGI'):
                url = f"https://www.legifrance.gouv.fr/eli/id/{doc_id}"
            elif doc_id.startswith('JORF'):
                url = f"https://www.legifrance.gouv.fr/jorf/id/{doc_id}"
            else:
                url = f"https://www.legifrance.gouv.fr/codes/id/{doc_id}"
            
            formatted_loda_results.append({
                "titre": titre,
                "id": doc_id,
                "nature": nature,
                "url": url
            })
        
        # Formatage des résultats JURI
        formatted_juri_results = []
        for result in juri_results:
            titre = getattr(result, 'title', '') or getattr(result, 'titre', '') or getattr(result, 'long_title', '')
            doc_id = getattr(result, 'id', '')
            
            formatted_juri_results.append({
                "titre": titre,
                "id": doc_id,
                "nature": "JURISPRUDENCE",
                "url": f"https://www.legifrance.gouv.fr/juri/id/{doc_id}"
            })
        
        # Fusion des résultats
        all_results = formatted_loda_results + formatted_juri_results
        
        return all_results
    
    except Exception as e:
        raise Exception(f"Erreur de l'API Légifrance: {str(e)}")

async def consulter_document_par_id(id_document: str) -> Optional[Dict[str, str]]:
    """
    Récupère le contenu complet d'un document juridique à partir de son ID unique.
    """
    try:
        # Initialisation du client Legifrance
        client = _get_legifrance_client()
        
        # Inspection du préfixe de l'ID pour déterminer le type de document
        if id_document.startswith("JURI"):
            # Utilisation de la classe Juri pour les jurisprudences
            juri = JuriAPI(client)
            document = juri.fetch(id_document)
        elif id_document.startswith("LEGIARTI"):
            # Utilisation de la classe Code pour les articles de code
            code = Code(client)
            document = code.fetch_article(id_document)
        else:
            # ID non reconnu
            return None
        
        # Si le document n'a pas été trouvé
        if document is None:
            return None
        
        # Formatage de la réponse
        titre = getattr(document, 'title', '') or getattr(document, 'titre', '') or getattr(document, 'long_title', '')
        contenu_html = getattr(document, 'content', '') or getattr(document, 'text', '')
        
        # Construction de l'URL
        if id_document.startswith("JURI"):
            url = f"https://www.legifrance.gouv.fr/juri/id/{id_document}"
        elif id_document.startswith("LEGIARTI"):
            url = f"https://www.legifrance.gouv.fr/codes/article_lc/{id_document}"
        elif id_document.startswith("LEGITEXT"):
            url = f"https://www.legifrance.gouv.fr/eli/id/{id_document}"
        else:
            url = f"https://www.legifrance.gouv.fr"
        
        return {
            "titre": titre,
            "id": id_document,
            "contenu_html": contenu_html,
            "url": url
        }
    
    except Exception as e:
        raise Exception(f"Erreur de l'API Légifrance: {str(e)}")

def create_legifrance_mcp_server() -> FastMCP:
    """
    Crée et configure le serveur FastMCP pour les outils Légifrance basés sur pylegifrance.
    """
    # Initialisation du serveur FastMCP
    mcp = FastMCP(name="legifrance_pylegi_service")
    
    # Création des objets Tool pour chaque fonction d'outil
    tool1 = Tool.from_function(fn=rechercher_textes_juridiques, name="rechercher_textes_juridiques")
    tool2 = Tool.from_function(fn=consulter_document_par_id, name="consulter_document_par_id")
    
    # Ajout des outils au serveur MCP
    mcp.add_tool(tool1)
    mcp.add_tool(tool2)
    
    # Ajout d'un endpoint de santé
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")
    
    # Retourne l'instance FastMCP configurée
    return mcp