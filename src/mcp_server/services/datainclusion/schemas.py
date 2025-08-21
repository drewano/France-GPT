# src/mcp_server/services/datainclusion/schemas.py
"""
Ce fichier définit les schémas de données Pydantic pour l'API Data Inclusion.
Ces modèles sont utilisés pour valider et structurer les données reçues de l'API
et retournées par les outils du serveur FastMCP.
"""
# --- Partie 1: Définition des Schémas de Données (schemas.py) ---

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# --- Modèles pour les Structures ---


class StructureSummary(BaseModel):
    """Informations de base sur une structure d'inclusion."""

    id: str = Field(
        description="Identifiant unique de la structure au sein de sa source."
    )
    source: str = Field(description="Source de la donnée (ex: 'dora', 'itou').")
    name: str = Field(alias="nom", description="Nom de la structure.")
    address: Optional[str] = Field(
        default=None,
        alias="adresse",
        description="Adresse postale complète de la structure.",
    )
    city: Optional[str] = Field(
        default=None, alias="commune", description="Commune où se situe la structure."
    )
    postal_code: Optional[str] = Field(
        default=None, alias="code_postal", description="Code postal de la structure."
    )
    themes: Optional[List[str]] = Field(
        default=None,
        alias="thematiques",
        description="Liste des thématiques principales couvertes par la structure.",
    )

    model_config = ConfigDict(populate_by_name=True)


class StructureDetails(StructureSummary):
    """Informations détaillées sur une structure d'inclusion."""

    description: Optional[str] = Field(
        default=None, description="Description détaillée de la structure."
    )
    phone: Optional[str] = Field(
        default=None, alias="telephone", description="Numéro de téléphone de contact."
    )
    email: Optional[str] = Field(
        default=None, alias="courriel", description="Adresse e-mail de contact."
    )
    website: Optional[str] = Field(
        default=None, alias="site_web", description="URL du site web de la structure."
    )
    opening_hours: Optional[str] = Field(
        default=None,
        alias="horaires_accueil",
        description="Horaires d'ouverture au format OpenStreetMap.",
    )
    accessibility_url: Optional[str] = Field(
        default=None,
        alias="accessibilite_lieu",
        description="Lien vers la page Acceslibre sur l'accessibilité du lieu.",
    )

    model_config = ConfigDict(populate_by_name=True)


# --- Modèles pour les Services ---


class ServiceSummary(BaseModel):
    """Informations de base sur un service d'inclusion."""

    id: str = Field(description="Identifiant unique du service au sein de sa source.")
    source: str = Field(description="Source de la donnée.")
    name: str = Field(alias="nom", description="Nom du service.")
    themes: Optional[List[str]] = Field(
        default=None,
        alias="thematiques",
        description="Liste des thématiques associées au service.",
    )
    structure_id: Optional[str] = Field(
        default=None, description="Identifiant de la structure qui propose ce service."
    )

    model_config = ConfigDict(populate_by_name=True)


class ServiceDetails(ServiceSummary):
    """Informations détaillées sur un service d'inclusion."""

    description: Optional[str] = Field(
        default=None, description="Description détaillée du service."
    )
    reception_modes: Optional[List[str]] = Field(
        default=None,
        alias="modes_accueil",
        description="Modes d'accueil (ex: 'en-presentiel', 'a-distance').",
    )
    costs: Optional[str] = Field(
        default=None,
        alias="frais",
        description="Frais associés au service (ex: 'gratuit').",
    )
    target_audience: Optional[List[str]] = Field(
        default=None, alias="publics", description="Publics cibles du service."
    )
    mobilization_modes: Optional[List[str]] = Field(
        default=None,
        alias="modes_mobilisation",
        description="Comment mobiliser ou accéder au service.",
    )

    model_config = ConfigDict(populate_by_name=True)


class SearchedService(ServiceDetails):
    """Modèle pour un service retourné par une recherche, incluant la distance et les détails de la structure."""

    distance_meters: Optional[int] = Field(
        default=None,
        alias="distance",
        description="Distance en mètres par rapport au point de recherche, si applicable.",
    )
    structure_details: Optional[StructureSummary] = Field(
        default=None,
        alias="structure",
        description="Informations de base sur la structure qui propose le service.",
    )

    model_config = ConfigDict(populate_by_name=True)


# --- Modèles pour les Référentiels ---


class ReferenceItem(BaseModel):
    """Modèle pour un élément d'un référentiel (ex: thématiques, frais)."""

    value: str = Field(description="La valeur technique ou le 'slug' de l'entrée.")
    label: str = Field(description="Le libellé lisible par un humain.")
    description: Optional[str] = Field(
        default=None,
        description="Description additionnelle de l'entrée, si disponible.",
    )
