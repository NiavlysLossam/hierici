---
title: "Story 5.4: Page de Présentation / Vitrine Patrimoniale (Landing Page)"
type: 'feature'
created: '2026-11-05'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-5-context.md'
  - 'frontend/src/App.vue'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:**
Les visiteurs arrivant sur la plateforme HierIci sont actuellement dirigés directement vers la carte d'exploration sans mise en contexte éditoriale, explicative ou patrimoniale préalable. Il manque une page d'accueil d'introduction valorisant le projet, ses innovations cartographiques (géoréférencement orienté, cône métrique, récits audio immersifs) et ses fonds photographiques d'archives.

**Approach:**
1. **Création du composant de présentation `HomePresentationView.vue` :**
   - Section Hero immersive mettant en lumière les 3 photographies d'époque fournies (viaduc fluvial, place du marché, façade du théâtre municipal) avec mentions de sources Gallica BnF.
   - Accroches éditoriales claires : « Hier Ici — Redonner vie à la mémoire des lieux ».
   - Boutons d'appel à l'action immédiats : « 🗺️ Explorer la Carte Interactive » et « 📖 Découvrir les Récits Scrollytelling ».
   - Grille de 3 piliers d'innovation :
     1. 📸 **Géoréférencement de Précision** : Prise de vue calibrée avec azimut et cône de vision métrique dynamique.
     2. 🗺️ **Exploration Cartographique 3D** : Fonds d'archives comparés au territoire contemporain.
     3. 🎧 **Récits Immersifs & Archives Sonores** : Scrollytelling interactif et témoignages audio d'époque.
   - Galerie interactive mettant en scène les 3 clichés d'archives avec fiches de découverte.
2. **Intégration dans `frontend/src/App.vue` :**
   - Ajout de l'onglet « 🏠 Accueil » dans la barre de navigation principale (mobile et desktop).
   - Prise en charge du routage d'état par URL (`?tab=accueil` ou sans paramètre par défaut).
   - Conservation des redirections automatiques si un lien direct `?photo=<uuid>` ou `?storymap=<slug>` est utilisé.

## Boundaries & Constraints

**Always:**
- Accessibilité et responsive design optimal sur smartphone, tablette et écran large.
- Rendu rapide et fluide avec images optimisées et lazy-loading natif.
- Respect rigoureux des mentions de licences et de sources (Gallica BnF / Bibliothèque nationale de France).

**Never:**
- Pas de blocage ou de redirection forcée si un visiteur partage un lien direct vers une photo ou une storymap.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Visiteur arrivant sur `/` | URL sans paramètre de requête | Affichage par défaut de la page d'accueil de présentation | Aucun |
| Clic sur « Explorer la Carte » | Clic bouton CTA | Bascule sur l'onglet `decouverte` et centrage carte | Sauvegarde état URL |
| Clic sur « Découvrir les Récits » | Clic bouton CTA | Bascule sur le catalogue public des storymaps | Sauvegarde état URL |
| Visite avec `?photo=<uuid>` | URL avec paramètre photo | Bascule automatique sur l'onglet `decouverte` avec volet ouvert | Fallback accueil si photo introuvable |

</frozen-after-approval>

## Code Map

- `frontend/public/images/landing/` -- Images d'archives historiques (`viaduc-pecheur.jpg`, `place-marche-boeufs.jpg`, `theatre-boeufs.jpg`).
- `frontend/src/components/public/HomePresentationView.vue` -- Composant de vitrine patrimoniale.
- `frontend/src/App.vue` -- Intégration de l'onglet Accueil et gestion du routage par défaut.
- `frontend/tests/home_presentation.test.mjs` -- Tests unitaires frontend.

## Tasks & Acceptance

**Execution:**
- [x] Créer `frontend/src/components/public/HomePresentationView.vue`.
- [x] Intégrer l'onglet dans `frontend/src/App.vue` avec les actions CTA.
- [x] Écrire les tests unitaires `frontend/tests/home_presentation.test.mjs`.
- [x] Vérifier la compilation TypeScript (`vue-tsc -b`) et exécuter la suite de tests.
- [x] BMAD Review Loop (Blind Hunter, Edge Case Hunter, Verification Gap Reviewer).

