"""
Module de gestion du client S3 avec une logique centralisée et une fonction
pour garantir l'existence du bucket.

Ce module fournit :
1. Une fonction `get_s3_client` qui retourne une instance de `S3StorageClient`
   en utilisant un pattern singleton.
2. Une fonction asynchrone `ensure_bucket_exists` qui vérifie et crée le bucket
   si nécessaire.

Utilisation :
    from src.core.s3_client import get_s3_client, ensure_bucket_exists

    # Obtenir le client S3 (singleton)
    client = get_s3_client()

    # S'assurer que le bucket existe
    await ensure_bucket_exists()
"""

import functools
import logging
from typing import Optional

import aioboto3
from botocore.exceptions import ClientError
from chainlit.data.storage_clients.s3 import S3StorageClient

from src.core.config import settings

# Configuration du logger
logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=None)
def get_s3_client() -> Optional[S3StorageClient]:
    """
    Retourne une instance de S3StorageClient en utilisant un pattern singleton.

    Cette fonction utilise le cache LRU pour s'assurer qu'une seule instance
    de S3StorageClient est créée et réutilisée.

    Returns:
        S3StorageClient: Instance configurée du client S3, ou None si non configuré
    """
    if not settings.agent.DEV_AWS_ENDPOINT:
        logger.info(
            "Le endpoint AWS n'est pas configuré. Le client S3 ne sera pas créé."
        )
        return None

    logger.info("Création du client S3 avec le bucket: %s", settings.agent.BUCKET_NAME)
    # Configuration des variables d'environnement pour LocalStack
    import os

    os.environ["AWS_ENDPOINT_URL"] = settings.agent.DEV_AWS_ENDPOINT
    os.environ["AWS_ACCESS_KEY_ID"] = settings.agent.APP_AWS_ACCESS_KEY
    os.environ["AWS_SECRET_ACCESS_KEY"] = settings.agent.APP_AWS_SECRET_KEY
    os.environ["AWS_REGION"] = settings.agent.APP_AWS_REGION

    return S3StorageClient(bucket=settings.agent.BUCKET_NAME)


async def ensure_bucket_exists() -> bool:
    """
    Vérifie si le bucket S3 existe et le crée si nécessaire.

    Cette fonction :
    1. Obtient une instance du client boto3 S3 asynchrone via aioboto3
    2. Vérifie si le bucket existe avec head_bucket
    3. Crée le bucket avec create_bucket si nécessaire
    4. Gère correctement la configuration de région

    Returns:
        bool: True si le bucket existe ou a été créé avec succès, False sinon
    """
    # Vérifier si le endpoint est configuré
    if not settings.agent.DEV_AWS_ENDPOINT:
        logger.warning(
            "Le endpoint AWS n'est pas configuré. Impossible de vérifier le bucket."
        )
        return False

    bucket_name = settings.agent.BUCKET_NAME
    region = settings.agent.APP_AWS_REGION
    endpoint_url = settings.agent.DEV_AWS_ENDPOINT

    logger.info("Vérification de l'existence du bucket S3: %s", bucket_name)
    logger.info("Endpoint S3 configuré: %s", endpoint_url)
    logger.info("Région S3 configurée: %s", region)

    # Créer une session aioboto3
    session = aioboto3.Session(
        aws_access_key_id=settings.agent.APP_AWS_ACCESS_KEY,
        aws_secret_access_key=settings.agent.APP_AWS_SECRET_KEY,
        region_name=region,
    )

    try:
        # Créer un client S3 asynchrone
        logger.info("Création du client S3 asynchrone avec endpoint: %s", endpoint_url)
        async with session.client("s3", endpoint_url=endpoint_url) as s3_client:
            # Vérifier si le bucket existe
            try:
                logger.info("Vérification de l'existence du bucket '%s'", bucket_name)
                await s3_client.head_bucket(Bucket=bucket_name)
                logger.info("Le bucket S3 '%s' existe déjà.", bucket_name)
                return True
            except ClientError as e:
                # Si l'erreur est 404, le bucket n'existe pas
                error_code = e.response["Error"]["Code"]
                if error_code == "404":
                    logger.info(
                        "Le bucket S3 '%s' n'existe pas. Création en cours...",
                        bucket_name,
                    )
                else:
                    # Une autre erreur s'est produite
                    logger.error(
                        "Erreur lors de la vérification du bucket S3 '%s': %s",
                        bucket_name,
                        e,
                    )
                    logger.error("Code d'erreur: %s", error_code)
                    return False

            # Créer le bucket
            try:
                logger.info(
                    "Création du bucket '%s' dans la région '%s'", bucket_name, region
                )
                # Pour la région us-east-1, il ne faut pas spécifier LocationConstraint
                if region == "us-east-1":
                    await s3_client.create_bucket(Bucket=bucket_name)
                else:
                    await s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": region},
                    )
                logger.info("Le bucket S3 '%s' a été créé avec succès.", bucket_name)
                return True
            except ClientError as e:
                logger.error(
                    "Erreur lors de la création du bucket S3 '%s': %s", bucket_name, e
                )
                return False
    except Exception as e:
        logger.error(
            "Erreur inattendue lors de la gestion du bucket S3 '%s': %s", bucket_name, e
        )
        return False
