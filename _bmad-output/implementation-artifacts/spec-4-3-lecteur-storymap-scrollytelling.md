---
title: "Story 4.3: Lecteur Public de Storymap en Scrollytelling avec Caméra Synchronisée et Audio"
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
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Les récits géohistoriques créés dans le studio ne disposent pas encore d'un lecteur public immersif permettant aux visiteurs de parcourir une Storymap de manière vivante et interactive, avec synchronisation dynamique entre le défilement du texte narratif (*scrollytelling*), les mouvements cinématographiques de la carte 3D (`flyTo`) et la lecture des documents sonores d'archives.

**Approach:** 
1. Concevoir et implémenter le lecteur grand public plein écran immersif (`StorymapReader.vue`) accessible par URL directe (`?storymap={slug}` ou `/storymaps/{slug}`).
2. Intégrer un mécanisme de défilement narratif vertical (*scrollytelling*) basé sur `IntersectionObserver` qui, au franchissement de chaque chapitre, pilote la caméra MapLibre GL en douceur (`map.flyTo()`) vers les coordonnées, le zoom, l'orientation (`bearing`) et l'inclinaison 3D (`pitch`) enregistrées.
3. Afficher les clichés d'archives associés en grand format avec légende et lien vers la fiche patrimoniale ou la visionneuse haute résolution.
4. Intégrer un lecteur audio compact et synchronisé qui diffuse le document sonore du chapitre actif et coupe proprement la lecture lors de la transition vers un autre chapitre.
5. Assurer une ergonomie 100% responsive (volet latéral semi-transparent sur desktop, cartes flottantes au défilement vertical sur mobile) avec navigation au clavier et barre de progression.

## Boundaries & Constraints

**Always:**
- Le lecteur ne charge et n'affiche que les storymaps ayant le statut `published` appartenant au territoire actif (AD-5). Tout récit en statut `draft` renvoie vers une page d'erreur 404 conviviale.
- Au passage d'un chapitre à l'autre via défilement vertical, la carte doit réaliser une transition cinématique fluide à 60 fps (`map.flyTo({ duration: 2000, essential: true })`).
- Si l'étape active comporte un fichier audio (`audio_url`), un lecteur audio intégré permet la lecture/pause ; si le visiteur défile vers une autre étape, la piste audio précédente doit se couper automatiquement pour éviter toute superposition sonore cacophonique.
- L'URL du navigateur reflète la storymap consultée (`?storymap={slug}`) pour permettre le partage direct par lien direct, et un bouton d'action permet de quitter le lecteur pour regagner l'exploration libre.
- La navigation au clavier (Flèches Haut/Bas ou PageUp/PageDown) permet de progresser d'une étape à l'autre de manière fluide et accessible.

