# Data Inclusion MCP Server

Un serveur MCP (Model Context Protocol) qui expose l'API [data.inclusion.beta.gouv.fr](https://data.inclusion.beta.gouv.fr) pour faciliter l'accès aux données d'inclusion en France via des assistants IA compatibles MCP.

[![Licence: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 📋 Description

Ce projet transforme automatiquement l'API REST de `data.inclusion` en outils MCP, permettant aux assistants IA (comme Claude Desktop) d'interroger facilement les données sur les structures, services et ressources d'inclusion sociale en France. Il charge la spécification OpenAPI de l'API à la volée pour générer les outils.

### ✨ Fonctionnalités

-   **🔄 Conversion Automatique** : Transforme les endpoints de l'API en outils MCP à la volée.
-   **🔧 Outils Conviviaux** : Noms d'outils renommés pour une meilleure compréhension par les IA.
-   **🐳 Support Docker** : Prêt à l'emploi avec une configuration Docker simple.
-   **🔑 Authentification Sécurisée** : Gère l'authentification par `Bearer Token` via les variables d'environnement.
-   **⚙️ Pagination Intelligente** : Limite automatiquement le nombre de résultats pour des réponses plus rapides et ciblées.

### 🛠️ Outils Disponibles

Le serveur expose plus d'une dizaine d'outils, dont les principaux :

-   `list_all_structures` : Liste les structures d'inclusion.
-   `get_structure_details` : Obtient les détails d'une structure spécifique.
-   `search_services` : Recherche des services selon des critères (code postal, thématique, etc.).
-   `list_all_services` : Liste l'ensemble des services disponibles.
-   `doc_list_*` : Accède aux différents référentiels (thématiques, types de frais, etc.).

## 🚀 Démarrage Rapide avec Docker (Recommandé)

Le moyen le plus simple de lancer le serveur est d'utiliser Docker.

### Prérequis

-   **Docker**
-   **Git**

### Étapes

1.  **Cloner le repository :**
    ```bash
    git clone https://github.com/votre-user/datainclusion-mcp-server.git
    cd datainclusion-mcp-server
    ```

2.  **Configurer l'environnement :**
    -   Copiez le fichier d'exemple : `cp env.example .env`
    -   Ouvrez le fichier `.env` et ajoutez votre clé API : `DATA_INCLUSION_API_KEY=votre_cle_api_ici`
    -   **Important :** Laissez `MCP_HOST=0.0.0.0` pour que le conteneur soit accessible depuis votre machine.

3.  **Construire l'image Docker :**
    ```bash
    docker build -t datainclusion-mcp .
    ```

4.  **Lancer le conteneur :**
    ```bash
    docker run -d --rm -p 8000:8000 --env-file .env --name mcp-server datainclusion-mcp
    ```

5.  **Vérifier les logs :**
    ```bash
    docker logs mcp-server
    ```
    Vous devriez voir `Uvicorn running on http://0.0.0.0:8000`. Votre serveur est prêt !

## 🔌 Intégration Client MCP (Claude Desktop, etc.)

Une fois le serveur lancé (localement ou via Docker), ajoutez cette configuration à votre client MCP :

```json
{
  "mcpServers": {
    "data-inclusion": {
      "transport": "sse",
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

> **Localisation du fichier de config Claude :**
> - **Windows** : `%APPDATA%\Claude\claude_desktop_config.json`
> - **macOS** : `~/Library/Application Support/Claude/claude_desktop_config.json`
> - **Linux** : `~/.config/Claude/claude_desktop_config.json`

## ⚙️ Installation et Lancement Manuels

Si vous ne souhaitez pas utiliser Docker.

### Prérequis

-   **Python 3.12+**

### Étapes

1.  **Cloner le repository et naviguer dans le dossier.**
2.  **Installer les dépendances :**
    ```bash
    # Avec uv (recommandé)
    uv pip install -e .
    
    # Ou avec pip
    pip install -e .
    ```
3.  **Configurer l'environnement :**
    -   `cp env.example .env`
    -   Ouvrez `.env` et ajoutez votre clé API.
    -   Pour un lancement local, `MCP_HOST=127.0.0.1` est suffisant.
4.  **Lancer le serveur :**
    ```bash
    python src/main.py
    ```

## 🛠️ Configuration des Variables d'Environnement

Configurez ces variables dans votre fichier `.env` :

| Variable                 | Description                                                               | Défaut                                                    |
| ------------------------ | ------------------------------------------------------------------------- | --------------------------------------------------------- |
| `MCP_HOST`               | Adresse IP d'écoute. **Utiliser `0.0.0.0` pour Docker.**                   | `127.0.0.1`                                               |
| `MCP_PORT`               | Port d'écoute du serveur.                                                 | `8000`                                                    |
| `MCP_SSE_PATH`           | Chemin de l'endpoint SSE.                                                 | `/sse`                                                    |
| `OPENAPI_URL`            | URL de la spécification OpenAPI à charger.                                | `https://api.data.inclusion.beta.gouv.fr/api/openapi.json` |
| `MCP_SERVER_NAME`        | Nom du serveur affiché dans les clients.                                  | `DataInclusionAPI`                                        |
| `DATA_INCLUSION_API_KEY` | **(Requis)** Votre clé API pour l'API `data.inclusion`.                   | `None`                                                    |

## 🏗️ Structure du Projet

```
datainclusion-mcp-server/
├── src/
│   ├── main.py              # Point d'entrée principal du serveur
│   └── utils.py             # Fonctions utilitaires (client HTTP, inspection)
├── .env.example             # Template de configuration d'environnement
├── .gitignore               # Fichiers ignorés par Git
├── Dockerfile               # Instructions pour construire l'image Docker
├── pyproject.toml           # Dépendances et métadonnées du projet
└── README.md                # Cette documentation
```

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une *Pull Request* ou une *Issue*.

1.  Forker le projet.
2.  Créer une branche pour votre fonctionnalité (`git checkout -b feature/ma-super-feature`).
3.  Commiter vos changements (`git commit -m 'Ajout de ma-super-feature'`).
4.  Pousser vers la branche (`git push origin feature/ma-super-feature`).
5.  Ouvrir une Pull Request.

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.