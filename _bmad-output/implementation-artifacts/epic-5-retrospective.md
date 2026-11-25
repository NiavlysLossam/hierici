# Rétrospective Epic 5 : Personnalisation Cartographique, Administration Générale & Vitrine Patrimoniale

**Date :** 5 novembre 2026  
**Projet :** HierIci (Patrimoine photographique & cartographie interactive)  
**Méthodologie :** BMAD (Spécification formelle -> TDD -> Boucle de revue 3 agents -> Clôture de sprint)  
**Statut Global :** ✅ **EPIC 5 ACCEPTÉ ET DÉPLOYÉ EN LOCAL**

---

## 1. Synthèse des Stories Livrées

L'Epic 5 concrétise l'ensemble des retours fonctionnels et esthétiques demandés sur la plateforme :

### Story 5.1 — Révision du Modèle de Métadonnées Photo & Cône Métrique
- **Allègement des métadonnées :** Suppression des champs superflus « époque / période » et « date précise ».
- **Précision historique :** Ajout du booléen `is_exact_year` (formatage automatique « Année » si exact, « Vers Année » si estimé).
- **Aide à la saisie :** Route `GET /api/v1/admin/photos/metadata-suggestions` et sélecteurs de tags/suggestions pour les institutions d'archives et les photographes.
- **Portée optique paramétrable :** Ajout du paramètre métrique `view_distance` (20 m à 2 000 m) avec curseur interactif dans le sélecteur d'azimut et projection géodésique conforme en WebGL.

### Story 5.2 — Optimisation de l'Exploration Cartographique (Découverte)
- **Visibilité renforcée :** Marqueurs de prise de vue agrandis (canevas 64x64, rayon 18px, bordure blanche 3px, ombre portée) pour un repérage immédiat.
- **Volet latéral d'inspection :** Remplacement des anciennes popups cartographiques encombrantes par un panneau coulissant à droite (`PhotoDetailDrawer.vue`), fluide, responsive et non bloquant.
- **Allègement de l'interface :** Suppression du compteur et du libellé de territoire en haut à droite pour laisser toute la place à la lecture cartographique.
- **Cône dynamique :** Projection en direct du cône de vue orienté avec respect de la distance métrique personnalisée `view_distance` de chaque cliché.

### Story 5.3 — Console d'Administration Générale
- **Cadrage territorial par défaut :** Saisie des coordonnées de centrage (latitude, longitude, zoom) avec prévisualisation cartographique et bouton de capture en un clic du point de vue actuel.
- **Gestion des contributeurs :** Liste, création de compte, activation/désactivation de statut, réinitialisation de mot de passe et suppression sécurisée (verrouillage contre l'auto-désactivation et protection stricte des superadmins).
- **Fonds cartographiques multi-sources :** Prise en charge des flux XYZ Raster, WMS, WMTS et Tuiles Vecteurs MapLibre avec sélection du fond par défaut et test de flux.

### Story 5.4 — Vitrine Patrimoniale & Page de Présentation
- **Accueil immersif :** Page d'accueil dédiée illustrée par les 3 photographies d'époque Gallica BnF fournies par l'utilisateur (Viaduc fluvial avec pêcheur, Place du marché avec attelages de bœufs, Façade du théâtre municipal).
- **Piliers d'innovation :** Présentation claire du géoréférencement orienté, des fonds comparatifs et des récits scrollytelling sonores.
- **Routage d'état URL unifié :** Module `navigationState.ts` gérant la persistance et le nettoyage contextuel des paramètres lors du basculement d'onglets (accueil, découverte, récits, studio).

---

## 2. Preuves de Vérification & Métriques Qualité

| Domaine | Outil / Suite | Résultat |
| :--- | :--- | :--- |
| **Backend API** | Pytest (Dockerisé) | **79 tests passés** (0 échec, 100% vert) |
| **Frontend Logic** | Node Test Runner / loader ESM | **76 tests unitaires passés** across all components |
| **Typage TypeScript** | `vue-tsc -b` | **0 erreur** de compilation |
| **Conteneurs Docker** | Docker Compose (`backend`, `db`, `frontend`) | Tous conteneurs **Up & Healthy** |
| **Serveur Web Local** | Nginx / Vite (`http://localhost:5173`) | **HTTP 200 OK**, images landing servies en 200 OK |

---

## 3. Revue BMAD 3-Agents (Points Clés Résolus)

Pour chaque story, la boucle de revue BMAD a mobilisé trois profils complémentaires :
1. **Blind Hunter Reviewer :** A débusqué le blocage silencieux en plein écran sur retour navigateur (`activeStorymapSlug` non nettoyé), corrigé l'affordance des cartes photos et les contrastes WCAG AA.
2. **Edge Case Hunter Reviewer :** A identifié la persistance parasite du paramètre `?photo=` lors du changement d'onglet et la réinitialisation de l'état `popstate`.
3. **Verification Gap Reviewer :** A neutralisé la tautologie de mock sur le routage d'état URL en extrayant le module de production `navigationState.ts` et en étendant la couverture bi-canal (desktop et mobile).

---

## 4. Décision & Clôture

L'ensemble des objectifs de l'Epic 5 est **validé, documenté et opérationnel**. La démo locale est immédiatement accessible sur `http://localhost:5173`.

