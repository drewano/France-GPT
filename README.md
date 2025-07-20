---

# Agent IA pour l'API Data Inclusion

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Chainlit](https://img.shields.io/badge/Chainlit-4B5563?style=for-the-badge)](https://chainlit.io/)

Ce projet fournit un agent conversationnel intelligent conçu pour interagir avec l'API [data.inclusion.beta.gouv.fr](https://data.inclusion.beta.gouv.fr/). Grâce à une interface de chat moderne, il permet aux utilisateurs (travailleurs sociaux, citoyens, etc.) de poser des questions en langage naturel pour trouver des structures et services d'aide sociale en France.

L'agent est capable de comprendre des requêtes complexes, d'utiliser les outils d'API appropriés et de fournir des réponses précises et contextualisées en temps réel.

## ✨ Fonctionnalités Clés

- **Interface de Chat Intuitive** : Une interface utilisateur propre et réactive construite avec [Chainlit](https://chainlit.io/) pour une expérience conversationnelle fluide.
- **Requêtes en Langage Naturel** : Posez des questions comme "Trouve-moi des services d'aide alimentaire près de Lyon" ou "Quelles structures proposent un accompagnement numérique pour les seniors ?".
- **Génération d'Outils Automatisée** : Le serveur [FastMCP](https://github.com/mcp-ai/fastmcp) transforme dynamiquement la spécification OpenAPI de Data Inclusion en outils utilisables par le LLM.
- **Réponses en Streaming** : Les réponses de l'agent s'affichent en temps réel, token par token, pour une meilleure interactivité.
- **Historique de Conversation** : Les conversations sont sauvegardées dans une base de données PostgreSQL, permettant aux utilisateurs de reprendre leurs sessions.
- **Architecture Robuste et Modulaire** : Entièrement conteneurisé avec Docker et Docker Compose, séparant l'agent, le serveur d'outils (MCP) et la base de données.
- **Authentification Sécurisée** : Support de l'authentification par mot de passe pour l'interface de chat et par jeton Bearer pour le serveur MCP.

## 🏛️ Architecture

Le projet est composé de trois services principaux orchestrés par Docker Compose :

1.  **Agent & UI (Service `agent`)** : Une application FastAPI qui héberge l'interface de chat Chainlit. Elle contient la logique de l'agent (basée sur `pydantic-ai`) qui reçoit les prompts de l'utilisateur, dialogue avec le LLM, et appelle les outils du serveur MCP pour obtenir des données.
2.  **Serveur d'Outils (Service `mcp_server`)** : Un serveur FastMCP qui lit la spécification `openapi.json` de l'API Data Inclusion, la transforme en un ensemble d'outils (ex: `search_services`, `get_structure_details`) et les expose via le *Model Context Protocol* (MCP). Il agit comme un pont sécurisé et structuré entre l'agent et l'API réelle.
3.  **Base de Données (Service `postgres`)** : Une instance PostgreSQL utilisée par Chainlit pour persister les utilisateurs, les conversations et les messages, offrant une expérience utilisateur continue.

Voici un diagramme illustrant le flux des informations :

```mermaid
graph TD
    subgraph "Navigateur de l'Utilisateur"
        A[Interface Chainlit]
    end

    subgraph "Service Agent (FastAPI)"
        B[Logique de l'Agent - Pydantic-AI]
        C[API de Chat - /api/chat]
    end

    subgraph "Service MCP Server"
        D[Serveur d'Outils FastMCP]
    end

    subgraph "Services Externes"
        E[API LLM - ex: OpenAI]
        F[API Data Inclusion]
    end

    subgraph "Base de données"
        G[PostgreSQL]
    end

    A -- Prompt utilisateur --> B
    B -- Requête formatée --> E
    E -- Raisonnement et Appel d'outil --> B
    B -- Appel d'outil MCP --> D
    D -- Requête API --> F
    F -- Données --> D
    D -- Résultat de l'outil --> B
    B -- Formate la réponse --> E
    E -- Réponse en langage naturel --> B
    B -- Réponse en streaming --> A
    A <-->|Historique des chats| G

```

## 🚀 Démarrage Rapide

Pour lancer le projet, vous aurez besoin de Docker et Docker Compose.

### 1. Prérequis

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### 2. Configuration

1.  Clonez ce dépôt :
    ```bash
    git clone https://github.com/votre-user/datainclusion-mcp-server.git
    cd datainclusion-mcp-server
    ```

2.  Créez un fichier `.env` à partir de l'exemple fourni :
    ```bash
    cp .env.example .env
    ```

3.  Modifiez le fichier `.env` pour y ajouter vos clés d'API :
    ```dotenv
    # Clé API OpenAI (ou d'un service compatible comme Ollama via OPENAI_API_BASE_URL)
    OPENAI_API_KEY="sk-..."

    # Clé API pour data.inclusion.beta.gouv.fr (si vous en avez une)
    DATA_INCLUSION_API_KEY="di_api_..."
    
    # Secret pour l'authentification Chainlit (changez cette valeur)
    CHAINLIT_AUTH_SECRET="votre_secret_aleatoire_tres_long"

    # Les autres valeurs par défaut sont configurées pour fonctionner avec Docker Compose.
    ```

### 3. Lancement de l'application

Lancez l'ensemble des services avec Docker Compose :

```bash
docker-compose up --build
```

Cette commande va :
- Construire les images Docker pour les services `agent` et `mcp_server`.
- Démarrer les trois conteneurs (`agent`, `mcp_server`, `postgres`).
- Établir un réseau commun pour qu'ils puissent communiquer entre eux.

Le démarrage peut prendre une minute, le temps que les healthchecks (vérifications de santé) valident que chaque service est prêt.

## 💬 Utilisation

1.  **Accéder à l'interface de chat** :
    Ouvrez votre navigateur et allez à l'adresse [**http://localhost:8001**](http://localhost:8001).

2.  **Authentification** :
    Utilisez les identifiants par défaut pour vous connecter :
    - **Nom d'utilisateur** : `admin`
    - **Mot de passe** : `admin`

3.  **Discutez avec l'agent** :
    Vous pouvez maintenant poser vos questions. Voici quelques exemples :
    - "Quels sont les différents types de services disponibles ?"
    - "Trouve-moi des points d'accès au numérique à Bordeaux."
    - "Je cherche une aide alimentaire d'urgence à Paris 18ème."
    - "Donne-moi les détails de la structure 'PIMMS Médiation Lyon Métropole'."

### Accès aux services pour les développeurs

- **Serveur MCP** : L'endpoint du serveur d'outils est accessible à [http://localhost:8000/mcp/](http://localhost:8000/mcp/).
- **API de l'agent** : La documentation de l'API FastAPI de l'agent est disponible sur [http://localhost:8001/docs](http://localhost:8001/docs).
- **Base de données** : Le service PostgreSQL est exposé sur le port `5432` de votre machine hôte.

## 🛠️ Configuration des Variables d'Environnement

Voici les principales variables que vous pouvez configurer dans votre fichier `.env` :

| Variable                               | Description                                                                                              | Exemple                                                        |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `OPENAI_API_KEY`                       | **Requis.** Votre clé d'API pour OpenAI.                                                                 | `sk-...`                                                       |
| `AGENT_MODEL_NAME`                     | Le modèle de langage à utiliser pour l'agent.                                                            | `gpt-4.1`                                                      |
| `DATA_INCLUSION_API_KEY`               | Clé d'API pour accéder aux endpoints authentifiés de Data Inclusion.                                     | `di_api_...`                                                   |
| `DATABASE_URL`                         | URL de connexion à la base de données PostgreSQL. La valeur par défaut est correcte pour Docker Compose. | `postgresql+asyncpg://user:password@postgres:5432/datainclusion` |
| `CHAINLIT_AUTH_SECRET`                 | Clé secrète pour signer les jetons d'authentification de Chainlit. **À changer pour la production.**      | `un_secret_complexe_et_aleatoire`                              |
| `AGENT_PORT`                           | Port sur lequel l'interface de chat et l'API de l'agent sont exposées.                                   | `8001`                                                         |
| `MCP_PORT`                             | Port sur lequel le serveur d'outils MCP est exposé.                                                      | `8000`                                                         |
| `MCP_SERVER_SECRET_KEY`                | Clé secrète pour sécuriser le serveur MCP avec des jetons Bearer. Si vide, l'authentification est désactivée. | `un_autre_secret_complexe`                                     |
| `OPENAI_API_BASE_URL`                  | Optionnel. URL pour utiliser une API compatible OpenAI (ex: Ollama, vLLM).                                 | `http://host.docker.internal:11434/v1`                         |

## ⚖️ Licence

Ce projet est distribué sous la licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.