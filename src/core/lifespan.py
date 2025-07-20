"""
Gestionnaire de cycle de vie pour l'application FastAPI.

Ce module contient la fonction de cycle de vie qui gère l'initialisation
et la finalisation de l'application FastAPI avec l'agent IA.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic_ai.mcp import MCPServerStreamableHTTP

# Imports locaux
from .config import settings
from src.agent.agent import create_agent_from_profile
from src.core.profiles import AGENT_PROFILES
from ..db.session import initialize_database

# Configuration du logging
logger = logging.getLogger("datainclusion.agent")


def setup_environment():
    """
    Configure l'environnement d'exécution de l'application.

    Cette fonction :
    - Affiche les avertissements de configuration
    - Valide les paramètres critiques
    """
    logger.info("🔧 Configuration de l'environnement...")

    # Avertissements pour la configuration
    if settings.agent.SECRET_KEY == "your-secret-key-here-change-in-production":
        logger.warning(
            "⚠️ SECRET_KEY utilise la valeur par défaut - à changer en production !"
        )

    if settings.agent.CORS_ORIGINS == ["*"]:
        logger.warning(
            "⚠️ CORS_ORIGINS autorise tous les domaines - à restreindre en production !"
        )

    if not settings.agent.OPENAI_API_KEY:
        logger.warning(
            "⚠️ OPENAI_API_KEY non définie - certaines fonctionnalités peuvent ne pas fonctionner"
        )

    logger.info("✅ Configuration de l'environnement terminée")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie pour l'application combinée.

    Gère la connexion au serveur MCP et l'initialisation de l'agent
    avec logique de retry et backoff exponentiel.

    Args:
        app: Instance FastAPI
    """
    logger.info("🚀 Démarrage de l'application Chainlit + FastAPI...")

    # Configuration de l'environnement
    setup_environment()

    # Initialisation de la base de données
    try:
        await initialize_database()
        logger.info("✅ Base de données initialisée avec succès")
    except Exception as e:
        logger.critical(f"❌ Échec de l'initialisation de la base de données: {e}")
        raise RuntimeError(
            f"L'application ne peut pas démarrer sans base de données: {e}"
        )

    # Création de l'agent avec le profil par défaut
    profile = AGENT_PROFILES["social_agent"]
    agent = create_agent_from_profile(profile)

    # Logique de connexion au MCP avec retry et backoff exponentiel
    max_retries = settings.agent.AGENT_MCP_CONNECTION_MAX_RETRIES
    base_delay = settings.agent.AGENT_MCP_CONNECTION_BASE_DELAY
    backoff_multiplier = settings.agent.AGENT_MCP_CONNECTION_BACKOFF_MULTIPLIER

    for attempt in range(max_retries):
        try:
            async with agent.run_mcp_servers():
                # Stocker l'instance de l'agent dans l'état de l'application
                app.state.agent = agent

                logger.info("✅ Application initialisée avec succès")

                # Application prête
                yield

                # Code après yield s'exécute lors du shutdown
                break

        except Exception as e:
            if attempt == max_retries - 1:
                # Dernière tentative échouée
                raise RuntimeError(
                    f"Échec de la connexion au serveur MCP après {max_retries} tentatives: {e}"
                )

            # Calcul du délai avec backoff exponentiel
            delay = base_delay * (backoff_multiplier**attempt)

            logger.warning(
                f"Tentative {attempt + 1}/{max_retries} échouée. "
                f"Nouvelle tentative dans {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

    # Nettoyage lors du shutdown
    logger.info("🛑 Arrêt de l'application...")
    logger.info("✅ Nettoyage terminé")
