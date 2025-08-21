from unittest.mock import patch
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

from src.agent.agent import create_agent_from_profile, create_synthesis_agent
from src.core.config import AppSettings, AgentSettings, MCPServerSettings
from src.core.profiles import AGENT_PROFILES


def test_create_agent_from_profile():
    """Test that create_agent_from_profile creates an agent with correct configuration."""

    # Create mock settings with a datainclusion service
    mock_agent_settings = AgentSettings(
        OPENAI_API_KEY="test-key",
        AGENT_MODEL_NAME="gpt-4.1",
        MCP_SERVER_HOST_URL="http://mcp_server",
    )

    mock_mcp_settings = MCPServerSettings(
        MCP_API_PATH="/mcp/",
        MCP_SERVICES_CONFIG='[{"name": "datainclusion", "port": 8001}]',
    )

    mock_settings = AppSettings(agent=mock_agent_settings, mcp_server=mock_mcp_settings)

    # Patch the settings in the agent module
    with patch("src.agent.agent.settings", mock_settings):
        # Get the social agent profile
        profile = AGENT_PROFILES["social_agent"]

        # Create the agent
        agent = create_agent_from_profile(profile)

        # Verify it's an Agent instance
        assert isinstance(agent, Agent)

        # Verify the system prompt is correct
        assert agent._system_prompts == (profile.system_prompt,)

        # Verify that toolsets contain an MCPServerStreamableHTTP instance
        # La nouvelle API utilise 'toolsets' au lieu de '_toolsets'
        # Note: pydantic-ai ajoute maintenant un toolset par défaut, donc on a 2 toolsets au total
        assert len(agent.toolsets) == 2
        # Le MCPServerStreamableHTTP devrait être le deuxième toolset
        mcp_server = agent.toolsets[1]
        assert isinstance(mcp_server, MCPServerStreamableHTTP)

        # Verify the MCP server URL is correctly constructed
        expected_url = "http://mcp_server:8001/mcp/"
        assert mcp_server.url == expected_url


def test_create_synthesis_agent():
    """Test that create_synthesis_agent creates an agent without toolsets."""

    # Create mock settings
    mock_agent_settings = AgentSettings(
        OPENAI_API_KEY="test-key", AGENT_MODEL_NAME="gpt-4.1"
    )

    mock_settings = AppSettings(
        agent=mock_agent_settings, mcp_server=MCPServerSettings()
    )

    # Patch the settings in the agent module
    with patch("src.agent.agent.settings", mock_settings):
        # Create the synthesis agent
        agent = create_synthesis_agent()

        # Verify it's an Agent instance
        assert isinstance(agent, Agent)

        # Verify the system prompt is correct
        expected_prompt = (
            "Tu es un assistant de synthèse. Ta seule mission est de formuler une réponse finale "
            "et cohérente à la question initiale de l'utilisateur en te basant exclusivement sur "
            "l'historique de la conversation incluant les résultats d'appels d'outils déjà effectués. "
            "Ne tente JAMAIS d'appeler un outil. Conclus la conversation en fournissant la "
            "meilleure réponse possible avec les informations disponibles."
        )
        assert agent._system_prompts == (expected_prompt,)

        # Verify that toolsets contains only the default toolset
        # La nouvelle API utilise 'toolsets' au lieu de '_toolsets'
        # Note: pydantic-ai ajoute maintenant un toolset par défaut même si on passe une liste vide
        assert len(agent.toolsets) == 1
