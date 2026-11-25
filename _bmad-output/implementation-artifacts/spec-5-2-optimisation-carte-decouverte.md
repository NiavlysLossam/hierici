---
title: "Story 5.2: Optimisation de l'Exploration Cartographique (Marqueurs Visibles & Fiche Latérale Droite)"
type: 'feature'
created: '2026-11-05'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-5-context.md'
  - '_bmad-output/implementation-artifacts/spec-3-1-visualiseur-cartographique-public-clustering.md'
  - '_bmad-output/implementation-artifacts/spec-3-2-marqueurs-orientes-cones-webgl.md'
  - '_bmad-output/implementation-artifacts/spec-3-3-fiche-detaillee-visionneuse.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Dans le mode Carte Découverte publique :
1. Les points/marqueurs des clichés individuels manquent de visibilité et d'impact visuel à l'échelle de la carte.
2. Le clic sur une photo déclenche une popup MapLibre flottante qui encombre l'écran et fait doublon avec la fiche détaillée.
3. Le bandeau haut-droit affiche un compteur et le nom de territoire jugés superflus par l'utilisateur.
4. La projection du cône de vue sur la carte utilise une portée fixe au lieu de respecter la distance métrique personnalisée (`view_distance`) introduite dans la Story 5.1.

**Approach:**
1. Agrandir et contraster les marqueurs de photos individuelles dans `PublicMapViewer.vue` :
   - Augmenter `icon-size` de `0.75` à `1.15` pour les couches `unclustered-oriented` et `unclustered-neutral`.
   - Renforcer la netteté et la présence graphique du canvas Canvas2D (cercle blanc de contour plus affirmé, ombre portée accentuée).
2. Supprimer la popup MapLibre (`new maplibregl.Popup`) :
   - Le clic sur un marqueur ouvre immédiatement et exclusivement la fiche latérale droite (`PhotoDetailDrawer.vue`).
   - Le survol (hover) met toujours à jour le cône de vue sans créer de popup.
3. Épurer l'interface utilisateur :
   - Retirer le bloc du compteur de photos et du territoire en haut à droite.
4. Brancher la portée métrique dynamique du cône :
   - Dans `updateViewCone()`, utiliser `target.properties.view_distance ?? 160` pour calculer l'emprise du polygone WebGL.
5. Adapter l'affichage de la date dans le volet latéral `PhotoDetailDrawer.vue` :
   - Remplacer l'ancien affichage brut de période/date exacte par l'utilitaire `formatPhotoYear(year_taken, is_exact_year)` ("1910" ou "Vers 1910").

## Boundaries & Constraints

**Always:**
- Performance MapLibre GL 60 fps maintenue sans tremblement ni saccade lors des survols et clics.
- Le volet latéral s'ouvre à droite sur desktop (`md:w-[420px]`, `right-0`) et en bas/modal adapté sur mobile.
- Support du partage d'URL direct avec le paramètre `?photo={uuid}` ouvrant directement le volet latéral et centrant la carte.
- Rétrocompatibilité totale avec les clichés n'ayant pas encore de `view_distance` explicite (fallback à 160m).

**Never:**
- Pas de popup MapLibre résiduelle qui s'affiche au clic.
- Pas de régression sur les clusters de clichés (le clic sur un cluster continue de zoomer pour éclater les points).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clic sur marqueur individuel | Clic sur une photo orientée | Pas de popup. Le volet latéral droit s'ouvre avec la fiche complète du cliché. Cône orienté projeté. | Sélection résiliente si réseau lent |
| Cliché avec portée spécifique | Photo avec `view_distance = 650` | Le cône vectoriel WebGL s'étend sur 650 mètres autour du point. | Fallback 160m si `view_distance` absent ou null |
| Cliché avec année approximative | `year_taken = 1905`, `is_exact_year = false` | Le volet latéral affiche « Vers 1905 ». | Fallback « Date inconnue » si null |
| Navigation par URL | Arrivée avec `?photo=<id>` | La carte se centre sur le cliché et le volet latéral droit s'ouvre automatiquement. | Toast d'erreur si photo inexistante |

</frozen-after-approval>

## Code Map

- `frontend/src/components/public/PublicMapViewer.vue` -- Taille des icônes, suppression de la popup, retrait du compteur haut-droit, intégration de `view_distance` dans `updateViewCone()`.
- `frontend/src/components/public/PhotoDetailDrawer.vue` -- Formatage de l'année archivistique avec `formatPhotoYear()`.
- `frontend/tests/photo_detail_drawer_logic.test.mjs` -- Tests unitaires de validation.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/public/PublicMapViewer.vue` -- Agrandir les marqueurs (`icon-size: 1.15`), supprimer `showPhotoPopup()`, supprimer le badge compteur/territoire haut-droit, et injecter `view_distance` dans `updateViewCone()`.
- [x] `frontend/src/components/public/PhotoDetailDrawer.vue` -- Nettoyer l'affichage de date au profit de `formatPhotoYear` et corriger la hauteur de rendu desktop.
- [x] Tests de non-régression et vérification de la compilation TypeScript (`vue-tsc -b`) et tests unitaires (`story-5.2-map-discovery.test.mjs`).

**Acceptance Criteria:**
- Given un visiteur sur la carte découverte, When il observe les marqueurs de photos, Then les icônes sont nettement plus grandes, visibles et contrastées.
- Given le visiteur clique sur une photo, When l'interaction se produit, Then aucune popup flottante n'apparaît sur la carte et la fiche photo s'ouvre directement dans le volet latéral droit.
- Given l'écran de la carte, When le visiteur regarde en haut à droite, Then aucun compteur de clichés ni badge de territoire n'encombre la vue.
- Given une photo avec une portée personnalisée (ex: 500m), When elle est survolée ou sélectionnée, Then son cône de vue s'étend exactement à la portée métrique spécifiée.

