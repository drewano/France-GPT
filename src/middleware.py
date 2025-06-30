"""
Middleware personnalisés pour le serveur MCP DataInclusion.
"""

import time
import logging
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp import McpError
from mcp.types import ErrorData


class ErrorHandlingMiddleware(Middleware):
    """
    Middleware pour capturer les exceptions et les transformer en erreurs MCP standardisées.
    
    Ce middleware intercepte toutes les exceptions non gérées et les transforme en
    erreurs MCP standardisées avec des codes d'erreur appropriés pour le client.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialise le middleware de gestion d'erreurs.
        
        Args:
            logger: Instance du logger pour enregistrer les erreurs
        """
        self.logger = logger
    
    async def on_request(self, context: MiddlewareContext, call_next):
        """
        Intercepte les requêtes MCP pour capturer et standardiser les erreurs.
        
        Args:
            context: Contexte de la requête MCP contenant les métadonnées
            call_next: Fonction pour continuer la chaîne de middleware
            
        Returns:
            Le résultat de la requête après traitement
            
        Raises:
            McpError: Exception MCP standardisée avec ErrorData approprié
        """
        try:
            # Traiter la requête normalement
            return await call_next(context)
            
        except Exception as e:
            # Logger l'erreur de manière détaillée
            self.logger.error(
                f"Unhandled exception in {context.method}: {type(e).__name__}: {e}",
                exc_info=True  # Inclut la stack trace complète
            )
            
            # Transformer l'exception en erreur MCP standardisée
            # Code -32000 : Erreur interne du serveur (selon la spec JSON-RPC)
            error_data = ErrorData(
                code=-32000,
                message=f"Internal server error in {context.method}: {type(e).__name__}"
            )
            
            # Lever une McpError standardisée pour le client
            raise McpError(error_data)


class TimingMiddleware(Middleware):
    """
    Middleware pour mesurer et journaliser le temps d'exécution des requêtes MCP.
    
    Ce middleware intercepte toutes les requêtes MCP, mesure leur temps d'exécution
    et enregistre les métriques de performance via le système de logging.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialise le middleware de timing.
        
        Args:
            logger: Instance du logger pour enregistrer les métriques de performance
        """
        self.logger = logger
    
    async def on_request(self, context: MiddlewareContext, call_next):
        """
        Intercepte les requêtes MCP pour mesurer leur temps d'exécution.
        
        Args:
            context: Contexte de la requête MCP contenant les métadonnées
            call_next: Fonction pour continuer la chaîne de middleware
            
        Returns:
            Le résultat de la requête après traitement
        """
        # Enregistrer le temps de début
        start_time = time.perf_counter()
        
        try:
            # Traiter la requête
            result = await call_next(context)
            
            # Calculer la durée en millisecondes
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Journaliser le succès de la requête
            self.logger.info(
                f"Request {context.method} completed in {duration_ms:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            # Calculer la durée même en cas d'erreur
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Journaliser l'échec de la requête
            self.logger.warning(
                f"Request {context.method} failed after {duration_ms:.2f}ms: {type(e).__name__}: {e}"
            )
            
            # Re-lever l'exception pour ne pas interrompre le flux d'erreur
            raise 