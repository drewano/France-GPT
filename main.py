#!/usr/bin/env python3
"""
Point d'entrée principal pour l'application Agent DataInclusion intégrée.

Ce script lance l'application web combinée qui expose :
- L'agent IA d'inclusion sociale via FastAPI (/api/*)
- L'interface Gradio moderne (/chat/*)
- Documentation interactive (/docs)
- Health checks (/health)

L'application utilise l'architecture FastAPI + Gradio pour offrir
une expérience utilisateur complète et une API programmatique.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire src au path Python
try:
    import uvicorn
    from src.core.config import AgentSettings
    from src.gradio_app import app, logger

    def setup_environment():
        """Configure l'environnement pour l'exécution."""
        # Créer les répertoires nécessaires
        directories = ["logs", "feedback_data", "exports", "static"]

        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
            logger.info(f"📁 Répertoire créé/vérifié: {directory}")

        # Vérifier les variables d'environnement critiques
        settings = AgentSettings()

        # Avertissements pour la configuration
        if settings.SECRET_KEY == "your-secret-key-here-change-in-production":
            logger.warning(
                "⚠️ SECRET_KEY utilise la valeur par défaut - à changer en production !"
            )

        if settings.CORS_ORIGINS == ["*"]:
            logger.warning(
                "⚠️ CORS_ORIGINS autorise tous les domaines - à restreindre en production !"
            )

        if not settings.OPENAI_API_KEY:
            logger.warning(
                "⚠️ OPENAI_API_KEY non définie - certaines fonctionnalités peuvent ne pas fonctionner"
            )

        logger.info("✅ Configuration de l'environnement terminée")
        return settings

    def run_app():
        """Lance l'application selon l'environnement configuré."""
        settings = setup_environment()

        # Déterminer le mode d'exécution
        environment = os.getenv("ENVIRONMENT", "production").lower()
        is_development = environment == "development"

        if is_development:
            logger.info("🔧 Démarrage de l'application en mode DÉVELOPPEMENT")
            logger.info("📋 Configuration:")
            logger.info("   - Host: 0.0.0.0")
            logger.info(f"   - Port: {settings.AGENT_PORT}")
            logger.info("   - Auto-reload: Activé")
            logger.info(
                f"   - Interface Gradio: http://localhost:{settings.AGENT_PORT}/chat"
            )
            logger.info(f"   - API Agent: http://localhost:{settings.AGENT_PORT}/api")
            logger.info(
                f"   - Documentation: http://localhost:{settings.AGENT_PORT}/docs"
            )
            logger.info(
                f"   - Health Check: http://localhost:{settings.AGENT_PORT}/health"
            )

            uvicorn.run(
                "src.gradio_app:app",
                host="0.0.0.0",
                port=settings.AGENT_PORT,
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
            logger.info(f"   - Port: {settings.AGENT_PORT}")
            logger.info(
                f"   - Interface Gradio: http://localhost:{settings.AGENT_PORT}/chat"
            )
            logger.info(f"   - API Agent: http://localhost:{settings.AGENT_PORT}/api")
            logger.info(
                f"   - Documentation: http://localhost:{settings.AGENT_PORT}/docs"
            )
            logger.info(
                f"   - Health Check: http://localhost:{settings.AGENT_PORT}/health"
            )

            uvicorn.run(
                app,
                host="0.0.0.0",
                port=settings.AGENT_PORT,
                log_level="info",
                access_log=True,
                reload=False,
                workers=1,  # Gradio ne supporte pas bien les workers multiples
            )

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
