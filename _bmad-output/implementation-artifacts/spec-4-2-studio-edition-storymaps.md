---
title: "Story 4.2: Studio d'Édition et d'Ordonnancement des Storymaps"
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-4-context.md'
  - '_bmad-output/implementation-artifacts/spec-4-1-modele-et-api-storymaps.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Bien que l'API et la base de données des storymaps soient opérationnelles (Story 4.1), les curateurs et auteurs de contenu historique ne disposent d'aucune interface utilisateur dans le panneau d'administration pour créer des récits, composer des étapes narratives, capturer visuellement les cadrages cartographiques MapLibre GL, lier des photos d'archives, téléverser des documents sonores MP3 et réordonner facilement les chapitres par glisser-déposer.

**Approach:** 
1. Concevoir et intégrer dans le Studio d'administration le catalogue des storymaps (`StorymapAdminCatalog.vue`) et le studio d'édition complet (`StorymapEditorModal.vue`).
2. Développer l'éditeur de chapitres séquentiels avec saisie de texte Markdown, sélecteur modal de photos d'archives issues de la photothèque territoriale, et téléversement direct de documents sonores (`.mp3`).
3. Intégrer un sélecteur cartographique interactif avec capture instantanée de la caméra MapLibre GL (`lat`, `lng`, `zoom`, `bearing`, `pitch`) et prévisualisation par animation cinématographique `flyTo`.
4. Permettre la réorganisation fluide des étapes par glisser-déposer (*drag and drop*) et boutons haut/bas, synchronisée avec l'endpoint atomique `PUT /steps/reorder`.

## Boundaries & Constraints

**Always:**
- L'interface d'édition doit permettre de renseigner les métadonnées globales : titre, résumé, statut (`draft` / `published`), couverture d'image.
- L'auteur doit pouvoir associer n'importe quelle photo publiée du territoire actif et visualiser immédiatement sa miniature et sa légende dans l'étape, avec possibilité de la détacher (`photo_id = null`).
- La capture cartographique doit extraire précisément les paramètres caméra MapLibre GL de la vue active : `lat` [-90, 90], `lng` [-180, 180], `zoom` [0, 24], `bearing` [0, 360], `pitch` [0, 85].
- Le téléversement de documents sonores doit accepter les fichiers audio courants (`.mp3`, `.m4a`, `.ogg`, `.wav`) avec lecteur de pré-écoute intégré.
- Le réordonnancement des étapes par glisser-déposer ou boutons haut/bas met à jour l'ordre séquentiel et persiste la nouvelle séquence via l'API.

**Never:**
- Pas d'accès aux photos ou récits d'un autre territoire (isolation multi-territoire stricte AD-2).
- Pas de blocage du formulaire en cas d'étape sans photo ou sans audio : ces deux éléments restent strictement optionnels.
- Pas de dépendance tierce lourde pour le drag & drop : utilisation de l'API HTML5 Drag and Drop native ou de contrôles ergonomiques haut/bas pour une robustesse maximale.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Création nouveau récit | Clic sur "Nouveau récit" dans le Studio | Ouverture du modal d'édition avec formulaire vierge et statut brouillon par défaut | N/A |
| Ajout d'une étape | Clic sur "Ajouter une étape" | Nouvelle étape initialisée avec titre par défaut et cadrage centré sur le territoire | N/A |
| Capture de vue cartographique | Déplacement de la carte et clic sur "Capturer la vue actuelle" | Renseignement automatique des champs `camera_lat`, `camera_lng`, `camera_zoom`, `camera_bearing`, `camera_pitch` avec feedback visuel | Valeurs bornées automatiquement |
| Sélection de photo d'archive | Clic sur "Choisir une photo" -> sélection d'un cliché territorial | Association de `photo_id` et affichage immédiat de la vignette et métadonnées | N/A |
| Dissociation de photo | Clic sur "Retirer la photo" de l'étape | `photo_id` passé à `null`, suppression de la miniature | N/A |
| Téléversement fichier audio | Dépôt d'un fichier `.mp3` sur l'étape | Upload vers le serveur, mise à jour du chemin audio et apparition du lecteur de pré-écoute | Message d'erreur si format invalide ou taille > 50Mo |
| Glisser-déposer d'étapes | Drag & drop de l'étape 3 vers l'étape 1 | Réorganisation visuelle immédiate et appel API `reorder` pour persister les `step_order` | Restauration de l'ordre initial en cas d'échec API |
| Publication du récit | Bascule du statut vers "Publié" et sauvegarde | Storymap mise à jour avec statut `published`, devenant visible sur le catalogue public | Validation des champs obligatoires |

