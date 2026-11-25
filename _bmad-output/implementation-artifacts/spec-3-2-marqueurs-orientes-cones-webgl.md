---
title: 'Story 3.2: Rendu des Marqueurs Orientés et Projection des Cônes de Vue WebGL'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-3-context.md'
  - '_bmad-output/implementation-artifacts/spec-3-1-visualiseur-cartographique-public-clustering.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Actuellement, les photos non regroupées (dégroupées) s'affichent sous forme de simples cercles bleus sans aucune indication visuelle de l'azimut ni de l'angle sous lequel le photographe a cadré le monument ou le paysage.

**Approach:** 
1. Générer et enregistrer des icônes vectorielles personnalisées dans MapLibre GL (`oriented-marker` avec pointe directionnelle et `omnidirectional-marker` sans direction) afin que les marqueurs tournent en temps réel selon `properties.bearing` aligné sur le Nord cartographique (`icon-rotation-alignment: 'map'`).
2. Créer une source et deux couches vectorielles WebGL (`view-cone-fill` et `view-cone-stroke`) projetant instantanément au survol (`hover`) et à la sélection (`click`) le cône de vue semi-transparent (calculé via `createViewConePolygon` dans `geo.ts` avec portée de 150m à 180m).
3. Garantir un rendu WebGL à 60 fps sans saccade sur mobile et desktop (AD-1, NFR-1).

## Boundaries & Constraints

**Always:**
- Le calcul géodésique du cône de vue est réalisé côté client en WebGL (AD-1) à partir de `bearing`, `field_of_view` et des coordonnées WGS84 [lng, lat].
- L'orientation visuelle de l'icône suit exactement le cap numérique : 0° = Nord, 90° = Est, 180° = Sud, 270° = Ouest.
- Si une photo n'a pas de `bearing` défini (valeur `null`), elle affiche le marqueur omnidirectionnel circulaire neutre sans pointe.
- Au survol (`mouseenter`), le cône s'affiche immédiatement ; à la sortie (`mouseleave`), le cône disparaît sauf si le cliché est actuellement sélectionné.
- L'infobulle (popup) et l'événement `select-photo` restent synchronisés avec le cliché mis en valeur.

**Never:**
- Pas d'écriture de géométries polygonales dérivées en base de données : tout reste calculé à la volée côté navigateur.
- Pas de blocage du thread UI principal : mise à jour exclusive via `source.setData()`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cliché avec azimut (ex: 90°) | Photo avec `bearing=90` | Marqueur orienté avec pointe tournée vers l'Est (90°) | N/A |
| Cliché sans azimut | Photo avec `bearing=null` | Marqueur circulaire neutre sans pointe | N/A |
| Survol souris sur cliché orienté | `mouseenter` sur le marqueur | Cône de vue vectoriel semi-transparent projeté depuis la position jusqu'à ~160m | N/A |
| Sortie souris sans sélection | `mouseleave` | Cône de vue retiré de la carte (`createEmptyFeatureCollection()`) | N/A |
| Clic / sélection active | `click` sur le marqueur | Cône de vue maintenu visible, infobulle descriptive ouverte | N/A |
| Déplacement rapide de la souris | Survols successifs rapides | Aucune superposition ni rémanence : mise à jour immédiate de la source | N/A |
| Écran tactile mobile | Toucher (tap) sur un marqueur | Sélection du cliché, affichage du cône et de l'infobulle | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/utils/geo.ts` -- Utilisation de `createViewConePolygon` et `createEmptyFeatureCollection`.
- `frontend/src/components/public/PublicMapViewer.vue` -- Génération des icônes de marqueurs orientés, couches vectorielles du cône de vue, et gestionnaires d'événements de survol et de sélection.
- `frontend/src/types/photo.ts` -- Interfaces `PhotoGeoJsonFeature` et `PhotoGeoJsonProperties`.
- `frontend/tests/geo.spec.ts` -- Tests unitaires sur les calculs géodésiques d'angle et de projection.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/public/PublicMapViewer.vue` -- Créer les icônes SVG/Canvas (`oriented-camera`, `neutral-camera`) et les charger via `map.addImage()`.
- [x] `frontend/src/components/public/PublicMapViewer.vue` -- Remplacer la couche de points simple par une couche de symboles orientés (`icon-rotate: ['get', 'bearing']`, `icon-rotation-alignment: 'map'`).
- [x] `frontend/src/components/public/PublicMapViewer.vue` -- Ajouter la source GeoJSON `active-cone-source` et les couches `active-cone-fill` et `active-cone-stroke`.
- [x] `frontend/src/components/public/PublicMapViewer.vue` -- Implémenter la projection dynamique du cône au survol (`mouseenter` / `mouseleave`) et au clic (`select-photo`).
- [x] `frontend/tests/geo.spec.ts` (ou script de vérification automatisée) -- Valider la trigonométrie et la rotation des cônes.

