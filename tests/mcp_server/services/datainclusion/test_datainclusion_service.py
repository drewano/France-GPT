import pytest
import json
import os
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
        self, httpx_mock, reference_themes_response
    ):
        """Test de fetch_reference_values avec une réponse réussie."""
        # Configuration du mock HTTP
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/doc/thematiques",
            json=reference_themes_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await fetch_reference_values("themes")

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(item, ReferenceItem) for item in result)
        assert result[0].value == "numerique--accompagnement-aux-outils-numeriques"
        assert result[0].label == "Accompagnement aux outils numériques"

    async def test_fetch_reference_values_http_error(self, httpx_mock):
        """Test de fetch_reference_values avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 500
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/doc/thematiques",
            status_code=500,
            text="Internal Server Error",
        )

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await fetch_reference_values("themes")


@pytest.mark.asyncio
class TestListAllStructures:
    """Tests pour la fonction list_all_structures."""

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
        self, httpx_mock, list_structures_response
    ):
        """Test de list_all_structures avec une réponse réussie."""
        # Configuration du mock HTTP
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v0/structures?size=15&thematiques=numerique--accompagnement-aux-outils-numeriques",
            json=list_structures_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await list_all_structures(
            "numerique--accompagnement-aux-outils-numeriques"
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, StructureSummary) for item in result)
        assert result[0].id == "structure-1"
        assert result[0].name == "Maison de quartier"

    async def test_list_all_structures_with_network_filter(
        self, httpx_mock, list_structures_response
    ):
        """Test de list_all_structures avec un filtre réseau."""
        # Configuration du mock HTTP
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v0/structures?size=15&thematiques=numerique--accompagnement-aux-outils-numeriques&reseau_porteur=ft",
            json=list_structures_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await list_all_structures(
            "numerique--accompagnement-aux-outils-numeriques", "ft"
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2

    async def test_list_all_structures_http_error(self, httpx_mock):
        """Test de list_all_structures avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 400
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v0/structures?size=15&thematiques=numerique--accompagnement-aux-outils-numeriques",
            status_code=400,
            text="Bad Request",
        )

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await list_all_structures("numerique--accompagnement-aux-outils-numeriques")


@pytest.mark.asyncio
class TestListAllServices:
    """Tests pour la fonction list_all_services."""

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

    async def test_list_all_services_success(self, httpx_mock, list_services_response):
        """Test de list_all_services avec une réponse réussie."""
        # Configuration du mock HTTP
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/services?size=15&thematiques=numerique--accompagnement-aux-outils-numeriques",
            json=list_services_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await list_all_services(
            "numerique--accompagnement-aux-outils-numeriques"
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, ServiceSummary) for item in result)
        assert result[0].id == "service-1"
        assert result[0].name == "Service d'accompagnement numérique"

    async def test_list_all_services_with_filters(
        self, httpx_mock, list_services_response
    ):
        """Test de list_all_services avec des filtres supplémentaires."""
        # Configuration du mock HTTP
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/services?size=15&thematiques=numerique--accompagnement-aux-outils-numeriques&frais=gratuit&publics=adultes",
            json=list_services_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await list_all_services(
            "numerique--accompagnement-aux-outils-numeriques",
            costs=["gratuit"],
            target_audience=["adultes"],
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2

    async def test_list_all_services_http_error(self, httpx_mock):
        """Test de list_all_services avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 500
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/services?size=15&thematiques=numerique--accompagnement-aux-outils-numeriques",
            status_code=500,
            text="Internal Server Error",
        )

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await list_all_services("numerique--accompagnement-aux-outils-numeriques")


@pytest.mark.asyncio
class TestGetStructureDetails:
    """Tests pour la fonction get_structure_details."""

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
        self, httpx_mock, get_structure_details_response
    ):
        """Test de get_structure_details avec une réponse réussie."""
        # Configuration du mock HTTP
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/structures/dora/structure-1",
            json=get_structure_details_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await get_structure_details("dora", "structure-1")

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

    async def test_get_structure_details_http_error(self, httpx_mock):
        """Test de get_structure_details avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 404
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/structures/dora/structure-1",
            status_code=404,
            text="Not Found",
        )

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await get_structure_details("dora", "structure-1")


@pytest.mark.asyncio
class TestGetServiceDetails:
    """Tests pour la fonction get_service_details."""

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
        self, httpx_mock, get_service_details_response
    ):
        """Test de get_service_details avec une réponse réussie."""
        # Configuration du mock HTTP
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/services/dora/service-1",
            json=get_service_details_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await get_service_details("dora", "service-1")

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

    async def test_get_service_details_http_error(self, httpx_mock):
        """Test de get_service_details avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 404
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/services/dora/service-1",
            status_code=404,
            text="Not Found",
        )

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await get_service_details("dora", "service-1")


@pytest.mark.asyncio
class TestSearchServices:
    """Tests pour la fonction search_services."""

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
        self, httpx_mock, search_services_response, geocoding_response
    ):
        """Test de search_services avec une réponse réussie."""
        # Configuration des mocks HTTP
        httpx_mock.add_response(
            url="https://api-adresse.data.gouv.fr/search/?q=Paris&limit=1",
            json=geocoding_response,
            status_code=200,
        )
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/search/services?size=10&code_commune=75056&thematiques=numerique--accompagnement-aux-outils-numeriques",
            json=search_services_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await search_services(
            "Paris", "numerique--accompagnement-aux-outils-numeriques"
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        # Vérifier la structure des résultats transformés
        assert "id" in result[0]
        assert "nom" in result[0]
        assert "structure" in result[0]
        assert "nom" in result[0]["structure"]
        assert "adresse" in result[0]["structure"]

    async def test_search_services_with_target_audience(
        self, httpx_mock, search_services_response, geocoding_response
    ):
        """Test de search_services avec un public cible."""
        # Configuration des mocks HTTP
        httpx_mock.add_response(
            url="https://api-adresse.data.gouv.fr/search/?q=Paris&limit=1",
            json=geocoding_response,
            status_code=200,
        )
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/search/services?size=10&code_commune=75056&thematiques=numerique--accompagnement-aux-outils-numeriques&publics=adultes",
            json=search_services_response,
            status_code=200,
        )

        # Appel de la fonction
        result = await search_services(
            "Paris", "numerique--accompagnement-aux-outils-numeriques", "adultes"
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
        with pytest.raises(
            ModelRetry,
            match="Le géocodage pour 'InvalidLocation' n'a pas retourné de code INSEE valide.",
        ):
            await search_services(
                "InvalidLocation", "numerique--accompagnement-aux-outils-numeriques"
            )

    async def test_search_services_http_error(self, httpx_mock, geocoding_response):
        """Test de search_services avec une erreur HTTP de l'API Data Inclusion."""
        # Configuration des mocks HTTP
        httpx_mock.add_response(
            url="https://api-adresse.data.gouv.fr/search/?q=Paris&limit=1",
            json=geocoding_response,
            status_code=200,
        )
        httpx_mock.add_response(
            url="https://api-staging.data.inclusion.gouv.fr/api/v1/search/services?size=10&code_commune=75056&thematiques=numerique--accompagnement-aux-outils-numeriques",
            status_code=500,
            text="Internal Server Error",
        )

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await search_services(
                "Paris", "numerique--accompagnement-aux-outils-numeriques"
            )
