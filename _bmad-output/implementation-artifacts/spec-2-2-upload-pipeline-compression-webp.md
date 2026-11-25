---
title: 'Story 2.2: Téléversement et Pipeline de Compression d''Images WebP'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-2-context.md'
  - '_bmad-output/implementation-artifacts/spec-2-1-modele-photo-api-gestion.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Les archives photographiques numérisées sont souvent très lourdes (scans TIFF/JPEG jusqu'à 25 Mo). Les charger directement sur la carte et sur mobile sature la bande passante et dégrade l'expérience utilisateur, tandis qu'il est indispensable de conserver le fichier haute définition d'origine.

**Approach:** Créer un service de traitement d'images basé sur Pillow (`ImageService`) qui valide les fichiers (taille max 25 Mo, formats d'image autorisés), désinfecte les métadonnées EXIF, et produit automatiquement 3 déclinaisons optimisées (`original`, `display` WebP 2048px q85, `thumb` WebP 400px q80) enregistrées via le `StorageDriver` et associées à la fiche photo.

## Boundaries & Constraints

**Always:**
- Les fichiers dépassant 25 Mo ou les fichiers corrompus/non-images sont rejetés avec un code `HTTP 400 Bad Request` au format RFC 7807 (`FILE_TOO_LARGE`, `INVALID_IMAGE_FORMAT`).
- L'orientation EXIF est automatiquement redressée avant suppression des métadonnées pour éviter les images tournées.
- La déclinaison `display` ne dépasse jamais 2048px sur sa dimension maximale, compressée en WebP avec qualité 85.
- La déclinaison `thumb` ne dépasse jamais 400px sur sa dimension maximale, compressée en WebP avec qualité 80.
- Les 3 fichiers sont enregistrés via l'adaptateur `StorageDriver` actif (`LocalStorageDriver` ou `S3StorageDriver`) avec des chemins cloisonnés par territoire : `photos/{territory_id}/{photo_id}/{variant}.webp`.
- La mise à jour ou le remplacement d'un cliché purge automatiquement les anciens fichiers associés via le `StorageDriver`.

**Never:**
- Aucun fichier exécutable, SVG malveillant ou script n'est accepté.
- Les métadonnées EXIF brutes potentiellement vulnérables ne sont jamais conservées dans les versions web (`display` et `thumb`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Upload JPEG HD valide | Fichier JPEG 15 Mo (4000x3000px) | `HTTP 200/201`, 3 fichiers générés (`original.jpg`, `display.webp` 2048x1536, `thumb.webp` 400x300) | N/A |
| Fichier trop volumineux | Fichier de 28 Mo | `HTTP 400 Bad Request` | RFC 7807 `FILE_TOO_LARGE` |
| Fichier non image (ex: .pdf, .exe) | Contenu texte ou binaire non image | `HTTP 400 Bad Request` | RFC 7807 `INVALID_IMAGE_FORMAT` |
| Image tournée avec flag EXIF | JPEG pris en mode portrait avec balise EXIF orientation 6 | Image redressée à la verticale dans `display` et `thumb` | N/A |
| Remplacement d'image sur photo existante | `POST /admin/photos/{id}/upload` sur photo ayant déjà une image | Anciens fichiers supprimés via `StorageDriver.delete()`, nouveaux chemins enregistrés | N/A |
| Upload sur photo d'un autre territoire | Contributeur A tente upload sur `photo_id` du territoire B | `HTTP 404 Not Found` | RFC 7807 `PHOTO_NOT_FOUND` |

</frozen-after-approval>

## Code Map

- `backend/app/services/image_service.py` -- Nouveau service de validation, redressement EXIF, redimensionnement et compression WebP.
- `backend/app/schemas/photo.py` -- Ajout du schéma `PhotoUploadResponse` et des propriétés d'URLs résolues.
- `backend/app/api/v1/admin/photos.py` -- Endpoints `POST /api/v1/admin/photos/{photo_id}/upload` et `POST /api/v1/admin/photos/upload`.
- `backend/tests/test_photo_upload.py` -- Nouveaux tests automatisés pour le pipeline d'upload et de traitement d'images.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/services/image_service.py` -- Implémenter le service Pillow : vérification taille/format, redressement EXIF, génération des 3 variantes et calcul des dimensions.
- [x] `backend/app/schemas/photo.py` -- Définir `PhotoUploadResponse` avec dimensions (largeur, hauteur) et URLs publiques d'accès.
- [x] `backend/app/api/v1/admin/photos.py` -- Ajouter les endpoints de téléversement (multipart/form-data) avec gestion des permissions et purge des anciens médias lors du remplacement.
- [x] `backend/tests/test_photo_upload.py` -- Créer la suite de tests pour la validation de taille, formats invalides, génération des 3 variantes et mise à jour de la photo.

**Acceptance Criteria:**
- Given un fichier JPEG valide de 5 Mo, When envoyé à `POST /api/v1/admin/photos/{id}/upload`, Then l'API retourne HTTP 200 et les 3 déclinaisons sont enregistrées dans le stockage.
- Given un fichier non-image ou supérieur à 25 Mo, When envoyé à l'endpoint d'upload, Then l'API renvoie HTTP 400 avec le code d'erreur RFC 7807 approprié.
- Given une photo possédant déjà des fichiers médias, When un nouveau cliché est téléversé, Then les anciens fichiers sont supprimés du stockage et la fiche photo pointe sur les nouveaux.

## Implementation Notes

## Spec Change Log

## Review Triage Log

- `patch` (`blind-hunter`): Traitement CPU Pillow bloquant la boucle d'événements asyncio -> Corrigé via `asyncio.to_thread`.
- `patch` (`blind-hunter+edge-case-hunter`): Purge prématurée des anciens médias avant le succès de la persistance -> Corrigé en ne purgeant les anciens chemins qu'après le commit en base de données.
- `patch` (`edge-case-hunter`): Exception `DecompressionBombError` de Pillow non interceptée -> Corrigée pour retourner une erreur 400 `INVALID_IMAGE_FORMAT`.
- `patch` (`verification-gap`): Absence d'assertions sur les URLs résolues de `PhotoRead` et sur la persistance des variantes display/thumb après remplacement -> Corrigé dans `test_photo_upload.py`.
- `patch` (`blind-hunter`): `delete_photo` instanciant `StorageDriver` en direct plutôt que par `Depends(get_storage_driver)` -> Corrigé.

## Verification

**Commands:**
- `python3 -m py_compile backend/app/services/image_service.py backend/app/api/v1/admin/photos.py backend/tests/test_photo_upload.py` -- expected: Compilation sans erreur syntaxique.
- `docker compose exec hierici-backend pytest backend/tests/test_photo_upload.py` -- expected: Tous les tests d'upload passent au vert (100% pass).

