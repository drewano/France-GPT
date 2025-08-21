import pytest
import json
from unittest.mock import mock_open
import httpx
from src.mcp_server.openapi_loader import OpenAPILoader
import logging


class TestOpenAPILoader:
    """Tests pour la classe OpenAPILoader."""

    @pytest.fixture
    def logger(self):
        """Fixture pour le logger."""
        return logging.getLogger(__name__)

    @pytest.fixture
    def openapi_loader(self, logger):
        """Fixture pour l'instance de OpenAPILoader."""
        return OpenAPILoader(logger)

    @pytest.fixture
    def openapi_spec(self):
        """Fixture pour une spécification OpenAPI de test."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/api/v1/structures": {
                    "get": {
                        "parameters": [
                            {
                                "name": "size",
                                "in": "query",
                                "schema": {
                                    "type": "integer",
                                    "default": 100,
                                    "maximum": 1000,
                                },
                            }
                        ],
                        "responses": {"200": {"description": "Successful response"}},
                    }
                },
                "/api/v1/services": {
                    "get": {
                        "parameters": [
                            {
                                "name": "size",
                                "in": "query",
                                "schema": {
                                    "type": "integer",
                                    "default": 100,
                                    "maximum": 1000,
                                },
                            }
                        ],
                        "responses": {"200": {"description": "Successful response"}},
                    }
                },
                "/api/v1/search/services": {
                    "get": {
                        "parameters": [
                            {
                                "name": "size",
                                "in": "query",
                                "schema": {
                                    "type": "integer",
                                    "default": 100,
                                    "maximum": 1000,
                                },
                            }
                        ],
                        "responses": {"200": {"description": "Successful response"}},
                    }
                },
            },
        }

    # Tests pour le chargement depuis une URL
    @pytest.mark.asyncio
    async def test_load_from_url_success(
        self, openapi_loader, httpx_mock, openapi_spec
    ):
        """Test du chargement réussi depuis une URL."""
        # Configuration du mock HTTP
        httpx_mock.add_response(
            url="https://api.example.com/openapi.json",
            json=openapi_spec,
            status_code=200,
        )

        # Création de la spécification attendue après modification
        import copy

        expected_spec = copy.deepcopy(openapi_spec)
        paths_to_modify = [
            "/api/v1/structures",
            "/api/v1/services",
            "/api/v1/search/services",
        ]
        for path in paths_to_modify:
            if path in expected_spec["paths"] and "get" in expected_spec["paths"][path]:
                params = expected_spec["paths"][path]["get"].get("parameters", [])
                for param in params:
                    if param.get("name") == "size":
                        param["schema"]["maximum"] = 50
                        param["schema"]["default"] = 50

        # Appel de la méthode
        spec, routes = await openapi_loader.load("https://api.example.com/openapi.json")

        # Vérifications
        assert spec == expected_spec
        assert isinstance(routes, list)

    @pytest.mark.asyncio
    async def test_load_from_url_http_error(self, openapi_loader, httpx_mock):
        """Test du chargement depuis une URL avec erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 404
        httpx_mock.add_response(
            url="https://api.example.com/openapi.json",
            status_code=404,
            text="Not Found",
        )

        # Vérification que l'exception est levée
        with pytest.raises(httpx.HTTPStatusError):
            await openapi_loader.load("https://api.example.com/openapi.json")

    @pytest.mark.asyncio
    async def test_load_from_url_invalid_json(self, openapi_loader, httpx_mock):
        """Test du chargement depuis une URL avec JSON invalide."""
        # Configuration du mock HTTP pour simuler un JSON invalide
        httpx_mock.add_response(
            url="https://api.example.com/openapi.json",
            text="invalid json",
            status_code=200,
        )

        # Vérification que l'exception est levée
        with pytest.raises(json.JSONDecodeError):
            await openapi_loader.load("https://api.example.com/openapi.json")

    # Tests pour le chargement depuis un fichier local
    @pytest.mark.asyncio
    async def test_load_from_local_file_success(
        self, openapi_loader, mocker, openapi_spec
    ):
        """Test du chargement réussi depuis un fichier local."""
        # Mock de os.path.exists pour retourner True
        mocker.patch("os.path.exists", return_value=True)

        # Mock de pathlib.Path.open pour retourner le contenu du fichier
        mocker.patch("pathlib.Path.open", mock_open(read_data=json.dumps(openapi_spec)))

        # Mock de parse_openapi_to_http_routes pour retourner une liste vide
        mocker.patch(
            "src.mcp_server.openapi_loader.parse_openapi_to_http_routes",
            return_value=[],
        )

        # Mock pour neutraliser la modification de la spécification par _limit_page_size
        mocker.patch(
            "src.mcp_server.openapi_loader.OpenAPILoader._limit_page_size",
            side_effect=lambda spec, max_size: spec,
        )

        # Appel de la méthode
        spec, routes = await openapi_loader.load("/path/to/openapi.json")

        # Vérifications
        assert spec == openapi_spec
        assert isinstance(routes, list)

    @pytest.mark.asyncio
    async def test_load_from_local_file_not_found(self, openapi_loader, mocker):
        """Test du chargement depuis un fichier local qui n'existe pas."""
        # Mock de os.path.exists pour retourner False
        mocker.patch("os.path.exists", return_value=False)

        # Vérification que l'exception est levée
        with pytest.raises(FileNotFoundError):
            await openapi_loader.load("/path/to/nonexistent.json")

    @pytest.mark.asyncio
    async def test_load_from_local_file_invalid_json(self, openapi_loader, mocker):
        """Test du chargement depuis un fichier local avec JSON invalide."""
        # Mock de os.path.exists pour retourner True
        mocker.patch("os.path.exists", return_value=True)

        # Mock de pathlib.Path.open pour retourner du contenu invalide
        mocker.patch("pathlib.Path.open", mock_open(read_data="invalid json"))

        # Vérification que l'exception est levée
        with pytest.raises(json.JSONDecodeError):
            await openapi_loader.load("/path/to/invalid.json")

    # Test pour la méthode _limit_page_size
    def test_limit_page_size(self, openapi_loader, openapi_spec):
        """Test de la méthode _limit_page_size."""
        # Appel de la méthode
        modified_spec = openapi_loader._limit_page_size(openapi_spec, max_size=50)

        # Vérifications
        # Vérifier que les paramètres size ont été modifiés
        paths_to_check = [
            "/api/v1/structures",
            "/api/v1/services",
            "/api/v1/search/services",
        ]

        for path in paths_to_check:
            params = modified_spec["paths"][path]["get"]["parameters"]
            size_param = next((p for p in params if p.get("name") == "size"), None)

            assert size_param is not None
            assert size_param["schema"]["maximum"] == 50
            assert size_param["schema"]["default"] == 50

        # Vérifier que le titre de l'API est préservé
        assert modified_spec["info"]["title"] == "Test API"
