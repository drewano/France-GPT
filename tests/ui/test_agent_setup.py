import pytest
from unittest.mock import AsyncMock, patch
from src.ui.agent_setup import setup_agent
from src.core.profiles import AgentProfile


@pytest.mark.asyncio
async def test_setup_agent(mocker):
    """Test the setup_agent function."""
    # Mock cl.user_session.get to return a specific profile name
    mock_get = mocker.patch("src.ui.agent_setup.cl.user_session.get")
    mock_get.return_value = "Agent Social"

    # Mock cl.user_session.set
    mock_set = mocker.patch("src.ui.agent_setup.cl.user_session.set")

    # Mock create_agent_from_profile to return a mock agent
    mock_agent = AsyncMock()
    with patch(
        "src.ui.agent_setup.create_agent_from_profile", return_value=mock_agent
    ) as mock_create_agent:
        # Create a mock profile
        mock_profile = AgentProfile(
            id="social_agent",
            name="Agent Social",
            description="A social agent",
            icon="/public/avatars/social_agent.svg",
            system_prompt="You are a social agent",
            mcp_service_name="datainclusion",
            tool_call_limit=10,
        )

        # Mock the AGENT_PROFILES to return our mock profile
        with patch("src.ui.agent_setup.AGENT_PROFILES", {"social_agent": mock_profile}):
            # Call the function
            await setup_agent()

            # Assertions
            # Check that cl.user_session.get was called with 'chat_profile'
            mock_get.assert_called_once_with("chat_profile")

            # Check that create_agent_from_profile was called with the correct profile
            mock_create_agent.assert_called_once()
            args, kwargs = mock_create_agent.call_args
            assert args[0].id == "social_agent"

            # Check that cl.user_session.set was called twice
            assert mock_set.call_count == 2

            # Check the first call was for 'agent'
            mock_set.assert_any_call("agent", mock_agent)

            # Check the second call was for 'selected_profile_id'
            mock_set.assert_any_call("selected_profile_id", "social_agent")
