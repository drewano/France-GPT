"""
Module d'initialisation de la base de données PostgreSQL pour Chainlit.

Ce module fournit une fonction pour créer le schéma requis par la couche de données
SQLAlchemy de Chainlit. Il définit les modèles SQLAlchemy correspondant aux tables
users, threads, steps, elements, et feedbacks avec les bonnes relations et contraintes.

Usage:
    from src.ui.db_init import initialize_database

    await initialize_database()

Fonctionnalités:
    - Modèles SQLAlchemy déclaratifs pour toutes les tables Chainlit
    - Création idempotente du schéma avec create_all()
    - Support des types PostgreSQL (UUID, JSONB, ARRAY)
    - Relations de clés étrangères avec suppression en cascade
    - Logging détaillé du processus d'initialisation
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, 
    UUID, ARRAY, ForeignKey
)
from sqlalchemy.dialects.postgresql import JSONB
from src.core.config import settings

# Base déclarative pour tous les modèles
Base = declarative_base()


class User(Base):
    """Modèle SQLAlchemy pour la table users de Chainlit."""
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True)
    identifier = Column(Text, nullable=False, unique=True)
    user_metadata = Column("metadata", JSONB, nullable=False)  # Évite le conflit avec Base.metadata
    createdAt = Column(Text)
    
    # Relations
    threads = relationship("Thread", back_populates="user", cascade="all, delete-orphan")


class Thread(Base):
    """Modèle SQLAlchemy pour la table threads de Chainlit."""
    __tablename__ = "threads"
    
    id = Column(UUID, primary_key=True)
    createdAt = Column(Text)
    name = Column(Text)
    userId = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"))
    userIdentifier = Column(Text)
    tags = Column(ARRAY(Text))
    thread_metadata = Column("metadata", JSONB)  # Évite le conflit avec Base.metadata
    
    # Relations
    user = relationship("User", back_populates="threads")
    steps = relationship("Step", back_populates="thread", cascade="all, delete-orphan")
    elements = relationship("Element", back_populates="thread", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="thread", cascade="all, delete-orphan")


class Step(Base):
    """Modèle SQLAlchemy pour la table steps de Chainlit."""
    __tablename__ = "steps"
    
    id = Column(UUID, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    threadId = Column(UUID, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    parentId = Column(UUID)
    streaming = Column(Boolean, nullable=False)
    waitForAnswer = Column(Boolean)
    isError = Column(Boolean)
    step_metadata = Column("metadata", JSONB)  # Évite le conflit avec Base.metadata
    tags = Column(ARRAY(Text))
    input = Column(Text)
    output = Column(Text)
    createdAt = Column(Text)
    command = Column(Text)
    start = Column(Text)
    end = Column(Text)
    generation = Column(JSONB)
    showInput = Column(Text)
    language = Column(Text)
    indent = Column(Integer)
    defaultOpen = Column(Boolean, default=False)
    
    # Relations
    thread = relationship("Thread", back_populates="steps")


class Element(Base):
    """Modèle SQLAlchemy pour la table elements de Chainlit."""
    __tablename__ = "elements"
    
    id = Column(UUID, primary_key=True)
    threadId = Column(UUID, ForeignKey("threads.id", ondelete="CASCADE"))
    type = Column(Text)
    url = Column(Text)
    chainlitKey = Column(Text)
    name = Column(Text, nullable=False)
    display = Column(Text)
    objectKey = Column(Text)
    size = Column(Text)
    page = Column(Integer)
    language = Column(Text)
    forId = Column(UUID)
    mime = Column(Text)
    props = Column(JSONB)
    
    # Relations
    thread = relationship("Thread", back_populates="elements")


class Feedback(Base):
    """Modèle SQLAlchemy pour la table feedbacks de Chainlit."""
    __tablename__ = "feedbacks"
    
    id = Column(UUID, primary_key=True)
    forId = Column(UUID, nullable=False)
    threadId = Column(UUID, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    value = Column(Integer, nullable=False)
    comment = Column(Text)
    
    # Relations
    thread = relationship("Thread", back_populates="feedbacks")


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
            f"🔗 Connexion à la base de données : {database_url.split('@')[1] if '@' in database_url else 'URL masquée'}"
        )

        # Création du moteur de base de données asynchrone
        engine = create_async_engine(database_url, echo=False)

        logger.info("📋 Création du schéma de base de données avec les modèles SQLAlchemy...")
        
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
        logger.error(
            f"❌ Erreur lors de l'initialisation de la base de données : {str(e)}"
        )
        logger.error(
            "🔍 Vérifiez que PostgreSQL est accessible et que les paramètres de connexion sont corrects"
        )
        logger.error(
            "💡 Assurez-vous que l'utilisateur a les permissions CREATE sur la base de données"
        )
        raise e


# Export des modèles pour utilisation dans d'autres modules si nécessaire
__all__ = ["initialize_database", "Base", "User", "Thread", "Step", "Element", "Feedback"]
