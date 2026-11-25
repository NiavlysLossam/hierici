---
title: "Story 5.1: Révision du Modèle de Métadonnées Photo et Cône de Vision Métrique"
type: 'feature'
created: '2026-11-05'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-5-context.md'
  - '_bmad-output/implementation-artifacts/spec-2-1-modele-photo-api-gestion.md'
  - '_bmad-output/implementation-artifacts/spec-2-3-interface-admin-metadonnees-archives.md'
  - '_bmad-output/implementation-artifacts/spec-2-4-selecteur-cartographique-azimut.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le modèle de métadonnées photo comporte des champs redondants ou peu adaptés à la pratique archivistique ("époque/période" et "date précise"), alors qu'il manque la qualification de certitude de l'année ("Année précise ?"), la suggestion facilitée des institutions et des photographes récurrents, ainsi que la capacité à régler la profondeur métrique du cône de vision (un plan rapproché ne portant pas à la même distance qu'un panorama lointain).

**Approach:**
1. Mettre à jour le modèle `Photo` et les schémas Pydantic :
   - Rendre obsolètes/retirer des contrats de saisie `period_label` et `date_exact`.
   - Ajouter `is_exact_year` (booléen, défaut `true`).
   - Ajouter `view_distance` (entier, mètres, défaut `160`, bornes `20` à `2000`).
2. Créer un endpoint `GET /api/v1/admin/photos/metadata-suggestions` retournant les listes uniques de `archive_source` et `photographer` déjà existantes pour le territoire.
3. Adapter l'interface d'édition (`PhotoFormModal.vue`) :
   - Supprimer les champs "époque/période" et "date précise".
   - Ajouter la case à cocher "Année précise ?".
   - Remplacer les champs texte simples `photographer` et `archive_source` par des entrées assistées avec suggestions / tags.
   - Ajouter le curseur métrique "Longueur du cône de vision" dans `PhotoLocationPicker.vue` avec réactivité en temps réel sur la projection du polygone.
4. Mettre à jour les tests unitaires et d'API.

## Boundaries & Constraints

**Always:**
- `is_exact_year` est un booléen strict (`true` = année exacte vérifiée, `false` = année estimée / "vers").
- `view_distance` est borné entre 20 et 2000 mètres (défaut 160m).
- Les colonnes `period_label` et `date_exact` restent tolérées en BDD (nullable) pour garantir la rétrocompatibilité des données déjà insérées, mais sont épurées de la vue et des formulaires.
- Le sélecteur cartographique `PhotoLocationPicker.vue` met à jour le cône selon `view_distance` immédiatement à 60 fps.

**Never:**
- Pas de fuite inter-territoire sur les suggestions de métadonnées (le filtre `territory_id` s'applique strictement).
- Pas de blocage si un contributeur saisit un photographe ou une archive inédite (saisie libre toujours permise en plus des suggestions).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Saisie année approximative | Année `1910`, `is_exact_year=false` | Persistance `year_taken=1910`, `is_exact_year=false`. Fiche affichera "Vers 1910". | N/A |
| Réglage de portée de cône | Curseur déplacé à 450 m | Le cône vectoriel s'étend à 450 mètres de rayon sur la carte. `view_distance=450` enregistré. | Bornage [20, 2000] |
| Suggestions métadonnées | Clic sur le champ institution ou photographe | Liste déroulante des valeurs déjà utilisées sur le territoire actif | Liste vide si premier cliché du territoire |
| Saisie libre d'un nouveau photographe | Tape un nom inédit | Le nouveau nom est enregistré et apparaîtra dans les suggestions suivantes | Trim des espaces superflus |

</frozen-after-approval>

## Code Map

- `backend/app/models/photo.py` -- Ajout de `is_exact_year` et `view_distance`.
- `backend/app/schemas/photo.py` -- Mise à jour des schémas Create, Update, Read, GeoJson.
- `backend/app/api/v1/admin/photos.py` -- Endpoint `GET /api/v1/admin/photos/metadata-suggestions` et mapping des nouveaux champs.
- `backend/app/api/v1/public/photos.py` -- Exposition de `is_exact_year` et `view_distance` dans le GeoJSON public.
- `frontend/src/types/photo.ts` -- Typage TypeScript de `is_exact_year` et `view_distance`.
- `frontend/src/services/api.ts` -- Méthode `photoApi.getMetadataSuggestions()`.
- `frontend/src/components/admin/PhotoFormModal.vue` -- Révision du formulaire (retrait des 2 champs, ajout switch exactitude, autocomplétion, champ distance).
- `frontend/src/components/admin/PhotoLocationPicker.vue` -- Curseur de longueur métrique du cône avec mise à jour MapLibre GL.
- `backend/tests/test_photos_admin.py` & tests frontend -- Tests unitaires automatisés.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/photo.py` -- Ajouter `is_exact_year` et `view_distance`.
- [x] `backend/app/schemas/photo.py` -- Adapter les schémas Pydantic.
- [x] `backend/app/api/v1/admin/photos.py` -- Ajouter l'endpoint de suggestions et adapter le CRUD.
- [x] `backend/app/api/v1/public/photos.py` -- Adapter la sérialisation GeoJSON publique.
- [x] `frontend/src/types/photo.ts` & `frontend/src/services/api.ts` -- Mettre à jour les types et méthodes API.
- [x] `frontend/src/components/admin/PhotoFormModal.vue` -- Réaménager le formulaire de saisie.
- [x] `frontend/src/components/admin/PhotoLocationPicker.vue` -- Ajouter le slider de longueur de cône.
- [x] Tests automatisés backend & frontend -- Valider l'intégrité et la non-régression.

**Acceptance Criteria:**
- Given un contributeur sur le formulaire photo, When il visualise la section date, Then les champs "époque/période" et "date précise" sont absents et remplacés par "Année" + switch "Année précise ?".
- Given le contributeur sur les champs "Photographe" et "Institution d'archives", When il clique, Then une liste déroulante propose les valeurs existantes du territoire.
- Given le sélecteur d'azimut, When le contributeur ajuste la longueur du cône, Then le polygone sur la carte s'allonge/se raccourcit en temps réel et la valeur est persistée.

## Implementation Notes
- Ajout des `server_default` sur les colonnes `is_exact_year` (true) et `view_distance` (160) pour assurer la rétrocompatibilité des bases de données.
- Support du paramètre `territory_id` et du fallback d'extraction de slug pour l'endpoint `/metadata-suggestions` en mode superadmin.
- Sécurisation de `createViewConePolygon` avec garde métrique bornée [20, 2000m].
- Intégration de `formatPhotoYear` dans `PhotoAdminCatalog.vue` et `PhotoDetailDrawer.vue`.

## Spec Change Log
- Alignement du curseur métrique du cône sur 20-2000m (au lieu de 1500m).
- Déduplication et limitation à 100 éléments des suggestions de photographes et institutions.

## Review Triage Log
- Blind Hunter, Edge Case Hunter & Verification Gap Reviewer ont été exécutés en parallèle.
- P1 (Crash null en update & absence de server_default) : Résolu par filtrage non-null et server_default SQL.
- P2 (Superadmin suggestions sans header) : Résolu via Query(territory_id) et extraction de slug.
- P2 (Bornage curseur 1500m vs 2000m) : Résolu en alignant le slider HTML sur 2000m et injection synchrone dans `updateViewConeLayer`.
- P3 (Dédoublonnage et garde distance dans geo.ts) : Résolu.
