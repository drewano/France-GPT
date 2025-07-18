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

try:
    from src.gradio_app import run_app
    from src.core.logging import setup_logging

    # Configuration du logging
    logger = setup_logging(name="datainclusion.agent")

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
