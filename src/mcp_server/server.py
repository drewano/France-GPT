"""
DataInclusion MCP Server

Ce serveur MCP expose l'API data.inclusion.beta.gouv.fr via le protocole Model Context Protocol.
Il transforme automatiquement les endpoints OpenAPI en outils MCP.
"""

import asyncio
import json
import logging
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.bearer import RSAKeyPair
from fastmcp.utilities.openapi import parse_openapi_to_http_routes
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from ..core.config import MCPSettings
from .utils import inspect_mcp_components, create_api_client
from ..core.logging import setup_logging
from .tool_transformer import (
    limit_page_size_in_spec,
    discover_and_customize,
    transform_and_register_tools,
)
from .tool_mapping import CUSTOM_MCP_TOOL_NAMES


class MCPFactory:
    """
    Factory class pour construire et configurer le serveur MCP.

    Cette classe encapsule toute la logique de construction du serveur MCP,
    en séparant chaque étape dans des méthodes privées dédiées.
    """

    def __init__(self, settings: MCPSettings, logger: logging.Logger):
        """
        Initialise la factory avec les paramètres de configuration et le logger.

        Args:
            settings: Instance de MCPSettings contenant la configuration
            logger: Instance du logger pour enregistrer les messages
        """
        self.settings = settings
        self.logger = logger
        self.api_client = None
        self.openapi_spec = None
        self.http_routes = None
        self.auth_provider = None
        self.op_id_to_mangled_name = {}

    async def _load_openapi_spec(self) -> None:
        """
        Charge et pré-parse la spécification OpenAPI.

        Cette méthode :
        1. Charge la spécification OpenAPI depuis l'URL configurée
        2. Parse la spécification en routes HTTP
        3. Applique les limites de pagination

        Raises:
            httpx.RequestError: Si la récupération de la spécification échoue
            json.JSONDecodeError: Si la réponse n'est pas un JSON valide
        """
        self.logger.info(
            f"Loading OpenAPI specification from URL: '{self.settings.OPENAPI_URL}'..."
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.settings.OPENAPI_URL)
                response.raise_for_status()  # Lève une exception si le statut n'est pas 2xx
                self.openapi_spec = response.json()

            api_title = self.openapi_spec.get("info", {}).get("title", "Unknown API")
            self.logger.info(f"Successfully loaded OpenAPI spec: '{api_title}'")

            # === PRÉ-PARSING DE LA SPÉCIFICATION OPENAPI ===
            self.logger.info("Parsing OpenAPI specification to HTTP routes...")
            self.http_routes = parse_openapi_to_http_routes(self.openapi_spec)
            self.logger.info(
                f"Successfully parsed {len(self.http_routes)} HTTP routes from OpenAPI specification"
            )

            # === MODIFICATION DES LIMITES DE PAGINATION ===
            # Limite la taille des pages pour les outils de listing à 25 éléments maximum
            # Cela s'applique aux outils: list_all_structures, list_all_services, search_services
            self.logger.info("Applying pagination limits to data-listing endpoints...")
            self.openapi_spec = limit_page_size_in_spec(
                self.openapi_spec, logger=self.logger, max_size=25
            )

        except httpx.RequestError as e:
            self.logger.error(
                f"Failed to fetch OpenAPI specification from '{self.settings.OPENAPI_URL}'."
            )
            self.logger.error(f"Details: {e}")
            raise

        except json.JSONDecodeError as e:
            self.logger.error(
                f"Invalid JSON in the response from '{self.settings.OPENAPI_URL}'."
            )
            self.logger.error(f"Details: {e}")
            raise

    async def _create_api_client(self) -> None:
        """
        Crée le client HTTP authentifié pour l'API Data Inclusion.

        Cette méthode :
        1. Détermine l'URL de base depuis la spécification OpenAPI
        2. Crée un client httpx avec authentification
        """
        # === DÉTERMINATION DE L'URL DE BASE ===
        if self.openapi_spec is None:
            raise ValueError("OpenAPI spec must be loaded before creating API client")

        servers = self.openapi_spec.get("servers", [])
        if (
            servers
            and isinstance(servers, list)
            and len(servers) > 0
            and "url" in servers[0]
        ):
            base_url = servers[0]["url"]
            self.logger.info(f"Using base URL from OpenAPI spec: {base_url}")
        else:
            base_url = "http://localhost:8000"
            self.logger.warning("No servers section found in OpenAPI spec.")
            self.logger.warning(f"Using default base URL: {base_url}")

        # === CRÉATION DU CLIENT HTTP AUTHENTIFIÉ ===
        self.logger.info("Configuring HTTP client with authentication...")
        self.api_client = create_api_client(
            base_url, self.logger, self.settings.DATA_INCLUSION_API_KEY
        )

    def _configure_auth(self) -> None:
        """
        Configure l'authentification Bearer pour le serveur MCP.

        Cette méthode :
        1. Lit la clé secrète depuis la configuration
        2. Configure BearerAuthProvider si une clé est fournie
        3. Génère un token de test pour le développement
        """
        self.logger.info("Configuring server authentication...")

        # Lecture de la clé secrète depuis la configuration
        secret_key = self.settings.MCP_SERVER_SECRET_KEY
        self.auth_provider = None

        if secret_key and secret_key.strip():
            self.logger.info(
                "Secret key found - configuring Bearer Token authentication..."
            )
            try:
                # Si la clé ressemble à une clé RSA privée PEM, l'utiliser directement
                if (
                    secret_key.strip().startswith("-----BEGIN")
                    and "PRIVATE KEY" in secret_key
                ):
                    # Utiliser la clé privée pour créer une paire de clés
                    from cryptography.hazmat.primitives import serialization

                    private_key = serialization.load_pem_private_key(
                        secret_key.encode(), password=None
                    )
                    public_key_pem = (
                        private_key.public_key()
                        .public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo,
                        )
                        .decode()
                    )

                    self.auth_provider = BearerAuthProvider(
                        public_key=public_key_pem, audience="datainclusion-mcp-client"
                    )
                else:
                    # Utiliser la clé comme seed pour générer une paire de clés déterministe
                    # Pour des raisons de simplicité, on génère une nouvelle paire de clés
                    key_pair = RSAKeyPair.generate()

                    self.auth_provider = BearerAuthProvider(
                        public_key=key_pair.public_key,
                        audience="datainclusion-mcp-client",
                    )

                    # Log du token de test (UNIQUEMENT pour le développement)
                    test_token = key_pair.create_token(
                        audience="datainclusion-mcp-client",
                        subject="test-user",
                        expires_in_seconds=3600,
                    )
                    self.logger.info(
                        f"🔑 Test Bearer Token (for development): {test_token}"
                    )

                self.logger.info(
                    "✓ Bearer Token authentication configured successfully"
                )
                self.logger.info("   - Audience: datainclusion-mcp-client")
                self.logger.info(
                    "   - Server will require valid Bearer tokens for access"
                )

            except Exception as e:
                self.logger.error(f"Failed to configure authentication: {e}")
                self.logger.warning("Continuing without authentication...")
                self.auth_provider = None
        else:
            self.logger.warning(
                "MCP_SERVER_SECRET_KEY not set - server will run WITHOUT authentication"
            )
            self.logger.warning(
                "⚠️  All clients will have unrestricted access to the server"
            )

    def _create_mcp_server(self) -> FastMCP:
        """
        Crée et configure l'instance FastMCP.

        Cette méthode :
        1. Configure les noms d'outils personnalisés
        2. Configure les routes MCP
        3. Crée l'instance FastMCP avec from_openapi
        4. Ajoute l'endpoint de santé

        Returns:
            FastMCP: Instance configurée du serveur MCP
        """
        # === CONFIGURATION DES NOMS D'OUTILS PERSONNALISÉS ===
        self.logger.info("Configuring custom tool names...")

        # Utilisation de la constante importée pour le mapping des outils
        self.custom_tool_names = CUSTOM_MCP_TOOL_NAMES

        # === CONFIGURATION DES ROUTES MCP ===
        self.logger.info("Configuring route mappings...")

        # Configuration pour mapper tous les endpoints GET comme des outils MCP
        custom_route_maps = [
            RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.TOOL),
        ]

        # === CRÉATION DU SERVEUR MCP ===
        self.logger.info(
            f"Creating FastMCP server '{self.settings.MCP_SERVER_NAME}'..."
        )

        if self.openapi_spec is None:
            raise ValueError("OpenAPI spec must be loaded before creating MCP server")
        if self.api_client is None:
            raise ValueError("API client must be created before creating MCP server")

        mcp_server = FastMCP.from_openapi(
            openapi_spec=self.openapi_spec,
            client=self.api_client,
            name=self.settings.MCP_SERVER_NAME,
            route_maps=custom_route_maps,
            auth=self.auth_provider,
            mcp_component_fn=lambda route, component: discover_and_customize(
                route, component, self.logger, self.op_id_to_mangled_name
            ),
        )

        self.logger.info(f"FastMCP server '{mcp_server.name}' created successfully!")
        self.logger.info("   - Custom GET-to-Tool mapping applied")

        # === AJOUT DE L'ENDPOINT DE SANTÉ ===
        @mcp_server.custom_route("/health", methods=["GET"])
        async def health_check(request: Request) -> PlainTextResponse:
            """A simple health check endpoint."""
            return PlainTextResponse("OK", status_code=200)

        self.logger.info("   - Health check endpoint (/health) added successfully")

        return mcp_server

    async def _enrich_tools(self, mcp_server: FastMCP) -> None:
        """
        Enrichit les outils MCP avec des noms et descriptions personnalisés.

        Args:
            mcp_server: Instance du serveur MCP à enrichir
        """
        if self.http_routes is None:
            raise ValueError("HTTP routes must be loaded before enriching tools")
        if not hasattr(self, "custom_tool_names"):
            raise ValueError(
                "Custom tool names must be configured before enriching tools"
            )

        # === RENOMMAGE ET ENRICHISSEMENT AVANCÉ DES OUTILS ===
        await transform_and_register_tools(
            mcp_server=mcp_server,
            http_routes=self.http_routes,
            custom_tool_names=self.custom_tool_names,
            op_id_map=self.op_id_to_mangled_name,
            logger=self.logger,
        )

    async def build(self) -> FastMCP:
        """
        Orchestre la construction complète du serveur MCP.

        Cette méthode appelle toutes les méthodes privées dans le bon ordre
        pour construire et configurer entièrement le serveur MCP.

        Returns:
            FastMCP: Instance complètement configurée du serveur MCP

        Raises:
            Exception: Si une étape de construction échoue
        """
        try:
            # 1. Chargement et parsing de la spécification OpenAPI
            await self._load_openapi_spec()

            # 2. Création du client API authentifié
            await self._create_api_client()

            # 3. Configuration de l'authentification
            self._configure_auth()

            # 4. Création du serveur MCP
            mcp_server = self._create_mcp_server()

            # 5. Enrichissement des outils
            await self._enrich_tools(mcp_server)

            # 6. Inspection des composants (pour debug)
            await inspect_mcp_components(mcp_server, self.logger)

            return mcp_server

        except Exception as e:
            self.logger.error(f"Failed to build MCP server: {e}")
            if self.api_client:
                await self.api_client.aclose()
            raise

    async def cleanup(self) -> None:
        """
        Nettoie les ressources utilisées par la factory.
        """
        if self.api_client:
            self.logger.info("Closing HTTP client...")
            await self.api_client.aclose()
            self.logger.info("HTTP client closed successfully")


