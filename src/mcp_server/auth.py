"""
Authentication module for the DataInclusion MCP Server.

This module handles the configuration and setup of authentication
for the MCP server, including Bearer token authentication.
"""

import logging
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.bearer import RSAKeyPair
from cryptography.hazmat.primitives import serialization

from ..core.config import settings


def setup_authentication(logger: logging.Logger, audience: str) -> BearerAuthProvider | None:
    """
    Configure l'authentification Bearer pour le serveur MCP.

    Cette fonction :
    1. Lit la clé secrète depuis la configuration
    2. Configure BearerAuthProvider si une clé est fournie
    3. Génère un token de test pour le développement

    Args:
        logger: Instance du logger pour enregistrer les messages
        audience: The audience for the Bearer token.

    Returns:
        BearerAuthProvider | None: Le provider d'authentification ou None
    """
    logger.info("Configuring server authentication...")

    # Lecture de la clé secrète depuis la configuration
    secret_key = settings.agent.SECRET_KEY

    if secret_key and secret_key.strip():
        logger.info("Secret key found - configuring Bearer Token authentication...")
        try:
            # Si la clé ressemble à une clé RSA privée PEM, l'utiliser directement
            if secret_key.strip().startswith("-----BEGIN") and "PRIVATE KEY" in str(
                secret_key
            ):
                # Utiliser la clé privée pour créer une paire de clés
                private_key = serialization.load_pem_private_key(
                    secret_key.encode(), password=None
                )
                public_key_pem = (
                    private_key.public_key()
                    .public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                    .decode()
                )

                auth_provider = BearerAuthProvider(
                    public_key=public_key_pem, audience=audience
                )
            else:
                # Utiliser la clé comme seed pour générer une paire de clés déterministe
                # Pour des raisons de simplicité, on génère une nouvelle paire de clés
                key_pair = RSAKeyPair.generate()

                auth_provider = BearerAuthProvider(
                    public_key=key_pair.public_key,
                    audience=audience,
                )

                # Log du token de test (UNIQUEMENT pour le développement)
                test_token = key_pair.create_token(
                    audience=audience,
                    subject="test-user",
                    expires_in_seconds=3600,
                )
                logger.info(f"🔑 Test Bearer Token (for development): {test_token}")

            logger.info("✓ Bearer Token authentication configured successfully")
            logger.info(f"   - Audience: {audience}")
            logger.info("   - Server will require valid Bearer tokens for access")
            return auth_provider

        except Exception as e:
            logger.error(f"Failed to configure authentication: {e}")
            logger.warning("Continuing without authentication...")
            return None
    else:
        logger.warning(
            "MCP_SERVER_SECRET_KEY not set - server will run WITHOUT authentication"
        )
        logger.warning("⚠️  All clients will have unrestricted access to the server")
        return None
