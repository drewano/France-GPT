"""
Serveur web ASGI pour l'agent IA d'inclusion sociale utilisant le protocole A2A.

Ce module expose l'agent via une API web en utilisant le protocole Agent-to-Agent
de Pydantic AI avec FastA2A.
"""

from contextlib import asynccontextmanager
import uvicorn
from fasta2a import FastA2A, Skill
from fasta2a.broker import InMemoryBroker
from fasta2a.storage import InMemoryStorage
from pydantic_ai.mcp import MCPServerStreamableHTTP

from .agent import create_inclusion_agent
from .config import Settings


# Instances globales
agent = None
mcp_server = None


@asynccontextmanager
async def lifespan(app: FastA2A):
    """
    Gestionnaire de cycle de vie pour l'application FastA2A.
    
    Configure l'agent et la connexion MCP au démarrage et nettoie
    les ressources à l'arrêt.
    """
    global agent, mcp_server
    
    # Charger la configuration
    settings = Settings()
    
    # Instancier le client MCP
    mcp_server = MCPServerStreamableHTTP(url=settings.MCP_SERVER_URL)
    
    # Créer l'agent d'inclusion
    agent = create_inclusion_agent(mcp_server)
    
    # S'assurer que la connexion au serveur MCP est active
    async with agent.run_mcp_servers():
        # Stocker l'agent dans l'état de l'application
        app.state.agent = agent
        yield  # Passer la main à l'application


# Créer l'application FastA2A avec configuration complète
app = FastA2A(
    # Configuration du stockage et du broker
    storage=InMemoryStorage(),
    broker=InMemoryBroker(),
    
    # Métadonnées de l'agent
    name="DataInclusion Agent",
    description="Agent IA spécialisé dans l'inclusion sociale en France. Aide à trouver des informations sur les structures et services d'aide, les ressources disponibles sur le territoire français.",
    url="http://localhost:8001",
    version="1.0.0",
    
    # Compétences de l'agent
    skills=[
        Skill(
            id="datainclusion_chat",
            name="DataInclusion Chat",
            description="Recherche et fournit des informations sur les services d'inclusion sociale, les structures d'aide et les ressources disponibles en France",
            tags=["inclusion", "social", "france", "aide", "services"],
            examples=[
                "Trouve-moi des structures d'aide pour l'insertion professionnelle à Paris",
                "Quels sont les services disponibles pour l'aide au logement en région PACA ?",
                "Comment trouver de l'aide alimentaire près de chez moi ?"
            ],
            input_modes=["application/json"],
            output_modes=["application/json"]
        )
    ],
    
    # Gestionnaire de cycle de vie
    lifespan=lifespan
)


if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "src.agent.server:app",
        host="0.0.0.0",
        port=settings.AGENT_PORT,
        reload=True
    ) 