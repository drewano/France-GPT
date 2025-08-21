import pytest
from unittest.mock import MagicMock, patch
from src.mcp_server.services.legifrance.service import (
    rechercher_textes_juridiques,
    consulter_article_code,
    consulter_texte_loi_decret,
    consulter_decision_justice,
    consulter_convention_collective,
    _format_full_document_output,
)
from pydantic_ai import ModelRetry


class TestFormatFullDocumentOutput:
    """Tests pour la fonction _format_full_document_output."""

    def test_format_with_texte_html(self):
        """Test du formatage avec attribut texte_html."""
        # Création d'un objet mock avec attribut texte_html
        mock_doc = MagicMock()
        mock_doc.id = "TEST123"
        mock_doc.title = "Test Document"
        mock_doc.texte_html = "<p>Contenu HTML</p>"
        mock_doc.url = "https://example.com"

        # Appel de la fonction
        result = _format_full_document_output(mock_doc)

        # Vérifications
        assert result == {
            "titre": "Test Document",
            "id": "TEST123",
            "contenu_html": "<p>Contenu HTML</p>",
            "url_legifrance": "https://example.com",
        }

    def test_format_with_content_html(self):
        """Test du formatage avec attribut content_html."""
        # Création d'un objet mock avec attribut content_html
        mock_doc = MagicMock()
        mock_doc.id = "TEST124"
        mock_doc.title = "Test Document 2"
        # Supprimer texte_html pour forcer l'utilisation de content_html
        if hasattr(mock_doc, "texte_html"):
            delattr(mock_doc, "texte_html")
        mock_doc.content_html = "<div>Contenu HTML</div>"
        mock_doc.url = "https://example.com/2"

        # Appel de la fonction
        result = _format_full_document_output(mock_doc)

        # Vérifications
        expected = {
            "titre": "Test Document 2",
            "id": "TEST124",
            "contenu_html": "<div>Contenu HTML</div>",
            "url_legifrance": "https://example.com/2",
        }
        assert result == expected

    def test_format_with_no_content(self):
        """Test du formatage avec aucun attribut de contenu."""
        # Création d'un objet mock sans attributs de contenu
        mock_doc = MagicMock()
        mock_doc.id = "TEST125"
        mock_doc.title = "Test Document 3"
        # Supprimer les attributs de contenu possibles
        if hasattr(mock_doc, "texte_html"):
            delattr(mock_doc, "texte_html")
        if hasattr(mock_doc, "content_html"):
            delattr(mock_doc, "content_html")
        if hasattr(mock_doc, "content"):
            delattr(mock_doc, "content")
        if hasattr(mock_doc, "text"):
            delattr(mock_doc, "text")
        # Supprimer l'attribut url pour que hasattr(mock_doc, 'url') renvoie False
        if hasattr(mock_doc, "url"):
            delattr(mock_doc, "url")

        # Appel de la fonction
        result = _format_full_document_output(mock_doc)

        # Vérifications
        expected = {
            "titre": "Test Document 3",
            "id": "TEST125",
            "contenu_html": "Contenu non disponible",
            "url_legifrance": "https://www.legifrance.gouv.fr/loda/id/TEST125",
        }
        assert result == expected

    def test_format_with_none_document(self):
        """Test du formatage avec document None."""
        # Appel de la fonction avec None
        result = _format_full_document_output(None)

        # Vérifications
        assert result == {}


@pytest.mark.asyncio
class TestRechercherTextesJuridiques:
    """Tests pour la fonction rechercher_textes_juridiques."""

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    @patch("src.mcp_server.services.legifrance.service.juri_api")
    async def test_rechercher_textes_juridiques_success(
        self, mock_juri_api, mock_loda_service
    ):
        """Test de rechercher_textes_juridiques avec succès."""
        # Configuration des mocks
        mock_loda_result = MagicMock()
        mock_loda_result.id = "LEGITEXT000000000001"
        mock_loda_result.title = "Loi Test"

        mock_juri_result = MagicMock()
        mock_juri_result.id = "JURI000000000001"
        mock_juri_result.titre = "Décision Test"

        mock_loda_service.search.return_value = [mock_loda_result]
        mock_juri_api.search.return_value = [mock_juri_result]

        # Appel de la fonction
        result = await rechercher_textes_juridiques("test")

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "LEGITEXT000000000001"
        assert result[0]["outil_recommande"] == "consulter_texte_loi_decret"
        assert result[1]["id"] == "JURI000000000001"
        assert result[1]["outil_recommande"] == "consulter_decision_justice"

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    @patch("src.mcp_server.services.legifrance.service.juri_api")
    async def test_rechercher_textes_juridiques_with_error(
        self, mock_juri_api, mock_loda_service
    ):
        """Test de rechercher_textes_juridiques avec une erreur."""
        # Configuration du mock pour lever une exception
        mock_loda_service.search.side_effect = ValueError("Erreur de recherche")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await rechercher_textes_juridiques("test")


