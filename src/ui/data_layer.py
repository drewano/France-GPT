"""
Module de configuration de la couche de persistance des données avec SQLAlchemy.

Ce module configure la couche de données SQLAlchemy pour Chainlit, permettant
la persistance des conversations, utilisateurs, et éléments de chat dans une
base de données PostgreSQL.

Usage:
    Ce module doit être importé pour activer la persistance des données.
    La configuration de la base de données est prise depuis settings.agent.DATABASE_URL.

Fonctionnalités:
    - Persistance des conversations (threads)
    - Sauvegarde des messages et étapes
    - Gestion des utilisateurs authentifiés
    - Stockage des éléments multimedia et fichiers
    - Système de feedback utilisateur
"""

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.data.storage_clients.s3 import S3StorageClient
from src.core.config import settings


@cl.data_layer
def get_data_layer():
    """
    Configure et retourne la couche de données SQLAlchemy pour Chainlit.

    Cette fonction est automatiquement appelée par Chainlit pour initialiser
    la persistance des données. Elle utilise la configuration de base de données
    définie dans settings.agent.DATABASE_URL.

    Returns:
        SQLAlchemyDataLayer: Instance configurée de la couche de données SQLAlchemy
    """
    storage_client = None
    if settings.agent.DEV_AWS_ENDPOINT:
        storage_client = S3StorageClient(
            bucket=settings.agent.BUCKET_NAME
        )

    return SQLAlchemyDataLayer(
        conninfo=settings.agent.DATABASE_URL,
        storage_provider=storage_client
    )
