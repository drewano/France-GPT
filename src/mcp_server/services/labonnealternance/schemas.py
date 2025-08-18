# src/mcp_server/services/labonnealternance/schemas.py
"""
Ce fichier définit les schémas de données Pydantic pour l'API La Bonne Alternance.
Ces modèles sont utilisés pour valider et structurer les données reçues de l'API
et retournées par les outils du serveur FastMCP.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime


# --- Modèles utilitaires ---


class GeoJsonPoint(BaseModel):
    """Point géographique au format GeoJSON."""
    type: str = Field(default="Point", description="Type de géométrie.")
    coordinates: List[float] = Field(description="Coordonnées [longitude, latitude].")


class Adresse(BaseModel):
    """Adresse d'un lieu."""
    label: Optional[str] = Field(default=None, description="Libellé de l'adresse.")
    code_postal: Optional[str] = Field(default=None, description="Code postal.")
    commune: Optional[dict] = Field(default=None, description="Informations sur la commune.")
    departement: Optional[dict] = Field(default=None, description="Informations sur le département.")
    region: Optional[dict] = Field(default=None, description="Informations sur la région.")
    academie: Optional[dict] = Field(default=None, description="Informations sur l'académie.")


# --- Modèles pour les Offres d'Emploi ---


class JobIdentifier(BaseModel):
    """Identifiant d'une offre d'emploi."""
    partner_job_id: str = Field(description="Identifiant de l'offre dans le système d'information du partenaire.")
    id: Optional[str] = Field(default=None, description="Identifiant de l'offre d'emploi dans la base de données La bonne alternance.")
    partner_label: str = Field(description="Partenaire à l'origine de l'offre d'emploi.")


class JobWorkplaceDomain(BaseModel):
    """Domaine d'activité du lieu de travail."""
    idcc: Optional[Union[int, None]] = Field(default=None, description="Numéro de convention collective associé au SIRET.")
    opco: Optional[Union[str, None]] = Field(default=None, description="Opérateur de Compétences (OPCO) associé au SIRET.")
    naf: Optional[Union[dict, None]] = Field(default=None, description="Code NAF (secteur d'activité) associé au SIRET.")


class JobWorkplace(BaseModel):
    """Lieu de travail."""
    name: Optional[Union[str, None]] = Field(default=None, description="Nom de l'établissement (enseigne ou, à défaut, nom légal).")
    description: Optional[Union[str, None]] = Field(default=None, description="Description de l'employeur et/ou du département où sera exécuté le contrat.")
    website: Optional[Union[str, None]] = Field(default=None, description="Site web de l'entreprise.")
    siret: Optional[Union[str, None]] = Field(default=None, description="SIRET du lieu d'exécution du contrat.")
    location: Optional[dict] = Field(default=None, description="Adresse postale et géolocalisation rattachées au numéro SIRET de l'entreprise.")
    brand: Optional[Union[str, None]] = Field(default=None, description="Enseigne de l'établissement.")
    legal_name: Optional[Union[str, None]] = Field(default=None, description="Raison sociale de l'entreprise.")
    size: Optional[Union[str, None]] = Field(default=None, description="Effectif de l'entreprise, en nombre d'employés.")
    domain: Optional[JobWorkplaceDomain] = Field(default=None, description="Domaine d'activité du lieu de travail.")


class JobApply(BaseModel):
    """Informations de candidature."""
    phone: Optional[Union[str, None]] = Field(default=None, description="Numéro de téléphone du recruteur.")
    url: str = Field(description="URL de redirection vers le formulaire de candidature.")
    recipient_id: Optional[Union[str, None]] = Field(default=None, description="Identifiant à utiliser pour postuler à l'offre d'emploi.")


class JobContract(BaseModel):
    """Contrat de l'offre."""
    start: Optional[Union[str, None]] = Field(default=None, description="Date de début du contrat.")
    duration: Optional[Union[int, None]] = Field(default=None, description="Durée du contrat en mois.")
    type: List[str] = Field(description="Type de contrat (apprentissage et/ou professionnalisation).")
    remote: Optional[Union[str, None]] = Field(default=None, description="Mode de travail (sur site, à distance ou hybride).")


