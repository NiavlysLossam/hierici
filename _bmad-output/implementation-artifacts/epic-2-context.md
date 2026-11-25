# Epic 2 Context: Ingestion & Géoréférencement Directionnel des Photos

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Permettre aux contributeurs de téléverser des photographies d'archives haute définition, de renseigner leur contexte documentaire rigoureux (cote, date, licence, auteur) et de définir précisément la position de prise de vue et l'azimut (orientation 0°–359°) via une interface cartographique interactive, afin de constituer le catalogue géolocalisé du patrimoine territorial.

## Stories

- Story 2.1: Modèle de Données Photo et API de Gestion (CRUD admin, cloisonnement par territoire, relations PostGIS)
- Story 2.2: Téléversement et Pipeline de Compression d'Images WebP (Pillow, 3 déclinaisons : original, display 2048px, thumb 400px, sanitisation EXIF)
- Story 2.3: Interface d'Administration de Saisie des Métadonnées d'Archives (formulaire documentaire, statut draft/published, validation)
- Story 2.4: Sélecteur Cartographique Interactif pour le Point GPS et l'Azimut (point de vue, boussole rotative 0-359°, cône vectoriel MapLibre/turf)

## Requirements & Constraints

- **Modèle de données géographique :** Coordonnées stockées en WGS84 (EPSG:4326) avec PostGIS sous forme de `Point(longitude, latitude)`.
- **Direction de vue :** Azimut (`bearing`) entier strict entre 0 et 359° (0° = Nord, 90° = Est). Ouverture angulaire (`field_of_view`) entier (défaut : 60°).
- **Cloisonnement multi-territoire :** Clé étrangère `territory_id` obligatoire sur chaque photo. Les contributeurs ne peuvent lire, créer, modifier ou supprimer que les photos de leur territoire actif.
- **Cycle de vie & Statuts :** `status` vaut `draft` (brouillon éditable, invisible en public) ou `published` (visible sur la carte publique). La publication exige des coordonnées géographiques valides.
- **Suppression en cascade :** La suppression d'une fiche photo en base déclenche la suppression physique de tous ses fichiers médias associés (`original`, `display`, `thumb`) via le `StorageDriver`.
- **API d'administration :** Routes `/api/v1/admin/photos` protégées par authentification JWT avec contrôle de rôle (`contributor` ou `superadmin`).

## Technical Decisions

- **Table PostgreSQL / PostGIS `photos` :**
  - `id`: UUID (clé primaire)
  - `territory_id`: UUID ForeignKey vers `territories.id`
  - `title`: String obligatoire
  - `description`: Text optionnel
  - `photographer`: String optionnel
  - `year`: Integer optionnel (ex: 1912)
  - `date_exact`: String optionnel (ex: "1912-05-14")
  - `period_label`: String optionnel (ex: "Belle Époque")
  - `archive_source`: String optionnel (ex: "Archives Municipales de Toulon")
  - `archive_reference`: String optionnel (cote d'inventaire, ex: "21Fi45")
  - `source_url`: String optionnel (URL de la notice source)
  - `license`: String (ex: "Domaine Public", "Licence Ouverte", "Tous droits réservés")
  - `location`: Geometry(Point, srid=4326) optionnel si draft, obligatoire si published
  - `latitude`: Float optionnel (dérivé/pratique)
  - `longitude`: Float optionnel (dérivé/pratique)
  - `bearing`: Integer optionnel (0–359)
  - `field_of_view`: Integer (défaut: 60)
  - `image_original_path`: String optionnel
  - `image_display_path`: String optionnel
  - `image_thumb_path`: String optionnel
  - `status`: Enum (`draft`, `published`) défaut: `draft`
  - `created_by_id`: UUID ForeignKey vers `users.id`
  - `created_at`: DateTime UTC
  - `updated_at`: DateTime UTC
- **GeoJSON & JSON conventions :** Standard `snake_case` pour les réponses d'API de gestion admin, et standard GeoJSON pour les formats géométriques.

## UX & Interaction Patterns

- **Validation souple pour le brouillon :** Permettre l'enregistrement partiel d'une photo en mode `draft` sans forcer la saisie immédiate des coordonnées.
- **Blocage à la publication :** Interdiction de basculer en `published` sans coordonnées GPS définies.

## Cross-Story Dependencies

- Story 2.1 pose le modèle SQLAlchemy, les migrations/tables, les schémas Pydantic et l'API CRUD d'administration.
- Story 2.2 ajoutera le traitement d'image Pillow et rattachera les chemins d'images à la fiche photo.
- Story 2.3 et 2.4 fourniront les interfaces Vue 3 (formulaire et carte interactive d'orientation).

