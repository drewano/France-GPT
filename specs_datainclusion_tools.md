### **Spécifications Techniques et Fonctionnelles des Outils MCP pour DataInclusion (Version Finale)**

#### **Philosophie de Conception "LLM-First"**

Ces outils sont conçus en suivant des principes visant à maximiser leur efficacité et leur simplicité d'utilisation par des modèles de langage (LLM) :

1.  **Simplification** : Les noms des outils et des paramètres sont clairs, en anglais et descriptifs pour une compréhension intuitive.
2.  **Flexibilité Intelligente** : Les concepts comme la localisation sont gérés de manière flexible, permettant au LLM d'utiliser le niveau de précision dont il dispose (coordonnées, code INSEE, ou texte libre).
3.  **Descriptions Riches** : Chaque outil et paramètre est doté d'une description détaillée (docstring) qui sert de documentation principale pour le LLM, lui expliquant quand et comment utiliser chaque fonctionnalité.
4.  **Consolidation Logique** : Les endpoints similaires, comme les différents référentiels de l'API, sont regroupés en un seul outil logique pour simplifier le choix du LLM.
5.  **Retours Structurés** : L'utilisation de modèles de données Pydantic garantit des réponses structurées, typées et prévisibles, que le LLM peut facilement analyser et utiliser.

---

### **1. Modèles de Données (Pydantic)**

Ces modèles définissent la structure des données retournées par les outils.

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Tuple

# --- Modèles pour les Structures ---

class StructureSummary(BaseModel):
    id: str = Field(description="Identifiant unique de la structure au sein de sa source.")
    source: str = Field(description="Source de la donnée (ex: 'dora', 'itou').")
    name: str = Field(description="Nom de la structure.")
    address: Optional[str] = Field(description="Adresse postale complète de la structure.")
    city: Optional[str] = Field(description="Commune où se situe la structure.")
    postal_code: Optional[str] = Field(description="Code postal de la structure.")
    themes: Optional[List[str]] = Field(description="Liste des thématiques principales couvertes par la structure.")

class StructureDetails(StructureSummary):
    description: Optional[str] = Field(description="Description détaillée de la structure.")
    phone: Optional[str] = Field(description="Numéro de téléphone de contact.")
    email: Optional[str] = Field(description="Adresse e-mail de contact.")
    website: Optional[str] = Field(description="URL du site web de la structure.")
    opening_hours: Optional[str] = Field(description="Horaires d'ouverture au format OpenStreetMap.")
    accessibility_url: Optional[str] = Field(description="Lien vers la page Acceslibre sur l'accessibilité du lieu.")

# --- Modèles pour les Services ---

class ServiceSummary(BaseModel):
    id: str = Field(description="Identifiant unique du service au sein de sa source.")
    source: str = Field(description="Source de la donnée.")
    name: str = Field(description="Nom du service.")
    themes: Optional[List[str]] = Field(description="Liste des thématiques associées au service.")
    structure_id: str = Field(description="Identifiant de la structure qui propose ce service.")

class SearchedService(ServiceSummary):
    distance_meters: Optional[int] = Field(description="Distance en mètres par rapport au point de recherche, si applicable.")
    structure_details: StructureSummary = Field(description="Informations de base sur la structure qui propose le service.")

class ServiceDetails(ServiceSummary):
    description: Optional[str] = Field(description="Description détaillée du service.")
    reception_modes: Optional[List[str]] = Field(description="Modes d'accueil (ex: 'en-presentiel', 'a-distance').")
    costs: Optional[List[str]] = Field(description="Frais associés au service (ex: 'gratuit').")
    target_audience: Optional[List[str]] = Field(description="Publics cibles du service.")
    mobilization_modes: Optional[List[str]] = Field(description="Comment mobiliser ou accéder au service.")

# --- Modèles pour les Référentiels ---

class ReferenceItem(BaseModel):
    value: str = Field(description="La valeur technique ou le 'slug' de l'entrée.")
    label: str = Field(description="Le libellé lisible par un humain.")
    description: Optional[str] = Field(description="Description additionnelle de l'entrée, si disponible.")