async def main():
    """
    Fonction principale qui configure et lance le serveur MCP.

    Cette fonction utilise MCPFactory pour construire et configurer le serveur MCP
    de manière modulaire et organisée.
    """

    # === 1. CHARGEMENT DE LA CONFIGURATION ===
    settings = MCPSettings()

    # === 2. CONFIGURATION DU LOGGING ===
    logger = setup_logging()

    factory = None

    try:
        # === 3. CRÉATION ET CONSTRUCTION DU SERVEUR MCP ===
        logger.info("Initializing MCP server factory...")
        factory = MCPFactory(settings, logger)

        logger.info("Building MCP server...")
        mcp_server = await factory.build()

        # === 4. LANCEMENT DU SERVEUR ===
        server_url = (
            f"http://{settings.MCP_HOST}:{settings.MCP_PORT}{settings.MCP_API_PATH}"
        )
        logger.info(f"Starting MCP server on {server_url}")
        logger.info("Press Ctrl+C to stop the server")

        await mcp_server.run_async(
            transport="http",
            host=settings.MCP_HOST,
            port=settings.MCP_PORT,
            path=settings.MCP_API_PATH,
        )

    except KeyboardInterrupt:
        logger.info("Server stopped by user")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error("Please check your configuration and try again.")

    finally:
        # === 5. NETTOYAGE DES RESSOURCES ===
        if factory:
            await factory.cleanup()


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
