---
title: 'Story 3.3: Fiche Détaillée du Cliché et Visionneuse Plein Écran'
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-3-context.md'
  - '_bmad-output/implementation-artifacts/spec-3-2-marqueurs-orientes-cones-webgl.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Actuellement, le clic sur un marqueur ou sur l'infobulle n'offre qu'un aperçu miniature de 240px sans accès aux métadonnées patrimoniales complètes (fonds d'archives, cote, licence, source), sans possibilité d'explorer l'image haute définition en plein écran, et sans URL partageable directement.

**Approach:** 
1. Concevoir et intégrer un volet d'exploration contextuel rétractable responsive : tiroir latéral (*slide-over drawer*) à droite sur desktop et feuille modale inférieure (*bottom sheet*) sur mobile affichant l'ensemble des métadonnées archivistiques et patrimoniales.
2. Développer une visionneuse plein écran (*lightbox*) haute performance avec commandes de zoom/pan (molette, boutons +/- et gestes tactiles) permettant d'examiner les détails historiques en pleine résolution.
3. Synchroniser l'état de la photo sélectionnée avec le paramètre d'URL `?photo={id}` avec prise en charge du deep linking au chargement et de la navigation historique du navigateur (`popstate`).

## Boundaries & Constraints

**Always:**
- Le volet doit présenter obligatoirement : le titre, l'image `display`, l'année/période, le photographe, le fonds d'archives et la cote, la licence patrimoniale (NFR-4) et le lien vers la notice d'origine.
- La visionneuse plein écran doit supporter le zoom et le déplacement (*pan*) à la souris et au tactile avec possibilité de réinitialiser la vue et de fermer via touche `Échap` ou bouton dédié.
- L'URL doit refléter l'identifiant de la photo active (`?photo={uuid}`) et se mettre à jour sans rechargement de page (`history.pushState` / `replaceState`).
- Si un visiteur arrive avec `?photo={uuid}` dans l'URL, la carte doit se centrer automatiquement sur le cliché, ouvrir son infobulle, projeter son cône de vue et déployer son volet détaillé.
- Un bouton d'action doit permettre de copier en un clic le lien direct de partage avec retour visuel immédiat.

**Never:**
- Pas d'ajout de dépendance lourde de routage ou de lightbox externe : utilisation de Vue 3 réactif natif et de l'API History du navigateur.
- Pas de fuite de métadonnées sensibles (aucun identifiant d'auteur interne ni chemin de stockage brut exposé).
- Pas d'obstruction totale de la carte sur grand écran : le volet desktop reste latéral et permet de continuer à observer le contexte territorial.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clic sur "Consulter la fiche" ou marqueur | Clic utilisateur sur un cliché | Ouverture fluide du volet latéral (desktop) ou de la bottom sheet (mobile) avec toutes les métadonnées | N/A |
| Clic sur l'image du volet | Clic / Tap sur la photo dans le volet | Ouverture de la lightbox plein écran avec l'image haute définition et contrôles de zoom | Fallback sur `image_display_url` si `image_original_url` absent |
| Partage par lien direct | Arrivée avec `?photo=uuid-valide` | Sélection automatique, centrage cartographique (`flyTo`), projection du cône et ouverture du volet | N/A |
| Lien direct avec ID inexistant ou non publié | Arrivée avec `?photo=uuid-inconnu` | Message toast/notification discret "Photo introuvable", nettoyage du paramètre URL, carte centrée sur le territoire | Notification d'erreur sans crash |
| Fermeture du volet ou de la lightbox | Clic sur la croix, touche `Échap` ou backdrop | Fermeture du composant, retrait du paramètre `?photo` de l'URL, désélection du cliché | N/A |
| Navigation historique du navigateur | Précédent / Suivant dans l'historique | Réactivité sur l'événement `popstate` synchronisant l'ouverture/fermeture du volet | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/types/photo.ts` -- Interfaces existantes `PhotoGeoJsonProperties`, `PhotoGeoJsonFeature`, `Photo`.
- `frontend/src/services/api.ts` -- Méthodes existantes `getPublicPhotos` et `getPublicPhoto(id)`.
- `frontend/src/components/public/PhotoDetailDrawer.vue` -- Nouveau composant responsive : volet latéral desktop et feuille modale mobile avec métadonnées d'archives, bouton de partage et déclencheur lightbox.
- `frontend/src/components/public/PhotoLightbox.vue` -- Nouveau composant : visionneuse plein écran modale avec zoom/pan interactif, raccourcis clavier et support tactile.
- `frontend/src/components/public/PublicMapViewer.vue` -- Intégration de la sélection bidirectionnelle, synchronisation deep linking `?photo={id}`, gestion du centrage `flyTo` et émission des événements d'ouverture.
- `frontend/src/App.vue` -- Coordination du switch d'onglets lors d'un accès direct par URL avec paramètre photo.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/components/public/PhotoLightbox.vue` -- Créer la visionneuse plein écran avec gestion du zoom (molette, boutons), pan interactif, touche `Escape` et vue réinitialisable.
- [x] `frontend/src/components/public/PhotoDetailDrawer.vue` -- Créer le volet latéral rétractable desktop & bottom sheet mobile avec affichage ordonné des métadonnées patrimoniales et action de partage.
- [x] `frontend/src/components/public/PublicMapViewer.vue` -- Intégrer les composants du volet et de la lightbox, brancher la synchronisation d'URL bidirectionnelle (`?photo={id}`) et le centrage automatique.
- [x] `frontend/src/App.vue` -- Assurer que la présence de `?photo=` bascule automatiquement sur l'onglet Découverte cartographique au montage.
- [x] `frontend/tests/` ou script de validation -- Vérifier la synchronisation de l'URL et l'intégrité du typage TypeScript via `vue-tsc`.

**Acceptance Criteria:**
- Given un marqueur sélectionné sur la carte, When le visiteur clique sur le marqueur ou sur l'aperçu rapide, Then un volet latéral (desktop) ou une feuille modale (mobile) s'ouvre avec le titre, l'image WebP optimisée, la date/période, le photographe, le fonds d'archives et la cote, la licence et le lien vers la notice d'origine.
- Given le volet ouvert, When le visiteur clique sur l'image, Then une visionneuse plein écran s'ouvre permettant de zoomer et de naviguer dans l'image haute définition.
- Given une photo ouverte dans le volet ou la visionneuse, Then l'URL du navigateur intègre l'identifiant de la photo (`?photo=uuid`), permettant de partager la vue exacte par lien direct.

## Implementation Notes

- **PhotoDetailDrawer (Responsive Contextual Drawer) :**
  - Desktop : volet latéral ancré à droite (`w-[420px] h-full`), fond sombre translucide `bg-slate-900/95 backdrop-blur-md` maintenant le contexte cartographique visible.
  - Mobile : bottom sheet ancrée en bas avec poignée de glissement tactile (`drag handle`) et hauteur maximale de 85vh.
  - Métadonnées patrimoniales ordonnées (NFR-4) : fonds d'archives, cote/référence, auteur/photographe, date/période, licence patrimoniale, lien externe vers notice originale d'archives, azimut et coordonnées GPS.
  - Bouton de partage direct avec copie en un clic dans le presse-papiers (`?photo=id`) et retour visuel immédiat ("Lien copié !").
- **PhotoLightbox (Visionneuse Plein Écran HD & Pan/Zoom) :**
  - Rendu par transformation CSS GPU-accélérée : `transform: translate3d(x, y, 0) scale(s)`.
  - Contrôles de zoom natifs : molette de la souris avec zoom centré sur la position du curseur, boutons +/- et bouton 1:1 de réinitialisation, double-clic basculant 1x/2.5x, et support tactile multipoint (pinch-to-zoom).
  - Déplacement interactif fluide par Pointer Events (`pointerdown`, `pointermove`, `pointerup`).
  - Fermeture rapide via touche `Échap`, bouton dédié ou clic backdrop.
  - Résolution d'image haute définition privilégiant `image_original_url` avec fallback sur `image_display_url`.
- **Synchronisation d'URL & Deep Linking :**
  - Arrivée avec `?photo=uuid` : sélection automatique, centrage cartographique (`flyTo`), projection du cône de vue WebGL et ouverture du volet.
  - Bascule automatique sur l'onglet Découverte dans `App.vue` si `?photo=` est présent.
  - Cas d'un ID inexistant ou non publié : toast discret "Photographie introuvable ou non publiée", suppression propre du paramètre d'URL sans rechargement, et recentrage sur le territoire sans crash.
  - Gestion historique du navigateur via écoute `popstate` synchronisant l'état du volet et de la carte.

## Review Triage Log

- **ISSUE-01 (Shared utility extraction):** Fonctions pures extraites dans `frontend/src/utils/photoViewer.ts` (`getUrlPhotoId`, `computePhotoUrl`, `clampZoom`, `calculateZoomToCursor`, `resolveDisplayImageUrl`, `resolveLightboxImageUrl`). Tests unitaires `photo_viewer_logic.test.mjs` branchés directement sur ces fonctions exportées.
- **ISSUE-02 (Escape key coordination):** `PhotoLightbox` intercepte et stoppe la propagation immédiate (`e.stopImmediatePropagation()`). `PhotoDetailDrawer` reçoit `isLightboxOpen` et n'écoute `Escape` que lorsque la lightbox est fermée.
- **ISSUE-03 (State desynchronization on filter update):** `PublicMapViewer` invoque `closeDrawer({ updateUrl: true, pushHistory: false })` lors d'un filtrage éliminant la photo sélectionnée.
- **ISSUE-04 (Browser history hygiene):** `closeDrawer()` utilise `replaceState` par défaut (`pushHistory: false`) pour éviter d'encombrer l'historique de retour arrière.
- **ISSUE-05 (Pinch/Pointer stability & transition drift):** Filtrage des touches secondaires non-primaires dans `handlePointerDown`, désactivation temporaire de la transition CSS pendant le zoom molette, et surveillance réactive de `imageUrl` pour réinitialiser le zoom.
- **ISSUE-06 (Race condition guard):** Dans `selectPhotoById(id)`, vérification `if (selectedPhotoId.value !== id || !isMounted) return` après résolution asynchrone pour écarter tout résultat obsolète.

## Verification

- `node --test frontend/tests/photo_viewer_logic.test.mjs` : 11/11 tests unitaires validés (synchronisation URL, deep linking, contraintes de zoom/pan, invariant de curseur, résolutions de fallbacks).
- `cd frontend && vue-tsc -b` : 100% OK sans aucune erreur TypeScript.
- `python3 -m unittest backend/tests/test_geo_math.py` : 100% OK (calculs géodésiques et azimuts).

## Design Notes

- **Ergonomie du volet (Drawer) :**
  - Desktop : volet latéral ancré à droite (largeur 420px), superposition avec ombre portée et fond sombre translucide `bg-slate-900/95 backdrop-blur-md` pour maintenir la visibilité sur la carte sous-jacente.
  - Mobile : bottom sheet ancrée en bas avec poignée de glissement (*drag handle*), hauteur max 85vh et défilement vertical doux.
- **Visionneuse plein écran (Lightbox Pan & Zoom) :**
  - Rendu par transformation CSS GPU-accélérée : `transform: translate3d(x, y, 0) scale(s)`.
  - Pas de bibliothèque tierce : gestion native des événements `wheel`, `pointerdown`, `pointermove`, `pointerup` pour une fluidité maximale et zéro latence.
- **Synchronisation d'URL sans rechargement :**
  - Utilisation de `window.history.pushState` lors de la sélection manuelle et `window.history.replaceState` pour les mises à jour sans pollution de l'historique de retour arrière.
  - Écoute de l'événement `window.onpopstate` pour garantir un comportement natif lors de l'utilisation des boutons Précédent/Suivant du navigateur.