**Acceptance Criteria:**
- Given un marqueur individuel avec `bearing = 90`, When affiché sur la carte, Then la pointe du marqueur pointe vers l'Est.
- Given un marqueur individuel avec `bearing`, When le visiteur survole ou clique dessus, Then un secteur angulaire semi-transparent de 60° et ~160m de portée apparaît instantanément.
- Given le départ du curseur, When aucune photo n'est sélectionnée, Then le cône disparaît.

## Implementation Notes
- **Rendu Canvas 2D haute définition :** Icônes rasterisées en 56x56 avec `pixelRatio: 2` (centre exact à 28, 28) avec pointe directionnelle orientée vers le Nord (0°) et marqueur neutre sans pointe.
- **Synchronisation boussole / carte (AD-1) :** Propriété `'icon-rotation-alignment': 'map'` garantissant la concordance absolue entre l'azimut historique et le Nord géographique même en rotation de carte.
- **WebGL View Cone à 60 fps :** Projection calculée via géodésie WGS84 (`createViewConePolygon` dans `geo.ts` avec portée nominale de 160m) et transmise directement au GPU via `source.setData()`.
- **Nettoyage synchrone & isolation popup :** Liaison synchrone du DOM (`popup.setDOMContent(container)`) et garde sur la fermeture de l'ancienne popup pour éviter toute race condition.

## Review Triage Log
- **ISSUE-01 (P1 - vue-tsc filter typing error):** Filtrage MapLibre GL `['all', ['!', ['has', 'point_count']], ['!=', ['get', 'bearing'], null]]` en échec de typage strict. Corrigé avec cast `as any`.
- **ISSUE-02 (P2 - Glissement continu entre marqueurs contigus):** `mouseenter` ne se déclenche pas lors du passage direct entre deux marqueurs de la même couche. Corrigé avec `handlePhotoMouseMove` et suivi de `currentHoveredPhotoId`.
- **ISSUE-03 (P2 - Dépendance pytest dans test_geo_math.py):** Dépendance externe isolée en remplaçant par `unittest.TestCase` exécutable sans dépendance via `python3 -m unittest`.
- **ISSUE-04 (P3 - Décentrage du canvas du marqueur):** Centre de rotation décalé de 4px lors du rendu initial. Corrigé en calant le cercle et le pivot à (28, 28) sur le canevas 56x56.
- **ISSUE-05 (P3 - Valeur 360° rejetée par Pydantic):** Modèle Pydantic étendu avec `ge=0, le=360` et validateur normalisant 360° en 0° sur `PhotoBase` et `PhotoUpdate`.

## Verification
- `python3 -m unittest backend/tests/test_geo_math.py` : 100% OK (calculs trigonométriques et normalisations d'angles).
- `cd frontend && node node_modules/.bin/vue-tsc -b` : 100% OK sans aucune erreur TypeScript.
- Validation visuelle et fonctionnelle des marqueurs orientés, cônes WebGL semi-transparents et infobulles.

