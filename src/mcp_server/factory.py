"""
Factory class for constructing and configuring the MCP server.
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import importlib
import inspect
import functools

from fastmcp import FastMCP
from fastmcp.tools import Tool
from starlette.requests import Request
from starlette.responses import PlainTextResponse
import httpx  # Add this import for httpx.AsyncClient

# Imports pour le service legifrance
from pylegifrance import LegifranceClient
from pylegifrance.fonds.loda import Loda
from pylegifrance.fonds.juri import JuriAPI
from pylegifrance.fonds.code import Code

# Import pour l'authentification Bearer
from .auth import create_auth_handler  # Import the new auth handler

from ..core.config import MCPServiceConfig
from .openapi_loader import OpenAPILoader
from .tool_transformer import ToolTransformer, ToolTransformerConfig


@dataclass
class FactoryState:
    """Container for factory state to reduce instance attributes."""

    api_client: Optional[httpx.AsyncClient] = None
    openapi_spec: Optional[Dict[str, Any]] = None
    http_routes: Optional[list] = None
    base_url: Optional[str] = None


class MCPServiceFactory:
    """
    Factory class for constructing and configuring the MCP server.

    This class orchestrates the construction of the MCP server using
    either:
    1. OpenAPI specifications with specialized components (OpenAPILoader, ToolTransformer, etc.)
    2. Programmatic Python tools by dynamically importing modules and converting
       async functions to MCP tools.
    """

    def __init__(self, config: MCPServiceConfig, logger: logging.Logger):
        """
        Initializes the factory with the service configuration and logger.

        Args:
            config: The MCP service configuration.
            logger: Logger instance for logging messages.
        """
        self.config = config
        self.logger = logger
        self.state = FactoryState()
        self.op_id_to_mangled_name = {}
        self.tool_mappings = {}

    async def _load_openapi_spec(self) -> None:
        """
        Loads and parses the OpenAPI specification.

        This method uses OpenAPILoader to load the OpenAPI specification
        and extract HTTP routes.

        Raises:
            Exception: If loading the specification fails.
        """
        self.logger.info("Loading OpenAPI specification...")
        openapi_loader = OpenAPILoader(self.logger)
        self.state.openapi_spec, self.state.http_routes = await openapi_loader.load(
            self.config.openapi_path_or_url  # Use openapi_path_or_url
        )

    def _determine_base_url(self) -> None:
        """
        Determines the base URL from the OpenAPI specification.

        This method analyzes the 'servers' section of the OpenAPI specification
        to determine the server's base URL.
        """
        if not self.state.openapi_spec:
            raise ValueError("OpenAPI specification not loaded")

        servers = self.state.openapi_spec.get("servers", [])
        if (
            servers
            and isinstance(servers, list)
            and len(servers) > 0
            and "url" in servers[0]
        ):
            self.state.base_url = servers[0]["url"]
            self.logger.info(f"Using base URL from OpenAPI spec: {self.state.base_url}")
        else:
            self.state.base_url = (
                "http://localhost:8000"  # Default if not found in spec
            )
            self.logger.warning("No servers section found in OpenAPI spec.")
            self.logger.warning(f"Using default base URL: {self.state.base_url}")

    def _create_api_client(self) -> None:
        """
        Creates the authenticated HTTP API client.

        This method creates an HTTP client configured with the base URL
        and appropriate authentication parameters.
        """
        if not self.state.base_url:
            raise ValueError("Base URL not determined")

        self.logger.info("Creating HTTP client...")
        auth_handler = None  # Default to no auth handler

        # Only create auth handler if auth config is provided
        if self.config.auth:
            self.logger.info("Creating authentication handler...")
            auth_handler = create_auth_handler(self.config.auth, self.logger)

        headers = {
            "User-Agent": "FranceGPT-MCP-Server/1.0",
            "Accept": "application/json",
        }

        self.state.api_client = httpx.AsyncClient(
            base_url=self.state.base_url,
            headers=headers,
            timeout=30.0,
            auth=auth_handler,  # Pass the auth handler (can be None)
        )
        if auth_handler:
            self.logger.info("HTTP client created successfully with authentication.")
        else:
            self.logger.info("HTTP client created successfully without authentication.")

    def _load_tool_mappings(self) -> Dict[str, Any]:
        """
        Loads custom tool mappings from a specified JSON file.

        Returns:
            Dict[str, Any]: A dictionary of custom tool mappings.
        """
        if not self.config.tool_mappings_file:
            self.logger.info(
                "No custom tool mappings file specified. Using empty mappings."
            )
            return {}

        try:
            with open(self.config.tool_mappings_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
            self.logger.info(
                f"Loaded custom tool mappings from {self.config.tool_mappings_file}"
            )
            return mappings
        except FileNotFoundError:
            self.logger.warning(
                f"Custom tool mappings file not found: {self.config.tool_mappings_file}. "
                "Using empty mappings."
            )
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(
                f"Error decoding JSON from tool mappings file {self.config.tool_mappings_file}: {e}. "
                "Using empty mappings."
            )
            return {}

    async def _create_mcp_server_with_transformer(self) -> FastMCP:
        """
        Creates and configures the MCP server with ToolTransformer for OpenAPI services.

        This method creates the FastMCP instance with the OpenAPI specification,
        the HTTP client, and ToolTransformer for enhanced tool names and descriptions.

        Returns:
            FastMCP: Configured instance of the MCP server.

        Raises:
            Exception: If server creation fails.
        """
        if not self.state.openapi_spec:
            raise ValueError("OpenAPI specification not loaded")
        if not self.state.http_routes:
            raise ValueError("HTTP routes not loaded")
        if not self.state.api_client:
            raise ValueError("API client not created")

        self.logger.info(f"Creating FastMCP server '{self.config.name}'...")

        # Configuration des routes MCP
        route_maps = []

        # Création du transformer pour le callback de personnalisation
        tool_transformer_config = ToolTransformerConfig(
            mcp_server=None,  # type: ignore # Sera défini après création du serveur
            http_routes=self.state.http_routes,
            custom_tool_names=self.tool_mappings,  # Use loaded mappings
            op_id_map=self.op_id_to_mangled_name,
            logger=self.logger,
        )
        tool_transformer = ToolTransformer(config=tool_transformer_config)

        # Création du serveur MCP avec le callback de personnalisation
        mcp_server = FastMCP.from_openapi(
            openapi_spec=self.state.openapi_spec,
            client=self.state.api_client,
            name=self.config.name,
            route_maps=route_maps,  # Pass the dynamically created route_maps
            auth=None,
            mcp_component_fn=tool_transformer.discover_and_customize,
        )

        # Ajout de l'endpoint de santé
        @mcp_server.custom_route("/health", methods=["GET"])
        async def health_check(_request: Request) -> PlainTextResponse:
            """A simple health check endpoint."""
            return PlainTextResponse("OK", status_code=200)

        self.logger.info(f"FastMCP server '{mcp_server.name}' created successfully!")
        self.logger.info("   - Custom GET-to-Tool mapping applied")
        self.logger.info("   - Health check endpoint (/health) added successfully")

        # Maintenant que le serveur est créé, mettons à jour la config du transformer
        tool_transformer_config.mcp_server = mcp_server  # type: ignore
        tool_transformer.mcp_server = mcp_server  # type: ignore

        # Appliquer les transformations d'outils
        await tool_transformer.transform_tools()

        return mcp_server

    async def build(self) -> FastMCP:
        """
        Orchestrates the complete construction of the MCP server.

        This method uses specialized components to build the MCP server
        in a modular and organized manner.

        Returns:
            FastMCP: Fully configured instance of the MCP server.

        Raises:
            Exception: If any build step fails.
            ValueError: If neither openapi_path_or_url nor programmatic_tools_module is defined.
        """
        # Check which type of server to build
        if self.config.openapi_path_or_url:
            # Build from OpenAPI specification with ToolTransformer
            try:
                # 1. Load custom tool mappings
                self.tool_mappings = self._load_tool_mappings()

                # 2. Load and parse the OpenAPI specification
                await self._load_openapi_spec()

                # 3. Determine the base URL
                self._determine_base_url()

                # 4. Create the authenticated API client
                self._create_api_client()

                # 5. Create the MCP server with ToolTransformer integration
                mcp_server = await self._create_mcp_server_with_transformer()

                return mcp_server

            except Exception as e:
                self.logger.error(f"Failed to build MCP server: {e}")
                if self.state.api_client:
                    await self.state.api_client.aclose()
                raise
        elif self.config.programmatic_tools_module:
            # Build from programmatic tools (no ToolTransformer needed)
            return await self._build_from_programmatic_tools()
        else:
            # Neither openapi_path_or_url nor programmatic_tools_module is defined
            raise ValueError(
                "Either openapi_path_or_url or programmatic_tools_module must be defined "
                "in the service configuration"
            )

    async def _build_from_programmatic_tools(self) -> FastMCP:
        """
        Builds an MCP server from programmatic Python tools.

        This method creates an MCP server by importing a module containing
        async functions and converting them to MCP tools.

        Returns:
            FastMCP: Configured instance of the MCP server.

        Raises:
            Exception: If any step in the build process fails.
        """
        self.logger.info(
            f"Creating FastMCP server '{self.config.name}' from programmatic tools..."
        )

        # Create a base FastMCP instance
        mcp_server = FastMCP(name=self.config.name)

        # Import the module dynamically
        self.logger.info(f"Importing module: {self.config.programmatic_tools_module}")
        try:
            tool_module = importlib.import_module(self.config.programmatic_tools_module)
        except ImportError as e:
            self.logger.error(
                f"Failed to import module '{self.config.programmatic_tools_module}': {e}"
            )
            raise

        # Determine which tools to import
        tool_names = []
        if hasattr(tool_module, "__all__"):
            # Use __all__ if defined
            tool_names = tool_module.__all__
            self.logger.info(
                f"Found __all__ with {len(tool_names)} tools: {tool_names}"
            )
        else:
            # Otherwise, inspect all members of the module
            self.logger.info("No __all__ found, inspecting all module members...")
            for name, member in inspect.getmembers(tool_module):
                # Check if it's an async function and not private (doesn't start with _)
                if (
                    inspect.iscoroutinefunction(member)
                    and not name.startswith("_")
                    and not name.startswith("async")
                ):
                    tool_names.append(name)

            self.logger.info(f"Found {len(tool_names)} async functions: {tool_names}")

        # Instanciation des clients et services nécessaires
        dependencies = {}

        # Si self.config.auth est de type BearerAuthConfig, créez un httpx.AsyncClient
        if (
            self.config.auth
            and hasattr(self.config.auth, "method")
            and self.config.auth.method == "bearer"
        ):
            import os

            api_key = os.getenv(self.config.auth.api_key_env_var)
            if api_key:
                dependencies["client"] = httpx.AsyncClient(
                    base_url=self.config.base_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                self.logger.info("Created HTTP client with Bearer authentication")

        # Si le service est legifrance, instanciez les services pylegifrance
        if self.config.name == "legifrance":
            try:
                legifrance_client = LegifranceClient()
                dependencies["loda_service"] = Loda(legifrance_client)
                dependencies["juri_api"] = JuriAPI(legifrance_client)
                dependencies["code_service"] = Code(legifrance_client)
                self.logger.info("Created Legifrance services")
            except Exception as e:
                self.logger.error(f"Failed to create Legifrance services: {e}")
                raise

        # Add each tool to the MCP server
        added_tools = 0
        for tool_name in tool_names:
            tool_func = getattr(tool_module, tool_name)

            # Verify it's an async function
            if not inspect.iscoroutinefunction(tool_func):
                self.logger.warning(
                    f"Skipping '{tool_name}' as it's not an async function"
                )
                continue

            # Add the tool to the server with dependency injection using functools.partial
            try:
                # Inspect the function signature to determine which dependencies to inject
                sig = inspect.signature(tool_func)
                dependencies_to_inject = {}

                for param_name, param in sig.parameters.items():
                    if param_name in dependencies:
                        dependencies_to_inject[param_name] = dependencies[param_name]

                # Create a wrapper function with proper signature for Pydantic
                if dependencies_to_inject:
                    wrapped_func = self._create_tool_wrapper(
                        tool_func, dependencies_to_inject
                    )
                    mcp_server.add_tool(Tool.from_function(fn=wrapped_func))
                    self.logger.info(
                        f"Added tool with dependency injection: {tool_name}"
                    )
                else:
                    # No dependencies to inject, add the function directly
                    mcp_server.add_tool(Tool.from_function(fn=tool_func))
                    self.logger.info(f"Added tool: {tool_name}")

                added_tools += 1
            except Exception as e:
                self.logger.error(f"Failed to add tool '{tool_name}': {e}")
                raise

        self.logger.info(f"Successfully added {added_tools} tools to the server")

        # Add health check endpoint
        @mcp_server.custom_route("/health", methods=["GET"])
        async def health_check(_request: Request) -> PlainTextResponse:
            """A simple health check endpoint."""
            return PlainTextResponse("OK", status_code=200)

        self.logger.info(
            f"FastMCP server '{mcp_server.name}' created successfully from programmatic tools!"
        )
        self.logger.info(f"   - {added_tools} programmatic tools added")
        self.logger.info("   - Health check endpoint (/health) added successfully")

        return mcp_server

    def _create_tool_wrapper(self, tool_func, dependencies_to_inject):
        """
        Creates a wrapper function with a proper signature for Pydantic schema generation.

        Args:
            tool_func: The original tool function
            dependencies_to_inject: Dictionary of dependencies to inject

        Returns:
            A wrapped function with proper signature
        """
        # Inspect the function signature
        sig = inspect.signature(tool_func)

        # Create new parameters excluding injected dependencies
        new_params = [
            param
            for name, param in sig.parameters.items()
            if name not in dependencies_to_inject
        ]

        # Create new signature without injected dependencies
        new_sig = sig.replace(parameters=new_params)

        # Define the async wrapper function
        async def wrapper(*args, **kwargs):
            # Bind the provided arguments to the new signature
            bound_args = new_sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Merge with injected dependencies
            all_args = {**bound_args.arguments, **dependencies_to_inject}

            # Call the original function with all arguments
            return await tool_func(**all_args)

        # Set the new signature and copy metadata
        wrapper.__signature__ = new_sig
        functools.update_wrapper(wrapper, tool_func)

        return wrapper

    async def cleanup(self) -> None:
        """
        Cleans up resources used by the factory.
        """
        if self.state.api_client and not self.state.api_client.is_closed:
            self.logger.info("Closing HTTP client...")
            await self.state.api_client.aclose()
            self.logger.info("HTTP client closed successfully")
