#!/usr/bin/env python3
"""
Point d'entrée principal pour l'application Agent DataInclusion intégrée.

Ce script orchestre l'assemblage et le lancement de l'application web combinée qui expose :
- L'agent IA d'inclusion sociale via FastAPI (/api/*)
- L'interface Gradio moderne (/chat/*)
- Documentation interactive (/docs)
- Health checks (/health)

L'application utilise l'architecture FastAPI + Gradio pour offrir
une expérience utilisateur complète et une API programmatique.
"""

import os
import sys

try:
    import uvicorn
    from src.core.config import settings
    from src.core.logging import setup_logging
    from src.app.factory import create_app as create_base_app
    from src.ui.chat import mount_gradio_interface

    # Configuration du logging
    logger = setup_logging(name="datainclusion.agent")

    def create_app():
        """
        Orchestre l'assemblage de l'application FastAPI combinée avec Gradio.

        Utilise la factory d'application pour créer l'instance FastAPI de base,
        puis délègue le montage de l'interface Gradio au module UI.

        Returns:
            Instance FastAPI configurée avec Gradio
        """
        # Créer l'application FastAPI de base via la factory
        app = create_base_app()

        # Déléguer le montage de l'interface Gradio au module UI
        app = mount_gradio_interface(app)

        return app

    def run_app():
        """Lance l'application selon l'environnement configuré."""
        # Déterminer le mode d'exécution
        environment = os.getenv("ENVIRONMENT", "production").lower()
        is_development = environment == "development"

        if is_development:
            logger.info("🔧 Démarrage de l'application en mode DÉVELOPPEMENT")
            logger.info("📋 Configuration:")
            logger.info("   - Host: 0.0.0.0")
            logger.info(f"   - Port: {settings.agent.AGENT_PORT}")
            logger.info("   - Auto-reload: Activé")
            logger.info(
                f"   - Interface Gradio: http://localhost:{settings.agent.AGENT_PORT}/chat"
            )
            logger.info(
                f"   - API Agent: http://localhost:{settings.agent.AGENT_PORT}/api"
            )
            logger.info(
                f"   - Documentation: http://localhost:{settings.agent.AGENT_PORT}/docs"
            )
            logger.info(
                f"   - Health Check: http://localhost:{settings.agent.AGENT_PORT}/health"
            )

            uvicorn.run(
                "main:app",
                host="0.0.0.0",
                port=settings.agent.AGENT_PORT,
                reload=True,
                reload_dirs=["src", "static"],
                reload_excludes=[
                    "*.pyc",
                    "__pycache__",
                    "*.log",
                    "feedback_data",
                    "exports",
                ],
                log_level="info",
                access_log=True,
                use_colors=True,
            )
        else:
            logger.info("🚀 Démarrage de l'application en mode PRODUCTION")
            logger.info("📋 Configuration:")
            logger.info("   - Host: 0.0.0.0")
            logger.info(f"   - Port: {settings.agent.AGENT_PORT}")
            logger.info(
                f"   - Interface Gradio: http://localhost:{settings.agent.AGENT_PORT}/chat"
            )
            logger.info(
                f"   - API Agent: http://localhost:{settings.agent.AGENT_PORT}/api"
            )
            logger.info(
                f"   - Documentation: http://localhost:{settings.agent.AGENT_PORT}/docs"
            )
            logger.info(
                f"   - Health Check: http://localhost:{settings.agent.AGENT_PORT}/health"
            )

            uvicorn.run(
                app,
                host="0.0.0.0",
                port=settings.agent.AGENT_PORT,
                log_level="info",
                access_log=True,
                reload=False,
                workers=1,  # Gradio ne supporte pas bien les workers multiples
            )

    # Instance de l'application
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

except ImportError as e:
    print(f"❌ Erreur d'importation: {e}")
    print("💡 Assurez-vous que toutes les dépendances sont installées:")
    print("   uv pip install --system -r pyproject.toml")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur inattendue: {e}")
    sys.exit(1)
