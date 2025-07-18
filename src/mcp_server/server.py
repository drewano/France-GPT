"""
DataInclusion MCP Server

Ce serveur MCP expose l'API data.inclusion.beta.gouv.fr via le protocole Model Context Protocol.
Il transforme automatiquement les endpoints OpenAPI en outils MCP.
"""

import asyncio
import logging
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType
from fastmcp.server.auth import BearerAuthProvider
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from ..core.config import settings
from ..core.logging import setup_logging
from .utils import inspect_mcp_components, create_api_client
from .openapi_loader import OpenAPILoader
from .tool_transformer import ToolTransformer
from .tool_mapping import CUSTOM_MCP_TOOL_NAMES
from .auth import setup_authentication


class MCPBuilder:
    """
    Builder class pour construire et configurer le serveur MCP.

    Cette classe orchestre la construction du serveur MCP en utilisant
    les composants spécialisés (OpenAPILoader, ToolTransformer, etc.).
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialise le builder avec le logger.

        Args:
            logger: Instance du logger pour enregistrer les messages
        """
        self.logger = logger
        self.api_client = None
        self.openapi_spec = None
        self.http_routes = None
        self.base_url = None
        self.op_id_to_mangled_name = {}

    def _configure_auth(self) -> BearerAuthProvider | None:
        """
        Configure l'authentification Bearer pour le serveur MCP.

        Cette méthode délègue la configuration d'authentification au module dédié.

        Returns:
            BearerAuthProvider | None: Le provider d'authentification ou None
        """
        return setup_authentication(self.logger)

    async def _load_openapi_spec(self) -> None:
        """
        Charge et parse la spécification OpenAPI.

        Cette méthode utilise OpenAPILoader pour charger la spécification
        OpenAPI et extraire les routes HTTP.

        Raises:
            Exception: Si le chargement de la spécification échoue
        """
        self.logger.info("Loading OpenAPI specification...")
        openapi_loader = OpenAPILoader(self.logger)
        self.openapi_spec, self.http_routes = await openapi_loader.load()

    def _determine_base_url(self) -> None:
        """
        Détermine l'URL de base à partir de la spécification OpenAPI.

        Cette méthode analyse la section 'servers' de la spécification
        OpenAPI pour déterminer l'URL de base du serveur.
        """
        if not self.openapi_spec:
            raise ValueError("OpenAPI specification not loaded")

        servers = self.openapi_spec.get("servers", [])
        if (
            servers
            and isinstance(servers, list)
            and len(servers) > 0
            and "url" in servers[0]
        ):
            self.base_url = servers[0]["url"]
            self.logger.info(f"Using base URL from OpenAPI spec: {self.base_url}")
        else:
            self.base_url = "http://localhost:8000"
            self.logger.warning("No servers section found in OpenAPI spec.")
            self.logger.warning(f"Using default base URL: {self.base_url}")

    def _create_api_client(self) -> None:
        """
        Crée le client API HTTP authentifié.

        Cette méthode crée un client HTTP configuré avec l'URL de base
        et les paramètres d'authentification appropriés.
        """
        if not self.base_url:
            raise ValueError("Base URL not determined")

        self.logger.info("Creating HTTP client...")
        self.api_client = create_api_client(
            self.base_url, self.logger, settings.mcp.DATA_INCLUSION_API_KEY
        )

    def _create_mcp_server(self, auth_provider: BearerAuthProvider | None) -> FastMCP:
        """
        Crée et configure le serveur MCP.

        Cette méthode crée l'instance FastMCP avec la spécification OpenAPI,
        le client HTTP, et la configuration d'authentification.

        Args:
            auth_provider: Provider d'authentification ou None

        Returns:
            FastMCP: Instance configurée du serveur MCP

        Raises:
            Exception: Si la création du serveur échoue
        """
        if not self.openapi_spec:
            raise ValueError("OpenAPI specification not loaded")
        if not self.http_routes:
            raise ValueError("HTTP routes not loaded")
        if not self.api_client:
            raise ValueError("API client not created")

        self.logger.info(f"Creating FastMCP server '{settings.mcp.MCP_SERVER_NAME}'...")

        # Configuration des routes MCP
        custom_route_maps = [
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.TOOL),
        ]

        # Création du transformer temporaire pour le callback
        temp_transformer = ToolTransformer(
            mcp_server=None,  # type: ignore # Sera défini après création du serveur
            http_routes=self.http_routes,
            custom_tool_names=CUSTOM_MCP_TOOL_NAMES,
            op_id_map=self.op_id_to_mangled_name,
            logger=self.logger,
        )

        # Création du serveur MCP
        mcp_server = FastMCP.from_openapi(
            openapi_spec=self.openapi_spec,
            client=self.api_client,
            name=settings.mcp.MCP_SERVER_NAME,
            route_maps=custom_route_maps,
            auth=auth_provider,
            mcp_component_fn=lambda route,
            component: temp_transformer.discover_and_customize(route, component),
        )

        # Ajout de l'endpoint de santé
        @mcp_server.custom_route("/health", methods=["GET"])
        async def health_check(request: Request) -> PlainTextResponse:
            """A simple health check endpoint."""
            return PlainTextResponse("OK", status_code=200)

        self.logger.info(f"FastMCP server '{mcp_server.name}' created successfully!")
        self.logger.info("   - Custom GET-to-Tool mapping applied")
        self.logger.info("   - Health check endpoint (/health) added successfully")

        return mcp_server

    async def _transform_tools(self, mcp_server: FastMCP) -> None:
        """
        Transforme les outils MCP.

        Cette méthode utilise ToolTransformer pour appliquer des transformations
        personnalisées aux outils MCP générés.

        Args:
            mcp_server: Instance du serveur MCP

        Raises:
            Exception: Si la transformation des outils échoue
        """
        if not self.http_routes:
            raise ValueError("HTTP routes not loaded")

        self.logger.info("Transforming tools...")
        tool_transformer = ToolTransformer(
            mcp_server=mcp_server,
            http_routes=self.http_routes,
            custom_tool_names=CUSTOM_MCP_TOOL_NAMES,
            op_id_map=self.op_id_to_mangled_name,
            logger=self.logger,
        )
        await tool_transformer.transform_tools()

    async def _inspect_components(self, mcp_server: FastMCP) -> None:
        """
        Inspecte les composants MCP pour le débogage.

        Cette méthode analyse et affiche des informations sur les composants
        MCP générés à des fins de débogage et de diagnostic.

        Args:
            mcp_server: Instance du serveur MCP
        """
        await inspect_mcp_components(mcp_server, self.logger)

    async def build(self) -> FastMCP:
        """
        Orchestre la construction complète du serveur MCP.

        Cette méthode utilise les composants spécialisés pour construire
        le serveur MCP de manière modulaire et organisée.

        Returns:
            FastMCP: Instance complètement configurée du serveur MCP

        Raises:
            Exception: Si une étape de construction échoue
        """
        try:
            # 1. Chargement et parsing de la spécification OpenAPI
            await self._load_openapi_spec()

            # 2. Détermination de l'URL de base
            self._determine_base_url()

            # 3. Création du client API authentifié
            self._create_api_client()

            # 4. Configuration de l'authentification
            auth_provider = self._configure_auth()

            # 5. Création du serveur MCP
            mcp_server = self._create_mcp_server(auth_provider)

            # 6. Transformation des outils
            await self._transform_tools(mcp_server)

            # 7. Inspection des composants (pour debug)
            await self._inspect_components(mcp_server)

            return mcp_server

        except Exception as e:
            self.logger.error(f"Failed to build MCP server: {e}")
            if self.api_client:
                await self.api_client.aclose()
            raise

    async def cleanup(self) -> None:
        """
        Nettoie les ressources utilisées par le builder.
        """
        if self.api_client:
            self.logger.info("Closing HTTP client...")
            await self.api_client.aclose()
            self.logger.info("HTTP client closed successfully")


