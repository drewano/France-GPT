"""
Configuration du logging pour l'application.

Ce module configure un système de logging cohérent pour tous les composants
de l'application, avec des niveaux et formatages appropriés pour le debugging 
et la surveillance en production.
"""

import logging
import sys
from typing import Optional, Any


def setup_logging(level: str = "INFO", format_style: str = "standard") -> logging.Logger:
    """
    Configure le système de logging pour l'application.
    
    Args:
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_style: Style de formatage ("standard", "detailed", "json")
        
    Returns:
        Logger configuré pour l'application
    """
    
    # Configuration des niveaux de log
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = log_levels.get(level.upper(), logging.INFO)
    
    # Configuration des formats de log
    formats = {
        "standard": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
        "json": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # Format JSON peut être étendu
    }
    
    log_format = formats.get(format_style, formats["standard"])
    
    # Configuration du logger principal
    logger = logging.getLogger("mcp_server")
    logger.setLevel(log_level)
    
    # Supprimer les handlers existants pour éviter les doublons
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Créer un handler pour la console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Créer un formatter
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)
    
    # Ajouter le handler au logger
    logger.addHandler(console_handler)
    
    # Éviter la propagation vers le logger racine
    logger.propagate = False
    
    # Configuration du logger spécialisé pour les outils MCP
    setup_mcp_tools_logger(log_level, formatter)
    
    return logger


def setup_mcp_tools_logger(level: int, formatter: logging.Formatter) -> logging.Logger:
    """
    Configure un logger spécialisé pour les appels aux outils MCP.
    
    Args:
        level: Niveau de log
        formatter: Formatter pour les messages
        
    Returns:
        Logger spécialisé pour les outils MCP
    """
    
    # Créer le logger spécialisé
    tools_logger = logging.getLogger("mcp_server.tools")
    tools_logger.setLevel(level)
    
    # Supprimer les handlers existants
    for handler in tools_logger.handlers[:]:
        tools_logger.removeHandler(handler)
    
    # Créer un handler dédié pour les outils
    tools_handler = logging.StreamHandler(sys.stdout)
    tools_handler.setLevel(level)
    
    # Formatter spécialisé pour les outils MCP
    tools_formatter = logging.Formatter(
        "%(asctime)s - 🛠️ MCP_TOOLS - %(levelname)s - %(message)s"
    )
    tools_handler.setFormatter(tools_formatter)
    
    # Ajouter le handler
    tools_logger.addHandler(tools_handler)
    
    # Éviter la propagation
    tools_logger.propagate = False
    
    return tools_logger


def get_tools_logger() -> logging.Logger:
    """
    Récupère le logger spécialisé pour les outils MCP.
    
    Returns:
        Logger pour les outils MCP
    """
    return logging.getLogger("mcp_server.tools")


def log_tool_call(tool_name: str, arguments: dict, call_id: Optional[str] = None) -> None:
    """
    Log un appel d'outil MCP avec un formatage standardisé.
    
    Args:
        tool_name: Nom de l'outil appelé
        arguments: Arguments passés à l'outil
        call_id: ID unique de l'appel (optionnel)
    """
    tools_logger = get_tools_logger()
    
    # Formatage des arguments (truncation si trop long)
    args_str = str(arguments)
    if len(args_str) > 200:
        args_str = args_str[:200] + "..."
    
    # Message de log
    call_info = f"[{call_id}] " if call_id else ""
    tools_logger.info(f"{call_info}Appel outil: {tool_name} | Args: {args_str}")


def log_tool_result(tool_name: str, result: Any, call_id: Optional[str] = None, duration: Optional[float] = None) -> None:
    """
    Log le résultat d'un appel d'outil MCP.
    
    Args:
        tool_name: Nom de l'outil
        result: Résultat de l'outil
        call_id: ID unique de l'appel (optionnel)
        duration: Durée d'exécution en secondes (optionnel)
    """
    tools_logger = get_tools_logger()
    
    # Formatage du résultat (truncation si trop long)
    result_str = str(result)
    if len(result_str) > 300:
        result_str = result_str[:300] + "..."
    
    # Message de log
    call_info = f"[{call_id}] " if call_id else ""
    duration_info = f" ({duration:.3f}s)" if duration is not None else ""
    tools_logger.info(f"{call_info}Résultat outil: {tool_name}{duration_info} | Result: {result_str}")


def log_tool_error(tool_name: str, error: Exception, call_id: Optional[str] = None) -> None:
    """
    Log une erreur lors d'un appel d'outil MCP.
    
    Args:
        tool_name: Nom de l'outil
        error: Exception levée
        call_id: ID unique de l'appel (optionnel)
    """
    tools_logger = get_tools_logger()
    
    # Message de log
    call_info = f"[{call_id}] " if call_id else ""
    tools_logger.error(f"{call_info}Erreur outil: {tool_name} | Error: {type(error).__name__}: {error}")


def configure_gradio_logging() -> None:
    """
    Configure le logging pour l'intégration avec Gradio.
    
    Cette fonction configure les loggers pour qu'ils soient compatibles
    avec l'affichage dans l'interface Gradio.
    """
    
    # Logger spécialisé pour Gradio
    gradio_logger = logging.getLogger("mcp_server.gradio")
    gradio_logger.setLevel(logging.INFO)
    
    # Handler pour Gradio (peut être étendu pour envoyer vers l'interface)
    gradio_handler = logging.StreamHandler(sys.stdout)
    gradio_formatter = logging.Formatter(
        "%(asctime)s - 🎯 GRADIO_MCP - %(levelname)s - %(message)s"
    )
    gradio_handler.setFormatter(gradio_formatter)
    gradio_logger.addHandler(gradio_handler)
    gradio_logger.propagate = False


# Configuration par défaut si le module est importé
if __name__ != "__main__":
    # Configuration automatique lors de l'import
    setup_logging()
    configure_gradio_logging() 