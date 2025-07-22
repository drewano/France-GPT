"""
Gestion des sessions de base de données et initialisation du schéma.

Ce module contient la logique d'initialisation de la base de données PostgreSQL
pour Chainlit, utilisant les modèles SQLAlchemy définis dans models.py.

Fonctionnalités:
    - Initialisation asynchrone de la base de données
    - Création idempotente du schéma avec create_all()
    - Gestion robuste des erreurs et logging détaillé
    - Configuration automatique à partir des settings
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import settings
from .models import Base


async def initialize_database():
    """
    Initialise la base de données PostgreSQL avec le schéma requis par Chainlit.

    Cette fonction crée toutes les tables nécessaires pour la persistance des données
    Chainlit en utilisant les modèles SQLAlchemy déclaratifs. Elle utilise create_all()
    pour une création idempotente et sûre du schéma.

    La fonction utilise une connexion asynchrone pour garantir la cohérence des
    opérations d'initialisation et s'assure que toutes les relations et contraintes
    sont correctement définies.

    Raises:
        Exception: Si l'initialisation de la base de données échoue
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "🚀 Début de l'initialisation de la base de données PostgreSQL pour Chainlit (SQLAlchemy)"
    )

    try:
        # Récupération de l'URL de la base de données depuis la configuration
        database_url = settings.agent.DATABASE_URL
        logger.info(
            "🔗 Connexion à la base de données : %s",
            database_url.split("@")[1] if "@" in database_url else "URL masquée",
        )

        # Création du moteur de base de données asynchrone
        engine = create_async_engine(database_url, echo=False)

        logger.info(
            "📋 Création du schéma de base de données avec les modèles SQLAlchemy..."
        )

        # Création de toutes les tables de manière idempotente
        # create_all() vérifie automatiquement l'existence des tables (équivalent à IF NOT EXISTS)
        async with engine.begin() as conn:
            # Exécution de create_all pour créer toutes les tables définies dans Base
            await conn.run_sync(Base.metadata.create_all)

            logger.info("✅ Schéma de base de données créé avec succès")
            logger.info("📊 Tables créées ou vérifiées :")
            logger.info("  ✓ users - Gestion des utilisateurs avec authentification")
            logger.info("  ✓ threads - Conversations de chat avec métadonnées")
            logger.info("  ✓ steps - Étapes de conversation et streaming")
            logger.info("  ✓ elements - Éléments multimédias et fichiers")
            logger.info("  ✓ feedbacks - Système de retours utilisateurs")
            logger.info("🔗 Relations et contraintes :")
            logger.info("  ✓ Clés étrangères avec suppression en cascade")
            logger.info("  ✓ Index et contraintes d'unicité")
            logger.info("  ✓ Types PostgreSQL (UUID, JSONB, ARRAY)")

        # Fermeture propre du moteur
        await engine.dispose()
        logger.info("🎯 Initialisation de la base de données terminée avec succès")

    except Exception as e:
        logger.error("❌ Erreur lors de l'initialisation de la base de données : %s", e)
        logger.error(
            "🔍 Vérifiez que PostgreSQL est accessible et que les paramètres de connexion sont corrects"
        )
        logger.error(
            "💡 Assurez-vous que l'utilisateur a les permissions CREATE sur la base de données"
        )
        raise e
