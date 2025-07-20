"""
Modèles SQLAlchemy pour la couche de persistance des données Chainlit.

Ce module contient toutes les définitions de modèles de données pour l'application
Chainlit, incluant les tables users, threads, steps, elements et feedbacks avec
leurs relations et contraintes.

Fonctionnalités:
    - Modèles SQLAlchemy déclaratifs pour toutes les tables Chainlit
    - Support des types PostgreSQL (UUID, JSONB, ARRAY)
    - Relations bidirectionnelles avec cascade delete
    - Résolution des conflits de noms d'attributs réservés
"""

from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, Boolean, Integer, Text, UUID, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

# Base déclarative pour tous les modèles
Base = declarative_base()


class User(Base):
    """Modèle SQLAlchemy pour la table users de Chainlit."""

    __tablename__ = "users"

    id = Column(UUID, primary_key=True)
    identifier = Column(Text, nullable=False, unique=True)
    user_metadata = Column(
        "metadata", JSONB, nullable=False
    )  # Évite le conflit avec Base.metadata
    createdAt = Column(Text)

    # Relations
    threads = relationship(
        "Thread", back_populates="user", cascade="all, delete-orphan"
    )


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
    elements = relationship(
        "Element", back_populates="thread", cascade="all, delete-orphan"
    )
    feedbacks = relationship(
        "Feedback", back_populates="thread", cascade="all, delete-orphan"
    )


class Step(Base):
    """Modèle SQLAlchemy pour la table steps de Chainlit."""

    __tablename__ = "steps"

    id = Column(UUID, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    threadId = Column(
        UUID, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
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
    threadId = Column(
        UUID, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    value = Column(Integer, nullable=False)
    comment = Column(Text)

    # Relations
    thread = relationship("Thread", back_populates="feedbacks")


# Export des modèles pour utilisation dans d'autres modules
__all__ = ["Base", "User", "Thread", "Step", "Element", "Feedback"]
