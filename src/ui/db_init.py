"""
Module d'initialisation de la base de données PostgreSQL pour Chainlit.

Ce module fournit une fonction pour créer le schéma requis par la couche de données
SQLAlchemy de Chainlit. Il initialise les tables users, threads, steps, elements,
et feedbacks avec les bonnes relations et contraintes.

Usage:
    from src.ui.db_init import initialize_database

    await initialize_database()

Fonctionnalités:
    - Création idempotente des tables (CREATE TABLE IF NOT EXISTS)
    - Support des types PostgreSQL (UUID, JSONB, TEXT[])
    - Relations de clés étrangères avec suppression en cascade
    - Logging détaillé du processus d'initialisation
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.core.config import settings


async def initialize_database():
    """
    Initialise la base de données PostgreSQL avec le schéma requis par Chainlit.

    Cette fonction crée toutes les tables nécessaires pour la persistance des données
    Chainlit : users, threads, steps, elements, et feedbacks. Les commandes SQL
    utilisent CREATE TABLE IF NOT EXISTS pour être idempotentes.

    La fonction utilise une connexion asynchrone et une transaction pour garantir
    la cohérence des opérations d'initialisation.

    Raises:
        Exception: Si l'initialisation de la base de données échoue
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "Début de l'initialisation de la base de données PostgreSQL pour Chainlit"
    )

    try:
        # Récupération de l'URL de la base de données depuis la configuration
        database_url = settings.agent.DATABASE_URL
        logger.info(
            f"Connexion à la base de données : {database_url.split('@')[1] if '@' in database_url else 'URL masquée'}"
        )

        # Création du moteur de base de données asynchrone
        engine = create_async_engine(database_url, echo=False)

        # Définition des commandes SQL pour créer le schéma Chainlit
        # Toutes les tables utilisent CREATE TABLE IF NOT EXISTS pour l'idempotence
        # Chaque commande est séparée pour éviter l'erreur "multiple commands in prepared statement"
        sql_commands = [
            """CREATE TABLE IF NOT EXISTS users (
                "id" UUID PRIMARY KEY,
                "identifier" TEXT NOT NULL UNIQUE,
                "metadata" JSONB NOT NULL,
                "createdAt" TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS threads (
                "id" UUID PRIMARY KEY,
                "createdAt" TEXT,
                "name" TEXT,
                "userId" UUID,
                "userIdentifier" TEXT,
                "tags" TEXT[],
                "metadata" JSONB,
                FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS steps (
                "id" UUID PRIMARY KEY,
                "name" TEXT NOT NULL,
                "type" TEXT NOT NULL,
                "threadId" UUID NOT NULL,
                "parentId" UUID,
                "streaming" BOOLEAN NOT NULL,
                "waitForAnswer" BOOLEAN,
                "isError" BOOLEAN,
                "metadata" JSONB,
                "tags" TEXT[],
                "input" TEXT,
                "output" TEXT,
                "createdAt" TEXT,
                "command" TEXT,
                "start" TEXT,
                "end" TEXT,
                "generation" JSONB,
                "showInput" TEXT,
                "language" TEXT,
                "indent" INT,
                "defaultOpen" BOOLEAN DEFAULT FALSE,
                FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS elements (
                "id" UUID PRIMARY KEY,
                "threadId" UUID,
                "type" TEXT,
                "url" TEXT,
                "chainlitKey" TEXT,
                "name" TEXT NOT NULL,
                "display" TEXT,
                "objectKey" TEXT,
                "size" TEXT,
                "page" INT,
                "language" TEXT,
                "forId" UUID,
                "mime" TEXT,
                "props" JSONB,
                FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS feedbacks (
                "id" UUID PRIMARY KEY,
                "forId" UUID NOT NULL,
                "threadId" UUID NOT NULL,
                "value" INT NOT NULL,
                "comment" TEXT,
                FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
            )""",
            # Ajout des colonnes manquantes pour compatibilité avec les versions récentes de Chainlit
            """ALTER TABLE steps ADD COLUMN IF NOT EXISTS "defaultOpen" BOOLEAN DEFAULT FALSE""",
        ]

        # Exécution des commandes SQL dans une transaction
        async with engine.begin() as conn:
            logger.info("Exécution des commandes de création des tables...")
            for i, command in enumerate(sql_commands, 1):
                await conn.execute(text(command))
                logger.info(
                    f"  {i}/{len(sql_commands)} - Commande exécutée avec succès"
                )
            logger.info("Tables créées avec succès :")
            logger.info("  ✓ users - Gestion des utilisateurs")
            logger.info("  ✓ threads - Conversations de chat")
            logger.info("  ✓ steps - Étapes de conversation (avec colonne defaultOpen)")
            logger.info("  ✓ elements - Éléments multimedia")
            logger.info("  ✓ feedbacks - Retours utilisateurs")
            logger.info("  ✓ Mise à jour des colonnes pour compatibilité Chainlit")

        # Fermeture du moteur
        await engine.dispose()
        logger.info("Initialisation de la base de données terminée avec succès")

    except Exception as e:
        logger.error(
            f"Erreur lors de l'initialisation de la base de données : {str(e)}"
        )
        logger.error(
            "Vérifiez que PostgreSQL est accessible et que les paramètres de connexion sont corrects"
        )
        raise e
