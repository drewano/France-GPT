import pytest
from unittest.mock import MagicMock, AsyncMock
from src.mcp_server.services.legifrance.service import (
    rechercher_textes_juridiques,
    consulter_article_code,
    consulter_texte_loi_decret,
    consulter_decision_justice,
    consulter_convention_collective,
)
from pydantic_ai import ModelRetry


@pytest.mark.asyncio
class TestRechercherTextesJuridiques:
    """Tests pour la fonction rechercher_textes_juridiques."""

    async def test_rechercher_textes_juridiques_success(self):
        """Test de rechercher_textes_juridiques avec succès."""
        # Configuration des mocks
        mock_loda = MagicMock()
        mock_juri = MagicMock()
        
        # Configuration des résultats LODA
        mock_loda_result = MagicMock()
        mock_loda_result.id = "LEGITEXT000000000001"
        mock_loda_result.title = "Loi Test"
        
        # Configuration des résultats JURI
        mock_juri_result = MagicMock()
        mock_juri_result.id = "JURI000000000001"
        mock_juri_result.title = "Décision Test"
        
        # Configuration des comportements des mocks
        mock_loda.search.return_value = [mock_loda_result]
        mock_juri.search.return_value = [mock_juri_result]

        # Appel de la fonction
        result = await rechercher_textes_juridiques(
            "test", 
            loda_service=mock_loda, 
            juri_api=mock_juri
        )

        # Vérifications
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "LEGITEXT000000000001"
        assert result[0]["outil_recommande"] == "consulter_texte_loi_decret"
        assert result[1]["id"] == "JURI000000000001"
        assert result[1]["outil_recommande"] == "consulter_decision_justice"

    async def test_rechercher_textes_juridiques_with_error(self):
        """Test de rechercher_textes_juridiques avec une erreur."""
        # Configuration des mocks
        mock_loda = MagicMock()
        mock_juri = MagicMock()
        
        # Configuration du mock pour lever une exception
        mock_loda.search.side_effect = ValueError("Erreur de recherche")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await rechercher_textes_juridiques(
                "test", 
                loda_service=mock_loda, 
                juri_api=mock_juri
            )

    async def test_rechercher_textes_juridiques_with_juri_error(self):
        """Test de rechercher_textes_juridiques avec une erreur dans la recherche JURI."""
        # Configuration des mocks
        mock_loda = MagicMock()
        mock_juri = MagicMock()
        
        # Configuration des résultats LODA
        mock_loda_result = MagicMock()
        mock_loda_result.id = "LEGITEXT000000000001"
        mock_loda_result.title = "Loi Test"
        mock_loda.search.return_value = [mock_loda_result]

        # Configuration du mock JURI pour lever une exception
        mock_juri.search.side_effect = ValueError("Erreur de recherche JURI")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await rechercher_textes_juridiques(
                "test", 
                loda_service=mock_loda, 
                juri_api=mock_juri
            )


@pytest.mark.asyncio
class TestConsulterArticleCode:
    """Tests pour la fonction consulter_article_code."""

    async def test_consulter_article_code_success(self):
        """Test de consulter_article_code avec succès."""
        # Configuration du mock
        mock_code_service = MagicMock()
        mock_article = MagicMock()
        mock_article.id = "LEGIARTI000000000001"
        mock_article.title = "Article Test"
        mock_article.texte_html = "<p>Contenu de l'article</p>"
        mock_article.url = "https://example.com/article"

        mock_fetch_result = MagicMock()
        mock_fetch_result.at.return_value = mock_article
        mock_code_service.fetch_article.return_value = mock_fetch_result

        # Appel de la fonction
        result = await consulter_article_code(
            "LEGIARTI000000000001", 
            code_service=mock_code_service
        )

        # Vérifications
        assert result is not None
        assert result["id"] == "LEGIARTI000000000001"
        assert result["titre"] == "Article Test"
        assert result["contenu_html"] == "<p>Contenu de l'article</p>"

    async def test_consulter_article_code_with_none_result(self):
        """Test de consulter_article_code avec résultat None."""
        # Configuration du mock
        mock_code_service = MagicMock()
        mock_fetch_result = MagicMock()
        mock_fetch_result.at.return_value = None
        mock_code_service.fetch_article.return_value = mock_fetch_result

        # Appel de la fonction
        result = await consulter_article_code(
            "LEGIARTI000000000001", 
            code_service=mock_code_service
        )

        # Vérifications
        assert result is None

    async def test_consulter_article_code_with_error(self):
        """Test de consulter_article_code avec une erreur."""
        # Configuration du mock
        mock_code_service = MagicMock()
        mock_code_service.fetch_article.side_effect = ValueError("Article non trouvé")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await consulter_article_code(
                "LEGIARTI000000000001", 
                code_service=mock_code_service
            )


