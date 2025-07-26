"""
DataInclusion MCP Server

Ce serveur MCP expose l'API data.inclusion.beta.gouv.fr via le protocole Model Context Protocol.
Il transforme automatiquement les endpoints OpenAPI en outils MCP.
"""

import asyncio
import sys
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

    logger = setup_logging(name="datainclusion.mcp-servers")
    logger.info("Starting MCP Servers setup...")

    server_tasks = []
    active_servers = []  # To keep track of servers for cleanup

    try:
        service_configs = settings.mcp_services
        if not service_configs:
            logger.warning(
                "No MCP services configured in settings. Skipping server creation."
            )
            return

        for service_config in service_configs:
            logger.info(
                "Building and preparing MCP server for service: %s on port %d",
                service_config.name,
                service_config.port,
            )
            factory = MCPFactory(config=service_config, logger=logger)
            service_mcp_instance = await factory.build()
            active_servers.append(service_mcp_instance)

            # Add a health check endpoint to each individual service MCP instance
            async def health_check(_request: Request) -> PlainTextResponse:
                """A simple health check endpoint for the individual service."""
                return PlainTextResponse("OK", status_code=200)

            service_mcp_instance.custom_route("/health", methods=["GET"])(health_check)

            logger.info(
                "Health check endpoint (/health) added to service '%s'.",
                service_config.name,
            )

            server_url = (
                f"http://{settings.mcp_server.MCP_HOST}:{service_config.port}"
                f"{settings.mcp_server.MCP_API_PATH}"
            )
            logger.info(
                "Scheduling MCP server '%s' to run on %s",
                service_config.name,
                server_url,
            )

            task = asyncio.create_task(
                service_mcp_instance.run_async(
                    transport="http",
                    host=settings.mcp_server.MCP_HOST,
                    port=service_config.port,
                    path=settings.mcp_server.MCP_API_PATH,
                )
            )
            server_tasks.append(task)

        logger.info("All MCP servers scheduled. Starting concurrently...")
        logger.info("Press Ctrl+C to stop all servers.")

        await asyncio.gather(*server_tasks)

    except KeyboardInterrupt:
        logger.info("Servers stopped by user.")

    except Exception as e:
        logger.error(
            "Unexpected error during MCP Servers startup: %s", e, exc_info=True
        )
        logger.error("Please check your configuration and try again.")

    finally:
        logger.info("Initiating MCP Servers cleanup...")
        for server in active_servers:
            if hasattr(server, "client") and server.client:
                # Attempt to close the client within the server instance if it exists
                try:
                    await server.client.aclose()
                    logger.info("Closed HTTP client for server '%s'.", server.name)
                except Exception as close_e:
                    logger.warning(
                        "Error closing HTTP client for server '%s': %s",
                        server.name,
                        close_e,
                    )
        logger.info("MCP Servers cleanup completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Failed to start MCP Gateway: {e}")
        sys.exit(1)
