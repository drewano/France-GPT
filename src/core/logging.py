"""
Configuration du logging pour l'application.

Ce module configure un système de logging cohérent pour tous les composants
de l'application, avec des niveaux et formatages appropriés pour le debugging
et la surveillance en production.
"""

import logging
import sys


def setup_logging(
    level: str = "INFO", format_style: str = "standard"
) -> logging.Logger:
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
        "CRITICAL": logging.CRITICAL,
    }

    log_level = log_levels.get(level.upper(), logging.INFO)

    # Configuration des formats de log
    formats = {
        "standard": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
        "json": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Format JSON peut être étendu
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


# Configuration par défaut si le module est importé
if __name__ != "__main__":
    # Configuration automatique lors de l'import
    setup_logging()
