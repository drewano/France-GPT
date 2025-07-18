#!/usr/bin/env python3
"""
Application Gradio intégrée avec FastAPI pour l'agent IA d'Inclusion Sociale.

Cette application combine :
- Le serveur FastAPI existant de l'agent IA (routes /api/*)
- L'interface Gradio moderne (routes /chat/*)
- Health checks pour les deux services

Architecture :
- /api/* : API REST de l'agent IA (chat/stream, health)
- /chat/* : Interface Gradio interactive
- / : Redirection vers l'interface Gradio
- /health : Health check global
- /docs : Documentation API FastAPI
"""

import os
from datetime import datetime
from pathlib import Path

import gradio as gr
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Imports locaux
from src.core.config import settings
from src.core.lifespan import lifespan
from src.core.logging import setup_logging
from src.api.router import api_router
from src.ui.chat import create_complete_interface

# Configuration du logging unifié
logger = setup_logging(name="datainclusion.agent")


def create_app() -> FastAPI:
    """
    Crée l'application FastAPI combinée avec Gradio.

    Returns:
        Instance FastAPI configurée
    """
    # Application principale
    app = FastAPI(
        title="Agent IA d'Inclusion Sociale - Interface Complète",
        description="Application complète combinant l'agent IA et l'interface Gradio",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configuration CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.agent.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Servir les fichiers statiques
    static_path = Path("static")
    if static_path.exists():
        app.mount("/static", StaticFiles(directory="static"), name="static")

    # Routes de l'application principale

    @app.get("/")
    async def root():
        """Redirection vers l'interface Gradio."""
        return RedirectResponse(url="/chat")

    @app.get("/health")
    async def health_check():
        """Health check global de l'application."""
        try:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "agent": {"healthy": True},
                        "interface": {"healthy": True},
                    },
                },
            )

        except Exception as e:
            logger.error(f"Erreur lors du health check: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
            )

    # Monter l'APIRouter sous /api
    app.include_router(api_router, prefix="/api")

    # Créer et monter l'interface Gradio
    # L'interface sera créée avec un agent qui sera résolu de manière paresseuse
    gradio_interface = create_complete_interface(app)
    app = gr.mount_gradio_app(app=app, blocks=gradio_interface, path="/chat")

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
        logger.info(f"   - API Agent: http://localhost:{settings.agent.AGENT_PORT}/api")
        logger.info(
            f"   - Documentation: http://localhost:{settings.agent.AGENT_PORT}/docs"
        )
        logger.info(
            f"   - Health Check: http://localhost:{settings.agent.AGENT_PORT}/health"
        )

        uvicorn.run(
            "src.gradio_app:app",
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
        logger.info(f"   - API Agent: http://localhost:{settings.agent.AGENT_PORT}/api")
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
    Point d'entrée pour l'exécution directe.
    
    Variables d'environnement supportées :
    - ENVIRONMENT : "production" ou "development" (défaut: production)
    - AGENT_PORT : Port d'écoute (défaut: 8001)
    - OPENAI_API_KEY : Clé API OpenAI (requis)
    - SECRET_KEY : Clé secrète pour les sessions (à changer en production)
    - CORS_ORIGINS : Domaines autorisés pour CORS (séparés par virgules)
    """
    run_app()
