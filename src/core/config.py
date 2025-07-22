"""
Configuration management centralisée pour tous les composants de l'application.

Ce module centralise la configuration de l'agent IA et du serveur MCP en utilisant
Pydantic Settings pour une gestion robuste et typée des variables d'environnement.

Point d'entrée unique pour toute la configuration de l'application :
    from src.core.config import settings

Utilisation :
    # Configuration de l'agent IA
    api_key = settings.agent.OPENAI_API_KEY
    model_name = settings.agent.AGENT_MODEL_NAME

    # Configuration du serveur MCP
    mcp_host = settings.mcp.MCP_HOST
    mcp_port = settings.mcp.MCP_PORT

Structure hiérarchique :
    - settings.agent.* : Configuration de l'agent IA (OpenAI, ports, connexions MCP)
    - settings.mcp.* : Configuration du serveur MCP (OpenAPI, authentification, serveur)

Variables d'environnement :
    Toutes les variables sont chargées automatiquement depuis le fichier .env
    ou depuis les variables d'environnement du système.
"""

from typing import Optional, List
import json

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, ValidationError


class AgentSettings(BaseSettings):
    """
    Configuration de l'agent IA basée sur Pydantic Settings.

    Cette classe charge automatiquement les variables d'environnement
    depuis le fichier .env et valide leur type.
    """

    # Configuration de l'API OpenAI (recommandé pour éviter les problèmes de schéma $ref)
    OPENAI_API_KEY: str = ""

    # URL de base pour les API compatibles OpenAI (ex: Ollama, vLLM)
    OPENAI_API_BASE_URL: str | None = None

    # Nom du modèle OpenAI à utiliser pour l'agent
    AGENT_MODEL_NAME: str = "gpt-4.1"

    # Configuration de connexion au serveur MCP
    # Utilise le nom du service Docker pour la communication inter-conteneurs
    MCP_GATEWAY_BASE_URL: str = "http://mcp_server:8000/mcp/"

    # Port du serveur agent
    AGENT_PORT: int = 8001

    # Configuration de la logique de retry pour la connexion MCP
    # Nombre maximum de tentatives de connexion au serveur MCP
    AGENT_MCP_CONNECTION_MAX_RETRIES: int = 10

    # Délai initial en secondes avant la première nouvelle tentative
    AGENT_MCP_CONNECTION_BASE_DELAY: float = 1.0

    # Multiplicateur pour le backoff exponentiel entre les tentatives
    AGENT_MCP_CONNECTION_BACKOFF_MULTIPLIER: float = 2.0

    # Configuration pour FastAPI + Chainlit
    CORS_ORIGINS: list[str] = ["*"]  # En production, spécifier les domaines autorisés
    SECRET_KEY: str = "your-secret-key-here-change-in-production"

    # Configuration de la base de données
    DATABASE_URL: str = "postgresql+asyncpg://user:password@postgres:5432/datainclusion"

    # Configuration S3 pour le stockage local (Localstack)
    BUCKET_NAME: str = "datainclusion-elements"
    APP_AWS_ACCESS_KEY: str = "test-key"
    APP_AWS_SECRET_KEY: str = "test-secret"
    APP_AWS_REGION: str = "eu-central-1"
    DEV_AWS_ENDPOINT: str | None = None


class MCPServiceConfig(BaseModel):
    """
    Configuration for a single MCP service.
    """

    name: str
    openapi_url: str
    api_key_env_var: str
    tool_mappings_file: Optional[str] = None


class MCPGatewaySettings(BaseSettings):
    """
    Configuration du serveur MCP basée sur Pydantic Settings.

    Cette classe charge automatiquement les variables d'environnement
    depuis le fichier .env et valide leur type.
    """

    # Configuration du serveur MCP
    MCP_SERVER_NAME: str = "DataInclusionAPI"
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 8000
    MCP_API_PATH: str = "/mcp/"
    MCP_SERVICES_CONFIG: str = "[]"


class AppSettings(BaseSettings):
    """
    Configuration principale de l'application.

    Cette classe centralise toutes les configurations des différents composants
    de l'application via des modèles imbriqués.
    """

    # Configurations des composants
    agent: AgentSettings = AgentSettings()
    mcp_gateway: MCPGatewaySettings = MCPGatewaySettings()

    # Configuration Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore les variables d'environnement non définies
    )

    @property
    def mcp_services(self) -> List[MCPServiceConfig]:
        """
        Parses the MCP_SERVICES_CONFIG JSON string and returns a list of MCPServiceConfig objects.
        Handles empty or malformed JSON.
        """
        try:
            if self.mcp_gateway.MCP_SERVICES_CONFIG:
                data = json.loads(self.mcp_gateway.MCP_SERVICES_CONFIG)
                return [MCPServiceConfig(**service) for service in data]
            return []
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Warning: Could not parse MCP_SERVICES_CONFIG: {e}")
            return []


# Instance globale de configuration
# Point d'entrée unique pour toute la configuration de l'application
# Utilisation recommandée : from src.core.config import settings
settings = AppSettings()
