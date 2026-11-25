# Epic 3 Context: Exploration Cartographique Interactive & Visualisation Patrimoniale

<!-- Compiled from planning artifacts. Edit freely. -->

## Goal

Permettre au grand public d'explorer le territoire sur une carte interactive fluide avec clustering automatique, de visualiser l'orientation exacte des clichés historiques grâce à des cônes de vue vectoriels projetés, et de consulter les fiches patrimoniales détaillées avec visionneuse haute définition et partage direct par URL.

## Stories

- **Story 3.1: Visualiseur Cartographique Public et Clustering Vectoriel**
  - Route d'API publique `GET /api/v1/photos` retournant un GeoJSON standard `FeatureCollection` des photos publiées (`status = 'published'`) du territoire actif.
  - Interface cartographique plein écran MapLibre GL JS avec tuiles libres OpenStreetMap.
  - Regroupement automatique en clusters vectoriels paramétrés avec pastilles numériques.
  - Zoom fluide et éclatement des clusters au clic.
- **Story 3.2: Rendu des Marqueurs Orientés et Projection des Cônes de Vue WebGL**
  - Affichage des clichés dégroupés sous forme de marqueurs orientés indiquant la direction du regard (azimut `bearing`).
  - Projection dynamique d'un cône de vue vectoriel semi-transparent (60°, portée visuelle de 150m) au survol ou à la sélection.
  - Rendu WebGL haute performance (60 fps) sans ralentissement sur mobile et desktop.
- **Story 3.3: Fiche Détaillée du Cliché et Visionneuse Plein Écran**
  - Volet latéral / tiroir coulissant (desktop) ou feuille modale basse (mobile) affichant les métadonnées complètes et l'image optimisée `display`.
  - Visionneuse plein écran (*lightbox*) haute définition avec zoom et déplacement pan/zoom.
  - Synchronisation de l'URL via le paramètre de recherche `?photo={id}` permettant le partage direct de vue.

## Requirements & Constraints

- **NFR-1 (Performance & Fluidité) :** Temps de chargement initial de la carte < 1.5s sur réseau standard ; transitions cartographiques (`flyTo`, zoom) fluides à 60 fps en WebGL.
- **AD-1 (Format géospatial & Rendu client) :** Coordonnées en EPSG:4326 (WGS84). L'API expose un GeoJSON standard `FeatureCollection`. Le calcul trigonométrique et l'affichage des cônes de vue sont réalisés côté client en WebGL avec MapLibre GL JS sans surcharger le serveur ni la base PostGIS de géométries dérivées.
- **AD-2 (Cloisonnement multi-territoire) :** La requête publique filtre impérativement par le territoire actif (résolu via `X-Territory-Slug` ou le sous-domaine/territoire par défaut).
- **Statut public strict :** Seules les photos ayant `status = 'published'` et des coordonnées GPS valides sont retournées par l'endpoint public.
- **NFR-3 (Responsive Design) :** Interface cartographique et fiches 100% utilisables sur écrans mobiles (≥ 360px de largeur) et écrans desktop.
- **NFR-4 (Crédits & Licences) :** Préservation visible et obligatoire des mentions d'archives, cotes, auteurs et licences sur les photos affichées.

## Technical Architecture & Conventions

- **Endpoint public GeoJSON :** `GET /api/v1/photos` (ou `GET /api/v1/public/photos`)
  - Format de réponse standard GeoJSON :
    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "id": "uuid-str",
          "geometry": {
            "type": "Point",
            "coordinates": [longitude, latitude]
          },
          "properties": {
            "id": "uuid-str",
            "title": "Titre du cliché",
            "year": 1912,
            "period_label": "Belle Époque",
            "bearing": 135,
            "field_of_view": 60,
            "image_thumb_url": "/api/v1/media/...",
            "image_display_url": "/api/v1/media/...",
            "photographer": "Nom Photographe",
            "archive_source": "Archives Municipales",
            "archive_reference": "21Fi45",
            "license": "Domaine Public"
          }
        }
      ]
    }
    ```
- **Clustering MapLibre GL JS :**
  - Source GeoJSON avec `cluster: true`, `clusterMaxZoom: 14`, `clusterRadius: 50`.
  - Couche `circle` avec cercles de taille et couleur proportionnelles au nombre de points (`step` expression).
  - Couche `symbol` avec `text-field: '{point_count_abbreviated}'`.
- **Réactivité et État Frontend :**
  - Store Pinia ou état composable pour la sélection de la photo active et le filtrage.
  - Synchronisation bidirectionnelle avec l'URL (`vue-router` query params).

## Cross-Story Dependencies

- **Story 3.1** met en place la route publique GeoJSON, la carte publique MapLibre GL, le clustering vectoriel et la détection du territoire.
- **Story 3.2** s'appuiera sur la source de Story 3.1 pour afficher les marqueurs non groupés orientés et les cônes de vue interactifs.
- **Story 3.3** utilisera la sélection du marqueur pour ouvrir la fiche détaillée et la visionneuse plein écran.