**Never:**
- Pas d'écriture de données côté lecteur : composant public de consultation purement en lecture seule.
- Pas de blocage du thread UI principal lors des transitions cartographiques : utilisation exclusive des animations WebGL natives de MapLibre GL.
- Pas de fuite de métadonnées sensibles (chemins de fichiers internes ou identifiants privés).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ouverture d'une storymap publiée | Navigation vers `?storymap=mon-slug` | Chargement du récit, affichage du Hero d'accroche et positionnement de la carte sur le 1er cadrage | Notification et redirection si slug inconnu ou non publié |
| Défilement vers le chapitre suivant | Scroll vertical franchissant le seuil du chapitre 2 | `IntersectionObserver` active le chapitre 2, la caméra exécute un `flyTo` vers le cadrage 2, la photo 2 s'affiche | N/A |
| Écoute audio sur chapitre avec document sonore | Clic sur "Lecture" dans le lecteur audio du chapitre | Déclenchement de la lecture audio | Affichage d'un message discret si le fichier ne peut être chargé |
| Défilement pendant la lecture audio | Défilement vers un chapitre suivant pendant qu'un son joue | La lecture audio du chapitre précédent est mise en pause et remise à zéro automatiquement | N/A |
| Clic sur la photo d'un chapitre | Clic sur la vignette photo grand format | Ouverture de la visionneuse plein écran HD (`PhotoLightbox`) pour examiner les détails | N/A |
| Quitter le lecteur | Clic sur le bouton "← Quitter" ou touche Échap sur l'accueil | Fermeture du lecteur, retrait de `?storymap=` de l'URL et retour à la carte d'exploration générale | N/A |
| Écran tactile mobile | Défilement au doigt sur smartphone | Cartes textuelles défilant au-dessus de la carte avec indicateur d'étape compact | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/services/api.ts` -- Ajout de `storymapApi.getPublicStorymap(slug)` consommant `GET /api/v1/storymaps/{slug}`.
- `frontend/src/utils/storymapReader.ts` -- Fonctions utilitaires pures (extraction de cible caméra, parsing de slug, calcul de progression d'étapes, gestion de coupure audio).
- `frontend/src/components/public/StorymapReader.vue` -- Nouveau composant : lecteur immersif de storymap en scrollytelling avec caméra synchronisée MapLibre GL, affichage des photos d'archives et audio coordonné.
- `frontend/src/App.vue` -- Intégration du lecteur grand public via le paramètre d'URL `?storymap={slug}` et gestion de l'état de retour.
- `frontend/tests/storymap_reader_logic.test.mjs` -- Tests unitaires automatisés validant la logique d'extraction caméra, de gestion audio et de progression.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/services/api.ts` -- Ajouter `getPublicStorymap(slug)` à `storymapApi` avec typage strict.
- [x] `frontend/src/utils/storymapReader.ts` -- Créer le module utilitaire pour la logique de calcul de caméra, progression et règles audio.
- [x] `frontend/src/components/public/StorymapReader.vue` -- Créer le lecteur immersif scrollytelling avec intégration MapLibre GL, `IntersectionObserver`, affichage photo, Markdown et lecteur audio.
- [x] `frontend/src/App.vue` -- Intégrer le lecteur dans l'application avec synchronisation d'URL bidirectionnelle (`?storymap={slug}`).
- [x] `frontend/tests/storymap_reader_logic.test.mjs` -- Écrire et exécuter la suite de tests unitaires validant l'ensemble des scénarios de logique du lecteur.

**Acceptance Criteria:**
- Given une storymap publiée avec des étapes ayant des cadrages cartographiques distincts, When le visiteur fait défiler la page verticalement, Then la carte s'anime automatiquement avec `flyTo` pour cadrer la vue sur chaque étape.
- Given une étape associée à une photo d'archive, When l'étape devient active, Then la photo s'affiche avec sa légende et peut être agrandie en plein écran.
- Given une étape avec fichier audio, When l'utilisateur fait défiler la page vers une autre étape, Then la lecture audio en cours est immédiatement coupée.
- Given le lecteur ouvert, When le visiteur clique sur le bouton de sortie, Then le lecteur se ferme et l'URL est nettoyée sans rechargement de page.

## Implementation Notes

- Lecteur immersif 100% responsive avec fond cartographique MapLibre GL animé à 60 fps (`flyTo` avec courbe cinématique `1.42` et durée `2200ms`).
- Panneau vertical de cartes scrollytelling avec séparation physique généreuse (`min-h-[60vh]`, `space-y-24`) prévenant toute oscillation intempestive de caméra.
- Écoute de l'IntersectionObserver synchronisée sur le défilement et arrêt automatique de la piste sonore active au franchissement de chapitre.
- Prise en charge des photographies patrimoniales HD avec ouverture de la visionneuse plein écran (`PhotoLightbox`).
- Synchronisation complète de l'URL (`?storymap={slug}` et chemins `/storymaps/{slug}`) avec restauration automatique du mode Découverte lors de la fermeture.

## Spec Change Log

- 2026-10-31: Implémentation du lecteur scrollytelling, synchronisation MapLibre GL, lecteur audio et deep-linking d'URL.

## Review Triage Log

- **[P1 - Fixé] HUNTER-4.3-1 : Course asynchrone `isLoading` neutralisant l'IntersectionObserver.**
  - *Constat :* `isLoading.value = false` était placé dans `finally`, ce qui masquait le conteneur scrollytelling lors de l'exécution de `setupObserver()`, laissant les cartes non observées.
  - *Action :* `isLoading.value = false` a été basculé avant `await nextTick()`, garantissant le montage DOM complet avant l'attachement de l'observateur.
- **[P1 - Fixé] HUNTER-4.3-2 : Échec d'extraction de slug sur objet `Location` avec `/storymaps/{slug}`.**
  - *Constat :* La présence de la clé `search` vide dans `window.location` provoquait un retour `null` prématuré sans évaluer le `pathname`.
  - *Action :* Prise en charge explicite du `pathname` et nettoyage des fragments `#` dans `extractStorymapSlug`.
- **[P1 - Fixé] HUNTER-4.3-3 : Anomalie de l'index d'épilogue (`data-step-index="999"`).**
  - *Constat :* L'indice 999 affichait "Chapitre 1000 sur 4", bloquait la navigation `↑` (cherche 998) et ramenait la caméra au chapitre 1.
  - *Action :* Plafonnement de la progression à 100%, libellé "Conclusion", navigation retour pointant sur le dernier chapitre, et maintien de la caméra sur le dernier cadre.
- **[P1 - Fixé] HUNTER-4.3-4 : Redirection vers Studio Admin lors de la fermeture du lecteur.**
  - *Constat :* La fermeture du lecteur laissait `currentTab` sur `'studio'` pour les visiteurs arrivant par lien direct.
  - *Action :* Forçage systématique de `currentTab.value = 'decouverte'` lors de l'ouverture et de la fermeture du lecteur.
- **[P2 - Fixé] HUNTER-4.3-5 : Hauteur minimale sur les cartes de chapitres.**
  - *Action :* Ajout de `min-h-[60vh]` sur `.scrolly-step-card` pour stabiliser les franchissements de seuils.
- **[P2 - Fixé] HUNTER-4.3-6 : Message d'erreur discret pour documents sonores indisponibles.**
  - *Action :* Ajout de `audioErrorStepIndex` et affichage du badge discret en cas d'erreur réseau ou codec.
- **[P2 - Fixé] HUNTER-4.3-7 : Synchronisation plein écran via `fullscreenchange`.**
  - *Action :* Écouteur global pour maintenir le témoin de plein écran à jour lors de l'appui sur Échap/F11.
- **[P3 - Fixé] HUNTER-4.3-8 : Sécurisation de `formatAudioDuration` face à `Infinity`.**
  - *Action :* Utilisation de `Number.isFinite(seconds)`.
- **[P2 - Fixé] VG-URL : Extraction de `cleanStorymapUrl` et tests automatisés.**
  - *Action :* Fonction utilitaire testée avec 23 assertions unitaires passantes.

## Design Notes

- **Architecture Scrollytelling :**
  - Desktop : Carte plein écran en arrière-plan fixe, avec un panneau narratif latéral gauche translucide (`w-[460px] bg-slate-950/85 backdrop-blur-md`) contenant les cartes de chapitres espacées avec marge généreuse (`min-h-[80vh]`).
  - Mobile : Carte occupant le fond de l'écran, avec cartes narratives flottantes défilantes au-dessus de la carte (`snap-y` optionnel ou défilement naturel).
- **Synchronisation MapLibre GL cinématique :**
  - Utilisation de `map.flyTo({ center: [lng, lat], zoom, bearing, pitch, duration: 2200, essential: true, curve: 1.42 })` pour un rendu de travelling cinématique fluide digne d'un documentaire géohistorique.
- **Coordination audio :**
  - Référence unique `activeAudioElement: HTMLAudioElement | null` garantissant qu'une seule piste sonore ne peut jouer à la fois.