@pytest.mark.asyncio
class TestConsulterTexteLoiDecret:
    """Tests pour la fonction consulter_texte_loi_decret."""

    async def test_consulter_texte_loi_decret_success(self):
        """Test de consulter_texte_loi_decret avec succès."""
        # Configuration du mock
        mock_loda_service = MagicMock()
        mock_texte = MagicMock()
        mock_texte.id = "LEGITEXT000000000001"
        mock_texte.title = "Loi Test"
        mock_texte.texte_html = "<p>Contenu de la loi</p>"
        mock_texte.url = "https://example.com/loi"

        mock_loda_service.fetch.return_value = mock_texte

        # Appel de la fonction
        result = await consulter_texte_loi_decret(
            "LEGITEXT000000000001", 
            loda_service=mock_loda_service
        )

        # Vérifications
        assert result is not None
        assert result["id"] == "LEGITEXT000000000001"
        assert result["titre"] == "Loi Test"
        assert result["contenu_html"] == "<p>Contenu de la loi</p>"

    async def test_consulter_texte_loi_decret_with_none_result(self):
        """Test de consulter_texte_loi_decret avec résultat None."""
        # Configuration du mock
        mock_loda_service = MagicMock()
        mock_loda_service.fetch.return_value = None

        # Appel de la fonction
        result = await consulter_texte_loi_decret(
            "LEGITEXT000000000001", 
            loda_service=mock_loda_service
        )

        # Vérifications
        assert result is None

    async def test_consulter_texte_loi_decret_with_error(self):
        """Test de consulter_texte_loi_decret avec une erreur."""
        # Configuration du mock
        mock_loda_service = MagicMock()
        mock_loda_service.fetch.side_effect = ValueError("Texte non trouvé")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await consulter_texte_loi_decret(
                "LEGITEXT000000000001", 
                loda_service=mock_loda_service
            )


@pytest.mark.asyncio
class TestConsulterDecisionJustice:
    """Tests pour la fonction consulter_decision_justice."""

    async def test_consulter_decision_justice_success(self):
        """Test de consulter_decision_justice avec succès."""
        # Configuration du mock
        mock_juri_api = MagicMock()
        mock_decision = MagicMock()
        mock_decision.id = "JURI000000000001"
        mock_decision.title = "Décision Test"
        mock_decision.texte_html = "<p>Contenu de la décision</p>"
        mock_decision.url = "https://example.com/decision"

        mock_juri_api.fetch.return_value = mock_decision

        # Appel de la fonction
        result = await consulter_decision_justice(
            "JURI000000000001", 
            juri_api=mock_juri_api
        )

        # Vérifications
        assert result is not None
        assert result["id"] == "JURI000000000001"
        assert result["titre"] == "Décision Test"
        assert result["contenu_html"] == "<p>Contenu de la décision</p>"

    async def test_consulter_decision_justice_with_none_result(self):
        """Test de consulter_decision_justice avec résultat None."""
        # Configuration du mock
        mock_juri_api = MagicMock()
        mock_juri_api.fetch.return_value = None

        # Appel de la fonction
        result = await consulter_decision_justice(
            "JURI000000000001", 
            juri_api=mock_juri_api
        )

        # Vérifications
        assert result is None

    async def test_consulter_decision_justice_with_error(self):
        """Test de consulter_decision_justice avec une erreur."""
        # Configuration du mock
        mock_juri_api = MagicMock()
        mock_juri_api.fetch.side_effect = ValueError("Décision non trouvée")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await consulter_decision_justice(
                "JURI000000000001", 
                juri_api=mock_juri_api
            )


@pytest.mark.asyncio
class TestConsulterConventionCollective:
    """Tests pour la fonction consulter_convention_collective."""

    async def test_consulter_convention_collective_success(self):
        """Test de consulter_convention_collective avec succès."""
        # Configuration du mock
        mock_loda_service = MagicMock()
        mock_convention = MagicMock()
        mock_convention.id = "KALITEXT000000000001"
        mock_convention.title = "Convention Collective Test"
        mock_convention.texte_html = "<p>Contenu de la convention</p>"
        mock_convention.url = "https://example.com/convention"

        mock_loda_service.fetch.return_value = mock_convention

        # Appel de la fonction
        result = await consulter_convention_collective(
            "KALITEXT000000000001", 
            loda_service=mock_loda_service
        )

        # Vérifications
        assert result is not None
        assert result["id"] == "KALITEXT000000000001"
        assert result["titre"] == "Convention Collective Test"
        assert result["contenu_html"] == "<p>Contenu de la convention</p>"

    async def test_consulter_convention_collective_with_none_result(self):
        """Test de consulter_convention_collective avec résultat None."""
        # Configuration du mock
        mock_loda_service = MagicMock()
        mock_loda_service.fetch.return_value = None

        # Appel de la fonction
        result = await consulter_convention_collective(
            "KALITEXT000000000001", 
            loda_service=mock_loda_service
        )

        # Vérifications
        assert result is None

    async def test_consulter_convention_collective_with_error(self):
        """Test de consulter_convention_collective avec une erreur."""
        # Configuration du mock
        mock_loda_service = MagicMock()
        mock_loda_service.fetch.side_effect = ValueError("Convention non trouvée")

        # Vérification que l'exception est levée
        with pytest.raises(ModelRetry):
            await consulter_convention_collective(
                "KALITEXT000000000001", 
                loda_service=mock_loda_service
            )
