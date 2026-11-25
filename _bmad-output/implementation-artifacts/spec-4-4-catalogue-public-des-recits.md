---
title: "Story 4.4: Catalogue Public des Récits et Navigation Territoriale"
type: 'feature'
created: '2026-10-31'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-4-context.md'
  - '_bmad-output/implementation-artifacts/spec-4-1-modele-et-api-storymaps.md'
  - '_bmad-output/implementation-artifacts/spec-4-2-studio-edition-storymaps.md'
  - '_bmad-output/implementation-artifacts/spec-4-3-lecteur-storymap-scrollytelling.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le grand public et les visiteurs disposent désormais d'une carte d'exploration et d'un lecteur immersif de storymaps (Story 4.3), mais il manque un point d'entrée fédérateur permettant de découvrir, parcourir et sélectionner l'ensemble des récits géohistoriques publiés pour le territoire actif, avec leurs couvertures, estimations de durée, thématiques et documents sonores.

**Approach:**
1. Concevoir et implémenter le catalogue public des récits (`StorymapPublicCatalog.vue`) intégré dans l'expérience de découverte citoyenne.
2. Ajouter la méthode `listPublicStorymaps()` à `storymapApi` dans `frontend/src/services/api.ts` consommant le endpoint `GET /api/v1/storymaps`.
3. Développer des utilitaires purs de calcul d'estimation de lecture et de filtrage (`storymapCatalog.ts`).
4. Intégrer un onglet de navigation dédié "📖 Récits & Storymaps" dans l'en-tête principal de `App.vue`, avec synchronisation bidirectionnelle de l'état d'URL (`?tab=recits`).
5. Permettre le déclenchement direct du lecteur immersif (`StorymapReader.vue`) au clic sur une vignette de récit (`?storymap={slug}`).
6. Rédiger une suite complète de tests unitaires automatisés (`storymap_catalog_logic.test.mjs`).

## Boundaries & Constraints

**Always:**
- Le catalogue n'affiche que les récits ayant le statut `published` rattachés au territoire actif (AD-2, AD-5). Aucun brouillon ne doit être exposé.
- Chaque carte de récit affiche sa couverture (ou un visuel de secours géohistorique soigné), son titre, son résumé, le nombre de chapitres, une estimation du temps de lecture et un badge "🎧 Audio" si des documents sonores sont inclus.
- Le filtrage par texte et la recherche sont réactifs avec debounce pour une sensation instantanée à 60 fps.
- L'URL du navigateur reflète l'onglet actif (`?tab=recits` ou retour à la carte `?tab=carte`).
- Clic sur "Découvrir ce récit" ouvre immédiatement le lecteur immersif `StorymapReader` sans rechargement de page.

**Never:**
- Pas d'exposition de métadonnées sensibles (chemins de stockage interne, identifiants d'utilisateurs privés).
- Pas de requêtes d'écriture sur cette vue publique de consultation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Consultation du catalogue | Navigation vers l'onglet "Récits" ou `?tab=recits` | Chargement et affichage des cartes de storymaps publiées du territoire | Affichage d'un message convivial si réseau indisponible |
| Recherche textuelle | Saisie d'un mot-clé dans la barre de recherche | Filtrage instantané des récits dont le titre ou le résumé correspond | Message "Aucun récit ne correspond à votre recherche" avec bouton de réinitialisation |
| Filtre "Documents sonores" | Coche du filtre "Avec archives audio" | Affichage uniquement des récits comportant au moins une étape avec document sonore | N/A |
| Territoire sans aucun récit publié | Territoire nouvellement créé ou sans storymap | État vide explicatif invitant à explorer la photothèque sur la carte | N/A |
| Clic sur une storymap | Clic sur la vignette ou bouton "Commencer la visite" | Ouverture du lecteur immersif plein écran (`?storymap={slug}`) | N/A |
| Retour depuis le lecteur | Clic sur "← Quitter" dans le lecteur | Fermeture du lecteur et retour direct sur la vue courante | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/services/api.ts` -- Ajout de `storymapApi.listPublicStorymaps()` avec typage strict et support `AbortSignal`.
- `frontend/src/utils/storymapCatalog.ts` -- Fonctions utilitaires pures (estimation de durée, filtrage, tri, détection audio).
- `frontend/src/components/public/StorymapPublicCatalog.vue` -- Nouveau composant : catalogue public des récits géohistoriques du territoire avec recherche, filtres et cartes immersives.
- `frontend/src/App.vue` -- Intégration de l'onglet public "📖 Récits & Storymaps" et gestion des transitions avec le lecteur.
- `frontend/tests/storymap_catalog_logic.test.mjs` -- Tests unitaires automatisés validant la logique de filtrage, tri et calcul de durée.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/services/api.ts` -- Ajouter `listPublicStorymaps` à `storymapApi`.
- [x] `frontend/src/utils/storymapCatalog.ts` -- Implémenter les utilitaires purs (durée estimée, filtres audio, tri).
- [x] `frontend/src/components/public/StorymapPublicCatalog.vue` -- Créer le catalogue public avec recherche réactive, filtres thématiques et cartes visuelles.
- [x] `frontend/src/App.vue` -- Ajouter l'onglet de navigation "📖 Récits" et connecter le déclenchement du lecteur immersif.
- [x] `frontend/tests/storymap_catalog_logic.test.mjs` -- Écrire et exécuter la suite de tests unitaires automatisés.