</frozen-after-approval>

## Code Map

- `backend/app/api/v1/admin/storymaps.py` -- Ajout des endpoints de téléversement média : couverture (`POST /{id}/cover`) et audio de chapitre (`POST /{id}/steps/{step_id}/audio`).
- `frontend/src/types/storymap.ts` -- Interfaces TypeScript `Storymap`, `StorymapStep`, `StorymapStatus`, payloads de création et mise à jour.
- `frontend/src/services/api.ts` -- Fonctions clientes API pour les storymaps admin (CRUD, téléversement cover, téléversement audio, réordonnancement).
- `frontend/src/components/admin/StorymapAdminCatalog.vue` -- Tableau de bord d'administration des récits du territoire (liste, recherche, filtres, déclencheur d'édition, suppression).
- `frontend/src/components/admin/StorymapEditorModal.vue` -- Studio modal complet d'édition de storymap (métadonnées, liste ordonnée d'étapes avec drag-and-drop, éditeur de chapitre Markdown, sélection de photo).
- `frontend/src/components/admin/StorymapCameraPicker.vue` -- Composant cartographique MapLibre GL interactif permettant de cadrer et capturer la vue 3D (lat, lng, zoom, bearing, pitch) avec test `flyTo`.
- `frontend/src/App.vue` -- Intégration du sélecteur d'onglets au sein du Studio Admin (bascule entre "Photothèque" et "Storymaps & Récits").
- `frontend/tests/storymap_studio_logic.test.mjs` -- Tests unitaires automatisés validant la logique d'ordonnancement, de validation des cadrages caméra et de formatage des payloads.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/api/v1/admin/storymaps.py` -- Ajouter les endpoints de téléversement de couverture et de fichier audio MP3 de chapitre avec validation de type MIME et stockage unifié.
- [x] `frontend/src/types/storymap.ts` -- Créer les définitions de types TypeScript pour les storymaps, chapitres et payloads.
- [x] `frontend/src/services/api.ts` -- Implémenter les méthodes d'appel API pour l'administration des storymaps, chapitres, médias et réordonnancement.
- [x] `frontend/src/components/admin/StorymapCameraPicker.vue` -- Créer le composant de capture cartographique interactive MapLibre GL avec bouton de capture et animation `flyTo`.
- [x] `frontend/src/components/admin/StorymapEditorModal.vue` -- Créer le studio d'édition complet avec gestion des étapes, éditeur Markdown, association de photo, audio et réordonnancement par glisser-déposer.
- [x] `frontend/src/components/admin/StorymapAdminCatalog.vue` -- Créer la vue catalogue d'administration des storymaps avec filtres et actions.
- [x] `frontend/src/App.vue` -- Ajouter la navigation par onglet ("Photothèque" / "Storymaps") dans le Studio d'administration.
- [x] `frontend/tests/storymap_studio_logic.test.mjs` -- Écrire et exécuter les tests unitaires de logique front-end du studio (ordonnancement, validations caméra, calculs).

**Acceptance Criteria:**
- Given un curateur dans le studio d'administration, When il crée ou édite une storymap, Then il peut ajouter des étapes, rédiger un texte narratif en Markdown et lier une photo existante du territoire.
- Given une étape en cours d'édition, When l'auteur ajuste la carte intégrée et clique sur *"Capturer la vue actuelle"*, Then les coordonnées (`camera_lat`, `camera_lng`, `camera_zoom`, `camera_bearing`, `camera_pitch`) sont enregistrées pour cette étape.
- Given une étape avec fichier audio `.mp3`, When l'auteur téléverse le fichier, Then le document sonore est sauvegardé et un lecteur permet d'en vérifier la lecture.
- Given plusieurs étapes dans une storymap, When l'auteur les réordonne par glisser-déposer (*drag and drop*) ou boutons fléchés, Then l'ordre est mis à jour en base de données de façon atomique.

## Implementation Notes

- **Endpoints de téléversement médias :**
  - `POST /api/v1/admin/storymaps/{id}/cover` : validation du format image (JPEG/PNG/WEBP), conversion optimisée WebP via Pillow (max 2048px, q=85), purge de l'ancienne couverture et sauvegarde via `StorageDriver`.
  - `DELETE /api/v1/admin/storymaps/{id}/cover` : suppression physique et remise à `null` du chemin de couverture.
  - `POST /api/v1/admin/storymaps/{id}/steps/{step_id}/audio` : validation du format sonore (.mp3, .m4a, .ogg, .wav), vérification de la taille max (50 Mo), purge de l'ancien média et stockage unifié.
  - `DELETE /api/v1/admin/storymaps/{id}/steps/{step_id}/audio` : suppression physique du document sonore et dissociation de l'étape.
