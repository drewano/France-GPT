"""
DataInclusion MCP Server

Ce serveur MCP expose l'API data.inclusion.beta.gouv.fr via le protocole Model Context Protocol.
Il transforme automatiquement les endpoints OpenAPI en outils MCP.
"""

import asyncio
import logging
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
        logger.info(f"Creating MCP Gateway: {settings.mcp_gateway.MCP_SERVER_NAME}")
        gateway_server = FastMCP(name=settings.mcp_gateway.MCP_SERVER_NAME)

        # === 4. CRÉATION ET MONTAGE DES SERVEURS MCP POUR CHAQUE SERVICE ===
        for service_config in service_configs:
            logger.info(f"Building and mounting MCP server for service: {service_config.name}")
            factory = MCPFactory(config=service_config, logger=logger)
            service_mcp_instance = await factory.build()

            # Monte le serveur du service sur la passerelle sans préfixe
            gateway_server.mount(service_mcp_instance)
            logger.info(f"Mounted service '{service_config.name}' at the gateway root (no prefix).")

        # === 5. AJOUT D'UN ENDPOINT DE SANTÉ GLOBAL ===
        @gateway_server.custom_route("/health", methods=["GET"])
        async def health_check(request: Request) -> PlainTextResponse:
            """A simple health check endpoint for the gateway."""
            return PlainTextResponse("OK", status_code=200)
        logger.info("Global health check endpoint (/health) added to gateway.")


        # === 6. LANCEMENT DE LA PASSERELLE MCP ===
        server_url = (
            f"http://{settings.mcp_gateway.MCP_HOST}:{settings.mcp_gateway.MCP_PORT}"
            f"{settings.mcp_gateway.MCP_API_PATH}"
        )
        logger.info(f"Starting MCP Gateway on {server_url}")
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
        logger.error(f"Unexpected error during MCP Gateway startup: {e}", exc_info=True)
        logger.error("Please check your configuration and try again.")

    finally:
        # === 7. NETTOYAGE DES RESSOURCES ===
        # Les clients HTTP des services montés sont fermés par leurs propres factories.
        # Ici, nous nous assurons que toute ressource de la passerelle principale est nettoyée si nécessaire.
        if gateway_server:
            # FastMCP gère généralement la fermeture de ses clients internes,
            # mais si des ressources spécifiques à la passerelle étaient ouvertes, elles seraient fermées ici.
            logger.info("MCP Gateway cleanup completed.")


if __name__ == "__main__":
    """
    Point d'entrée du script.
    Lance la passerelle MCP avec gestion d'erreurs appropriée.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Failed to start MCP Gateway: {e}")
        exit(1)
