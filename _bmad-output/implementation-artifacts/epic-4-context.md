# Epic 4 Context: Création & Découverte de Storymaps Narratives (Scrollytelling & Audio)

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Permettre aux auteurs et conservateurs de composer des parcours géohistoriques thématiques articulés en étapes séquentielles associant photos d'archives, cadrages cartographiques 3D/cinématographiques et documents sonores, et d'offrir au public un lecteur immersif en scrollytelling avec synchronisation automatique de la caméra cartographique et catalogue territorial des récits.

## Stories

- **Story 4.1: Modèle de Données et API des Storymaps et Chapitres**
  - Modèles relationnels PostgreSQL/SQLAlchemy `Storymap` et `StorymapStep` avec isolation territoriale (`territory_id`) et contrôle de statut (`draft` / `published`).
  - Endpoints d'administration sécurisés (`POST`, `GET`, `PUT`, `DELETE /api/v1/admin/storymaps`) pour gérer les récits et leurs étapes ordonnées.
  - Route publique de consultation `GET /api/v1/public/storymaps/{slug}` retournant le récit et ses étapes uniquement si le statut est `published`.
- **Story 4.2: Studio d'Édition et d'Ordonnancement des Storymaps**
  - Interface d'administration pour composer le récit : ordonnancement par glisser-déposer, saisie Markdown, sélection d'une photo d'archive, capture du cadrage caméra de la carte (`lat`, `lng`, `zoom`, `bearing`, `pitch`), et téléversement de fichier audio MP3.
- **Story 4.3: Lecteur Public de Storymap en Scrollytelling avec Caméra Synchronisée et Audio**
  - Lecteur plein écran grand public synchronisé : le défilement vertical (*scrollytelling*) déclenche des transitions cartographiques cinématographiques fluides (`flyTo`), affiche la photo en grand format et pilote la lecture audio étape par étape.
- **Story 4.4: Catalogue Public des Récits et Navigation Territoriale**
  - Page catalogue public listant les parcours historiques publiés du territoire actif avec vignettes de couverture, durée estimée et bascule vers le lecteur immersif ou retour vers la carte générale.

## Requirements & Constraints

- **AD-2 (Isolation multi-territoire) :** Clé étrangère obligatoire `territory_id` sur la table `storymaps`. Toutes les requêtes filtrent par le territoire actif (`X-Territory-Slug` ou sous-domaine/défaut).
- **AD-5 (Cloisonnement et sécurité des accès) :**
  - Les routes d'administration `/api/v1/admin/storymaps` exigent une authentification JWT valide (`contributor` ou `superadmin`).
  - Les routes publiques `/api/v1/public/storymaps` n'exposent que les storymaps avec `status = 'published'` appartenant au territoire actif.
- **Intégrité relationnelle :**
  - Les étapes `storymap_steps` sont ordonnées via `step_order` (0-indexed ou 1-indexed séquentiel).
  - La suppression d'une storymap entraîne la suppression en cascade de ses étapes (`cascade="all, delete-orphan"`).
  - Le lien avec une photo d'archive (`photo_id`) est optionnel ; si la photo est supprimée, la référence passe à `NULL` sans détruire l'étape du récit.
- **Format caméra :** Chaque étape enregistre la position de la caméra cartographique MapLibre GL : `camera_lat` (-90 à 90), `camera_lng` (-180 à 180), `camera_zoom` (0 à 22), `camera_bearing` (0 à 360), `camera_pitch` (0 à 85).
- **Format multimédia :** Les couvertures d'images et les pistes sonores (`.mp3`) sont stockées via l'adaptateur de stockage unifié (`MediaStorageAdapter`).

## Technical Decisions

- **Modèles de base :**
  - `Storymap` : `id`, `territory_id`, `author_user_id`, `slug` (unique par territoire), `title`, `summary`, `cover_image_path`, `status` (`PhotoStatus` ou `StorymapStatus` : `draft` / `published`), `created_at`, `updated_at`.
  - `StorymapStep` : `id`, `storymap_id`, `photo_id` (nullable), `step_order`, `title`, `content_markdown`, `audio_file_path` (nullable), `camera_lat`, `camera_lng`, `camera_zoom`, `camera_bearing`, `camera_pitch`, `created_at`.
- **Slug territorial :** Génération automatique d'un slug URL-friendly normalisé à partir du titre si non fourni.
- **Résolution des URLs médias :** Les chemins de fichiers (`cover_image_path`, `audio_file_path`) sont résolus vers les URLs publiques via `resolve_media_url`.

## Cross-Story Dependencies

- **Story 4.1** fournit les fondations BDD, migrations, schémas Pydantic et endpoints API REST nécessaires au studio d'édition (Story 4.2), au lecteur public (Story 4.3) et au catalogue (Story 4.4).
- Les étapes peuvent référencer des clichés de l'**Epic 2** via `photo_id`.

