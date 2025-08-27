# ==============================================================================
# Étape 1: "Builder" - Environnement de construction
# ==============================================================================
# On utilise une image complète pour la construction, mais on la nomme "builder".
# Son contenu ne sera pas dans l'image finale.
FROM python:3.12-slim as builder

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires pour la construction (si besoin) et uv.
# curl n'est plus nécessaire ici, il sera dans l'image finale.
RUN pip install uv

# Créer un environnement virtuel. C'est la meilleure pratique pour isoler les dépendances.
# Cela nous permettra de copier l'intégralité du venv dans l'image finale.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copier uniquement le fichier de dépendances pour optimiser le cache Docker.
# Si pyproject.toml ne change pas, cette couche ne sera pas reconstruite.
COPY pyproject.toml ./

# Installer UNIQUEMENT les dépendances de production dans le venv.
# On utilise `uv pip install .` qui lit `pyproject.toml` mais ignore les `optional-dependencies` (comme 'dev').
# C'est beaucoup plus propre et léger que d'installer tout le projet.
RUN uv pip install --no-cache-dir .

# ==============================================================================
# Étape 2: "Final" - Environnement d'exécution
# ==============================================================================
# On repart d'une image "slim" propre et légère.
FROM python:3.12-slim

# Définir les arguments
ARG PORT=8000

# Définir le répertoire de travail
WORKDIR /app

# Installer uniquement les dépendances système STRICTEMENT nécessaires à l'exécution.
# Dans votre cas, c'est `curl` pour le healthcheck.
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root pour des raisons de sécurité.
# Exécuter des conteneurs en tant que root est une mauvaise pratique.
# `--system` crée un utilisateur sans home directory, `--group` crée un groupe correspondant.
RUN adduser --system --group appuser

# Copier l'environnement virtuel avec les dépendances depuis l'étape "builder".
# C'est la magie du multi-stage : on ne récupère que les paquets installés, pas les outils de build.
COPY --from=builder /opt/venv /opt/venv

# Copier le code source de l'application.
COPY src/ ./src/
COPY public/ ./public/
COPY main.py ./

# S'approprier les fichiers de l'application par l'utilisateur non-root.
RUN chown -R appuser:appuser /app

# Activer l'environnement virtuel pour toutes les commandes suivantes.
ENV PATH="/opt/venv/bin:$PATH"
# Configurer le PYTHONPATH pour que Python trouve les modules dans /app/src.
ENV PYTHONPATH="/app:$PYTHONPATH"

# Passer à l'utilisateur non-root. Toutes les commandes suivantes s'exécuteront avec cet utilisateur.
USER appuser

# Exposer le port sur lequel l'application va écouter.
EXPOSE ${PORT}

# Définir les variables d'environnement.
# Celles-ci peuvent toujours être surchargées par docker-compose.yml.
ENV TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=${PORT}
ENV MCP_API_PATH=/mcp/

# Définir la commande pour lancer le serveur.
CMD ["python", "main.py"]