"""Définitions détaillées des outils pour l'API Légifrance.

Ce module centralise les descriptions, exemples et transformations d'arguments
pour les outils MCP générés à partir de l'API Légifrance.

L'objectif est de fournir des métadonnées riches et précises pour que les LLMs
puissent utiliser ces outils de manière efficace et correcte."""

LEGIFRANCE_TOOL_DEFINITIONS = {
    "rechercher_dans_legifrance": {
        "description": """Recherche des textes juridiques (lois, décrets, codes, etc.) dans l'ensemble de la base Légifrance.
Idéal pour une recherche générale par mots-clés.
Paramètres:
    - fond: Le fond juridique où chercher ('ALL', 'CODE', 'CONVENTION', 'JORF', 'JURI').
    - pageNumber: Numéro de la page de résultats.
    - pageSize: Nombre de résultats par page (max 100).
    - sort: Ordre de tri ('SIGNATURE_DATE_DESC', 'SIGNATURE_DATE_ASC', 'RELEVANCE').
    - operator: Opérateur pour les mots-clés ('AND', 'OR').
    - searchedText: Mots-clés de la recherche.
Exemples:
    - Chercher "garde à vue" dans tous les fonds: {fond="ALL", searchedText="garde à vue"}
    - Chercher les derniers textes sur le "télétravail": {fond="ALL", searchedText="télétravail", sort="SIGNATURE_DATE_DESC"}""",
        "arguments": {
            "fond": {
                "name": "fond",
                "description": "Le fond juridique où effectuer la recherche.",
            },
            "recherche": {
                "name": "recherche",
                "description": "Objet contenant les paramètres de recherche.",
                "hide": True,
            },
        },
    },
    "consulter_article_par_id": {
        "description": """Consulte le contenu d'un article de loi ou de code spécifique à partir de son identifiant unique (CID).
Paramètre:
    - id: L'identifiant unique de l'article (ex: 'LEGIARTI000038814944').
Exemple:
    - Consulter l'article avec l'ID 'LEGIARTI000038814944': {id="LEGIARTI000038814944"}""",
        "arguments": {
            "id": {
                "name": "id",
                "description": "L'identifiant unique (CID) de l'article à consulter.",
            },
        },
    },
    "consulter_table_des_matieres": {
        "description": """Affiche la table des matières d'un texte législatif (loi, code, etc.) à partir de son identifiant de texte.
Utile pour comprendre la structure d'un texte.
Paramètre:
    - textId: L'identifiant unique du texte (ex: 'LEGITEXT000006070721' pour le Code civil).
Exemple:
    - Obtenir la table des matières du Code civil: {textId="LEGITEXT000006070721"}""",
        "arguments": {
            "textId": {
                "name": "textId",
                "description": "L'identifiant unique (CID) du texte dont on veut la table des matières.",
            },
        },
    },
    "rechercher_jurisprudence": {
        "description": """Recherche des décisions de jurisprudence dans la base JURI (judiciaire) ou JORF (administrative).
Paramètres:
    - searchedString: Termes de recherche libre dans les décisions.
    - textId: Identifiant du texte.
Exemples:
    - Rechercher la décision avec l'ID 'JURITEXT000037999394': {textId="JURITEXT000037999394"}""",
        "arguments": {
            "searchedString": {"name": "searchedString", "description": "Termes de recherche libre dans les décisions."},
            "textId": {"name": "textId", "description": "Identifiant du texte."},
        },
    },
    "consulter_section_texte_legi": {
        "description": """Consulte une section (ou une partie) d'un texte législatif (LEGI) à partir de son identifiant.
Paramètres:
    - date: Date de consultation.
    - searchedString: Texte de la recherche ayant aboutie à la consultation du texte.
    - textId: Chronical ID du texte.
Exemple:
    - Consulter une section spécifique d'un code: {textId="LEGITEXT000006075116", date="2021-04-15T00:00:00.000Z"}""",
        "arguments": {
            "date": {
                "name": "date",
                "description": "Date de consultation.",
            },
            "searchedString": {
                "name": "searchedString",
                "description": "Texte de la recherche ayant aboutie à la consultation du texte.",
            },
            "textId": {
                "name": "textId",
                "description": "Chronical ID du texte.",
            },
        },
    },
}