**Acceptance Criteria:**
- Given des récits publiés sur le territoire actif, When le visiteur consulte l'onglet "Récits", Then l'ensemble des récits publiés s'affiche sous forme de grille de vignettes avec leurs résumés, chapitres et durées estimées.
- Given le catalogue affiché, When le visiteur saisit une requête dans la barre de recherche, Then la liste se filtre instantanément sans rechargement.
- Given le catalogue affiché, When le visiteur active le filtre audio, Then seuls les récits comportant des archives sonores restent visibles.
- Given une vignette de récit, When le visiteur clique sur le récit, Then le lecteur immersif de scrollytelling s'ouvre avec l'URL synchronisée `?storymap={slug}`.

## Implementation Notes

- **Architecture Pure des Utilitaires :** La logique de recherche (insensible aux diacritiques/accents), de calcul du temps de lecture (~2.5 min/étape) et de détection de pistes sonores a été isolée dans `storymapCatalog.ts` et couverte par 13 tests unitaires exhaustifs.
- **Réactivité Territoriale :** `StorymapPublicCatalog.vue` surveille les changements de `territorySlug` pour recharger automatiquement les récits du territoire sans rechargement de page.
- **Gestion des Concurrences Réseau :** Utilisation d'un `AbortController` pour annuler toute requête en vol lors d'un changement de filtre rapide ou de territoire.

## Spec Change Log

- 2026-10-31: Implémentation complète et revue tri-agents de la Story 4.4. Passage au statut `done`.

## Review Triage Log

- **P1 (Popstate URL state stuck on navigation back) :** Dans `App.vue:syncUrlState()`, naviguer en arrière depuis `?tab=recits` vers `/` ne réinitialisait pas l'onglet sur `decouverte` car la condition vérifiait uniquement des valeurs explicites sans clause de repli. Corrigé en forçant le repli sur `decouverte` quand `tab` est absent.
- **P1 (Fermeture de storymap et pile d'historique) :** Remplacement de `pushState` par `replaceState` dans `handleCloseStorymap()` pour éviter de piéger l'utilisateur dans une boucle de retours arrière après consultation d'un récit.
- **P2 (Normalisation des accents en recherche) :** Les recherches en français ("debarquement" pour "débarquement", "epoque" pour "Époque") échouaient. Implémentation de `normalizeSearchString` via décomposition Unicode NFD dans `storymapCatalog.ts`.
- **P2 (Debounce de recherche) :** Ajout d'un debounce de 200 ms sur la saisie textuelle pour préserver les 60 fps sur mobile et éviter les saccades lors de la frappe.
- **P2 (Annulation de requêtes obsolètes) :** Branchement d'un `AbortController` sur `storymapApi.listPublicStorymaps()` pour neutraliser les conditions de concurrence réseau.
- **P3 (Fallback d'erreur d'image de couverture) :** Ajout d'un écouteur `@error` basculant proprement vers une icône décorative de secours si une URL d'image renvoie une 404 ou est corrompue.
- **P3 (Accessibilité clavier des cartes) :** Ajout des attributs `role="button"`, `tabindex="0"` et de l'écouteur `@keydown.enter` pour une navigation intégrale au clavier.

## Design Notes

- **Ergonomie du Catalogue :**
  - Grille responsive (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`) mettant en valeur les couvertures d'archives.
  - En-tête territorial engageant valorisant le patrimoine local et le nombre d'itinéraires disponibles.
  - Badges visuels distinctifs : durée de parcours estimée (`~10 min`), nombre d'étapes (`4 chapitres`), archive sonore (`🎧 Audio`).
