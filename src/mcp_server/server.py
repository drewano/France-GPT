"""
DataInclusion MCP Server

Ce serveur MCP expose l'API data.inclusion.beta.gouv.fr via le protocole Model Context Protocol.
Il transforme automatiquement les endpoints OpenAPI en outils MCP.
"""

import asyncio
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from ..core.config import settings
from ..core.logging import setup_logging
from .factory import MCPFactory


async def main():
    """
    Fonction principale qui configure et lance la passerelle MCP.

    Cette fonction crée une passerelle FastMCP et monte dynamiquement
    plusieurs serveurs MCP configurés via `settings.mcp_services`.
    """

    # === 1. CONFIGURATION DU LOGGING ===
    logger = setup_logging(name="datainclusion.mcp-gateway")
    logger.info("Starting MCP Gateway server setup...")

    gateway_server = None  # Initialize gateway_server to None for finally block

    try:
        # === 2. CHARGEMENT DES CONFIGURATIONS DE SERVICE ===
        service_configs = settings.mcp_services
        if not service_configs:
            logger.warning("No MCP services configured in settings. Skipping server creation.")
            return

        # === 3. CRÉATION DE L'INSTANCE PRINCIPALE DE LA PASSERELLE MCP ===
        logger.info("Creating MCP Gateway: %s", settings.mcp_gateway.MCP_SERVER_NAME)
        gateway_server = FastMCP(name=settings.mcp_gateway.MCP_SERVER_NAME)

        # === 4. CRÉATION ET MONTAGE DES SERVEURS MCP POUR CHAQUE SERVICE ===
        for service_config in service_configs:
            logger.info("Building and mounting MCP server for service: %s", service_config.name)
            factory = MCPFactory(config=service_config, logger=logger)
            service_mcp_instance = await factory.build()

            # Monte le serveur du service sur la passerelle sans préfixe
            gateway_server.mount(service_mcp_instance)
            logger.info(
                "Mounted service '%s' at the gateway root (no prefix).",
                service_config.name
            )

        # === 5. AJOUT D'UN ENDPOINT DE SANTÉ GLOBAL ===
        @gateway_server.custom_route("/health", methods=["GET"])
        async def health_check(_request: Request) -> PlainTextResponse:
            """A simple health check endpoint for the gateway."""
            return PlainTextResponse("OK", status_code=200)
        logger.info("Global health check endpoint (/health) added to gateway.")


        # === 6. LANCEMENT DE LA PASSERELLE MCP ===
        server_url = (
            f"http://{settings.mcp_gateway.MCP_HOST}:{settings.mcp_gateway.MCP_PORT}"
            f"{settings.mcp_gateway.MCP_API_PATH}"
        )
        logger.info("Starting MCP Gateway on %s", server_url)
        logger.info("Press Ctrl+C to stop the server")

        await gateway_server.run_async(
            transport="http",
            host=settings.mcp_gateway.MCP_HOST,
            port=settings.mcp_gateway.MCP_PORT,
            path=settings.mcp_gateway.MCP_API_PATH,
        )

    except KeyboardInterrupt:
        logger.info("Server stopped by user")

    except Exception as e:
        logger.error("Unexpected error during MCP Gateway startup: %s", e, exc_info=True)
        logger.error("Please check your configuration and try again.")

    finally:
        # === 7. NETTOYAGE DES RESSOURCES ===
        if gateway_server:
            logger.info("MCP Gateway cleanup completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Failed to start MCP Gateway: {e}")
        exit(1)
