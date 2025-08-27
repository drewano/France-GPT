import pytest
import json
import os
import httpx
from unittest.mock import AsyncMock, MagicMock
from src.mcp_server.services.datainclusion.service import (
    fetch_reference_values,
    list_all_structures,
    list_all_services,
    get_structure_details,
    get_service_details,
    search_services,
)
from src.mcp_server.services.datainclusion.schemas import (
    ReferenceItem,
    StructureSummary,
    ServiceSummary,
    StructureDetails,
    ServiceDetails,
)
from pydantic_ai import ModelRetry


@pytest.mark.asyncio
class TestReferenceValues:
    """Tests pour la fonction fetch_reference_values."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def reference_themes_response(self):
        """Charge la réponse de référence pour les thèmes."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "fixtures", "reference_themes_response.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    async def test_fetch_reference_values_success(
        self, mock_client, reference_themes_response
    ):
        """Test de fetch_reference_values avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(
            return_value=reference_themes_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await fetch_reference_values(mock_client, "themes")

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(item, ReferenceItem) for item in result)
        assert result[0].value == "numerique--accompagnement-aux-outils-numeriques"
        assert result[0].label == "Accompagnement aux outils numériques"

    async def test_fetch_reference_values_http_error(self, mock_client):
        """Test de fetch_reference_values avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 500
        from httpx import HTTPStatusError

        mock_client.get.return_value.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "Internal Server Error", request=MagicMock(), response=MagicMock()
            )
        )
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await fetch_reference_values(mock_client, "themes")


@pytest.mark.asyncio
class TestListAllStructures:
    """Tests pour la fonction list_all_structures."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def list_structures_response(self):
        """Charge la réponse de list_structures."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "fixtures", "list_structures_response.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    async def test_list_all_structures_success(
        self, mock_client, list_structures_response
    ):
        """Test de list_all_structures avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(
            return_value=list_structures_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await list_all_structures(
            mock_client, "numerique--accompagnement-aux-outils-numeriques"
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, StructureSummary) for item in result)
        assert result[0].id == "structure-1"
        assert result[0].name == "Maison de quartier"

    async def test_list_all_structures_with_network_filter(
        self, mock_client, list_structures_response
    ):
        """Test de list_all_structures avec un filtre réseau."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(
            return_value=list_structures_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await list_all_structures(
            mock_client, "numerique--accompagnement-aux-outils-numeriques", "ft"
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2

    async def test_list_all_structures_http_error(self, mock_client):
        """Test de list_all_structures avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 400
        from httpx import HTTPStatusError

        mock_client.get.return_value.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "Bad Request", request=MagicMock(), response=MagicMock()
            )
        )
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await list_all_structures(
                mock_client, "numerique--accompagnement-aux-outils-numeriques"
            )


@pytest.mark.asyncio
class TestListAllServices:
    """Tests pour la fonction list_all_services."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def list_services_response(self):
        """Charge la réponse de list_services."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "fixtures", "list_services_response.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    async def test_list_all_services_success(self, mock_client, list_services_response):
        """Test de list_all_services avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(
            return_value=list_services_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await list_all_services(
            mock_client, "numerique--accompagnement-aux-outils-numeriques"
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, ServiceSummary) for item in result)
        assert result[0].id == "service-1"
        assert result[0].name == "Service d'accompagnement numérique"

    async def test_list_all_services_with_filters(
        self, mock_client, list_services_response
    ):
        """Test de list_all_services avec des filtres supplémentaires."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(
            return_value=list_services_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await list_all_services(
            mock_client,
            "numerique--accompagnement-aux-outils-numeriques",
            costs=["gratuit"],
            target_audience=["adultes"],
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2

    async def test_list_all_services_http_error(self, mock_client):
        """Test de list_all_services avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 500
        from httpx import HTTPStatusError

        mock_client.get.return_value.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "Internal Server Error", request=MagicMock(), response=MagicMock()
            )
        )
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await list_all_services(
                mock_client, "numerique--accompagnement-aux-outils-numeriques"
            )


@pytest.mark.asyncio
class TestGetStructureDetails:
    """Tests pour la fonction get_structure_details."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def get_structure_details_response(self):
        """Charge la réponse de get_structure_details."""
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "fixtures",
                "get_structure_details_response.json",
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    async def test_get_structure_details_success(
        self, mock_client, get_structure_details_response
    ):
        """Test de get_structure_details avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(
            return_value=get_structure_details_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await get_structure_details(mock_client, "dora", "structure-1")

        # Vérifications
        assert isinstance(result, StructureDetails)
        assert result.id == "structure-1"
        assert result.name == "Maison de quartier"
        assert (
            result.description
            == "Structure communautaire offrant divers services aux habitants."
        )
        assert result.phone == "0123456789"
        assert result.email == "contact@maison-quartier.fr"

    async def test_get_structure_details_http_error(self, mock_client):
        """Test de get_structure_details avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 404
        from httpx import HTTPStatusError

        mock_client.get.return_value.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "Not Found", request=MagicMock(), response=MagicMock()
            )
        )
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await get_structure_details(mock_client, "dora", "structure-1")


@pytest.mark.asyncio
class TestGetServiceDetails:
    """Tests pour la fonction get_service_details."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def get_service_details_response(self):
        """Charge la réponse de get_service_details."""
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "fixtures",
                "get_service_details_response.json",
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    async def test_get_service_details_success(
        self, mock_client, get_service_details_response
    ):
        """Test de get_service_details avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(
            return_value=get_service_details_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await get_service_details(mock_client, "dora", "service-1")

        # Vérifications
        assert isinstance(result, ServiceDetails)
        assert result.id == "service-1"
        assert result.name == "Service d'accompagnement numérique"
        assert (
            result.description
            == "Accompagnement personnalisé pour maîtriser les outils numériques du quotidien."
        )
        assert result.reception_modes == ["en-presentiel"]
        assert result.costs == "gratuit"
        assert result.target_audience == ["adultes"]

    async def test_get_service_details_http_error(self, mock_client):
        """Test de get_service_details avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 404
        from httpx import HTTPStatusError

        mock_client.get.return_value.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "Not Found", request=MagicMock(), response=MagicMock()
            )
        )
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await get_service_details(mock_client, "dora", "service-1")