```

---

### **2. Outils MCP**

#### **Groupe 1 : Recherche et Listing**

##### **`search_services`**

*   **Spécification Fonctionnelle (Docstring)** :
    ```python
    """
    Recherche des services d'inclusion sociale et professionnelle à proximité d'un lieu en France.
    Les résultats sont triés par distance croissante.
    Utilisez cet outil pour répondre à des questions géolocalisées.
    Fournissez UN SEUL des paramètres de localisation suivants, du plus précis au moins précis : `location_lat_lon`, `location_insee_code`, ou `location_text`.
    Pour des recherches non géographiques, utilisez 'list_all_services'.
    """
    ```
*   **Spécification Technique (Signature)** :
    ```python
    from typing import Optional, List, Tuple
    
    @mcp.tool
    async def search_services(
        location_text: Optional[str] = Field(default=None, description="Une adresse, un code postal ou un nom de ville. À utiliser si des informations plus précises ne sont pas disponibles."),
        location_insee_code: Optional[str] = Field(default=None, description="Le code INSEE à 5 chiffres d'une commune. À privilégier pour une recherche précise par ville."),
        location_lat_lon: Optional[Tuple[float, float]] = Field(default=None, description="Un tuple de (latitude, longitude) pour la recherche la plus précise."),
        themes: Optional[List[str]] = Field(default=None, description="Liste de thématiques pour filtrer. Utiliser 'get_reference_data' pour voir les options."),
        target_audience: Optional[List[str]] = Field(default=None, description="Liste des publics cibles pour filtrer. Utiliser 'get_reference_data' pour voir les options."),
        limit: int = Field(default=10, description="Nombre maximum de résultats à retourner.")
    ) -> List[SearchedService]:
    ```
*   **Endpoint API Mappé** : `GET /api/v1/search/services`
*   **Exemple d'utilisation LLM** :
    *   *Utilisateur :* "Trouve des services d'aide au logement près de la Tour Eiffel."
    *   *LLM (interne) :* "La Tour Eiffel est à (48.8584, 2.2945). Je vais utiliser les coordonnées."
    *   *LLM décide d'appeler :* `search_services(location_lat_lon=(48.8584, 2.2945), themes=["logement-hebergement"])`

##### **`list_all_services`**

*   **Spécification Fonctionnelle (Docstring)** :
    ```python
    """
    Liste les services d'inclusion disponibles en France, avec des options de filtrage non géographiques.
    Utilisez cet outil pour des recherches larges ou basées sur des critères spécifiques comme les thématiques, les frais ou les publics cibles, sans contrainte de lieu.
    Pour une recherche basée sur la localisation, préférez l'outil 'search_services'.
    """
    ```
*   **Spécification Technique (Signature)** :
    ```python
    @mcp.tool
    async def list_all_services(
        themes: Optional[List[str]] = Field(default=None, description="Filtre par thématiques. Utiliser 'get_reference_data' pour voir les options."),
        costs: Optional[List[str]] = Field(default=None, description="Filtre par type de frais (ex: 'gratuit'). Utiliser 'get_reference_data' pour voir les options."),
        target_audience: Optional[List[str]] = Field(default=None, description="Filtre par publics cibles. Utiliser 'get_reference_data' pour voir les options."),
        limit: int = Field(default=20, description="Nombre maximum de résultats à retourner.")
    ) -> List[ServiceSummary]:
    ```
*   **Endpoint API Mappé** : `GET /api/v1/services`
*   **Exemple d'utilisation LLM** :
    *   *Utilisateur :* "Quels sont les services gratuits disponibles pour la création d'entreprise ?"
    *   *LLM décide d'appeler :* `list_all_services(themes=["creation-activite"], costs=["gratuit"])`

##### **`list_all_structures`**

*   **Spécification Fonctionnelle (Docstring)** :
    ```python
    """
    Liste les structures d'inclusion en France. Peut être filtré par localisation (nom de commune, de département ou de région) ou par réseau porteur.
    Utilisez cet outil pour trouver des organisations spécifiques ou pour explorer les structures dans une zone administrative donnée.
    """
    ```
*   **Spécification Technique (Signature)** :
    ```python
    @mcp.tool
    async def list_all_structures(
        location: Optional[str] = Field(default=None, description="Un nom de région, de département ou de commune pour filtrer les structures."),
        network: Optional[str] = Field(default=None, description="Nom d'un réseau porteur pour filtrer. Utiliser 'get_reference_data' pour voir les options."),
        limit: int = Field(default=20, description="Nombre maximum de résultats à retourner.")
    ) -> List[StructureSummary]:
    ```
*   **Endpoint API Mappé** : `GET /api/v1/structures`
*   **Exemple d'utilisation LLM** :
    *   *Utilisateur :* "Liste-moi les Missions Locales en Île-de-France."
    *   *LLM décide d'appeler :* `list_all_structures(location="Île-de-France", network="mission-locale")`

---

#### **Groupe 2 : Détails Spécifiques**

##### **`get_service_details`**

*   **Spécification Fonctionnelle (Docstring)** :
    ```python
    """
    Récupère les informations détaillées d'un service spécifique à partir de son identifiant et de sa source.
    Utilisez cet outil après avoir identifié un service via 'search_services' ou 'list_all_services' pour obtenir plus d'informations comme la description complète, les conditions d'accès ou les modes de mobilisation.
    """
    ```
*   **Spécification Technique (Signature)** :
    ```python
    @mcp.tool
    async def get_service_details(
        source: str = Field(description="La source du service (ex: 'dora')."),
        service_id: str = Field(description="L'identifiant unique du service.")
    ) -> ServiceDetails:
    ```
*   **Endpoint API Mappé** : `GET /api/v1/services/{source}/{id}`
*   **Exemple d'utilisation LLM** :
    *   *LLM (après un appel à `search_services`) :* "J'ai trouvé un service nommé 'Atelier CV' avec l'ID '123' de la source 'dora'. Voulez-vous plus de détails ?"
    *   *Utilisateur :* "Oui"
    *   *LLM décide d'appeler :* `get_service_details(source="dora", service_id="123")`

##### **`get_structure_details`**

*   **Spécification Fonctionnelle (Docstring)** :
    ```python
    """
    Récupère les informations détaillées d'une structure spécifique à partir de son identifiant et de sa source.
    Utilisez cet outil après avoir identifié une structure via 'list_all_structures' pour obtenir des informations complètes comme la description, les contacts et les horaires.
    """
    ```
*   **Spécification Technique (Signature)** :
    ```python
    @mcp.tool
    async def get_structure_details(
        source: str = Field(description="La source de la structure (ex: 'dora')."),
        structure_id: str = Field(description="L'identifiant unique de la structure.")
    ) -> StructureDetails:
    ```
*   **Endpoint API Mappé** : `GET /api/v1/structures/{source}/{id}`
*   **Exemple d'utilisation LLM** :
    *   *LLM (après `list_all_structures`) :* "La structure 'MJC de la Ville' (ID 'abc', source 'itou') semble pertinente. Voulez-vous ses coordonnées ?"
    *   *Utilisateur :* "Oui, merci."
    *   *LLM décide d'appeler :* `get_structure_details(source="itou", structure_id="abc")`

---

#### **Groupe 3 : Données de Référence**

##### **`get_reference_data`**

*   **Spécification Fonctionnelle (Docstring)** :
    ```python
    """
    Récupère les valeurs possibles pour les différentes catégories de filtres utilisées dans les autres outils.
    Utilisez cet outil pour savoir quelles options sont disponibles pour les paramètres 'themes', 'costs', 'target_audience', 'networks', etc. des outils de recherche.
    """
    ```
*   **Spécification Technique (Signature)** :
    ```python
    from typing import Literal
    
    @mcp.tool
    async def get_reference_data(
        category: Literal[
            "themes", "costs", "reception_modes",
            "mobilization_modes", "mobilizing_persons",
            "target_audience", "networks", "service_types"
        ] = Field(description="La catégorie de référentiel à récupérer.")
    ) -> List[ReferenceItem]:
    ```
*   **Endpoints API Mappés** :
    *   `themes` -> `GET /api/v1/doc/thematiques`
    *   `costs` -> `GET /api/v1/doc/frais`
    *   `reception_modes` -> `GET /api/v1/doc/modes-accueil`
    *   etc.
*   **Exemple d'utilisation LLM** :
    *   *Utilisateur :* "Quels types de publics peuvent être ciblés par les services ?"
    *   *LLM décide d'appeler :* `get_reference_data(category="target_audience")`

---

### **3. Notes d'Implémentation**

*   **Gestion de la Localisation (`search_services`)** : L'implémentation de cet outil doit gérer la priorité des paramètres de localisation :
    1.  Si `location_lat_lon` est fourni, utiliser les paramètres `lat` et `lon` de l'API DataInclusion.
    2.  Sinon, si `location_insee_code` est fourni, utiliser le paramètre `code_commune`.
    3.  Sinon, si `location_text` est fourni, faire un appel à une API de géocodage externe (comme `geo.api.gouv.fr`) pour obtenir un `code_commune`, puis appeler l'API DataInclusion.
    4.  Si aucun paramètre de localisation n'est fourni, retourner une erreur indiquant qu'un lieu est requis.
*   **Mapping des Référentiels (`get_reference_data`)** : La fonction implémentant cet outil doit contenir une logique de mapping (ex: `match/case`) qui fait correspondre la `category` reçue à l'endpoint `/api/v1/doc/...` approprié.
*   **Gestion des Erreurs** : Si un `service_id` ou `structure_id` n'est pas trouvé, les outils de détail doivent retourner une erreur claire ou `None` pour indiquer que l'élément n'existe pas, plutôt que de lever une exception non gérée. De même, les outils de listing doivent retourner une liste vide si aucun résultat n'est trouvé.