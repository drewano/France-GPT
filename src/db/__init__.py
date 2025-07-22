"""
Package de gestion de la base de données pour Chainlit.

Ce package contient :
    - models.py : Modèles SQLAlchemy pour toutes les tables
    - session.py : Gestion des sessions et initialisation de la BD

Usage:
    from src.db.models import Base, User, Thread, Step, Element, Feedback
    from src.db.session import initialize_database
"""

from .models import Base, User, Thread, Step, Element, Feedback
from .session import initialize_database

__all__ = [
    # Modèles
    "Base",
    "User",
    "Thread",
    "Step",
    "Element",
    "Feedback",
    # Session
    "initialize_database",
]
