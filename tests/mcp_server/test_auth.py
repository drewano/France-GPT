import pytest
import httpx
from unittest.mock import Mock, patch
import time
from src.mcp_server.auth import (
    BearerAuth,
    OAuth2ClientCredentialsAuth,
    create_auth_handler,
)
from src.core.config import BearerAuthConfig, OAuth2ClientCredentialsConfig


class TestBearerAuth:
    def test_bearer_auth_adds_authorization_header(self):
        """Test que le header Authorization est correctement ajouté à la requête."""
        api_key = "test-api-key"
        auth = BearerAuth(api_key)

        request = httpx.Request("GET", "https://api.example.com")
        flow = auth.auth_flow(request)
        next(flow)  # Exécute le générateur

        assert request.headers["Authorization"] == f"Bearer {api_key}"


class TestOAuth2ClientCredentialsAuth:
    @pytest.fixture
    def oauth_config(self):
        return OAuth2ClientCredentialsConfig(
            token_url="https://api.example.com/oauth/token",
            client_id_env_var="CLIENT_ID",
            client_secret_env_var="CLIENT_SECRET",
            scope="read write",
        )

    @pytest.fixture
    def logger(self):
        return Mock()

    def test_successful_token_fetch_and_auth_header(
        self, oauth_config, logger, httpx_mock
    ):
        """Test 1 : Simule une réponse réussie du token_url et vérifie que le token est ajouté au header."""
        # Configuration des variables d'environnement
        with patch.dict(
            "os.environ",
            {"CLIENT_ID": "test_client_id", "CLIENT_SECRET": "test_client_secret"},
        ):
            # Simulation de la réponse du token endpoint
            httpx_mock.add_response(
                url=oauth_config.token_url,
                json={"access_token": "test-access-token", "expires_in": 3600},
                status_code=200,
            )

            # Création de l'authentificateur
            auth = OAuth2ClientCredentialsAuth(oauth_config, logger)

            # Création d'une requête
            request = httpx.Request("GET", "https://api.example.com/data")
            flow = auth.auth_flow(request)
            next(flow)  # Exécute le générateur

            # Vérification que le header Authorization est ajouté
            assert request.headers["Authorization"] == "Bearer test-access-token"
            # Vérification que le logger a bien été appelé
            logger.info.assert_called_with("Successfully fetched new OAuth2 token.")

    def test_failed_token_fetch_logs_error_and_proceeds_without_auth(
        self, oauth_config, logger, httpx_mock
    ):
        """Test 2 : Simule une réponse en échec du token_url et vérifie le comportement."""
        # Configuration des variables d'environnement
        with patch.dict(
            "os.environ",
            {"CLIENT_ID": "test_client_id", "CLIENT_SECRET": "test_client_secret"},
        ):
            # Simulation d'une erreur de réseau
            httpx_mock.add_exception(
                url=oauth_config.token_url,
                exception=httpx.RequestError("Connection failed"),
            )

            # Création de l'authentificateur
            auth = OAuth2ClientCredentialsAuth(oauth_config, logger)

            # Création d'une requête
            request = httpx.Request("GET", "https://api.example.com/data")
            flow = auth.auth_flow(request)
            next(flow)  # Exécute le générateur

            # Vérification que le header Authorization n'est pas ajouté
            assert "Authorization" not in request.headers
            # Vérification que le logger a bien enregistré l'erreur
            logger.error.assert_called()
            assert "Error requesting OAuth2 token" in logger.error.call_args[0][0]

    def test_token_expiry_logic_requests_new_token(
        self, oauth_config, logger, httpx_mock
    ):
        """Test 3 : Teste la logique d'expiration du token."""
        # Configuration des variables d'environnement
        with patch.dict(
            "os.environ",
            {"CLIENT_ID": "test_client_id", "CLIENT_SECRET": "test_client_secret"},
        ):
            # Simulation de deux réponses de token (deux appels différents)
            httpx_mock.add_response(
                url=oauth_config.token_url,
                json={
                    "access_token": "first-token",
                    "expires_in": 1,  # Expire rapidement
                },
                status_code=200,
            )

            httpx_mock.add_response(
                url=oauth_config.token_url,
                json={"access_token": "second-token", "expires_in": 3600},
                status_code=200,
            )

            # Création de l'authentificateur
            auth = OAuth2ClientCredentialsAuth(oauth_config, logger)

            # Première requête
            request1 = httpx.Request("GET", "https://api.example.com/data1")
            flow1 = auth.auth_flow(request1)
            next(flow1)  # Exécute le générateur

            assert request1.headers["Authorization"] == "Bearer first-token"

            # Attendre que le token expire
            time.sleep(2)

            # Deuxième requête après expiration
            request2 = httpx.Request("GET", "https://api.example.com/data2")
            flow2 = auth.auth_flow(request2)
            next(flow2)  # Exécute le générateur

            # Vérification qu'un nouveau token a été demandé
            assert request2.headers["Authorization"] == "Bearer second-token"
            # Vérifier que le logger a bien enregistré les deux succès
            assert logger.info.call_count >= 2
            logger.info.assert_any_call("Successfully fetched new OAuth2 token.")


class TestCreateAuthHandler:
    def test_create_bearer_auth_handler(self):
        """Test la création d'un gestionnaire BearerAuth."""
        with patch.dict("os.environ", {"API_KEY": "test-api-key"}):
            config = BearerAuthConfig(api_key_env_var="API_KEY")
            logger = Mock()

            handler = create_auth_handler(config, logger)

            assert isinstance(handler, BearerAuth)
            assert handler.api_key == "test-api-key"

    def test_create_bearer_auth_handler_missing_env_var(self):
        """Test la création d'un gestionnaire BearerAuth avec variable d'environnement manquante."""
        config = BearerAuthConfig(api_key_env_var="MISSING_API_KEY")
        logger = Mock()

        handler = create_auth_handler(config, logger)

        assert handler is None
        logger.error.assert_called_once()

    def test_create_oauth2_auth_handler(self):
        """Test la création d'un gestionnaire OAuth2ClientCredentialsAuth."""
        config = OAuth2ClientCredentialsConfig(
            token_url="https://api.example.com/oauth/token",
            client_id_env_var="CLIENT_ID",
            client_secret_env_var="CLIENT_SECRET",
            scope="read",
        )
        logger = Mock()

        handler = create_auth_handler(config, logger)

        assert isinstance(handler, OAuth2ClientCredentialsAuth)
        assert handler.config == config
