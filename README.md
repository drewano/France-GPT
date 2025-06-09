# Data Inclusion MCP Server

Un serveur MCP (Model Context Protocol) qui expose l'API [data.inclusion.beta.gouv.fr](https://data.inclusion.beta.gouv.fr) pour faciliter l'accès aux données d'inclusion en France via des assistants IA compatibles MCP.

## 📋 Description

Ce projet transforme automatiquement l'API REST de data.inclusion en outils MCP, permettant aux assistants IA (comme Claude Desktop) d'interroger facilement les données sur les structures, services et ressources d'inclusion sociale en France.

### Fonctionnalités

- 🔄 **Conversion automatique** : Transforme les endpoints OpenAPI en outils MCP
- 🔧 **Outils personnalisés** : Noms d'outils conviviaux pour une meilleure utilisation
- 🔑 **Authentification** : Support pour les clés API Bearer Token
- 🌐 **Transport SSE** : Compatible avec les clients MCP modernes
- ⚙️ **Configuration flexible** : Variables d'environnement pour tous les paramètres

### Outils disponibles

- `list_all_structures` - Liste toutes les structures d'inclusion
- `get_structure_details` - Obtient les détails d'une structure
- `list_all_services` - Liste tous les services disponibles
- `search_services` - Recherche des services selon des critères
- `doc_list_*` - Accès aux référentiels de documentation

## 🔧 Prérequis

- **Python 3.12+** (requis par le projet)
- **Git** pour cloner le repository
- **Accès internet** pour les requêtes vers l'API data.inclusion

## 📦 Installation

### 1. Cloner le repository

```bash
git clone https://github.com/votre-user/datainclusion-mcp-server.git
cd datainclusion-mcp-server
```

### 2. Installer les dépendances

Avec pip (recommandé) :
```bash
pip install -e .
```

Ou avec uv (plus rapide) :
```bash
uv pip install -e .
```

### 3. Vérifier l'installation

```bash
python -c "import fastmcp, httpx; print('✅ Installation réussie')"
```

## ⚙️ Configuration

### 1. Créer le fichier de configuration

```bash
cp env.example .env
```

### 2. Éditer le fichier `.env`

Ouvrez le fichier `.env` et configurez les variables selon vos besoins :

```bash
# --- Configuration du serveur ---
# Transport utilisé par le serveur MCP ('sse' pour serveur web, 'stdio' pour local)
TRANSPORT=sse

# Adresse IP d'écoute du serveur
MCP_HOST=127.0.0.1

# Port d'écoute du serveur
MCP_PORT=8000

# Chemin de l'endpoint SSE
MCP_SSE_PATH=/sse

# --- Configuration de l'API ---
# Nom du fichier de spécification OpenAPI
OPENAPI_URL=https://api.data.inclusion.beta.gouv.fr/api/openapi.json

# Nom du serveur MCP (affiché dans les clients)
MCP_SERVER_NAME=DataInclusionAPI

# Clé API pour l'API data.inclusion (optionnelle)
DATA_INCLUSION_API_KEY=votre_cle_api_ici
```

### 📋 Description des variables

| Variable | Description | Valeur par défaut | Obligatoire |
|----------|-------------|-------------------|-------------|
| `MCP_HOST` | Adresse IP d'écoute | `127.0.0.1` | Non |
| `MCP_PORT` | Port d'écoute | `8000` | Non |
| `MCP_SSE_PATH` | Chemin endpoint SSE | `/sse` | Non |
| `OPENAPI_URL` | Lien du Fichier spécification OpenAPI | `https://api.data.inclusion.beta.gouv.fr/api/openapi.json` | Oui |
| `MCP_SERVER_NAME` | Nom du serveur MCP | `DataInclusionAPI` | Non |
| `DATA_INCLUSION_API_KEY` | Clé API data.inclusion | - | Oui |

## 🚀 Lancement du serveur

### Démarrage simple

```bash
python src/main.py
```

### Avec variables d'environnement inline

```bash
MCP_PORT=8001 python src/main.py
```

### Vérification du fonctionnement

Si le serveur démarre correctement, vous devriez voir :

```
Loading OpenAPI specification from 'openapi.json'...
✅ Successfully loaded OpenAPI spec: 'data.inclusion API'
🔑 Configuring HTTP client with authentication...
🛠️  Configuring custom tool names...
🗺️  Configuring route mappings...
🚀 Creating FastMCP server 'DataInclusionAPI'...
✅ FastMCP server 'DataInclusionAPI' created successfully!
🔍 Inspecting MCP components...
🌐 Starting MCP server on http://127.0.0.1:8000/sse
Press Ctrl+C to stop the server
```

## 🔌 Intégration Client MCP

### Claude Desktop

Pour utiliser ce serveur avec Claude Desktop, ajoutez la configuration suivante à votre fichier `claude_desktop_config.json` :

**Localisation du fichier :**
- **macOS** : `~/Library/Application\ Support/Claude/claude_desktop_config.json`
- **Windows** : `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux** : `~/.config/Claude/claude_desktop_config.json`

**Configuration :**

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

### Autres clients MCP

Pour d'autres clients compatibles MCP, utilisez :
- **URL du serveur** : `http://127.0.0.1:8000/sse`
- **Transport** : `sse` (Server-Sent Events)
- **Authentification** : Aucune (sauf si clé API configurée)

### Test de la connexion

Une fois configuré, vous pouvez tester dans Claude Desktop :

```
Peux-tu lister quelques structures d'inclusion disponibles ?
```

Claude devrait utiliser l'outil `list_all_structures` pour répondre à votre demande.

## 🛠️ Développement

### Structure du projet

```
datainclusion-mcp-server/
├── src/
│   ├── __init__.py          # Package Python
│   ├── main.py              # Point d'entrée principal
│   └── utils.py             # Fonctions utilitaires
├── .env.example             # Template de configuration
├── .gitignore              # Fichiers ignorés par Git
├── pyproject.toml          # Configuration et dépendances
├── README.md               # Cette documentation
├── LICENSE                 # Licence MIT
```

### Logs et debugging

Pour activer les logs détaillés :

```bash
DEBUG=true python src/main.py
```

### Modification de la configuration

Après modification du fichier `.env`, redémarrez le serveur pour appliquer les changements.

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :

1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## 📚 Ressources

- [Documentation data.inclusion](https://gip-inclusion.github.io/data-inclusion-schema/latest/)
- [Spécification MCP](https://modelcontextprotocol.io/)
- [Documentation FastMCP](https://github.com/jlowin/fastmcp)
- [Claude Desktop](https://claude.ai/download)

## ❓ Support

Si vous rencontrez des problèmes :

1. Vérifiez que toutes les dépendances sont installées
2. Consultez les logs du serveur
3. Vérifiez votre configuration `.env`
4. Ouvrez une issue sur GitHub avec les détails du problème

---

**Développé avec ❤️ pour faciliter l'accès aux données d'inclusion en France** 
