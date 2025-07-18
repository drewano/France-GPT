"""
Configuration du logging pour l'application.

Ce module configure un système de logging cohérent pour tous les composants
de l'application, avec des niveaux et formatages appropriés pour le debugging
et la surveillance en production.
"""

import logging
import sys


def setup_logging(name: str, level: str = "INFO") -> logging.Logger:
    """
    Configure le système de logging pour l'application.

    Args:
        name: Nom du logger à créer
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)

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

    # Configuration du format de log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configuration du logger principal
    logger = logging.getLogger(name)
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

    return logger


def log_gradio_message(message, context: str = "GRADIO") -> None:
    """
    Log un message Gradio pour le debugging.

    Args:
        message: Message Gradio à logger
        context: Contexte du message (pour le logging)
    """
    # Obtenir le logger par défaut de l'application
    logger = logging.getLogger("datainclusion.agent")

    logger.debug(f"[{context}] Message: {message.role} - {message.metadata}")
    if isinstance(message.content, str) and len(message.content) < 200:
        logger.debug(f"[{context}] Content: {message.content}")
    else:
        logger.debug(f"[{context}] Content: {len(str(message.content))} caractères")


# Configuration par défaut si le module est importé
if __name__ != "__main__":
    # Configuration automatique lors de l'import
    setup_logging("mcp_server")
