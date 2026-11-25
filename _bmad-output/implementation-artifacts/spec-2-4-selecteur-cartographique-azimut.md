---
title: 'Story 2.4: Sélecteur Cartographique Interactif pour le Point GPS et l''Azimut'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-2-context.md'
  - '_bmad-output/implementation-artifacts/spec-2-3-interface-admin-metadonnees-archives.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Les contributeurs doivent actuellement renseigner manuellement des coordonnées décimales abstraites et un angle numérique sans retour visuel sur l'orientation et la perspective du cliché par rapport au paysage.

**Approach:** Intégrer dans l'onglet de géoréférencement de `PhotoFormModal` un composant cartographique interactif (`PhotoLocationPicker.vue`) basé sur MapLibre GL JS : placement du marqueur au clic ou par glisser-déposer, génération trigonométrique en temps réel d'un cône de vue vectoriel projeté, et boussole rotative interactive de 0° à 359°.

## Boundaries & Constraints

**Always:**
- Les coordonnées `latitude` et `longitude` sont arrondies à 6 décimales (précision ~10 cm).
- L'azimut (`bearing`) est un entier strict `0 <= bearing <= 359` (0° = Nord, 90° = Est). L'ouverture par défaut du champ de vision est de 60°.
- Le cône de vue vectoriel est calculé côté client sous forme de polygone GeoJSON dynamique (secteur angulaire projeté) sans surcharger la base de données de polygones dérivés (AD-1).
- La carte se centre automatiquement sur le territoire actif lors de l'ouverture pour une nouvelle photo, ou sur la position existante du cliché en mode édition.
- Le marqueur est déplaçable (draggable) et le clic sur la carte repositionne le point.
- Un bouton permet de réinitialiser/effacer la position pour repasser la photo en non géolocalisée (mode brouillon).

**Never:**
- Pas d'utilisation de géométries polygonales dérivées enregistrées en base : seuls `latitude`, `longitude`, `bearing` et `field_of_view` sont persistés.
- Pas de dépendance à des clés API propriétaires tierces (styles OSM libres).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clic sur la carte | Clic sur la carte à (5.9285, 43.1245) | Marqueur positionné, `latitude=43.124500` et `longitude=5.928500` mis à jour, cône affiché | N/A |
| Glisser-déposer du marqueur | Drag & drop du marqueur vers un nouveau point | Coordonnées et cône synchronisés en temps réel | N/A |
| Rotation de la boussole / azimut | Curseur d'azimut déplacé à 180° | Cône de vue pivote instantanément vers le Sud (180°) | N/A |
| Ajustement du champ de vision | Modification de l'ouverture (ex: 45° ou 90°) | Cône s'élargit ou se resserre sur la carte | Bornage 10° - 120° |
| Réinitialisation de la position | Clic sur "Effacer la position" | Marqueur et cône retirés de la carte, `latitude=null` et `longitude=null` | N/A |
| Photo déjà géolocalisée en édition | Ouverture de la modale pour photo avec GPS | Carte centrée sur la photo, marqueur et cône orienté immédiatement visibles | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/utils/geo.ts` -- Fonctions utilitaires trigonométriques pour générer le polygone GeoJSON du cône de vue projeté (`createViewConePolygon`).
- `frontend/src/components/admin/PhotoLocationPicker.vue` -- Nouveau composant MapLibre GL interactif avec marqueur, boussole et cône de vue.
- `frontend/src/components/admin/PhotoFormModal.vue` -- Intégration du sélecteur cartographique dans l'onglet "Géoréférencement".
- `frontend/src/main.ts` -- Import du fichier CSS de MapLibre GL (`maplibre-gl/dist/maplibre-gl.css`).

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/utils/geo.ts` -- Développer la fonction mathématique de projection du cône de vue GeoJSON (arc trigonométrique basé sur distance métrique, bearing et field_of_view).
- [x] `frontend/src/main.ts` -- Importer la feuille de style globale `maplibre-gl/dist/maplibre-gl.css`.
- [x] `frontend/src/components/admin/PhotoLocationPicker.vue` -- Créer le composant cartographique MapLibre GL : tuiles libres OSM, marqueur draggable, couche vectorielle GeoJSON du cône de vue et contrôles d'azimut (boussole/curseur).
- [x] `frontend/src/components/admin/PhotoFormModal.vue` -- Remplacer la saisie manuelle de coordonnées par `PhotoLocationPicker` avec synchronisation bidirectionnelle.