@pytest.mark.asyncio
class TestConsulterArticleCode:
    """Tests pour la fonction consulter_article_code."""

    @patch("src.mcp_server.services.legifrance.service.code_service")
    async def test_consulter_article_code_success(self, mock_code_service):
        """Test de consulter_article_code avec succès."""
        # Configuration du mock
        mock_article = MagicMock()
        mock_article.id = "LEGIARTI000000000001"
        mock_article.title = "Article Test"
        mock_article.texte_html = "<p>Contenu de l'article</p>"
        mock_article.url = "https://example.com/article"

        mock_fetch_result = MagicMock()
        mock_fetch_result.at.return_value = mock_article
        mock_code_service.fetch_article.return_value = mock_fetch_result

        # Appel de la fonction
        result = await consulter_article_code("LEGIARTI000000000001")

        # Vérifications
        assert result is not None
        assert result["id"] == "LEGIARTI000000000001"
        assert result["titre"] == "Article Test"
        assert result["contenu_html"] == "<p>Contenu de l'article</p>"

    @patch("src.mcp_server.services.legifrance.service.code_service")
    async def test_consulter_article_code_with_none_result(self, mock_code_service):
        """Test de consulter_article_code avec résultat None."""
        # Configuration du mock pour retourner None
        mock_fetch_result = MagicMock()
        mock_fetch_result.at.return_value = None
        mock_code_service.fetch_article.return_value = mock_fetch_result

        # Appel de la fonction
        result = await consulter_article_code("LEGIARTI000000000001")

        # Vérifications
        assert result is None

    @patch("src.mcp_server.services.legifrance.service.code_service")
    async def test_consulter_article_code_with_error(self, mock_code_service):
        """Test de consulter_article_code avec une erreur."""
        # Configuration du mock pour lever une exception
        mock_code_service.fetch_article.side_effect = ValueError("Article non trouvé")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await consulter_article_code("LEGIARTI000000000001")


@pytest.mark.asyncio
class TestConsulterTexteLoiDecret:
    """Tests pour la fonction consulter_texte_loi_decret."""

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    async def test_consulter_texte_loi_decret_success(self, mock_loda_service):
        """Test de consulter_texte_loi_decret avec succès."""
        # Configuration du mock
        mock_texte = MagicMock()
        mock_texte.id = "LEGITEXT000000000001"
        mock_texte.title = "Loi Test"
        mock_texte.texte_html = "<p>Contenu de la loi</p>"
        mock_texte.url = "https://example.com/loi"

        mock_loda_service.fetch.return_value = mock_texte

        # Appel de la fonction
        result = await consulter_texte_loi_decret("LEGITEXT000000000001")

        # Vérifications
        assert result is not None
        assert result["id"] == "LEGITEXT000000000001"
        assert result["titre"] == "Loi Test"
        assert result["contenu_html"] == "<p>Contenu de la loi</p>"

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    async def test_consulter_texte_loi_decret_with_id_enrichment(
        self, mock_loda_service
    ):
        """Test de consulter_texte_loi_decret avec enrichissement d'ID."""
        # Configuration du mock
        mock_texte = MagicMock()
        mock_texte.id = "LEGITEXT000000000001_01-01-2023"
        mock_texte.title = "Loi Test"
        mock_texte.texte_html = "<p>Contenu de la loi</p>"

        mock_loda_service.fetch.return_value = mock_texte

        # Appel de la fonction avec ID sans date
        result = await consulter_texte_loi_decret("LEGITEXT000000000001")

        # Vérifications
        mock_loda_service.fetch.assert_called()
        assert result is not None

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    async def test_consulter_texte_loi_decret_with_none_result(self, mock_loda_service):
        """Test de consulter_texte_loi_decret avec résultat None."""
        # Configuration du mock pour retourner None
        mock_loda_service.fetch.return_value = None

        # Appel de la fonction
        result = await consulter_texte_loi_decret("LEGITEXT000000000001")

        # Vérifications
        assert result is None

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    async def test_consulter_texte_loi_decret_with_error(self, mock_loda_service):
        """Test de consulter_texte_loi_decret avec une erreur."""
        # Configuration du mock pour lever une exception
        mock_loda_service.fetch.side_effect = ValueError("Texte non trouvé")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await consulter_texte_loi_decret("LEGITEXT000000000001")