async def main():
    """
    Fonction principale qui configure et lance le serveur MCP.

    Cette fonction utilise MCPBuilder pour construire et configurer le serveur MCP
    de manière modulaire et organisée.
    """

    # === 1. CONFIGURATION DU LOGGING ===
    logger = setup_logging(name="datainclusion.mcp")

    builder = None

    try:
        # === 2. CRÉATION ET CONSTRUCTION DU SERVEUR MCP ===
        logger.info("Initializing MCP server builder...")
        builder = MCPBuilder(logger)

        logger.info("Building MCP server...")
        mcp_server = await builder.build()

        # === 3. LANCEMENT DU SERVEUR ===
        server_url = (
            f"http://{settings.mcp.MCP_HOST}:{settings.mcp.MCP_PORT}"
            f"{settings.mcp.MCP_API_PATH}"
        )
        logger.info(f"Starting MCP server on {server_url}")
        logger.info("Press Ctrl+C to stop the server")

        await mcp_server.run_async(
            transport="http",
            host=settings.mcp.MCP_HOST,
            port=settings.mcp.MCP_PORT,
            path=settings.mcp.MCP_API_PATH,
        )

    except KeyboardInterrupt:
        logger.info("Server stopped by user")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error("Please check your configuration and try again.")

    finally:
        # === 4. NETTOYAGE DES RESSOURCES ===
        if builder:
            await builder.cleanup()


if __name__ == "__main__":
    """
    Point d'entrée du script.
    Lance le serveur MCP avec gestion d'erreurs appropriée.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(1)