@pytest.mark.asyncio
class TestSearchServices:
    """Tests pour la fonction search_services."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def search_services_response(self):
        """Charge la réponse de search_services."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "fixtures", "search_services_response.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    @pytest.fixture
    def geocoding_response(self):
        """Réponse simulée pour le géocodage."""
        return {"features": [{"properties": {"citycode": "75056"}}]}

    async def test_search_services_success(
        self, httpx_mock, mock_client, search_services_response, geocoding_response
    ):
        """Test de search_services avec une réponse réussie."""
        from src.mcp_server.services.datainclusion.schemas import SearchedService

        # Configuration des mocks HTTP
        httpx_mock.add_response(
            url="https://api-adresse.data.gouv.fr/search/?q=Paris&limit=1",
            json=geocoding_response,
            status_code=200,
        )

        # Configuration du mock HTTP pour le client principal
        mock_client.get.return_value.json = MagicMock(
            return_value=search_services_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await search_services(
            mock_client, "Paris", "numerique--accompagnement-aux-outils-numeriques"
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        # Vérifier que les objets retournés sont des instances de SearchedService
        assert isinstance(result[0], SearchedService)
        assert isinstance(result[1], SearchedService)

        # Vérifier les champs de contact du service
        assert result[0].phone == "0123456789"
        assert result[0].email == "contact@service-numerique.fr"
        assert result[1].phone == "0198765432"
        assert result[1].email == "info@atelier-mediation.fr"

        # Vérifier les champs de contact de la structure
        assert result[0].structure_details.phone == "0123456789"
        assert result[0].structure_details.email == "contact@maison-quartier.fr"
        assert result[0].structure_details.website == "http://maison-quartier.fr"
        assert result[1].structure_details.phone == "0198765432"
        assert result[1].structure_details.email == "contact@centresocial.paris.fr"
        assert result[1].structure_details.website == "http://centresocial.paris.fr"

    async def test_search_services_with_target_audience(
        self, httpx_mock, mock_client, search_services_response, geocoding_response
    ):
        """Test de search_services avec un public cible."""
        # Configuration des mocks HTTP
        httpx_mock.add_response(
            url="https://api-adresse.data.gouv.fr/search/?q=Paris&limit=1",
            json=geocoding_response,
            status_code=200,
        )

        # Configuration du mock HTTP pour le client principal
        mock_client.get.return_value.json = MagicMock(
            return_value=search_services_response
        )
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await search_services(
            mock_client,
            "Paris",
            "numerique--accompagnement-aux-outils-numeriques",
            "adultes",
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2

    async def test_search_services_geocoding_error(self, httpx_mock):
        """Test de search_services avec une erreur de géocodage."""
        # Configuration du mock HTTP pour simuler une erreur de géocodage
        httpx_mock.add_response(
            url="https://api-adresse.data.gouv.fr/search/?q=InvalidLocation&limit=1",
            json={"features": []},
            status_code=200,
        )

        # Vérification que l'exception est levée
        # Note: Le décorateur api_call_handler attrape les ValueError et les relance comme ModelRetry
        with pytest.raises(ModelRetry) as exc_info:
            await search_services(
                AsyncMock(),
                "InvalidLocation",
                "numerique--accompagnement-aux-outils-numeriques",
            )

        # Vérifier que le message d'erreur contient la raison attendue
        assert (
            "Le géocodage pour 'InvalidLocation' n'a pas retourné de code INSEE valide."
            in str(exc_info.value)
        )

    async def test_search_services_http_error(
        self, httpx_mock, mock_client, geocoding_response
    ):
        """Test de search_services avec une erreur HTTP de l'API Data Inclusion."""
        # Configuration des mocks HTTP
        httpx_mock.add_response(
            url="https://api-adresse.data.gouv.fr/search/?q=Paris&limit=1",
            json=geocoding_response,
            status_code=200,
        )

        # Configuration du mock HTTP pour le client principal
        from httpx import HTTPStatusError

        mock_client.get.return_value.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "Internal Server Error", request=MagicMock(), response=MagicMock()
            )
        )
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await search_services(
                mock_client, "Paris", "numerique--accompagnement-aux-outils-numeriques"
            )
