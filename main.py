#!/usr/bin/env python3
"""
Point d'entrée principal pour l'application Agent DataInclusion intégrée.

Ce script orchestre l'assemblage et le lancement de l'application web combinée qui expose :
- L'agent IA d'inclusion sociale via FastAPI (/api/*)
- L'interface Chainlit moderne (/chat/*)
- Documentation interactive (/docs)
- Health checks (/health)

L'application utilise l'architecture FastAPI + Chainlit pour offrir
une expérience utilisateur complète et une API programmatique.
"""

import os
import sys

try:
    import uvicorn
    from src.core.config import settings
    from src.core.logging import setup_logging
    from src.app.factory import create_app

    # Configuration du logging
    logger = setup_logging(name="datainclusion.agent")

    def log_server_config(port: int):
        """Log la configuration du serveur FastAPI."""
        logger.info("📋 Configuration:")
        logger.info("   - Host: 0.0.0.0")
        logger.info(f"   - Port: {port}")
        logger.info(f"   - Interface Chainlit: http://localhost:{port}/")
        logger.info(f"   - Documentation: http://localhost:{port}/docs")
        logger.info(f"   - Health Check: http://localhost:{port}/health")

    def run_app():
        """Lance l'application selon l'environnement configuré."""
        # Déterminer le mode d'exécution
        environment = os.getenv("ENVIRONMENT", "production").lower()
        is_development = environment == "development"

        if is_development:
            logger.info("🔧 Démarrage de l'application en mode DÉVELOPPEMENT")
        else:
            logger.info("🚀 Démarrage de l'application en mode PRODUCTION")

        log_server_config(settings.agent.AGENT_PORT)

        uvicorn_config = {
            "host": "0.0.0.0",
            "port": settings.agent.AGENT_PORT,
            "log_level": "info",
            "access_log": True,
            "use_colors": True,
        }

        if is_development:
            uvicorn_config.update(
                {
                    "reload": True,
                    "reload_dirs": ["src"],
                    "reload_excludes": [
                        "*.pyc",
                        "__pycache__",
                        "*.log",
                    ],
                }
            )
            uvicorn.run("main:app", **uvicorn_config)
        else:
            uvicorn_config.update(
                {
                    "reload": False,
                    "workers": 1,  # Chainlit ne supporte pas bien les workers multiples
                }
            )
            uvicorn.run(app, **uvicorn_config)

    # Instance de l'application entièrement configurée par la factory
    app = create_app()

    if __name__ == "__main__":
        """
        Point d'entrée du script.

        Variables d'environnement supportées :
        - ENVIRONMENT : "production" ou "development" (défaut: production)
        - AGENT_PORT : Port d'écoute (défaut: 8001)
        - OPENAI_API_KEY : Clé API OpenAI (requis)
        - SECRET_KEY : Clé secrète pour les sessions (à changer en production)
        - CORS_ORIGINS : Domaines autorisés pour CORS (séparés par virgules)
        """
        try:
            run_app()

        except KeyboardInterrupt:
            logger.info("👋 Arrêt demandé par l'utilisateur")
            print("\nGoodbye!")
        except Exception as e:
            logger.error(f"💥 Erreur fatale lors du démarrage: {e}")
            print(f"Failed to start server: {e}")
            sys.exit(1)

except Exception as e:
    print(f"❌ Erreur inattendue: {e}")
    sys.exit(1)