class JobOffer(BaseModel):
    """Détails de l'offre."""
    title: str = Field(description="Intitulé de l'offre d'emploi.")
    desired_skills: List[str] = Field(description="Les compétences ou qualités attendues pour le poste.")
    to_be_acquired_skills: List[str] = Field(description="Les compétences ou qualités à acquérir durant l'apprentissage.")
    access_conditions: List[str] = Field(description="Les conditions d'accès au métier.")
    opening_count: Union[int, float] = Field(description="Nombre de postes disponibles pour cette offre d'emploi.")
    publication: Optional[dict] = Field(default=None, description="Informations de publication de l'offre.")
    rome_codes: List[str] = Field(description="Code(s) ROME de l'offre.")
    description: str = Field(description="Description de l'offre d'emploi.")
    target_diploma: Optional[Union[dict, None]] = Field(default=None, description="Diplôme visé à l'issue des études.")
    status: str = Field(description="Statut de l'offre (cycle de vie).")


class JobOfferRead(BaseModel):
    """Offre d'emploi complète."""
    identifier: JobIdentifier = Field(description="Identifiant de l'offre.")
    workplace: JobWorkplace = Field(description="Lieu de travail.")
    apply: JobApply = Field(description="Informations de candidature.")
    contract: JobContract = Field(description="Contrat.")
    offer: JobOffer = Field(description="Détails de l'offre.")


class EmploiSummary(BaseModel):
    """Informations de base sur une offre d'emploi en alternance."""
    id: Optional[str] = Field(description="Identifiant unique de l'offre.")
    title: str = Field(description="Intitulé du poste.")
    company_name: Optional[str] = Field(description="Nom de l'entreprise.")
    location: Optional[str] = Field(description="Localisation de l'offre.")
    contract_type: List[str] = Field(description="Type de contrat.")


class EmploiDetails(EmploiSummary):
    """Informations détaillées sur une offre d'emploi en alternance."""
    description: Optional[str] = Field(default=None, description="Description complète du poste.")
    desired_skills: List[str] = Field(default=[], description="Compétences requises.")
    application_url: Optional[str] = Field(default=None, description="URL pour postuler.")
    start_date: Optional[str] = Field(default=None, description="Date de début du contrat.")


# --- Modèles pour les Formations ---


class FormationIdentifiant(BaseModel):
    """Identifiant d'une formation."""
    cle_ministere_educatif: str = Field(description="Identifiant unique de la formation sur le catalogue des formations en apprentissage.")


class FormationStatut(BaseModel):
    """Statut d'une formation."""
    catalogue: str = Field(description="Statut de la formation sur le catalogue.")


class OrganismeIdentifiant(BaseModel):
    """Identifiant d'un organisme."""
    uai: Optional[Union[str, None]] = Field(default=None, description="Numéro UAI de l'organisme.")
    siret: str = Field(description="Numéro SIRET de l'organisme.")


class OrganismeEtablissement(BaseModel):
    """Établissement d'un organisme."""
    siret: str = Field(description="Numéro SIRET de l'établissement.")
    ouvert: bool = Field(description="Établissement ouvert.")
    enseigne: Optional[Union[str, None]] = Field(default=None, description="Enseigne de l'établissement.")
    adresse: Optional[Union[Adresse, None]] = Field(default=None, description="Adresse de l'établissement.")
    geopoint: Optional[Union[GeoJsonPoint, None]] = Field(default=None, description="Coordonnées GPS de l'établissement.")
    creation: datetime = Field(description="Date de création de l'établissement.")
    fermeture: Optional[Union[datetime, None]] = Field(default=None, description="Date de fermeture de l'établissement.")


class OrganismeUniteLegale(BaseModel):
    """Unité légale d'un organisme."""
    siren: str = Field(description="Numéro SIREN de l'unité légale.")
    actif: bool = Field(description="Unité légale active.")
    raison_sociale: str = Field(description="Raison sociale de l'unité légale.")
    creation: datetime = Field(description="Date de création de l'unité légale.")
    cessation: Optional[Union[datetime, None]] = Field(default=None, description="Date de cessation de l'unité légale.")


