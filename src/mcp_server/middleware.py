"""
Middlewares personnalisés pour le serveur MCP DataInclusion.

Ce module contient les middlewares qui ajoutent des fonctionnalités transversales
au serveur MCP, comme la gestion d'erreurs, le timing et le logging des appels aux outils.
"""

import logging
import time
import json
from typing import Any, Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from mcp.types import CallToolRequest, CallToolResult


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de gestion d'erreurs pour le serveur MCP.
    
    Ce middleware capture les erreurs non gérées et les transforme en réponses
    appropriées pour les clients MCP.
    """
    
    def __init__(self, app: ASGIApp, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Traite les requêtes avec gestion d'erreurs.
        
        Args:
            request: La requête HTTP entrante
            call_next: La fonction suivante dans la chaîne de middleware
            
        Returns:
            Response: La réponse HTTP avec gestion d'erreurs
        """
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            self.logger.error(f"Erreur non gérée dans le serveur MCP: {e}")
            # Retourner une réponse d'erreur appropriée
            return Response(
                content=json.dumps({"error": str(e)}),
                status_code=500,
                media_type="application/json"
            )


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de timing pour mesurer les performances des requêtes.
    
    Ce middleware mesure le temps de traitement de chaque requête et le log.
    """
    
    def __init__(self, app: ASGIApp, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Traite les requêtes avec mesure du temps.
        
        Args:
            request: La requête HTTP entrante
            call_next: La fonction suivante dans la chaîne de middleware
            
        Returns:
            Response: La réponse HTTP avec timing
        """
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log le timing
        self.logger.info(f"Requête {request.method} {request.url.path} traitée en {process_time:.4f}s")
        
        # Ajouter le timing dans les headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class MCPToolCallLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware spécialisé pour logger les appels aux outils MCP.
    
    Ce middleware capture et log en détail tous les appels aux outils MCP,
    incluant les arguments, les résultats et les métadonnées.
    """
    
    def __init__(self, app: ASGIApp, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger
        self.call_counter = 0
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Traite les requêtes avec logging des appels aux outils MCP.
        
        Args:
            request: La requête HTTP entrante
            call_next: La fonction suivante dans la chaîne de middleware
            
        Returns:
            Response: La réponse HTTP avec logging des outils
        """
        # Incrémenter le compteur d'appels
        self.call_counter += 1
        call_id = self.call_counter
        
        # Vérifier si c'est un appel d'outil MCP
        is_tool_call = self._is_tool_call_request(request)
        
        if is_tool_call:
            # Logger le début de l'appel d'outil
            tool_info = await self._extract_tool_info(request)
            self.logger.info(f"🛠️ [Appel #{call_id}] Début appel outil: {tool_info.get('name', 'Unknown')}")
            self.logger.debug(f"🛠️ [Appel #{call_id}] Arguments: {tool_info.get('arguments', {})}")
            
            start_time = time.time()
        
        # Traiter la requête
        response = await call_next(request)
        
        if is_tool_call:
            # Logger le résultat de l'appel d'outil
            process_time = time.time() - start_time
            
            try:
                # Extraire le résultat de la réponse
                result_info = await self._extract_result_info(response)
                
                self.logger.info(f"✅ [Appel #{call_id}] Outil terminé en {process_time:.4f}s")
                self.logger.debug(f"✅ [Appel #{call_id}] Résultat: {result_info}")
                
                # Logger des statistiques supplémentaires
                if result_info.get('is_error', False):
                    self.logger.warning(f"⚠️ [Appel #{call_id}] Erreur dans l'outil: {result_info.get('error', 'Unknown')}")
                else:
                    result_size = len(str(result_info.get('content', '')))
                    self.logger.debug(f"📊 [Appel #{call_id}] Taille résultat: {result_size} caractères")
                
            except Exception as e:
                self.logger.error(f"❌ [Appel #{call_id}] Erreur lors de l'extraction du résultat: {e}")
        
        return response
    
    def _is_tool_call_request(self, request: Request) -> bool:
        """
        Vérifie si la requête est un appel d'outil MCP.
        
        Args:
            request: La requête HTTP
            
        Returns:
            bool: True si c'est un appel d'outil MCP
        """
        # Vérifier l'URL et la méthode pour les appels d'outils MCP
        path = request.url.path
        method = request.method
        
        # Les appels d'outils MCP sont généralement des POST vers /mcp/tools/<tool_name>
        return (method == "POST" and 
                ("/mcp" in path or "/tools" in path or "/call_tool" in path))
    
    async def _extract_tool_info(self, request: Request) -> Dict[str, Any]:
        """
        Extrait les informations sur l'outil depuis la requête.
        
        Args:
            request: La requête HTTP
            
        Returns:
            Dict: Informations sur l'outil (nom, arguments, etc.)
        """
        tool_info = {
            "name": "Unknown",
            "arguments": {},
            "path": request.url.path,
            "method": request.method
        }
        
        try:
            # Extraire le nom de l'outil depuis l'URL
            path_parts = request.url.path.split('/')
            if len(path_parts) > 1:
                tool_info["name"] = path_parts[-1]
            
            # Tenter d'extraire les arguments du body (si applicable)
            if hasattr(request, '_body') and request._body:
                try:
                    body_json = json.loads(request._body.decode())
                    if isinstance(body_json, dict):
                        tool_info["arguments"] = body_json.get("arguments", {})
                except (json.JSONDecodeError, AttributeError):
                    pass
            
        except Exception as e:
            self.logger.debug(f"Impossible d'extraire les info de l'outil: {e}")
        
        return tool_info
    
    async def _extract_result_info(self, response: Response) -> Dict[str, Any]:
        """
        Extrait les informations sur le résultat depuis la réponse.
        
        Args:
            response: La réponse HTTP
            
        Returns:
            Dict: Informations sur le résultat
        """
        result_info = {
            "status_code": response.status_code,
            "content": "",
            "is_error": response.status_code >= 400
        }
        
        try:
            # Extraire le contenu de la réponse
            if hasattr(response, 'body') and response.body:
                try:
                    body_content = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
                    result_info["content"] = body_content[:500] + "..." if len(body_content) > 500 else body_content
                    
                    # Tenter de parser comme JSON
                    try:
                        parsed_content = json.loads(body_content)
                        if isinstance(parsed_content, dict):
                            result_info["is_error"] = parsed_content.get("isError", False)
                            if "error" in parsed_content:
                                result_info["error"] = parsed_content["error"]
                    except json.JSONDecodeError:
                        pass
                        
                except Exception as e:
                    result_info["content"] = f"Erreur lors de l'extraction: {e}"
                    
        except Exception as e:
            self.logger.debug(f"Impossible d'extraire les info du résultat: {e}")
        
        return result_info


class MCPRequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour logger toutes les requêtes et réponses MCP.
    
    Ce middleware fournit un logging complet de toutes les interactions MCP.
    """
    
    def __init__(self, app: ASGIApp, logger: logging.Logger, log_bodies: bool = False):
        super().__init__(app)
        self.logger = logger
        self.log_bodies = log_bodies
        self.request_counter = 0
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Traite les requêtes avec logging complet.
        
        Args:
            request: La requête HTTP entrante
            call_next: La fonction suivante dans la chaîne de middleware
            
        Returns:
            Response: La réponse HTTP avec logging complet
        """
        self.request_counter += 1
        req_id = self.request_counter
        
        # Logger la requête entrante
        self.logger.info(f"📥 [Req #{req_id}] {request.method} {request.url.path}")
        
        if self.log_bodies:
            try:
                # Logger les headers importants
                headers = dict(request.headers)
                filtered_headers = {k: v for k, v in headers.items() 
                                  if k.lower() not in ['authorization', 'cookie']}
                self.logger.debug(f"📥 [Req #{req_id}] Headers: {filtered_headers}")
                
                # Logger le body si disponible
                if hasattr(request, '_body') and request._body:
                    body_content = request._body.decode()[:1000]  # Limiter à 1000 caractères
                    self.logger.debug(f"📥 [Req #{req_id}] Body: {body_content}")
                    
            except Exception as e:
                self.logger.debug(f"📥 [Req #{req_id}] Erreur lors du logging du body: {e}")
        
        start_time = time.time()
        
        # Traiter la requête
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Logger la réponse
        self.logger.info(f"📤 [Req #{req_id}] {response.status_code} ({process_time:.4f}s)")
        
        if self.log_bodies and hasattr(response, 'body'):
            try:
                body_content = str(response.body)[:1000]  # Limiter à 1000 caractères
                self.logger.debug(f"📤 [Req #{req_id}] Response body: {body_content}")
            except Exception as e:
                self.logger.debug(f"📤 [Req #{req_id}] Erreur lors du logging du body de réponse: {e}")
        
        return response 