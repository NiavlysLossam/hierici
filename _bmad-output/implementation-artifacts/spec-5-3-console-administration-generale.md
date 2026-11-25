---
title: "Story 5.3: Console d'Administration Générale (Territoire, Contributeurs & Fonds de Carte)"
type: 'feature'
created: '2026-11-05'
status: 'done'
baseline_commit: '025975fc867c678d89e182e1caf5ffed1408636c'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-hierici-2026-10-31/ARCHITECTURE-SPINE.md'
  - '_bmad-output/implementation-artifacts/epic-5-context.md'
  - 'backend/app/models/territory.py'
  - 'backend/app/models/user.py'
  - 'backend/app/api/v1/admin/territory.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:**
L'administrateur de territoire ou le superadministrateur doit disposer d'une interface d'administration générale centralisée pour :
1. Configurer le centrage initial par défaut de la carte (latitude, longitude, zoom) spécifique à son territoire avec prévisualisation interactive et possibilité de capturer le cadrage courant de la carte.
2. Gérer les comptes des contributeurs de son territoire (lister les utilisateurs, inviter/créer un contributeur avec mot de passe initial, modifier nom/rôle, activer ou désactiver un compte, réinitialiser le mot de passe).
3. Administrer les fonds de carte disponibles (WMS / WMTS, tuiles vecteurs, XYZ raster OSM/IGN/Esri), en définir un par défaut et en ajouter de nouveaux.

**Approach:**
1. **Modèle & Persistance :**
   - Mise à jour du modèle `Territory` avec la colonne `basemaps` (`JSONB`, default `[]`).
   - Schémas Pydantic `BasemapConfig`, `TerritoryBase`, `TerritoryUpdate`, `TerritoryRead`.
   - Schémas Pydantic `UserCreate`, `UserUpdate`, `UserRead`.
2. **API Backend :**
   - `GET /api/v1/admin/territory` : Renvoie les informations du territoire actif (cadrage, nom, fonds de carte).
   - `PATCH /api/v1/admin/territory` : Met à jour le centrage (`center_lat`, `center_lng`, `default_zoom`), le nom et les fonds de carte.
   - `GET /api/v1/admin/users` : Liste les utilisateurs du territoire avec filtrage / isolation multi-tenant stricte.
   - `POST /api/v1/admin/users` : Crée un nouvel utilisateur contributeur pour le territoire.
   - `PATCH /api/v1/admin/users/{user_id}` : Modifie le statut actif, le rôle ou le mot de passe.
   - `DELETE /api/v1/admin/users/{user_id}` : Désactive ou supprime un compte avec protection anti-auto-suppression.
3. **Frontend :**
   - Vue `frontend/src/components/admin/GeneralAdminView.vue` organisée en 3 onglets / sections claires :
     - 🎯 **Cadrage Cartographique du Territoire** : curseurs/inputs de latitude, longitude, zoom par défaut, mini-carte interactive MapLibre avec bouton « 📸 Capturer la vue actuelle » et bouton d'enregistrement.
     - 👥 **Gestion des Contributeurs** : liste tabulaire avec badge rôle, statut actif/inactif, bouton d'ajout de contributeur (modal création) et actions (activer/désactiver, réinitialiser mot de passe).
     - 🗺️ **Fonds de Carte Disponibles** : liste des fonds (OSM, Orthophoto IGN/Esri, etc.), types (XYZ, WMS, WMTS, Vecteur), bascule de fond par défaut, bouton d'ajout/suppression de source.
   - Navigation intégrée dans `App.vue` pour les utilisateurs authentifiés.

## Boundaries & Constraints

**Always:**
- Isolation territoriale stricte : un administrateur ne peut gérer que les utilisateurs de son propre territoire (ou tous si Superadmin).
- Un administrateur ne peut pas désactiver ou supprimer son propre compte (garde de sécurité).
- Validation rigoureuse des coordonnées géographiques (-90 <= lat <= 90, -180 <= lng <= 180, 1 <= zoom <= 22).
- Mots de passe hashés de manière sécurisée (Argon2 / bcrypt via passlib).

**Never:**
- Jamais de mot de passe en clair stocké ou renvoyé dans les schémas de lecture `UserRead`.
- Jamais de modification de territoire croisé non autorisé (HTTP 403 Forbidden).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Modification cadrage | `center_lat: 43.12, center_lng: 5.93, default_zoom: 14` | Territoire mis à jour, 200 OK | 422 si coordonnées hors bornes |
| Création contributeur | `email: "user@domain.com", password: "...", full_name: "Jean"` | Utilisateur créé rattaché au territoire, 201 Created | 400 si email déjà existant |
| Auto-désactivation | Utilisateur tente de désactiver son propre compte | Action refusée avec message d'erreur | 400 Bad Request |
| Ajout fond de carte | `name: "Ortho IGN", type: "xyz", url: "https://..."` | Ajouté dans le tableau `basemaps` du territoire | 422 si URL invalide |

</frozen-after-approval>

## Code Map

- `backend/app/models/territory.py` -- Ajout du champ `basemaps`.
- `backend/app/schemas/territory.py` -- Définition de `BasemapConfig` et enrichissement de `TerritoryRead`/`TerritoryUpdate`.
- `backend/app/schemas/user.py` -- Définition de `UserUpdate`.
- `backend/app/api/v1/admin/territory.py` -- Nouveaux endpoints d'administration générale (territoire, fonds de carte, contributeurs).
- `frontend/src/components/admin/GeneralAdminView.vue` -- Interface d'administration générale avec 3 sections.
- `frontend/src/App.vue` -- Bouton d'accès dans la navigation administration.
- `frontend/src/services/api.ts` -- Fonctions clientes pour l'administration générale.
- `backend/tests/test_admin_general.py` -- Tests backend complets.
- `frontend/tests/general_admin.test.mjs` -- Tests unitaires frontend.

## Tasks & Acceptance

**Execution:**
- [x] Backend : Mettre à jour `Territory` et `schemas/territory.py` + `schemas/user.py`.
- [x] Backend : Créer le routeur `backend/app/api/v1/admin/territory.py` avec endpoints cadrage, fonds de carte et gestion des utilisateurs.
- [x] Backend : Écrire les tests `backend/tests/test_admin_general.py` et les valider avec pytest.
- [x] Frontend : Créer `frontend/src/components/admin/GeneralAdminView.vue`.
- [x] Frontend : Connecter le service API dans `frontend/src/services/adminApi.ts` et la navigation dans `App.vue`.
- [x] Frontend : Écrire les tests unitaires et vérifier la compilation TypeScript (`vue-tsc -b`).
- [x] BMAD Review Loop (Blind Hunter, Edge Case Hunter, Verification Gap Reviewer) complétée et sécurisée.

