"""
Gestionnaire de cycle de vie pour l'application FastAPI.

Ce module contient la fonction de cycle de vie qui gère l'initialisation
et la finalisation de l'application FastAPI avec l'agent IA.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx  # Import httpx

# Imports locaux
from .config import settings
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
async def lifespan(_app: FastAPI):
    """
    Gestionnaire de cycle de vie pour l'application combinée.

    Gère la connexion au serveur MCP et l'initialisation de l'agent
    avec logique de retry et backoff exponentiel.

    Args:
        _app: Instance FastAPI (renamed to _app as it's not directly used)
    """
    logger.info("🚀 Démarrage de l'application Chainlit + FastAPI...")

    # Configuration de l'environnement
    setup_environment()

    # Initialisation de la base de données
    try:
        await initialize_database()
        logger.info("✅ Base de données initialisée avec succès")
    except Exception as e:
        logger.critical("❌ Échec de l'initialisation de la base de données: %s", e)
        raise RuntimeError(
            f"L'application ne peut pas démarrer sans base de données: {e}"
        ) from e

    # Logique de connexion au MCP avec retry et backoff exponentiel
    max_retries = settings.agent.AGENT_MCP_CONNECTION_MAX_RETRIES
    base_delay = settings.agent.AGENT_MCP_CONNECTION_BASE_DELAY
    backoff_multiplier = settings.agent.AGENT_MCP_CONNECTION_BACKOFF_MULTIPLIER

    for attempt in range(max_retries):
        try:
            health_check_url = (
                f"http://mcp_server:{settings.mcp_gateway.MCP_PORT}/health"
            )
            async with httpx.AsyncClient() as client:
                response = await client.get(health_check_url)
                response.raise_for_status()  # Lève une exception pour les codes d'état 4xx/5xx

            logger.info("✅ MCP Gateway is healthy and reachable.")

            # Application prête
            yield

            # Code après yield s'exécute lors du shutdown
            break

        except httpx.HTTPStatusError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Échec de la connexion au serveur MCP après {max_retries} tentatives: {e.response.status_code} - {e.response.text}"
                ) from e
            delay = base_delay * (backoff_multiplier**attempt)
            logger.warning(
                "Tentative %d/%d échouée (HTTP Status: %s). Nouvelle tentative dans %.2fs...",
                attempt + 1,
                max_retries,
                e.response.status_code,
                delay,
            )
            await asyncio.sleep(delay)
        except httpx.RequestError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Échec de la connexion au serveur MCP après {max_retries} tentatives: {e}"
                ) from e
            delay = base_delay * (backoff_multiplier**attempt)
            logger.warning(
                "Tentative %d/%d échouée (Request Error: %s). Nouvelle tentative dans %.2fs...",
                attempt + 1,
                max_retries,
                e,
                delay,
            )
            await asyncio.sleep(delay)
        except Exception as e:
            if attempt == max_retries - 1:
                # Dernière tentative échouée
                raise e
            # Calcul du délai avec backoff exponentiel
            delay = base_delay * (backoff_multiplier**attempt)

            logger.warning(
                "Tentative %d/%d échouée. Nouvelle tentative dans %.2fs...",
                attempt + 1,
                max_retries,
                delay,
            )
            await asyncio.sleep(delay)

    # Nettoyage lors du shutdown
    logger.info("🛑 Arrêt de l'application...")
    logger.info("✅ Nettoyage terminé")
