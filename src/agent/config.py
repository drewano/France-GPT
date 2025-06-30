"""
Configuration management for the AI Agent using Pydantic Settings.

Ce module centralise la configuration de l'agent IA en utilisant
Pydantic Settings pour une gestion robuste et typée des variables d'environnement.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration de l'agent IA basée sur Pydantic Settings.
    
    Cette classe charge automatiquement les variables d'environnement
    depuis le fichier .env et valide leur type.
    """
    
    # Configuration de l'API OpenAI (recommandé pour éviter les problèmes de schéma $ref)
    OPENAI_API_KEY: str
    
    # Configuration de l'API Gemini (optionnel, peut causer des problèmes avec les schémas $ref)
    GEMINI_API_KEY: str | None = None
    
    # Configuration de connexion au serveur MCP
    MCP_SERVER_URL: str = "http://127.0.0.1:8000/mcp"
    
    # Configuration Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore les variables d'environnement non définies
    ) 