class OrganismeRenseignementsSpecifiques(BaseModel):
    """Renseignements spécifiques d'un organisme."""
    qualiopi: bool = Field(description="Qualiopi.")
    numero_activite: Optional[Union[str, None]] = Field(default=None, description="Numéro d'activité.")


class OrganismeStatut(BaseModel):
    """Statut d'un organisme."""
    referentiel: str = Field(description="Statut de l'organisme dans le référentiel des organismes en apprentissage.")


class Organisme(BaseModel):
    """Organisme de formation."""
    identifiant: OrganismeIdentifiant = Field(description="Identifiant de l'organisme.")
    etablissement: OrganismeEtablissement = Field(description="Établissement de l'organisme.")
    unite_legale: OrganismeUniteLegale = Field(description="Unité légale de l'organisme.")
    renseignements_specifiques: OrganismeRenseignementsSpecifiques = Field(description="Renseignements spécifiques.")
    statut: OrganismeStatut = Field(description="Statut de l'organisme.")
    contacts: List[dict] = Field(description="Contacts de l'organisme.")


class CertificationIdentifiant(BaseModel):
    """Identifiant d'une certification."""
    cfd: Optional[Union[str, None]] = Field(default=None, description="Code Formation Diplôme (CFD) de la certification.")
    rncp: Optional[Union[str, None]] = Field(default=None, description="Code Répertoire National des Certifications Professionnelles (RNCP) de la certification.")
    rncp_anterieur_2019: Optional[Union[bool, None]] = Field(default=None, description="Identifie les certifications dont le code RNCP correspond à une fiche antérieure à la réforme de 2019.")


class CertificationIntituleCfd(BaseModel):
    """Intitulé CFD d'une certification."""
    long: str = Field(description="Intitulé long du diplôme.")
    court: str = Field(description="Intitulé court du diplôme.")


class CertificationIntitule(BaseModel):
    """Intitulé d'une certification."""
    cfd: Optional[Union[CertificationIntituleCfd, None]] = Field(default=None, description="Intitulés de la certification issue de la base centrale des nomenclatures (BCN).")
    niveau: Optional[dict] = Field(default=None, description="Niveau de qualification de la certification professionnelle.")
    rncp: Optional[Union[str, None]] = Field(default=None, description="Intitulé de la certification issue de France Compétences.")


class Certification(BaseModel):
    """Certification d'une formation."""
    identifiant: CertificationIdentifiant = Field(description="Identifiants de la certification.")
    intitule: CertificationIntitule = Field(description="Intitulé de la certification.")
    base_legale: Optional[dict] = Field(default=None, description="Dates de création et d'abrogation des diplômes crées par arrêtés.")
    blocs_competences: Optional[dict] = Field(default=None, description="Liste du (ou des) code (s) et intitulé(s) des blocs de compétences validés par la certification.")
    convention_collectives: Optional[dict] = Field(default=None, description="Liste(s) de la ou des convention(s) collective(s) rattachées à la certification.")
    domaines: Optional[dict] = Field(default=None, description="Domaines de la certification.")
    periode_validite: Optional[dict] = Field(default=None, description="Période de validité de la certification.")
    type: Optional[dict] = Field(default=None, description="Type de certification.")
    continuite: Optional[dict] = Field(default=None, description="Liste des couples CFD-RNCP assurant la continuité de la certification professionnelle.")


class FormationFormateur(BaseModel):
    """Formateur d'une formation."""
    organisme: Optional[Union[Organisme, None]] = Field(default=None, description="L'organisme de formation.")
    connu: bool = Field(description="Indique si le formateur est connu de l'API.")


class FormationResponsable(BaseModel):
    """Responsable d'une formation."""
    organisme: Optional[Union[Organisme, None]] = Field(default=None, description="L'organisme responsable.")
    connu: bool = Field(description="Indique si le responsable est connu de l'API.")


class FormationCertification(BaseModel):
    """Certification d'une formation."""
    valeur: Certification = Field(description="La certification de la formation.")
    connue: bool = Field(description="Indique si la certification est connue.")


