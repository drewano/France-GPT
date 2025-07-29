"""
Gestionnaire de cycle de vie pour l'application FastAPI.

Ce module contient la fonction de cycle de vie qui gère l'initialisation
et la finalisation de l'application FastAPI avec l'agent IA.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx  # Import httpx

# Langfuse and Pydantic AI imports
from langfuse import get_client
from pydantic_ai.agent import Agent

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

    Gère la connexion aux serveurs MCP et l'initialisation de la base de données
    avec une logique de retry et backoff exponentiel.

    Args:
        _app: Instance FastAPI (renamed to _app as it's not directly used)
    """
    logger.info("🚀 Démarrage de l'application Chainlit + FastAPI...")

    # Configuration de l'environnement
    setup_environment()

    # Configuration des variables d'environnement pour Langfuse
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.agent.LANGFUSE_PUBLIC_KEY
    os.environ["LANGFUSE_SECRET_KEY"] = settings.agent.LANGFUSE_SECRET_KEY
    if settings.agent.LANGFUSE_HOST:
        os.environ["LANGFUSE_HOST"] = settings.agent.LANGFUSE_HOST

    # Initialisation de l'instrumentation et vérification de l'authentification
    if settings.agent.LANGFUSE_PUBLIC_KEY and settings.agent.LANGFUSE_SECRET_KEY:
        logger.info(" Initialisation de l'instrumentation Langfuse pour Pydantic AI...")
        Agent.instrument_all()
        langfuse_client = get_client()
        if langfuse_client.auth_check():
            logger.info("✅ Connexion à Langfuse réussie.")
        else:
            logger.error(
                "❌ Échec de l'authentification à Langfuse. Veuillez vérifier vos clés."
            )
            # Optionnel mais recommandé : lever une exception pour empêcher le démarrage
            # raise RuntimeError("Échec de la connexion à Langfuse.")
    else:
        logger.warning("⚠️ Clés Langfuse non fournies. Le tracing est désactivé.")

    # Initialisation de la base de données
    try:
        await initialize_database()
        logger.info("✅ Base de données initialisée avec succès")
    except Exception as e:
        logger.critical("❌ Échec de l'initialisation de la base de données: %s", e)
        raise RuntimeError(
            f"L'application ne peut pas démarrer sans base de données: {e}"
        ) from e

    # Logique de connexion aux serveurs MCP avec retry et backoff exponentiel
    max_retries = settings.agent.AGENT_MCP_CONNECTION_MAX_RETRIES
    base_delay = settings.agent.AGENT_MCP_CONNECTION_BASE_DELAY
    backoff_multiplier = settings.agent.AGENT_MCP_CONNECTION_BACKOFF_MULTIPLIER

    all_services_healthy = False
    for attempt in range(max_retries):
        try:
            logger.info("🩺 Vérification de la santé des serveurs MCP...")
            all_services_healthy = True
            service_configs = settings.mcp_services
            if not service_configs:
                logger.warning(
                    "Aucun service MCP n'est configuré. Démarrage sans vérification."
                )
                break

            async with httpx.AsyncClient() as client:
                for service_config in service_configs:
                    health_check_url = f"http://mcp_server:{service_config.port}/health"
                    logger.info(
                        "   - Test de '%s' sur le port %s...",
                        service_config.name,
                        service_config.port,
                    )
                    response = await client.get(health_check_url)
                    response.raise_for_status()
                    logger.info("   ✓ Le service '%s' est sain.", service_config.name)

            # Si toutes les vérifications ont réussi, on sort de la boucle
            break

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            all_services_healthy = False
            error_details = (
                f"({e.response.status_code} - {e.response.text})"
                if isinstance(e, httpx.HTTPStatusError)
                else str(e)
            )
            logger.warning("❌ Un service MCP n'est pas encore prêt: %s", error_details)
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Échec de la connexion aux serveurs MCP après {max_retries} tentatives."
                ) from e
            delay = base_delay * (backoff_multiplier**attempt)
            logger.warning(
                "Tentative %d/%d échouée. Nouvelle tentative dans %.2fs...",
                attempt + 1,
                max_retries,
                delay,
            )
            await asyncio.sleep(delay)

    if all_services_healthy:
        logger.info("✅ Tous les serveurs MCP sont sains et joignables.")
        # L'application est prête
        yield
        # Le code après yield s'exécute lors du shutdown
        logger.info("🛑 Arrêt de l'application...")
        logger.info("✅ Nettoyage terminé")
    else:
        # Si on arrive ici, c'est que la boucle s'est terminée sans succès
        logger.critical(
            "❌ Impossible de démarrer : tous les services MCP ne sont pas disponibles."
        )
