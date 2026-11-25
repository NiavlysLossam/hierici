---
title: 'Story 3.1: Visualiseur Cartographique Public et Clustering Vectoriel'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-3-context.md'
  - '_bmad-output/implementation-artifacts/spec-2-4-selecteur-cartographique-azimut.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Les visiteurs du grand public ne disposent actuellement d'aucune interface cartographique interactive publique pour explorer les clichés historiques de leur territoire, et il n'existe pas d'API publique délivrant les photos publiées sous un format géospatial standardisé avec regroupement vectoriel performant (clustering).

**Approach:** 
1. Exposer un endpoint public `GET /api/v1/photos` (ou `GET /api/v1/public/photos`) retournant un GeoJSON standard `FeatureCollection` (RFC 7946) des photos publiées (`status = 'published'`) et géolocalisées pour le territoire actif.
2. Créer le composant cartographique public `PublicMapViewer.vue` sous MapLibre GL JS avec clustering vectoriel côté client (`cluster: true`, rayon 50px, zoom max cluster 14), cercles de cluster dynamiques et zoom automatique d'éclatement au clic (`getClusterExpansionZoom`).

## Boundaries & Constraints

**Always:**
- L'API publique ne renvoie **strictement que** les clichés ayant `status = 'published'` et des coordonnées valides (`latitude` et `longitude` non nuls).
- Le filtrage par territoire actif est obligatoire (`territory_id` résolu via `get_current_territory`).
- Format de sortie GeoJSON conforme au standard RFC 7946 (`FeatureCollection`, géométrie `Point [longitude, latitude]`).
- Les clusters MapLibre affichent le nombre de clichés regroupés et permettent d'éclater la vue au clic.
- Affichage fluide sur écran mobile (≥ 360px) et desktop.

**Never:**
- Aucun cliché en statut `draft` (brouillon) ne doit être divulgué sur l'API publique.
- Aucune donnée privée de contributeurs (mots de passe, emails personnels) dans les propriétés GeoJSON.
- Pas de dépendance à des clés d'API propriétaires payantes pour les tuiles cartographiques de base.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Requête GeoJSON sans filtre | `GET /api/v1/photos` sur territoire actif | `HTTP 200 OK`, `FeatureCollection` contenant tous les clichés `published` géolocalisés | N/A |
| Clichés en brouillon (`draft`) | 3 photos publiées + 2 photos draft | Seules les 3 photos publiées sont présentes dans les `features` | N/A |
| Territoire sans photos publiées | Territoire vide | `HTTP 200 OK`, `FeatureCollection` avec `features: []` | N/A |
| Clic sur un cluster cartographique | Clic sur une pastille cluster de 8 photos | La carte calcule le niveau de zoom d'éclatement (`getClusterExpansionZoom`) et zoome de manière fluide (`easeTo`) | N/A |
| Changement de territoire actif | Header `X-Territory-Slug: autre-territoire` | Les photos du nouveau territoire sont chargées et la carte est recentrée sur son emprise | Recentrage automatique |
| Redimensionnement d'écran | Rotation mobile ou passage desktop | `map.resize()` automatique pour éviter tout canevas gris | N/A |

</frozen-after-approval>

## Code Map