**Acceptance Criteria:**
- Given un contributeur ouvrant l'onglet Géoréférencement, When il clique sur la carte, Then un marqueur apparaît et les coordonnées s'affichent avec 6 décimales.
- Given une position définie, When le contributeur modifie l'azimut (0-359°), Then le cône de vue pivote visuellement sur la carte en temps réel.
- Given une fiche éditée avec position et azimut, When le contributeur enregistre, Then `latitude`, `longitude`, `bearing` et `field_of_view` sont fidèlement sauvegardés en base de données.

## Implementation Notes

- Création de `frontend/src/utils/geo.ts` comprenant les fonctions `roundCoordinate` (arrondi à 6 décimales), `normalizeBearing` (entier strict 0-359°), `clampFov` (bornage 10°-120°), `destinationPoint` (résolution géodésique directe Haversine sur sphère terrestre) et `createViewConePolygon` (génération vectorielle GeoJSON du secteur de prise de vue).
- Import global du style CSS de MapLibre GL dans `frontend/src/main.ts`.
- Création du composant interactif `PhotoLocationPicker.vue` :
  - Intégration de MapLibre GL JS avec tuiles raster OpenStreetMap libres (aucune clé requise).
  - Marqueur déplaçable (draggable) avec synchronisation bidirectionnelle des coordonnées WGS84 au clic et au drag.
  - Couche vectorielle dynamique GeoJSON (`view-cone-source`, `view-cone-fill`, `view-cone-stroke`) pivotant instantanément avec l'azimut et se redimensionnant avec le champ de vision (FOV).
  - Boussole visuelle rotative avec aiguille animée et boutons de direction rapide (Nord, Est, Sud, Ouest).
  - Contrôle curseur et saisie directe d'azimut (0-359°) et d'angle de vue (10-120°).
  - Boutons de recentrage automatique sur le marqueur et d'effacement de la position pour repasser en brouillon.
  - Résolution automatique du territoire actif via `photoApi.getCurrentTerritory()` pour centrer la carte sur le territoire en mode création de nouveau cliché.
  - Gestion réactive des redimensionnements de conteneur via `ResizeObserver` et méthode exposée `resize()` pour éviter tout artefact de rendu lors des ouvertures de modale et changements d'onglets.
- Intégration dans `PhotoFormModal.vue` dans l'onglet "Géoréférencement" en remplacement des champs texte manuels bruts, avec synchronisation complète de `latitude`, `longitude`, `bearing` et `field_of_view`, et appel de `resize()` lors du basculement d'onglet.
- Correction préalable de deux coquilles TypeScript héritées dans `PhotoFormModal.vue` (`imagePreviewUrl` -> `localImagePreview` et `'notice'` -> `'document'`).

## Spec Change Log

## Review Triage Log

- **[P2 - Quality] Nettoyage JSDoc et validation stepDegrees dans `geo.ts`**: Supprimé le bloc de commentaire dupliqué et ajouté une garde `step = stepDegrees > 0 ? stepDegrees : 2` pour prévenir toute boucle infinie dans l'échantillonnage de l'arc de cercle.
- **[P2 - Latence UI] Synchronisation immédiate du cône pendant le drag dans `PhotoLocationPicker.vue`**: Éliminé le décalage perçu lors du glisser-déposer en passant explicitement les coordonnées réelles du marqueur `updateViewConeLayer(lat, lng)` sans attendre la réactivité asynchrone des props Vue.
- **[P3 - Robustesse] Drapeau `isDragging` et normalisation des coordonnées**: Ajouté le drapeau `isDragging` pour éviter les conflits d'état lors du drag, et normalisation de la longitude.

## Verification

**Commands:**
- `cd frontend && npm run build` -- expected: Build Vite et TypeScript sans aucune erreur.

