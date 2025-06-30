#!/usr/bin/env python3
"""
Point d'entrée principal pour le serveur MCP DataInclusion.

Ce script lance le serveur MCP qui expose l'API data.inclusion.beta.gouv.fr
via le protocole Model Context Protocol.
"""

import asyncio
import sys
from src.mcp.server import main


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
        sys.exit(1) 