- `backend/app/schemas/photo.py` -- Schémas Pydantic pour GeoJSON `Feature` et `FeatureCollection`.
- `backend/app/api/v1/public/photos.py` -- Route publique `GET /api/v1/photos` avec filtrage par statut et territoire.
- `backend/app/api/v1/__init__.py` -- Montage du routeur public `photos.py` sur l'API v1.
- `backend/tests/test_photos_public.py` -- Tests automatisés de non-régression de l'endpoint public GeoJSON.
- `frontend/src/types/photo.ts` -- Types TypeScript GeoJSON pour les clichés publics.
- `frontend/src/services/api.ts` -- Méthode `getPublicPhotosGeoJson()` dans l'API client.
- `frontend/src/components/public/PublicMapViewer.vue` -- Composant cartographique public MapLibre GL avec clustering vectoriel.
- `frontend/src/App.vue` -- Intégration de `PublicMapViewer.vue` dans l'onglet "Découverte Publique".

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/schemas/photo.py` -- Définir le schéma Pydantic `PhotoGeoJsonFeature` et `PhotoGeoJsonFeatureCollection`.
- [x] `backend/app/api/v1/public/photos.py` -- Implémenter l'endpoint public `GET /api/v1/photos` filtré par territoire actif et statut `published`.
- [x] `backend/app/api/v1/__init__.py` -- Inclure le routeur public dans `api_v1_router`.
- [x] `backend/tests/test_photos_public.py` -- Rédiger les tests de l'endpoint public (filtrage draft vs published, isolation territoire, GeoJSON conforme).
- [x] `frontend/src/types/photo.ts` & `frontend/src/services/api.ts` -- Déclarer les types GeoJSON et l'appel API public.
- [x] `frontend/src/components/public/PublicMapViewer.vue` -- Créer le visualiseur MapLibre avec source GeoJSON clustérisée, couches de cercles, symboles de décompte, et interaction zoom sur clic cluster.
- [x] `frontend/src/App.vue` -- Remplacer le placeholder de l'onglet "Découverte Publique" par `PublicMapViewer.vue`.

**Acceptance Criteria:**
- Given un visiteur sur l'onglet Découverte Publique, When la page s'affiche, Then la carte se centre sur le territoire actif et affiche les clusters de photos publiées.
- Given un groupe de plusieurs photos proches, When le visiteur clique sur une pastille de cluster, Then la carte zoome pour éclater les points.
- Given une photo en statut `draft`, When l'API publique `/api/v1/photos` est appelée, Then cette photo n'apparaît jamais dans le flux GeoJSON.

## Implementation Notes

- Création du routeur public `backend/app/api/v1/public/photos.py` avec `GET /api/v1/photos` (GeoJSON FeatureCollection) et `GET /api/v1/photos/{id}` (détail complet d'une photo publiée).
- Les coordonnées GeoJSON respectent strictement la spécification RFC 7946 : `[longitude, latitude]`.
- Modèles Pydantic `GeoJsonPointGeometry`, `PhotoGeoJsonProperties`, `PhotoGeoJsonFeature` et `PhotoGeoJsonFeatureCollection` dans `backend/app/schemas/photo.py`.
- Résolution des URLs des variantes d'images (`thumb`, `display`, `original`) via `resolve_media_url`.
- Création de la suite de tests automatisés `backend/tests/test_photos_public.py` vérifiant l'isolation multi-territoire, le filtrage strict des brouillons (`draft`), les filtres de recherche et période, et la conformité GeoJSON.
- Types TypeScript enrichis dans `frontend/src/types/photo.ts` et méthodes `getPublicPhotos()` et `getPublicPhoto()` dans `frontend/src/services/api.ts`.
- Nouveau composant interactif `frontend/src/components/public/PublicMapViewer.vue` :
  - MapLibre GL JS avec tuiles raster OpenStreetMap libres de droit.
  - Source vectorielle GeoJSON avec clustering côté client (`cluster: true`, `clusterMaxZoom: 14`, `clusterRadius: 50`).
  - Couche de pastilles de clusters proportionnelles et nuancées (`< 10`, `10-24`, `25-49`, `≥ 50`).
  - Couche textuelle avec nombre abrégé de photos par cluster.
  - Couche de clichés individuels pour les points dégroupés.
  - Interaction fluide d'éclatement au clic via `getClusterExpansionZoom`.
  - Barre supérieure de recherche et filtres temporels (années min/max) avec debounce.
  - Compteur dynamique de clichés publiés affichés et bouton de recentrage immédiat sur le territoire actif.
  - Gestion réactive des redimensionnements de fenêtre (`ResizeObserver`).
- Intégration du visualiseur public dans `frontend/src/App.vue` dans l'onglet "Découverte Publique".

## Review Triage Log

- **[P1 - Confidentialité] Création de `PhotoPublicRead` sans fuite de chemins internes ni d'identifiants contributeurs**: `GET /api/v1/photos/{id}` utilise un schéma dédié qui n'expose ni `author_user_id`, ni `created_by_id`, ni les chemins physiques de fichiers `file_*_path`, ni le statut interne.
- **[P1 - Résilience API & Sécurité] Bornage des années et validation des intervalles**: `year_min` et `year_max` bornés entre 1000 et 3000 (évite tout crash 500 sur entier PostgreSQL 32-bit), rejet 422 explicite si `year_min > year_max`.
- **[P1 - Plafond volumétrique] Protection DoS sur la route GeoJSON**: Paramètre `limit` avec plafond de sécurité (5000 items max).
- **[P1 - Robustesse Frontend & Concurrence] Annulation des requêtes via `AbortController` et drapeau `isMounted`**: Annulation des requêtes en vol lors de la frappe rapide pour éliminer les écrasements asynchrones et suppression des fuites mémoires WebGL lors d'un démontage précoce.
- **[P2 - Performance SQL] Suppression des requêtes selectin surnuméraires**: Ajout de `options(noload(Photo.author), noload(Photo.territory))` sur la route publique.
- **[P2 - Recherche SQL] Échappement des métacaractères `LIKE`**: Échappement de `\`, `%` et `_` dans le filtre de recherche textuelle.
- **[P2 - UX & Cartographie] Popup interactive sur cliché individuel et gestion des photos co-localisées**: Affichage d'une infobulle MapLibre au clic avec vignette et métadonnées, et gestion du zoom cap sur les points ayant des coordonnées strictement identiques.
- **[P2 - Réactivité Territoire] Rechargement automatique des données lors d'un changement de territoire actif**.
- **[P2 - Couverture de Tests] Tests automatisés enrichis**: Tests de confidentialité, d'intervalles invalides (422), de collection vide (RFC 7946) et de filtres textuels multi-champs.

## Verification

**Commands:**
- `python3 -m py_compile backend/app/api/v1/public/photos.py`
- `python3 -m py_compile backend/app/schemas/photo.py`
- `python3 -m py_compile backend/tests/test_photos_public.py`