class FormationLieu(BaseModel):
    """Lieu de la formation."""
    adresse: Adresse = Field(description="Adresse du lieu de formation.")
    geolocalisation: GeoJsonPoint = Field(description="Géolocalisation du lieu de formation.")
    precision: Optional[Union[float, None]] = Field(default=None, description="Précision de la géolocalisation du lieu de formation en mètres.")
    siret: Optional[Union[str, None]] = Field(default=None, description="Numéro SIRET du lieu de formation.")
    uai: Optional[Union[str, None]] = Field(default=None, description="Numéro UAI du lieu de formation.")


class FormationContact(BaseModel):
    """Contact pour la formation."""
    email: Optional[Union[str, None]] = Field(default=None, description="Email de contact de la formation.")
    telephone: Optional[Union[str, None]] = Field(default=None, description="Téléphone de contact de la formation.")


class FormationOnisep(BaseModel):
    """Informations ONISEP de la formation."""
    url: Optional[Union[str, None]] = Field(default=None)
    intitule: Optional[Union[str, None]] = Field(default=None)
    libelle_poursuite: Optional[Union[str, None]] = Field(default=None)
    lien_site_onisepfr: Optional[Union[str, None]] = Field(default=None)
    discipline: Optional[Union[str, None]] = Field(default=None)
    domaine_sousdomaine: Optional[Union[str, None]] = Field(default=None)


class FormationModalite(BaseModel):
    """Modalités de la formation."""
    entierement_a_distance: bool = Field(description="Indique si la formation est entièrement à distance.")
    duree_indicative: Union[int, float] = Field(description="Durée indicative de la formation.")
    annee_cycle: Optional[Union[int, None]] = Field(default=None, description="L'année de démarrage de la session de formation.")
    mef_10: Optional[Union[str, None]] = Field(default=None, description="Code MEF 10 de la formation.")


class FormationContenuEducatif(BaseModel):
    """Contenu éducatif de la formation."""
    contenu: str = Field(description="Contenu de la formation.")
    objectif: str = Field(description="Objectif de la formation.")


class FormationSession(BaseModel):
    """Session de formation."""
    debut: datetime = Field(description="Date de début de la session.")
    fin: datetime = Field(description="Date de fin de la session.")
    capacite: Optional[Union[Union[int, float], None]] = Field(default=None, description="Capacité de la session.")


class Formation(BaseModel):
    """Formation en alternance."""
    identifiant: FormationIdentifiant = Field(description="Identifiant de la formation.")
    statut: FormationStatut = Field(description="Statut de la formation.")
    formateur: FormationFormateur = Field(description="Formateur de la formation.")
    responsable: FormationResponsable = Field(description="Responsable de la formation.")
    certification: FormationCertification = Field(description="Certification de la formation.")
    lieu: FormationLieu = Field(description="Lieu où la formation est dispensée.")
    contact: FormationContact = Field(description="Coordonnées à utiliser pour contacter l'organisme.")
    onisep: FormationOnisep = Field(description="Informations lié à la formation issues de l'ONISEP.")
    modalite: FormationModalite = Field(description="Modalité de la formation.")
    contenu_educatif: FormationContenuEducatif = Field(description="Contenu éducatif de la formation.")
    sessions: List[FormationSession] = Field(description="Liste des sessions de formation.")


class FormationSummary(BaseModel):
    """Informations de base sur une formation en alternance."""
    id: str = Field(description="Identifiant unique de la formation.")
    title: Optional[str] = Field(description="Intitulé de la formation.")
    organisme_name: Optional[str] = Field(description="Nom de l'organisme formateur.")
    city: Optional[str] = Field(description="Ville de la formation.")


class FormationDetails(FormationSummary):
    """Informations détaillées sur une formation en alternance."""
    educational_content: Optional[str] = Field(default=None, description="Contenu pédagogique de la formation.")
    objective: Optional[str] = Field(default=None, description="Objectifs de la formation.")
    sessions: Optional[List[dict]] = Field(default=None, description="Liste des sessions de la formation.")