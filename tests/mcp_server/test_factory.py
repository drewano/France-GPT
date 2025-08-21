import pytest
import json
from unittest.mock import Mock
from src.mcp_server.factory import MCPFactory
from src.core.config import MCPServiceConfig, BearerAuthConfig
from fastmcp import FastMCP


@pytest.mark.asyncio
class TestMCPFactory:
    """Tests pour la classe MCPFactory."""

    @pytest.fixture
    def logger(self):
        """Fixture pour le logger."""
        return Mock()

    @pytest.fixture
    def service_config(self):
        """Fixture pour la configuration du service."""
        return MCPServiceConfig(
            name="test_service",
            openapi_path_or_url="https://api.example.com/openapi.json",
            auth=BearerAuthConfig(api_key_env_var="TEST_API_KEY"),
            tool_mappings_file="test_mappings.json",
        )

    @pytest.fixture
    def openapi_spec(self):
        """Fixture pour une spécification OpenAPI minimale."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "get_test",
                        "summary": "Get test data",
                        "description": "Retrieve test data from the API",
                        "responses": {"200": {"description": "Successful response"}},
                    }
                }
            },
        }

    @pytest.fixture
    def tool_mappings(self):
        """Fixture pour les mappings d'outils."""
        return {"get_test": "get_test_data"}

    async def test_build_success(
        self, logger, service_config, openapi_spec, tool_mappings, httpx_mock, mocker
    ):
        """Test de la méthode build avec succès."""
        # Configuration des mocks
        # Mock pour la lecture du fichier de mappings
        mocker.patch(
            "builtins.open", mocker.mock_open(read_data=json.dumps(tool_mappings))
        )

        # Mock pour le chargement de la spécification OpenAPI
        httpx_mock.add_response(
            url=service_config.openapi_path_or_url, json=openapi_spec, status_code=200
        )

        # Création de la factory
        factory = MCPFactory(config=service_config, logger=logger)

        # Appel de la méthode build
        mcp_server = await factory.build()

        # Vérifications
        assert isinstance(mcp_server, FastMCP)
        assert mcp_server.name == "test_service"

        # Vérifier que le client API a été créé
        assert factory.state.api_client is not None

        # Vérifier que la spécification OpenAPI a été chargée
        assert factory.state.openapi_spec is not None
        assert factory.state.openapi_spec["info"]["title"] == "Test API"

        # Vérifier que les mappings ont été chargés
        assert factory.tool_mappings == tool_mappings

        # Vérifier que le logger a été appelé avec les bons messages
        logger.info.assert_any_call("Loading OpenAPI specification...")

        # Nettoyage
        await factory.cleanup()

    async def test_build_with_local_file(
        self, logger, openapi_spec, tool_mappings, mocker
    ):
        """Test de la méthode build avec un fichier local."""
        # Configuration du service pour utiliser un fichier local
        service_config = MCPServiceConfig(
            name="test_service",
            openapi_path_or_url="local_openapi.json",
            auth=BearerAuthConfig(api_key_env_var="TEST_API_KEY"),
            tool_mappings_file="test_mappings.json",
        )

        # Mock pour la lecture du fichier de mappings
        mocker.patch(
            "builtins.open", mocker.mock_open(read_data=json.dumps(tool_mappings))
        )

        # Mock pour la lecture du fichier OpenAPI local
        mocker.patch(
            "pathlib.Path.open", mocker.mock_open(read_data=json.dumps(openapi_spec))
        )
        mocker.patch("os.path.exists", return_value=True)

        # Création de la factory
        factory = MCPFactory(config=service_config, logger=logger)

        # Appel de la méthode build
        mcp_server = await factory.build()

        # Vérifications
        assert isinstance(mcp_server, FastMCP)
        assert mcp_server.name == "test_service"

        # Nettoyage
        await factory.cleanup()

    async def test_build_with_missing_mappings_file(
        self, logger, service_config, openapi_spec, httpx_mock, mocker
    ):
        """Test de la méthode build quand le fichier de mappings est manquant."""
        # Configuration des mocks
        # Mock pour désactiver la lecture des fichiers .env par pydantic-settings
        mocker.patch("dotenv.main.dotenv_values", return_value={})
        # Mock pour simuler un fichier de mappings manquant
        original_open = open

        def open_side_effect(file, *args, **kwargs):
            if file == service_config.tool_mappings_file:
                raise FileNotFoundError("Mocked: File not found")
            return original_open(file, *args, **kwargs)

        mocker.patch("builtins.open", side_effect=open_side_effect)

        # Mock pour le chargement de la spécification OpenAPI
        httpx_mock.add_response(
            url=service_config.openapi_path_or_url, json=openapi_spec, status_code=200
        )

        # Création de la factory
        factory = MCPFactory(config=service_config, logger=logger)

        # Appel de la méthode build
        mcp_server = await factory.build()

        # Vérifications
        assert isinstance(mcp_server, FastMCP)
        assert mcp_server.name == "test_service"

        # Vérifier que le logger a enregistré un warning
        logger.warning.assert_any_call(
            f"Custom tool mappings file not found: {service_config.tool_mappings_file}. "
            "Using empty mappings."
        )

        # Nettoyage
        await factory.cleanup()

    async def test_build_with_invalid_mappings_file(
        self, logger, service_config, openapi_spec, httpx_mock, mocker
    ):
        """Test de la méthode build quand le fichier de mappings est invalide."""
        # Configuration des mocks
        # Mock pour simuler un fichier de mappings invalide
        mocker.patch("builtins.open", mocker.mock_open(read_data="invalid json"))

        # Mock pour le chargement de la spécification OpenAPI
        httpx_mock.add_response(
            url=service_config.openapi_path_or_url, json=openapi_spec, status_code=200
        )

        # Création de la factory
        factory = MCPFactory(config=service_config, logger=logger)

        # Appel de la méthode build
        mcp_server = await factory.build()

        # Vérifications
        assert isinstance(mcp_server, FastMCP)
        assert mcp_server.name == "test_service"

        # Vérifier que le logger a enregistré une erreur
        logger.error.assert_any_call(
            f"Error decoding JSON from tool mappings file {service_config.tool_mappings_file}: "
            "Expecting value: line 1 column 1 (char 0). "
            "Using empty mappings."
        )

        # Nettoyage
        await factory.cleanup()

    async def test_build_with_openapi_error(self, logger, service_config, httpx_mock):
        """Test de la méthode build avec une erreur lors du chargement de l'OpenAPI."""
        # Configuration des mocks
        # Mock pour simuler une erreur HTTP lors du chargement de l'OpenAPI
        httpx_mock.add_exception(
            url=service_config.openapi_path_or_url, exception=Exception("Network error")
        )

        # Création de la factory
        factory = MCPFactory(config=service_config, logger=logger)

        # Vérification que l'exception est levée
        with pytest.raises(Exception, match="Network error"):
            await factory.build()

        # Vérifier que le logger a enregistré une erreur
        logger.error.assert_any_call("Failed to build MCP server: Network error")

    async def test_cleanup(
        self, logger, service_config, openapi_spec, tool_mappings, httpx_mock, mocker
    ):
        """Test de la méthode cleanup."""
        # Configuration des mocks
        mocker.patch(
            "builtins.open", mocker.mock_open(read_data=json.dumps(tool_mappings))
        )
        httpx_mock.add_response(
            url=service_config.openapi_path_or_url, json=openapi_spec, status_code=200
        )

        # Création de la factory
        factory = MCPFactory(config=service_config, logger=logger)

        # Construire le serveur
        await factory.build()

        # Vérifier que le client API a été créé
        assert factory.state.api_client is not None

        # Appel de la méthode cleanup
        await factory.cleanup()

        # Vérifier que le logger a enregistré les bons messages
        logger.info.assert_any_call("Closing HTTP client...")
        logger.info.assert_any_call("HTTP client closed successfully")