@pytest.mark.asyncio
class TestConsulterDecisionJustice:
    """Tests pour la fonction consulter_decision_justice."""

    @patch("src.mcp_server.services.legifrance.service.juri_api")
    async def test_consulter_decision_justice_success(self, mock_juri_api):
        """Test de consulter_decision_justice avec succès."""
        # Configuration du mock
        mock_decision = MagicMock()
        mock_decision.id = "JURI000000000001"
        mock_decision.title = "Décision Test"
        mock_decision.texte_html = "<p>Contenu de la décision</p>"
        mock_decision.url = "https://example.com/decision"

        mock_juri_api.fetch.return_value = mock_decision

        # Appel de la fonction
        result = await consulter_decision_justice("JURI000000000001")

        # Vérifications
        assert result is not None
        assert result["id"] == "JURI000000000001"
        assert result["titre"] == "Décision Test"
        assert result["contenu_html"] == "<p>Contenu de la décision</p>"

    @patch("src.mcp_server.services.legifrance.service.juri_api")
    async def test_consulter_decision_justice_with_none_result(self, mock_juri_api):
        """Test de consulter_decision_justice avec résultat None."""
        # Configuration du mock pour retourner None
        mock_juri_api.fetch.return_value = None

        # Appel de la fonction
        result = await consulter_decision_justice("JURI000000000001")

        # Vérifications
        assert result is None

    @patch("src.mcp_server.services.legifrance.service.juri_api")
    async def test_consulter_decision_justice_with_error(self, mock_juri_api):
        """Test de consulter_decision_justice avec une erreur."""
        # Configuration du mock pour lever une exception
        mock_juri_api.fetch.side_effect = ValueError("Décision non trouvée")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await consulter_decision_justice("JURI000000000001")


@pytest.mark.asyncio
class TestConsulterConventionCollective:
    """Tests pour la fonction consulter_convention_collective."""

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    async def test_consulter_convention_collective_success(self, mock_loda_service):
        """Test de consulter_convention_collective avec succès."""
        # Configuration du mock
        mock_convention = MagicMock()
        mock_convention.id = "KALITEXT000000000001"
        mock_convention.title = "Convention Collective Test"
        mock_convention.texte_html = "<p>Contenu de la convention</p>"
        mock_convention.url = "https://example.com/convention"

        mock_loda_service.fetch.return_value = mock_convention

        # Appel de la fonction
        result = await consulter_convention_collective("KALITEXT000000000001")

        # Vérifications
        assert result is not None
        assert result["id"] == "KALITEXT000000000001"
        assert result["titre"] == "Convention Collective Test"
        assert result["contenu_html"] == "<p>Contenu de la convention</p>"

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    async def test_consulter_convention_collective_with_id_enrichment(
        self, mock_loda_service
    ):
        """Test de consulter_convention_collective avec enrichissement d'ID."""
        # Configuration du mock
        mock_convention = MagicMock()
        mock_convention.id = "KALITEXT000000000001_01-01-2023"
        mock_convention.title = "Convention Collective Test"
        mock_convention.texte_html = "<p>Contenu de la convention</p>"

        mock_loda_service.fetch.return_value = mock_convention

        # Appel de la fonction avec ID sans date
        result = await consulter_convention_collective("KALITEXT000000000001")

        # Vérifications
        mock_loda_service.fetch.assert_called()
        assert result is not None

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    async def test_consulter_convention_collective_with_none_result(
        self, mock_loda_service
    ):
        """Test de consulter_convention_collective avec résultat None."""
        # Configuration du mock pour retourner None
        mock_loda_service.fetch.return_value = None

        # Appel de la fonction
        result = await consulter_convention_collective("KALITEXT000000000001")

        # Vérifications
        assert result is None

    @patch("src.mcp_server.services.legifrance.service.loda_service")
    async def test_consulter_convention_collective_with_error(self, mock_loda_service):
        """Test de consulter_convention_collective avec une erreur."""
        # Configuration du mock pour lever une exception
        mock_loda_service.fetch.side_effect = ValueError("Convention non trouvée")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await consulter_convention_collective("KALITEXT000000000001")
