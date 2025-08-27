import pytest
import json
import os
import httpx
from unittest.mock import mock_open, AsyncMock, MagicMock
from src.mcp_server.services.labonnealternance.service import (
    search_emploi,
    get_emploi,
    search_formations,
    get_formations,
    get_romes,
    get_rncp,
    apply_for_job,
)
from src.mcp_server.services.labonnealternance.schemas import (
    EmploiSummary,
    EmploiDetails,
    FormationSummary,
    FormationDetails,
    RomeCode,
    RncpCode,
)
from pydantic_ai import ModelRetry


@pytest.mark.asyncio
class TestSearchEmploi:
    """Tests pour la fonction search_emploi."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def search_emploi_response(self):
        """Charge la réponse de search_emploi."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "fixtures", "search_emploi_response.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    @pytest.mark.asyncio
    async def test_search_emploi_success(self, mock_client, search_emploi_response):
        """Test de search_emploi avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(return_value=search_emploi_response)
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await search_emploi(mock_client, ["D1405", "D1406"])

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, EmploiSummary) for item in result)
        assert result[0].id == "job-1"
        assert result[0].title == "Commercial en alternance"

    @pytest.mark.asyncio
    async def test_search_emploi_with_location(
        self, mock_client, search_emploi_response
    ):
        """Test de search_emploi avec des coordonnées géographiques."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(return_value=search_emploi_response)
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await search_emploi(mock_client, "D1405", latitude=48.8566, longitude=2.3522)

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_emploi_with_diploma_level(
        self, mock_client, search_emploi_response
    ):
        """Test de search_emploi avec un niveau de diplôme."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(return_value=search_emploi_response)
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await search_emploi(mock_client, "D1405", target_diploma_level="LICENCE")

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_emploi_http_error(self, mock_client):
        """Test de search_emploi avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 500
        from httpx import HTTPStatusError
        mock_client.get.return_value.raise_for_status = MagicMock(side_effect=HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=MagicMock()
        ))
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await search_emploi(mock_client, "D1405")


@pytest.mark.asyncio
class TestGetEmploi:
    """Tests pour la fonction get_emploi."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def get_emploi_response(self):
        """Charge la réponse de get_emploi."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "fixtures", "get_emploi_response.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    @pytest.mark.asyncio
    async def test_get_emploi_success(self, mock_client, get_emploi_response):
        """Test de get_emploi avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(return_value=get_emploi_response)
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await get_emploi(mock_client, "job-1")

        # Vérifications
        assert isinstance(result, EmploiDetails)
        assert result.id == "job-1"
        assert result.title == "Commercial en alternance"
        assert result.company_name == "Entreprise Exemple"
        assert result.description == "Description du poste"

    @pytest.mark.asyncio
    async def test_get_emploi_http_error(self, mock_client):
        """Test de get_emploi avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 404
        from httpx import HTTPStatusError
        mock_client.get.return_value.raise_for_status = MagicMock(side_effect=HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock()
        ))
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await get_emploi(mock_client, "job-1")