- **Capture et test cartographique cinématique :**
  - Composant `StorymapCameraPicker.vue` avec intégration MapLibre GL, réticule central de visée, curseurs d'inclinaison 3D (pitch) et d'azimut (bearing).
  - Bouton de capture instantanée avec feedback visuel et bouton *"Tester le cadrage"* déclenchant une animation cinématique `flyTo({ center, zoom, bearing, pitch, duration: 1500 })`.
- **Studio d'édition et ordonnancement :**
  - Volet gauche avec stepper des chapitres ordonnés, drag & drop HTML5 natif, boutons fléchés haut/bas pour l'accessibilité, suppression et badges d'état.
  - Volet droit avec édition du titre, Markdown avec prévisualisation bascule, sélecteur modal de photos territoriales avec détachement sans suppression, et pré-écoute audio intégrée.
- **Catalogue d'administration :**
  - `StorymapAdminCatalog.vue` avec recherche textuelle en temps réel, filtres de statut (Tous, Publiés, Brouillons), pagination et suppression en cascade sécurisée avec modale de confirmation.

## Spec Change Log

## Review Triage Log

- **ISSUE-01 (Extraction utilitaires purs) :** Création de `frontend/src/utils/storymapStudio.ts` regroupant `normalizeBearing`, `clampCameraCoordinates`, `reorderStepsLocally`, `detachPhotoFromStep`, `validateAudioFile`, `renderMarkdownPreview` et consommation directe dans les composants et tests.
- **ISSUE-02 (Validation audio stricte extension ET mime) :** Vérification conjointe `ext in ALLOWED_AUDIO_EXTENSIONS and ct in ALLOWED_AUDIO_MIMES` rejetant strictement tout format non audio.
- **ISSUE-03 (Nettoyage médias orphelins) :** Purge physique de `cover_image_path` et `audio_file_path` lors de `delete_storymap` et `delete_storymap_step`.
- **ISSUE-04 (Garde champs non-nullables) :** Protection contre l'écrasement par None de `title` et `status` lors des mises à jour.
- **ISSUE-05 (Capture Pillow élargie) :** Interception de `OSError`, `ValueError`, et `Image.DecompressionBombError` pour rejeter les images corrompues.
- **ISSUE-06 (Watcher caméra 3D) :** Prise en compte du décalage de bearing et de pitch dans `StorymapCameraPicker.vue` et affichage sécurisé des coordonnées.
- **ISSUE-07 (Restauration index actif) :** Restauration de `activeStepIndex` en cas d'erreur de réordonnancement dans `moveStep`.
- **ISSUE-08 (Test isolation multi-territoire médias) :** Ajout du test pytest `test_media_cross_territory_isolation` garantissant l'accès interdit (404) cross-territoire.

## Verification

- `docker exec hierici-backend pytest tests/test_storymaps.py` : 16/16 tests passés avec succès.
- `python3 -m unittest backend/tests/test_storymaps_logic.py` : 3/3 tests unitaires de logique passés.
- `node --loader ./frontend/tests/loader.mjs frontend/tests/storymap_studio_logic.test.mjs` : 15/15 tests passés avec succès.
- `node --loader ./frontend/tests/loader.mjs frontend/tests/photo_viewer_logic.test.mjs` : 11/11 tests passés avec succès.
- `cd frontend && node node_modules/.bin/vue-tsc -b` : 100% OK sans aucune erreur TypeScript.

## Design Notes

- **Ergonomie du Studio d'édition :**
  - Volet gauche / stepper : liste des chapitres ordonnés sous forme de cartes d'étapes compactes avec miniature photo, poignée de glissement (drag handle `⠿`), bouton de suppression et indicateurs d'audio/caméra.
  - Volet droit : éditeur contextuel du chapitre actif avec panneau scindé (texte Markdown, liaison photo, carte de cadrage avec bouton de capture proéminent, et zone audio).
- **Capture de caméra MapLibre GL :**
  - Récupère `map.getCenter()`, `map.getZoom()`, `map.getBearing()`, `map.getPitch()`.
  - Bouton *"Tester le cadrage"* déclenchant `map.flyTo({ center, zoom, bearing, pitch, duration: 1500 })` pour tester le rendu cinématique avant sauvegarde.

