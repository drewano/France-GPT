import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.mcp_server.tool_transformer import ToolTransformer, ToolTransformerConfig
from src.mcp_server.utils import HTTPRoute
from fastmcp.tools import Tool
from fastmcp.utilities.components import FastMCPComponent


class TestToolTransformer:
    """Tests for the ToolTransformer class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_mcp_server(self):
        """Create a mock MCP server."""
        return MagicMock()

    @pytest.fixture
    def mock_http_routes(self):
        """Create mock HTTP routes."""
        return []

    @pytest.fixture
    def transformer_config(self, mock_mcp_server, mock_http_routes, mock_logger):
        """Create a ToolTransformerConfig."""
        return ToolTransformerConfig(
            mcp_server=mock_mcp_server,
            http_routes=mock_http_routes,
            custom_tool_names={},
            op_id_map={},
            logger=mock_logger,
        )

    @pytest.fixture
    def tool_transformer(self, transformer_config):
        """Create a ToolTransformer instance."""
        return ToolTransformer(transformer_config)

    def test_discover_and_customize(self, tool_transformer):
        """Test the discover_and_customize method."""
        # Create mocks
        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.operation_id = "test_operation"

        mock_component = MagicMock(spec=FastMCPComponent)
        mock_component.name = "test_tool_name"

        # Mock the clean_json_schema function
        with patch("src.mcp_server.tool_transformer.clean_json_schema") as mock_clean:
            # Call the method
            tool_transformer.discover_and_customize(mock_route, mock_component)

            # Verify clean_json_schema was called
            mock_clean.assert_called_once_with(mock_component, tool_transformer.logger)

            # Verify op_id_map was updated
            assert tool_transformer.op_id_map["test_operation"] == "test_tool_name"

    def test_discover_and_customize_without_operation_id(self, tool_transformer):
        """Test discover_and_customize when route has no operation_id."""
        # Create mocks
        mock_route = MagicMock(spec=HTTPRoute)
        del mock_route.operation_id  # Remove operation_id attribute

        mock_component = MagicMock(spec=FastMCPComponent)
        mock_component.name = "test_tool_name"

        # Mock the clean_json_schema function
        with patch("src.mcp_server.tool_transformer.clean_json_schema") as mock_clean:
            # Call the method
            tool_transformer.discover_and_customize(mock_route, mock_component)

            # Verify clean_json_schema was called
            mock_clean.assert_called_once_with(mock_component, tool_transformer.logger)

            # Verify op_id_map was not updated
            assert len(tool_transformer.op_id_map) == 0

    def test_discover_and_customize_without_component_name(self, tool_transformer):
        """Test discover_and_customize when component has no name."""
        # Create mocks
        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.operation_id = "test_operation"

        mock_component = MagicMock(spec=FastMCPComponent)
        del mock_component.name  # Remove name attribute

        # Mock the clean_json_schema function
        with patch("src.mcp_server.tool_transformer.clean_json_schema") as mock_clean:
            # Call the method
            tool_transformer.discover_and_customize(mock_route, mock_component)

            # Verify clean_json_schema was called
            mock_clean.assert_called_once_with(mock_component, tool_transformer.logger)

            # Verify op_id_map was not updated
            assert len(tool_transformer.op_id_map) == 0

    @pytest.mark.asyncio
    async def test_transform_tools(self, tool_transformer):
        """Test the transform_tools method."""
        # Setup mock data
        original_name = "original_tool"
        new_name = "new_tool"

        tool_transformer.custom_tool_names = {original_name: new_name}
        tool_transformer.op_id_map = {original_name: "mangled_tool_name"}

        # Create mock route
        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.operation_id = original_name
        mock_route.parameters = []
        mock_route.description = "Test tool description"
        tool_transformer.http_routes = [mock_route]

        # Create mock original tool
        mock_original_tool = MagicMock(spec=Tool)
        mock_original_tool.name = original_name

        # Create mock transformed tool
        mock_transformed_tool = MagicMock(spec=Tool)
        mock_transformed_tool.name = new_name
        mock_transformed_tool.description = "Test tool description"

        # Mock the _find_route_and_tool_name method
        with patch.object(
            tool_transformer,
            "_find_route_and_tool_name",
            return_value=(mock_route, "mangled_tool_name"),
        ):
            # Mock the mcp_server.get_tool method directly
            tool_transformer.mcp_server.get_tool = AsyncMock(
                return_value=mock_original_tool
            )
            # Mock the mcp_server.remove_tool method
            tool_transformer.mcp_server.remove_tool = AsyncMock()
            # Mock the add_tool method
            tool_transformer.mcp_server.add_tool = MagicMock()

            # Mock Tool.from_tool method
            with patch(
                "src.mcp_server.tool_transformer.Tool.from_tool",
                return_value=mock_transformed_tool,
            ):
                # Mock the _log_transformation_stats method to avoid logging
                with patch.object(tool_transformer, "_log_transformation_stats"):
                    # Call the method
                    await tool_transformer.transform_tools()

                    # Verify get_tool was called
                    tool_transformer.mcp_server.get_tool.assert_awaited_once_with(
                        "mangled_tool_name"
                    )

                    # Verify remove_tool was called
                    tool_transformer.mcp_server.remove_tool.assert_awaited_once_with(
                        "mangled_tool_name"
                    )

                    # Verify add_tool was called with a transformed tool
                    tool_transformer.mcp_server.add_tool.assert_called_once()

                    # Get the transformed tool that was added
                    added_tool = tool_transformer.mcp_server.add_tool.call_args[0][0]
                    assert added_tool.name == new_name
                    assert added_tool.description == "Test tool description"

    @pytest.mark.asyncio
    async def test_transform_tools_missing_route(self, tool_transformer):
        """Test transform_tools when route is not found."""
        # Setup mock data
        original_name = "original_tool"
        new_name = "new_tool"

        tool_transformer.custom_tool_names = {original_name: new_name}

        # Mock the _find_route_and_tool_name method to return None
        with patch.object(
            tool_transformer, "_find_route_and_tool_name", return_value=(None, None)
        ):
            # Mock the _log_transformation_stats method to avoid logging
            with patch.object(tool_transformer, "_log_transformation_stats"):
                # Call the method
                await tool_transformer.transform_tools()

                # Verify that no tools were added or removed
                tool_transformer.mcp_server.add_tool.assert_not_called()
                tool_transformer.mcp_server.remove_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_transform_tools_missing_original_tool(self, tool_transformer):
        """Test transform_tools when original tool is not found."""
        # Setup mock data
        original_name = "original_tool"
        new_name = "new_tool"

        tool_transformer.custom_tool_names = {original_name: new_name}
        tool_transformer.op_id_map = {original_name: "mangled_tool_name"}

        # Create mock route
        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.operation_id = original_name
        tool_transformer.http_routes = [mock_route]

        # Mock the _find_route_and_tool_name method
        with patch.object(
            tool_transformer,
            "_find_route_and_tool_name",
            return_value=(mock_route, "mangled_tool_name"),
        ):
            # Mock the _get_original_tool method to return None
            with patch.object(
                tool_transformer, "_get_original_tool", return_value=None
            ):
                # Mock the _log_transformation_stats method to avoid logging
                with patch.object(tool_transformer, "_log_transformation_stats"):
                    # Call the method
                    await tool_transformer.transform_tools()

                    # Verify that no tools were added or removed
                    tool_transformer.mcp_server.add_tool.assert_not_called()
                    tool_transformer.mcp_server.remove_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_route_and_tool_name(self, tool_transformer):
        """Test the _find_route_and_tool_name method."""
        # Setup mock data
        operation_id = "test_operation"
        mangled_name = "mangled_tool_name"

        tool_transformer.op_id_map = {operation_id: mangled_name}

        # Create mock route
        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.operation_id = operation_id
        tool_transformer.http_routes = [mock_route]

        # Mock the find_route_by_id function
        with patch(
            "src.mcp_server.tool_transformer.find_route_by_id", return_value=mock_route
        ):
            # Call the method
            route, name = await tool_transformer._find_route_and_tool_name(operation_id)

            # Verify results
            assert route == mock_route
            assert name == mangled_name

    @pytest.mark.asyncio
    async def test_find_route_and_tool_name_missing_route(self, tool_transformer):
        """Test _find_route_and_tool_name when route is not found."""
        # Setup mock data
        operation_id = "test_operation"

        # Mock the find_route_by_id function to return None
        with patch(
            "src.mcp_server.tool_transformer.find_route_by_id", return_value=None
        ):
            # Call the method
            route, name = await tool_transformer._find_route_and_tool_name(operation_id)

            # Verify results
            assert route is None
            assert name is None

    @pytest.mark.asyncio
    async def test_get_original_tool(self, tool_transformer):
        """Test the _get_original_tool method."""
        # Create mock tool
        mock_tool = MagicMock(spec=Tool)

        # Mock the mcp_server.get_tool method
        tool_transformer.mcp_server.get_tool = AsyncMock(return_value=mock_tool)

        # Call the method
        tool = await tool_transformer._get_original_tool("test_tool")

        # Verify results
        assert tool == mock_tool
        tool_transformer.mcp_server.get_tool.assert_called_once_with("test_tool")

    @pytest.mark.asyncio
    async def test_get_original_tool_not_found(self, tool_transformer):
        """Test _get_original_tool when tool is not found."""
        # Mock the mcp_server.get_tool method to return None
        tool_transformer.mcp_server.get_tool = AsyncMock(return_value=None)

        # Call the method
        tool = await tool_transformer._get_original_tool("test_tool")

        # Verify results
        assert tool is None

    def test_enrich_arguments(self, tool_transformer):
        """Test the _enrich_arguments method."""
        # Create mock route with parameters
        mock_param1 = MagicMock()
        mock_param1.name = "param1"
        mock_param1.description = "Description for param1"

        mock_param2 = MagicMock()
        mock_param2.name = "param2"
        mock_param2.description = "  Description for param2 with spaces  "

        mock_param3 = MagicMock()
        mock_param3.name = "param3"
        mock_param3.description = ""  # Empty description

        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.parameters = [mock_param1, mock_param2, mock_param3]

        # Call the method
        arg_transforms, param_count = tool_transformer._enrich_arguments(mock_route)

        # Verify results
        assert param_count == 2  # Only param1 and param2 have descriptions
        assert "param1" in arg_transforms
        assert "param2" in arg_transforms
        assert "param3" not in arg_transforms
        assert arg_transforms["param1"].description == "Description for param1"
        assert (
            arg_transforms["param2"].description == "Description for param2 with spaces"
        )

    def test_create_tool_description_from_description(self, tool_transformer):
        """Test _create_tool_description when route has description."""
        # Create mock route with description
        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.description = "Test tool description"
        mock_route.summary = "Test tool summary"

        # Call the method
        description = tool_transformer._create_tool_description(mock_route, "test_tool")

        # Verify results
        assert description == "Test tool description"

    def test_create_tool_description_from_summary(self, tool_transformer):
        """Test _create_tool_description when route has summary but no description."""
        # Create mock route with summary but no description
        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.description = ""
        mock_route.summary = "Test tool summary"

        # Call the method
        description = tool_transformer._create_tool_description(mock_route, "test_tool")

        # Verify results
        assert description == "Test tool summary"

    def test_create_tool_description_default(self, tool_transformer):
        """Test _create_tool_description when route has no description or summary."""
        # Create mock route with no description or summary
        mock_route = MagicMock(spec=HTTPRoute)
        mock_route.description = ""
        mock_route.summary = ""

        # Call the method
        description = tool_transformer._create_tool_description(mock_route, "test_tool")

        # Verify results
        assert description == "Execute the test_tool operation"

    def test_create_tool_tags(self, tool_transformer):
        """Test the _create_tool_tags method."""
        # Test with a listing tool
        tags = tool_transformer._create_tool_tags("list_all_structures")
        assert "api" in tags
        assert "listing" in tags
        assert "core-data" in tags

        # Test with a details tool
        tags = tool_transformer._create_tool_tags("get_structure_details")
        assert "api" in tags
        assert "details" in tags

        # Test with a documentation tool
        tags = tool_transformer._create_tool_tags("doc_get_structure")
        assert "api" in tags
        assert "documentation" in tags

        # Test with a generic tool
        tags = tool_transformer._create_tool_tags("update_structure")
        assert "api" in tags
        assert "listing" not in tags
        assert "details" not in tags
        assert "documentation" not in tags
        assert "core-data" not in tags


if __name__ == "__main__":
    pytest.main([__file__])
