"""
Tests unitaires pour le module s3_client.py
"""

import pytest
from unittest.mock import patch, AsyncMock

from src.core.s3_client import get_s3_client, ensure_bucket_exists
from src.core.config import settings


class TestS3Client:
    """Tests pour le module s3_client.py"""

    def test_get_s3_client_singleton(self):
        """Test que get_s3_client retourne une instance singleton."""
        # Réinitialiser le cache
        get_s3_client.cache_clear()

        # Premier appel
        with patch(
            "src.core.config.settings.agent.DEV_AWS_ENDPOINT", "http://localhost:4566"
        ):
            client1 = get_s3_client()
            client2 = get_s3_client()

            # Vérifier que les deux appels retournent la même instance
            assert client1 is client2

    def test_get_s3_client_no_endpoint(self):
        """Test que get_s3_client retourne None quand le endpoint n'est pas configuré."""
        # Réinitialiser le cache
        get_s3_client.cache_clear()

        with patch("src.core.config.settings.agent.DEV_AWS_ENDPOINT", None):
            client = get_s3_client()
            assert client is None


@pytest.mark.asyncio
async def test_ensure_bucket_exists_no_endpoint():
    """Test que ensure_bucket_exists retourne False quand le endpoint n'est pas configuré."""
    with patch("src.core.config.settings.agent.DEV_AWS_ENDPOINT", None):
        result = await ensure_bucket_exists()
        assert result is False


@pytest.mark.asyncio
async def test_ensure_bucket_exists_bucket_exists():
    """Test que ensure_bucket_exists retourne True quand le bucket existe déjà."""
    with patch(
        "src.core.config.settings.agent.DEV_AWS_ENDPOINT", "http://localhost:4566"
    ):
        with patch("aioboto3.Session") as mock_session:
            # Créer un mock pour le client S3
            mock_client = AsyncMock()
            mock_client.head_bucket.return_value = None  # Le bucket existe

            # Configurer le context manager async
            mock_session_instance = mock_session.return_value
            mock_session_instance.client.return_value.__aenter__.return_value = (
                mock_client
            )

            result = await ensure_bucket_exists()
            assert result is True

            # Vérifier que head_bucket a été appelé
            mock_client.head_bucket.assert_called_once_with(
                Bucket=settings.agent.BUCKET_NAME
            )


@pytest.mark.asyncio
async def test_ensure_bucket_exists_bucket_created():
    """Test que ensure_bucket_exists crée le bucket quand il n'existe pas."""
    with patch(
        "src.core.config.settings.agent.DEV_AWS_ENDPOINT", "http://localhost:4566"
    ):
        with patch("src.core.config.settings.agent.APP_AWS_REGION", "eu-central-1"):
            with patch("aioboto3.Session") as mock_session:
                # Créer un mock pour le client S3
                mock_client = AsyncMock()
                # Le premier appel à head_bucket lève une exception 404
                from botocore.exceptions import ClientError

                error_response = {"Error": {"Code": "404"}}
                mock_client.head_bucket.side_effect = ClientError(
                    error_response, "head_bucket"
                )

                # Configurer le context manager async
                mock_session_instance = mock_session.return_value
                mock_session_instance.client.return_value.__aenter__.return_value = (
                    mock_client
                )

                # Mock create_bucket pour qu'il réussisse
                mock_client.create_bucket.return_value = None

                result = await ensure_bucket_exists()
                assert result is True

                # Vérifier que head_bucket a été appelé
                mock_client.head_bucket.assert_called_once_with(
                    Bucket=settings.agent.BUCKET_NAME
                )

                # Vérifier que create_bucket a été appelé
                mock_client.create_bucket.assert_called_once_with(
                    Bucket=settings.agent.BUCKET_NAME,
                    CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
                )
