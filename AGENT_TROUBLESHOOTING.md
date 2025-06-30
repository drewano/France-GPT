# Résolution du problème "Could not find $ref definition for Thematique"

## Problème identifié

L'erreur `UserError: Could not find $ref definition for Thematique` se produit lors de l'utilisation de l'agent avec le modèle Gemini. Cette erreur est causée par :

1. **Limitation de Gemini** : Le modèle Gemini ne supporte pas les schémas JSON avec des références `$ref` récursives
2. **Schémas complexes de l'API DataInclusion** : L'endpoint `doc_list_thematiques` retourne des schémas JSON avec des références `$ref`
3. **Incompatibilité** : Pydantic-AI génère des schémas avec `$ref` que Gemini refuse de traiter

## Solution appliquée

### 1. Changement de modèle : Gemini → OpenAI

**Fichier modifié** : `src/agent/agent.py`

```python
# AVANT (problématique avec Gemini)
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

model = GeminiModel('gemini-2.0-flash', provider=GoogleGLAProvider(api_key=settings.GEMINI_API_KEY))

# APRÈS (solution avec OpenAI)
from pydantic_ai.models.openai import OpenAIModel

model = OpenAIModel('gpt-4o')  # OpenAI gère mieux les schémas JSON complexes
```

### 2. Mise à jour de la configuration

**Fichier modifié** : `src/agent/config.py`

```python
class Settings(BaseSettings):
    # Configuration recommandée (évite les erreurs $ref)
    OPENAI_API_KEY: str
    
    # Configuration optionnelle (peut causer des problèmes)
    GEMINI_API_KEY: str | None = None
```

### 3. Configuration des variables d'environnement

Ajouter dans votre fichier `.env` :

```bash
# OBLIGATOIRE : Clé API OpenAI (recommandé)
OPENAI_API_KEY=votre_cle_openai_ici

# OPTIONNEL : Clé API Gemini (peut causer des erreurs)
# GEMINI_API_KEY=votre_cle_gemini_ici
```

## Recommandation

**Utilisez OpenAI (GPT-4o)** car :
- ✅ Support complet des schémas JSON complexes avec `$ref`
- ✅ Meilleure compatibilité avec FastMCP
- ✅ Pas de limitation sur les références récursives
- ✅ Performance stable avec Pydantic-AI

## Test de la solution

```bash
# Lancer l'agent avec la nouvelle configuration
python -m src.agent.main
```

L'erreur `UserError: Could not find $ref definition for Thematique` ne devrait plus apparaître. 