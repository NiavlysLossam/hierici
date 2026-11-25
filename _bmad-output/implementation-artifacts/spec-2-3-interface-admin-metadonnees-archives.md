---
title: 'Story 2.3: Interface d''Administration de Saisie des Métadonnées d''Archives'
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
  - '_bmad-output/implementation-artifacts/spec-2-2-upload-pipeline-compression-webp.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Les contributeurs et archivistes n'ont actuellement aucune interface graphique web pour saisir, vérifier et administrer les métadonnées historiques et documentaires des clichés patrimoniaux (cotes d'archives, licences, dates, photographes).

**Approach:** Développer l'interface d'administration Vue 3 / TailwindCSS comprenant un gestionnaire de catalogue (liste, recherche, filtre statut) et un formulaire documentaire modal (`PhotoFormModal`) permettant la saisie complète, le téléversement d'images avec aperçu, et la validation stricte empêchant la publication sans coordonnées GPS.

## Boundaries & Constraints

**Always:**
- Le titre est obligatoire.
- La licence propose un sélecteur normalisé : "Domaine Public", "Licence Ouverte (Etalab)", "Creative Commons (BY)", "Creative Commons (BY-SA)", "Tous droits réservés".
- Si le statut sélectionné est `published` alors que la photo ne dispose pas de coordonnées (`latitude` ou `longitude` absentes), l'interface bloque l'enregistrement et affiche un message d'alerte invitant à géolocaliser le cliché.
- Le mode `draft` permet l'enregistrement partiel de la fiche sans coordonnées GPS.
- L'interface s'interface avec les endpoints existants `/api/v1/admin/photos` et gère le téléversement d'images via `/api/v1/admin/photos/{id}/upload` avec retour d'état réactif (vignette `thumb_url`, dimensions).

**Never:**
- Aucune soumission HTTP valide avec `status: 'published'` et sans coordonnées ne doit être autorisée par le formulaire.
- Pas de perte de données saisies lors d'une erreur réseau ou d'un téléversement.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Enregistrement brouillon valide | Formulaire rempli (titre seul ou partiel), statut `draft` | Enregistrement réussi, ajout/mise à jour dans la liste, fermeture modale | Toast de confirmation |
| Tentative publication sans GPS | Statut `published` sélectionné, `latitude=null` | Bouton d'enregistrement désactivé ou alerte visible "Coordonnées GPS obligatoires pour publier" | Blocage côté client avant envoi |
| Téléversement d'image direct | Sélection d'un scan JPEG dans le formulaire | Appel à l'API d'upload, affichage immédiat de l'aperçu WebP | Affichage d'une barre de progression / spinner |
| Suppression de cliché | Clic sur "Supprimer" avec confirmation | Appel `DELETE /admin/photos/{id}`, suppression de la ligne dans la table | Toast d'information |
| Modification métadonnées | Clic sur "Modifier" sur une photo existante | Modale pré-remplie avec toutes les cotes, dates et licence | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/types/photo.ts` -- Définition des types TypeScript (`Photo`, `PhotoStatus`, `PhotoCreatePayload`, `PhotoUpdatePayload`).
- `frontend/src/services/api.ts` -- Client HTTP typé pour l'API `/api/v1/admin/photos` (CRUD, upload, recherche).
- `frontend/src/components/admin/PhotoFormModal.vue` -- Composant modal de création/édition documentaire avec upload d'image et validation conditionnelle de publication.
- `frontend/src/components/admin/PhotoAdminCatalog.vue` -- Composant de gestion de catalogue : tableau avec vignettes, statut, recherche et actions.
- `frontend/src/App.vue` -- Intégration de la navigation et affichage du studio d'administration.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/types/photo.ts` -- Déclarer les interfaces TypeScript pour le modèle Photo, les licences et les statuts.
- [x] `frontend/src/services/api.ts` -- Implémenter le service API fetch pour le catalogue, le CRUD et l'upload multipart.
- [x] `frontend/src/components/admin/PhotoFormModal.vue` -- Construire le formulaire documentaire complet avec upload d'image, drag & drop, aperçu et validation bloquante pour la publication sans GPS.
- [x] `frontend/src/components/admin/PhotoAdminCatalog.vue` -- Développer la liste paginée des clichés avec filtrage par statut, recherche et confirmation de suppression.
- [x] `frontend/src/App.vue` -- Intégrer les onglets de navigation Studio / Découverte et brancher le catalogue.

**Acceptance Criteria:**
- Given un contributeur ouvrant le formulaire de création, When il saisit un titre et choisit le statut `draft`, Then il peut enregistrer la fiche sans renseigner de coordonnées.
- Given une fiche sans coordonnées géographiques, When le contributeur tente de basculer en `published`, Then le formulaire refuse l'enregistrement et affiche une alerte explicite.
- Given une photo existante, When le contributeur téléverse une nouvelle image dans le formulaire, Then la vignette est immédiatement actualisée et sauvegardée.

## Implementation Notes

- Définition complète des interfaces TypeScript (`Photo`, `PhotoStatus`, `PhotoLicense`, `PhotoCreatePayload`, `PhotoUpdatePayload`, `PhotoListResponse`, `PhotoUploadResponse`) et de la liste normalisée des 5 licences de diffusion patrimoniales.
- Service HTTP API avec support d'authentification JWT (stockage local et gestion transparente des en-têtes Authorization Bearer), conversion et détection des erreurs RFC 7807 (`ApiError`), endpoints CRUD `/api/v1/admin/photos` et téléversement multipart (`uploadPhotoImage` et `uploadPhotoDirect`).
- Composant modal `PhotoFormModal` avec 3 onglets thématiques (Notice documentaire, Géoréférencement, Image & Numérisation), téléversement par drag & drop avec prévisualisation immédiate, spinner de traitement WebP et règle stricte de blocage en mode `published` sans coordonnées GPS avec alerte explicite.
- Composant `PhotoAdminCatalog` avec affichage en tableau réactif, vignettes WebP, badges de statut, indicateurs de géolocalisation, recherche texte debouncée, filtrage par statut, pagination serveur, et modale de confirmation avant suppression physique et en base.
- Intégration de la navigation dans `App.vue` avec onglets Studio / Découverte, indicateurs de santé API et de territoire actif, et gestion de session.
- Correction d'un import manquant `asyncio` dans le backend `admin/photos.py` et synchronisation de l'adaptateur de stockage dans `delete_photo`.

## Spec Change Log

## Review Triage Log

- `patch` (`edge-case-hunter+verification-gap`): Coercion erronée de chaîne vide `""` en `0` pour latitude, longitude et azimut -> Corrigé via `parseNullableNumber`.
- `patch` (`verification-gap`): Paramètre injecté `storage` court-circuité par `get_storage_driver()` dans `delete_photo` -> Corrigé par utilisation directe de `storage`.
- `patch` (`blind-hunter`): Recherche du catalogue ignorant l'auteur et la cote dans la requête SQL backend -> Corrigé en ajoutant `photographer.ilike()` et `archive_ref.ilike()`.
- `patch` (`edge-case-hunter`): Pagination vide lors de la suppression de l'unique élément d'une page > 1 -> Corrigé par décrément automatique de la page courante.
- `patch` (`blind-hunter`): Bannière d'erreur API manquante en cas d'échec de chargement du catalogue -> Ajout d'une bannière réactive avec bouton de rechargement.

## Verification

**Commands:**
- `cd frontend && npm run build` (ou via conteneur Vite) -- expected: Compilation TypeScript et build Vite sans aucune erreur.

