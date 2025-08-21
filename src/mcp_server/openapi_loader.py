"""
Module de chargement et pré-traitement de la spécification OpenAPI.

Ce module contient la classe OpenAPILoader qui centralise la logique de chargement
et de pré-traitement des spécifications OpenAPI pour le serveur MCP.
"""

import json
import logging
import os  # Import os
import pathlib  # Import pathlib
import copy
from typing import List, Dict, Tuple
import httpx
from fastmcp.utilities.openapi import parse_openapi_to_http_routes, HTTPRoute


class OpenAPILoader:
    """
    Classe responsable du chargement et du pré-traitement de la spécification OpenAPI.

    Cette classe encapsule toute la logique de :
    - Chargement de la spécification OpenAPI depuis une URL
    - Parsing des routes HTTP
    - Application des limites de pagination
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialise le loader avec le logger et l'URL OpenAPI.

        Args:
            logger: Instance du logger pour enregistrer les messages
            openapi_url: L'URL de la spécification OpenAPI à charger
        """
        self.logger = logger

    async def load(self, openapi_path_or_url: str) -> Tuple[Dict, List[HTTPRoute]]:
        """
        Charge et pré-traite la spécification OpenAPI.

        Cette méthode :
        1. Charge la spécification OpenAPI depuis l'URL configurée
        2. Parse la spécification en routes HTTP
        3. Applique les limites de pagination

        Returns:
            Tuple[Dict, List[HTTPRoute]]: Un tuple contenant la spécification OpenAPI
            et la liste des routes HTTP parsées.

        Raises:
            httpx.RequestError: Si la récupération de la spécification échoue
            json.JSONDecodeError: Si la réponse n'est pas un JSON valide
            FileNotFoundError: Si le fichier local spécifié n'existe pas
        """
        openapi_spec = {}
        if openapi_path_or_url.startswith("http://") or openapi_path_or_url.startswith(
            "https://"
        ):
            self.logger.info(
                f"Loading OpenAPI specification from URL: '{openapi_path_or_url}'..."
            )
            try:
                # === CHARGEMENT DE LA SPÉCIFICATION OPENAPI DEPUIS URL ===
                async with httpx.AsyncClient() as client:
                    response = await client.get(openapi_path_or_url)
                    response.raise_for_status()  # Lève une exception si le statut n'est pas 2xx
                    openapi_spec = response.json()
            except httpx.RequestError as e:
                self.logger.error(
                    f"Failed to fetch OpenAPI specification from '{openapi_path_or_url}'."
                )
                self.logger.error(f"Details: {e}")
                raise
            except json.JSONDecodeError as e:
                self.logger.error(
                    f"Invalid JSON in the response from '{openapi_path_or_url}'."
                )
                self.logger.error(f"Details: {e}")
                raise
        else:
            self.logger.info(
                f"Loading OpenAPI specification from local file: '{openapi_path_or_url}'..."
            )
            try:
                # === CHARGEMENT DE LA SPÉCIFICATION OPENAPI DEPUIS FICHIER LOCAL ===
                if not os.path.exists(openapi_path_or_url):
                    raise FileNotFoundError(
                        f"Local OpenAPI file not found at '{openapi_path_or_url}'"
                    )
                with pathlib.Path(openapi_path_or_url).open("r", encoding="utf-8") as f:
                    openapi_spec = json.load(f)
            except FileNotFoundError as e:
                self.logger.error(f"Failed to load local OpenAPI file. Details: {e}")
                raise
            except json.JSONDecodeError as e:
                self.logger.error(
                    f"Invalid JSON in the local file '{openapi_path_or_url}'."
                )
                self.logger.error(f"Details: {e}")
                raise

        api_title = openapi_spec.get("info", {}).get("title", "Unknown API")
        self.logger.info(f"Successfully loaded OpenAPI spec: '{api_title}'")

        # === PRÉ-PARSING DE LA SPÉCIFICATION OPENAPI ===
        self.logger.info("Parsing OpenAPI specification to HTTP routes...")
        http_routes = parse_openapi_to_http_routes(openapi_spec)
        self.logger.info(
            f"Successfully parsed {len(http_routes)} HTTP routes from OpenAPI specification"
        )

        # === MODIFICATION DES LIMITES DE PAGINATION ===
        # Limite la taille des pages pour les outils de listing à 25 éléments maximum
        # Cela s'applique aux outils: list_all_structures, list_all_services, search_services
        self.logger.info("Applying pagination limits to data-listing endpoints...")
        openapi_spec = self._limit_page_size(openapi_spec, max_size=50)

        return openapi_spec, http_routes

    def _limit_page_size(self, spec: dict, max_size: int = 50) -> dict:
        """
        Modifie la spécification OpenAPI pour limiter la taille des pages.

        Cette méthode parcourt les points de terminaison pertinents et ajuste le paramètre
        'size' pour qu'il ait une valeur maximale et par défaut de `max_size`. Cela permet
        d'éviter que les LLMs demandent des résultats trop volumineux qui pourraient
        dépasser les limites de contexte ou ralentir les réponses.

        Args:
            spec: Le dictionnaire de la spécification OpenAPI à modifier.
            max_size: La taille maximale à définir pour les résultats paginés (défaut: 25).

        Returns:
            dict: Le dictionnaire de la spécification modifié avec les limites de page appliquées.
        """
        # Créer une copie profonde pour éviter les effets de bord
        spec_copy = copy.deepcopy(spec)

        paths_to_modify = [
            "/api/v1/structures",
            "/api/v1/services",
            "/api/v1/search/services",
        ]

        self.logger.info(f"Applying page size limit (max_size={max_size}) to spec...")

        for path in paths_to_modify:
            if path in spec_copy["paths"] and "get" in spec_copy["paths"][path]:
                params = spec_copy["paths"][path]["get"].get("parameters", [])
                for param in params:
                    if param.get("name") == "size":
                        param["schema"]["maximum"] = max_size
                        param["schema"]["default"] = max_size
                        self.logger.info(
                            f"  - Limited 'size' parameter for endpoint: GET {path}"
                        )

        return spec_copy
