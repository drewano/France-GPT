from pydantic import BaseModel, Field
from typing import Optional, List

# --- Modèles pour les Structures ---

class StructureSummary(BaseModel):
    id: str = Field(description="Identifiant unique de la structure au sein de sa source.")
    source: str = Field(description="Source de la donnée (ex: 'dora', 'itou').")
    name: str = Field(alias='nom', description="Nom de la structure.")
    address: Optional[str] = Field(alias='adresse', description="Adresse postale complète de la structure.")
    city: Optional[str] = Field(alias='commune', description="Commune où se situe la structure.")
    postal_code: Optional[str] = Field(alias='code_postal', description="Code postal de la structure.")
    themes: Optional[List[str]] = Field(alias='thematiques', description="Liste des thématiques principales couvertes par la structure.")

    class Config:
        populate_by_name = True

class StructureDetails(StructureSummary):
    description: Optional[str] = Field(description="Description détaillée de la structure.")
    phone: Optional[str] = Field(alias='telephone', description="Numéro de téléphone de contact.")
    email: Optional[str] = Field(alias='courriel', description="Adresse e-mail de contact.")
    website: Optional[str] = Field(alias='site_web', description="URL du site web de la structure.")
    opening_hours: Optional[str] = Field(alias='horaires_accueil', description="Horaires d'ouverture au format OpenStreetMap.")
    accessibility_url: Optional[str] = Field(alias='accessibilite_lieu', description="Lien vers la page Acceslibre sur l'accessibilité du lieu.")

    class Config:
        populate_by_name = True

# --- Modèles pour les Services ---

class ServiceSummary(BaseModel):
    id: str = Field(description="Identifiant unique du service au sein de sa source.")
    source: str = Field(description="Source de la donnée.")
    name: str = Field(alias='nom', description="Nom du service.")
    themes: Optional[List[str]] = Field(alias='thematiques', description="Liste des thématiques associées au service.")
    structure_id: Optional[str] = Field(description="Identifiant de la structure qui propose ce service.")

    class Config:
        populate_by_name = True

class SearchedService(ServiceSummary):
    distance_meters: Optional[int] = Field(alias='distance', description="Distance en mètres par rapport au point de recherche, si applicable.")
    structure_details: Optional[StructureSummary] = Field(alias='structure', description="Informations de base sur la structure qui propose le service.")

    class Config:
        populate_by_name = True

class ServiceDetails(ServiceSummary):
    description: Optional[str] = Field(description="Description détaillée du service.")
    reception_modes: Optional[List[str]] = Field(alias='modes_accueil', description="Modes d'accueil (ex: 'en-presentiel', 'a-distance').")
    costs: Optional[List[str]] = Field(alias='frais', description="Frais associés au service (ex: 'gratuit').")
    target_audience: Optional[List[str]] = Field(alias='publics', description="Publics cibles du service.")
    mobilization_modes: Optional[List[str]] = Field(alias='modes_mobilisation', description="Comment mobiliser ou accéder au service.")

    class Config:
        populate_by_name = True

# --- Modèles pour les Référentiels ---

class ReferenceItem(BaseModel):
    value: str = Field(description="La valeur technique ou le 'slug' de l'entrée.")
    label: str = Field(description="Le libellé lisible par un humain.")
    description: Optional[str] = Field(description="Description additionnelle de l'entrée, si disponible.")