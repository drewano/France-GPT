"""
Configuration des mappings des outils MCP.

Ce module centralise la configuration des noms d'outils MCP personnalisés
pour l'API Data Inclusion. Il mappe les operation_ids OpenAPI vers des noms
d'outils plus conviviaux et lisibles par les LLMs.
"""

# Mapping des noms d'opérations OpenAPI vers des noms d'outils MCP plus conviviaux
# Note: Noms courts pour respecter la limite de 60 caractères de FastMCP
CUSTOM_MCP_TOOL_NAMES = {
    # Endpoints de Structures
    "list_structures_endpoint_api_v0_structures_get": "list_all_structures",
    "retrieve_structure_endpoint_api_v0_structures__source___id__get": "get_structure_details",
    # Endpoints de Sources
    "list_sources_endpoint_api_v0_sources_get": "list_all_sources",
    # Endpoints de Services
    "list_services_endpoint_api_v0_services_get": "list_all_services",
    "retrieve_service_endpoint_api_v0_services__source___id__get": "get_service_details",
    "search_services_endpoint_api_v0_search_services_get": "search_services",
    # Endpoints de Documentation
    "as_dict_list_api_v0_doc_labels_nationaux_get": "doc_list_labels_nationaux",
    "as_dict_list_api_v0_doc_thematiques_get": "doc_list_thematiques",
    "as_dict_list_api_v0_doc_typologies_services_get": "doc_list_typologies_services",
    "as_dict_list_api_v0_doc_frais_get": "doc_list_frais",
    "as_dict_list_api_v0_doc_profils_get": "doc_list_profils_publics",
    "as_dict_list_api_v0_doc_typologies_structures_get": "doc_list_typologies_structures",
    "as_dict_list_api_v0_doc_modes_accueil_get": "doc_list_modes_accueil",
    # Endpoints modes_orientation (NOMS RACCOURCIS pour respecter limite 60 caractères)
    "as_dict_list_api_v0_doc_modes_orientation_accompagnateur_get": "doc_modes_orient_accomp",
    "as_dict_list_api_v0_doc_modes_orientation_beneficiaire_get": "doc_modes_orient_benef",
}