@pytest.mark.asyncio
class TestSearchFormations:
    """Tests pour la fonction search_formations."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def search_formations_response(self):
        """Charge la réponse de search_formations."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "fixtures", "search_formations_response.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    @pytest.mark.asyncio
    async def test_search_formations_success(
        self, mock_client, search_formations_response
    ):
        """Test de search_formations avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(return_value=search_formations_response)
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await search_formations(mock_client, ["D1405", "D1406"])

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, FormationSummary) for item in result)
        assert result[0].id == "formation-1"
        assert result[0].title == "Formation en alternance"

    @pytest.mark.asyncio
    async def test_search_formations_with_location(
        self, mock_client, search_formations_response
    ):
        """Test de search_formations avec des coordonnées géographiques."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(return_value=search_formations_response)
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await search_formations(
            mock_client, "D1405", latitude=48.8566, longitude=2.3522, radius=30
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_formations_http_error(self, mock_client):
        """Test de search_formations avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 500
        from httpx import HTTPStatusError
        mock_client.get.return_value.raise_for_status = MagicMock(side_effect=HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=MagicMock()
        ))
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await search_formations(mock_client, "D1405")


@pytest.mark.asyncio
class TestGetFormations:
    """Tests pour la fonction get_formations."""

    @pytest.fixture
    def mock_client(self):
        """Crée un client HTTP mocké."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def get_formations_response(self):
        """Charge la réponse de get_formations."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "fixtures", "get_formations_response.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)

    @pytest.mark.asyncio
    async def test_get_formations_success(self, mock_client, get_formations_response):
        """Test de get_formations avec une réponse réussie."""
        # Configuration du mock HTTP
        mock_client.get.return_value.json = MagicMock(return_value=get_formations_response)
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Appel de la fonction
        result = await get_formations(mock_client, "formation-1")

        # Vérifications
        assert isinstance(result, FormationDetails)
        assert result.id == "formation-1"
        assert result.title == "Formation en alternance"
        assert result.organisme_name == "Organisme Exemple"
        assert result.educational_content == "Contenu pédagogique"

    @pytest.mark.asyncio
    async def test_get_formations_http_error(self, mock_client):
        """Test de get_formations avec une erreur HTTP."""
        # Configuration du mock HTTP pour simuler une erreur 404
        from httpx import HTTPStatusError
        mock_client.get.return_value.raise_for_status = MagicMock(side_effect=HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock()
        ))
        # Ajout d'un mock pour json() même si elle n'est pas appelée dans le chemin d'erreur
        mock_client.get.return_value.json = MagicMock()

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await get_formations(mock_client, "formation-1")


@pytest.mark.asyncio
class TestGetRomes:
    """Tests pour la fonction get_romes."""

    @pytest.fixture
    def mock_romes_data(self):
        """Données de test pour les codes ROME."""
        return [
            {"code": "D1405", "libelle": "Commercial en alternance"},
            {"code": "D1406", "libelle": "Technico-commercial en alternance"},
            {"code": "D1501", "libelle": "Animateur commercial"},
        ]

    @pytest.mark.asyncio
    async def test_get_romes_success(self, mocker, mock_romes_data):
        """Test de get_romes avec une réponse réussie."""
        # Mock du fichier romes.json
        mocker.patch("builtins.open", mock_open(read_data=json.dumps(mock_romes_data)))
        # Mock pathlib.Path.exists to return True
        mocker.patch("pathlib.Path.exists", return_value=True)

        # Appel de la fonction
        result = await get_romes("commercial", 10)

        # Vérifications
        assert isinstance(result, list)
        # Vérifier que nous avons 3 résultats (tous ceux qui contiennent "commercial")
        assert len(result) == 3
        assert all(isinstance(item, RomeCode) for item in result)
        assert result[0].code == "D1405"
        assert "commercial" in result[0].libelle.lower()

    @pytest.mark.asyncio
    async def test_get_romes_file_not_found(self, mocker):
        """Test de get_romes quand le fichier n'est pas trouvé."""
        # Mock pour simuler un fichier non trouvé
        mocker.patch("pathlib.Path.exists", return_value=False)

        # Appel de la fonction
        result = await get_romes("commercial", 10)

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_romes_invalid_json(self, mocker):
        """Test de get_romes avec un fichier JSON invalide."""
        # Mock du fichier romes.json avec du contenu invalide
        mocker.patch("builtins.open", mock_open(read_data="invalid json"))

        # Appel de la fonction
        result = await get_romes("commercial", 10)

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 0


@pytest.mark.asyncio
class TestGetRncp:
    """Tests pour la fonction get_rncp."""

    @pytest.fixture
    def mock_rncp_data(self):
        """Données de test pour les codes RNCP."""
        return [
            {
                "Code RNCP": "RNCP1234",
                "Intitulé de la certification": "Technicien supérieur en commercialisation",
                "Certificateur": "MINISTERE DE L'EDUCATION NATIONALE",
                "Type diplôme": "BTS",
            },
            {
                "Code RNCP": "RNCP5678",
                "Intitulé de la certification": "Technico-commercial",
                "Certificateur": "MINISTERE DE L'EDUCATION NATIONALE",
                "Type diplôme": "BTS",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_rncp_success(self, mocker, mock_rncp_data):
        """Test de get_rncp avec une réponse réussie."""
        # Mock du fichier rncp.json
        mocker.patch("builtins.open", mock_open(read_data=json.dumps(mock_rncp_data)))

        # Appel de la fonction
        result = await get_rncp("technico-commercial", 10)

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 1
        assert all(isinstance(item, RncpCode) for item in result)
        assert result[0].code_rncp == "RNCP5678"
        assert "technico-commercial" in result[0].intitule.lower()

    @pytest.mark.asyncio
    async def test_get_rncp_file_not_found(self, mocker):
        """Test de get_rncp quand le fichier n'est pas trouvé."""
        # Mock pour simuler un fichier non trouvé
        mocker.patch("pathlib.Path.exists", return_value=False)

        # Appel de la fonction
        result = await get_rncp("technico-commercial", 10)

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_rncp_invalid_json(self, mocker):
        """Test de get_rncp avec un fichier JSON invalide."""
        # Mock du fichier rncp.json avec du contenu invalide
        mocker.patch("builtins.open", mock_open(read_data="invalid json"))

        # Appel de la fonction
        result = await get_rncp("technico-commercial", 10)

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 0


@pytest.mark.asyncio
class TestApplyForJob:
    """Tests pour la fonction apply_for_job."""

    @pytest.mark.asyncio
    async def test_apply_for_job_success(self, mocker):
        """Test de apply_for_job avec une réponse réussie."""
        # Mock du client S3 asynchrone avec aioboto3
        mock_body = mocker.AsyncMock()
        mock_body.__aenter__ = mocker.AsyncMock(return_value=mocker.AsyncMock())
        mock_body.__aenter__.return_value.read = mocker.AsyncMock(
            return_value=b"contenu-cv-test"
        )

        mock_s3_client = mocker.AsyncMock()
        mock_s3_client.get_object = mocker.AsyncMock(return_value={"Body": mock_body})

        # Mock de la session aioboto3
        mock_session = mocker.patch(
            "src.mcp_server.services.labonnealternance.service.aioboto3.Session"
        )
        mock_session.return_value.client.return_value.__aenter__ = mocker.AsyncMock(
            return_value=mock_s3_client
        )
        mock_session.return_value.client.return_value.__aexit__ = mocker.AsyncMock()

        # Création d'un client HTTP mocké
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value.json = MagicMock(return_value={"id": "application-123"})
        mock_client.post.return_value.raise_for_status = MagicMock()

        # Appel de la fonction avec des données de test
        result = await apply_for_job(
            mock_client,
            applicant_first_name="Jean",
            applicant_last_name="Dupont",
            applicant_email="jean.dupont@example.com",
            applicant_phone="0123456789",
            applicant_attachment_name="cv_jean_dupont.pdf",
            cv_s3_object_key="cvs/test-cv.pdf",
            recipient_id="recipient-123",
        )

        # Vérifications
        assert isinstance(result, dict)
        assert result["id"] == "application-123"

        # Vérifier que get_object a été appelé avec les bons paramètres
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="datainclusion-elements", Key="cvs/test-cv.pdf"
        )

        # Vérifier que le contenu encodé en base64 est correct dans la requête
        import base64

        expected_base64_content = base64.b64encode(b"contenu-cv-test").decode("utf-8")

        # Vérifier que post a été appelé avec les bons arguments
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/job/v1/apply"
        
        # Vérifier que le payload contient le contenu encodé en base64
        payload = call_args[1]["json"]
        assert payload["applicant_attachment_content"] == expected_base64_content
