import logging
import httpx
from fastmcp import FastMCP


async def inspect_mcp_components(mcp_instance: FastMCP, logger: logging.Logger):
    """Inspecte et affiche les composants MCP (outils, ressources, templates)."""
    logger.info("--- Inspecting MCP Components ---")
    tools = await mcp_instance.get_tools()
    resources = await mcp_instance.get_resources()
    templates = await mcp_instance.get_resource_templates()

    logger.info(f"{len(tools)} Tool(s) found:")
    if tools:
        logger.info(f"  Names: {', '.join(sorted([t.name for t in tools.values() if t.name is not None]))}")
    else:
        logger.info("  No tools generated.")

    logger.info(f"{len(resources)} Resource(s) found:")
    if resources:
        logger.info(f"  Names: {', '.join(sorted([r.name for r in resources.values() if r.name is not None]))}")
    else:
        logger.info("  No resources generated.")

    logger.info(f"{len(templates)} Resource Template(s) found:")
    if templates:
        logger.info(f"  Names: {', '.join(sorted([t.name for t in templates.values() if t.name is not None]))}")
    else:
        logger.info("  No resource templates generated.")
    logger.info("--- End of MCP Components Inspection ---")


def create_api_client(base_url: str, logger: logging.Logger, api_key: str | None = None) -> httpx.AsyncClient:
    """Crée un client HTTP avec authentification pour l'API Data Inclusion.
    
    Args:
        base_url: L'URL de base de l'API
        logger: Instance du logger pour les messages
        api_key: Clé d'API optionnelle pour l'authentification
        
    Returns:
        httpx.AsyncClient: Client HTTP configuré avec les headers d'authentification
    """
    headers = {}
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        logger.info(f"Using DATA_INCLUSION_API_KEY from configuration (key: ***{api_key[-4:]})")
    else:
        logger.warning("DATA_INCLUSION_API_KEY not set in configuration.")
        logger.warning("Some API endpoints may be publicly accessible, but authenticated endpoints will fail.")
        logger.warning("Please set DATA_INCLUSION_API_KEY in your .env file if you have an API key.")
    
    # Ajout d'headers par défaut
    headers.update({
        "User-Agent": "DataInclusion-MCP-Server/1.0",
        "Accept": "application/json"
    })
    
    return httpx.AsyncClient(
        base_url=base_url, 
        headers=headers,
        timeout=30.0  # Timeout de 30 secondes
    )
