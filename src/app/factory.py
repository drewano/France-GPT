"""
Factory d'application FastAPI pour l'agent IA d'Inclusion Sociale.

Cette factory centralise la création et la configuration de l'instance FastAPI,
en séparant la logique de l'application de celle du lancement du serveur.
"""

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Imports locaux
from src.core.config import settings
from src.core.lifespan import lifespan
from src.core.logging import setup_logging
from src.api.router import api_router
from chainlit.utils import mount_chainlit

# Configuration du logging unifié
logger = setup_logging(name="datainclusion.agent")


def create_app() -> FastAPI:
    """
    Crée l'application FastAPI configurée complète avec l'interface Gradio.

    Cette fonction centralise la création et la configuration de l'instance
    FastAPI, incluant :
    - Configuration de base (titre, description, cycle de vie)
    - Middleware CORS
    - Montage des fichiers statiques
    - Routes de base (/, /health)
    - Inclusion du routeur API
    - Montage de l'interface Gradio

    Returns:
        Instance FastAPI configurée complète avec l'interface Gradio montée
    """
    # Application principale
    app = FastAPI(
        title="Agent IA d'Inclusion Sociale - Interface Chainlit",
        description="Application complète combinant l'agent IA et l'interface Chainlit",
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

    @app.get("/api-info")
    async def api_info():
        """Information sur l'API - Chainlit gère maintenant la racine."""
        return {"message": "API is running. Access the chat at /", "api_docs": "/docs"}

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

    # Monter l'interface Chainlit à la racine
    mount_chainlit(app=app, target="src/ui/chat.py", path="/")

    return app
