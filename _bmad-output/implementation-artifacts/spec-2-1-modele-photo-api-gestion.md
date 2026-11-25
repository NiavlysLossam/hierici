---
title: 'Story 2.1: Modèle de Données Photo et API de Gestion'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Les contributeurs territoriaux n'ont actuellement aucun modèle de données ni API pour enregistrer, consulter, modifier et archiver des photographies historiques géoréférencées dans leur territoire.

**Approach:** Définir le modèle SQLAlchemy `Photo` avec colonne géométrique PostGIS (WGS84 EPSG:4326), les schémas Pydantic de validation (brouillon souple vs publication exigeant les coordonnées GPS), et les endpoints REST d'administration `/api/v1/admin/photos` cloisonnés par territoire avec suppression synchronisée des médias stockés.

## Boundaries & Constraints

**Always:**
- Chaque photo est rattachée à un `territory_id` non nul. Les contributeurs ne peuvent accéder qu'aux photos de leur territoire.
- L'azimut (`bearing`) est un entier valide `0 <= bearing <= 359`. Le champ de vision angulaire (`field_of_view`) a pour valeur par défaut 60°.
- Si le statut de la photo est `published`, les coordonnées géographiques (`latitude` et `longitude`) sont obligatoires. En mode `draft`, elles sont optionnelles.
- La suppression d'une photo `DELETE /api/v1/admin/photos/{id}` supprime la ligne en base de données et déclenche la suppression physique de tous les fichiers médias associés via le `StorageDriver`.
- Les réponses de l'API suivent la convention `snake_case` et les erreurs utilisent l'enveloppe RFC 7807 Problem Details.

**Never:**
- Aucune fuite d'enregistrements d'un territoire vers un autre dans les endpoints de consultation.
- Pas de suppression de photos d'un autre territoire par un contributeur territorial.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Création brouillon sans GPS | `POST /admin/photos` avec `title`, `status='draft'` | `HTTP 201 Created`, fiche persistée avec `location=None` | N/A |
| Publication avec coordonnées | `POST /admin/photos` avec `title`, `status='published'`, `latitude=43.12`, `longitude=5.93` | `HTTP 201 Created`, geometry Point(5.93, 43.12) créée | N/A |
| Publication sans coordonnées | `POST /admin/photos` avec `status='published'` sans latitude/longitude | `HTTP 422 Unprocessable Entity` | Erreur explicite : coordonnées requises pour publication |
| Azimut hors bornes (<0 ou >=360) | `bearing=365` | `HTTP 422 Unprocessable Entity` | Erreur de validation de l'azimut |
| Liste filtrée par territoire | `GET /admin/photos` pour un contributeur du Territoire A | Ne renvoie que les photos avec `territory_id == A` | N/A |
| Accès fiche d'un autre territoire | `GET /admin/photos/{id_B}` par contributeur A | `HTTP 404 Not Found` | RFC 7807 `PHOTO_NOT_FOUND` |
| Suppression avec fichiers médias | `DELETE /admin/photos/{id}` sur photo ayant des chemins d'images | Photo supprimée et `StorageDriver.delete()` appelé sur chaque fichier | `HTTP 204 No Content` |

</frozen-after-approval>

## Code Map

- `backend/app/models/photo.py` -- Modèle SQLAlchemy `Photo` et enum `PhotoStatus` (nouveau fichier).
- `backend/app/schemas/photo.py` -- Schémas Pydantic `PhotoCreate`, `PhotoUpdate`, `PhotoRead`, `PhotoListResponse` (nouveau fichier).
- `backend/app/api/v1/admin/photos.py` -- Router FastAPI pour CRUD `/api/v1/admin/photos` (nouveau fichier).
- `backend/app/api/v1/__init__.py` -- Montage du sous-routeur photos dans `api_v1_router`.
- `backend/app/core/init_db.py` -- Importation de `Photo` pour l'enregistrement des métadonnées SQLAlchemy.
- `backend/tests/test_photos_admin.py` -- Tests unitaires et d'intégration de l'API de gestion photo (nouveau fichier).

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/photo.py` -- Créer le modèle `Photo` avec PostGIS Point, métadonnées d'archives, statuts `draft`/`published`, et contraintes de clés étrangères.
- [x] `backend/app/schemas/photo.py` -- Définir la validation Pydantic avec contrainte conditionnelle de coordonnées GPS lors de la publication et validation de l'azimut 0-359°.
- [x] `backend/app/api/v1/admin/photos.py` -- Implémenter les routes CRUD admin (création, consultation paginée, mise à jour, suppression avec nettoyage `StorageDriver`).
- [x] `backend/app/api/v1/__init__.py` -- Inclure le routeur photos d'administration.
- [x] `backend/app/core/init_db.py` -- Intégrer le modèle `Photo` au cycle d'initialisation de la base de données.
- [x] `backend/tests/test_photos_admin.py` -- Écrire la suite de tests automatisés couvrant tous les cas de la matrice I/O.

**Acceptance Criteria:**
- Given un contributeur authentifié, When il crée une photo `draft` avec seulement le titre, Then la photo est enregistrée avec succès et rattachée à son territoire.
- Given une photo avec le statut `published`, When la requête ne fournit pas de coordonnées GPS, Then l'API rejette la création avec une erreur 422.
- Given un contributeur du territoire Toulon, When il appelle `GET /api/v1/admin/photos`, Then aucune photo d'un autre territoire n'apparaît dans la liste.
- Given une photo existante avec des fichiers stockés, When le contributeur appelle `DELETE /api/v1/admin/photos/{id}`, Then la photo est retirée de la base et `StorageDriver.delete()` est exécuté pour chaque fichier associé.

## Implementation Notes

## Spec Change Log

## Review Triage Log

- `patch` (`blind-hunter+edge-case-hunter`): Ligne de code morte avec variable non formatée dans l'assignation de la géométrie de `update_photo` -> Corrigé par suppression de la ligne redondante.
- `patch` (`edge-case-hunter`): Inversion de la suppression physique et de la suppression en base dans `delete_photo` -> Corrigé en committant la suppression DB avant la purge des fichiers via le `StorageDriver`.
- `patch` (`edge-case-hunter`): Absence de validation de paire pour les coordonnées lors de la mise à jour d'un brouillon -> Corrigé en levant une erreur 422 si une seule coordonnée est modifiée.
- `patch` (`blind-hunter`): Pagination non déterministe sur `created_at` seul -> Corrigé par ajout de `Photo.id.desc()` comme second critère de tri.
- `patch` (`verification-gap`): Couverture incomplète pour la consultation unitaire d'une photo, les filtres de recherche et le rôle superadmin -> Corrigé par l'ajout de 3 tests d'intégration dans `test_photos_admin.py`.
- `false` (`blind-hunter`): Absence de migration Alembic -> Rejeté : la V1 s'appuie sur `init_db.py` et `Base.metadata.create_all` pour l'amorçage initial conteneurisé.

## Verification

**Commands:**
- `python3 -m py_compile backend/app/models/photo.py backend/app/schemas/photo.py backend/app/api/v1/admin/photos.py backend/tests/test_photos_admin.py` -- expected: Compilation sans erreur syntaxique.
- `docker compose exec hierici-backend pytest backend/tests/test_photos_admin.py` -- expected: Tous les tests passent au vert (100% pass).

